import numpy as np
import itertools
import time
import os
import datetime
# from pathos.pools import _ThreadPool
from multiprocessing import Process, Manager, Value, Queue, Event, Array
import queue as q
from direct_concatenation import direct_concatenation
import copy
import ctypes

# Fix the random seed for realative reproducibility
np.random.seed(17)

# Process arguments
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input', help='input folder')
parser.add_argument('--output', help='output folder')
parser.add_argument('--njobs', help='number of threads')
parser.add_argument('--dvtol', help='best DV tolerance')
parser.add_argument('--objects', help='number of objects')
parser.add_argument('--results', help='results filename')
parser.add_argument('--inmemory', type=bool, default=False, help='whether to keep sequences of 3 in memory')
args = parser.parse_args()

if args.inmemory:
    print("In-memory storage of 3-sequences enabled")

# Configuration
input_prefix = args.input+'/'
tmp_prefix = args.output+'/'
objects = np.arange(96,96+int(args.objects))
N_THREADS = int(args.njobs)
POOL_LIMIT_TASKS = N_THREADS * 10
DV_TOLERANCE = float(args.dvtol)  #Will make sure to have the sequences that cannot improve the min, but can come this close

# Make the tmp folder if doesn't exist
if not os.path.exists(tmp_prefix):
    os.makedirs(tmp_prefix)

# Initialize variables to share between the subprocesses.
manager = Manager()
SD = dict()
taskQueue = Queue(maxsize=POOL_LIMIT_TASKS)
updateQueue = Queue()
stopEvent = Event()
SD['CURR_MIN'] = Value('f', np.inf)
SD['CURR_MIN_SEQ'] = Array(ctypes.c_ulong, 5)
SD['input_prefix'] = input_prefix
SD['tmp_prefix'] = tmp_prefix
SD['processed_count'] = Value('i', 0)
SD['count_3seq_concats'] = Value('i', 0)
SD['count_5seq_concats'] = Value('i', 0)
SD['DV_TOLERANCE'] = DV_TOLERANCE


# Initialize DV caches
print('Initializing the 2 object cache')
cache_2obj = dict()
for i in objects:
    for j in objects:
        if len(np.unique([i,j]))==2:
            tmp_matrix = np.load(input_prefix+"%s_%s.npy"%(str(i).zfill(3), str(j).zfill(3)))
            cache_2obj[(i, j)] = np.min(tmp_matrix)

SD['cache_2obj'] = manager.dict(cache_2obj)

print('Initializing the 3 object cache')
cache_3obj = dict()
for i in objects:
    for j in objects:
        for k in objects:
            if len(np.unique([i,j,k]))==3:
                cache_3obj[(i, j, k)] = -2

SD['cache_3obj'] = manager.dict(cache_3obj)
SD['cache_3obj_storage'] = manager.dict()
SD['cache_5obj'] = manager.dict()


# Create a 5-obj iterator
class FullSequenceIterator:
    def __init__(self, objects, seq_len=5):
        self.seq_list = list()
        for seq in itertools.product(objects, repeat=seq_len):
            if len(np.unique(seq)) == seq_len: self.seq_list.append(seq)
        np.random.shuffle(self.seq_list)
        self.objects = objects
        self.seq_len = seq_len

        self.limit = 1
        for i in range(seq_len): self.limit*=len(objects)-i
        self.served = 0


    def __iter__(self):
        return self

    def __next__(self):
        candidate_seq = self.seq_list[self.served]
        self.served+=1
        return candidate_seq


# Task definition: dict with
#   'function': 'dc_3obj' or 'dc_5obj'
#   'seq': the actual sequence to process

def dc_3obj(seq, SD, updateQueue):
    # Check if it has any chance to participate in a sequnce that reduces the current total min DV
    if SD['cache_2obj'][(seq[0], seq[1])] + SD['cache_2obj'][(seq[1], seq[2])] <= SD['CURR_MIN'].value  + SD['DV_TOLERANCE']:
        A = np.load(SD['input_prefix']+'_'.join(tuple(map(lambda x: str(x).zfill(3),seq[:2])))+'.npy')
        B = np.load(SD['input_prefix']+'_'.join(tuple(map(lambda x: str(x).zfill(3),seq[1:])))+'.npy')
        C = direct_concatenation(A, B)
        np.save(SD['tmp_prefix']+"_".join(tuple(map(lambda x: str(x).zfill(3),seq))), C)
        Cmin = np.min(C.flatten())
    else:
        Cmin = np.inf
        C = None

    updateQueue.put((tuple(seq), Cmin, C))

def dc_5obj(seq, SD, updateQueue):
    # Check if it has any chance to participate in a sequnce that reduces the current total min DV
    # print("CURR MIN: %.04f, this best shot: %.04f" %(SD['CURR_MIN'].value, SD['cache_3obj'][(seq[0], seq[1], seq[2])] + SD['cache_3obj'][(seq[2], seq[3], seq[4])]))
    if SD['cache_3obj'][(seq[0], seq[1], seq[2])] + SD['cache_3obj'][(seq[2], seq[3], seq[4])] <= SD['CURR_MIN'].value + SD['DV_TOLERANCE']:
        try:
            A = SD['cache_3obj_storage'][(seq[0], seq[1], seq[2])]
            B = SD['cache_3obj_storage'][(seq[2], seq[3], seq[4])]
        except KeyError:
            A = np.load(SD['tmp_prefix']+'_'.join(tuple(map(lambda x: str(x).zfill(3),seq[:3])))+'.npy')
            B = np.load(SD['tmp_prefix']+'_'.join(tuple(map(lambda x: str(x).zfill(3),seq[2:])))+'.npy')
        C = direct_concatenation(A, B)
        Cmin = np.min(C.flatten())

        # save if the the min is within DV_TOLERANCE of the current min
        if Cmin <= SD['CURR_MIN'].value + SD['DV_TOLERANCE']:
            np.save(SD['tmp_prefix']+"_".join(tuple(map(lambda x: str(x).zfill(3),seq))), C)

    else:
        Cmin = np.inf

    updateQueue.put((tuple(seq), Cmin, None))

def worker_thread(taskQueue, updateQueue, SD, stopEvent):
    # Continuously check if there are new tasks and process them if there are
    # After finishing adding tasks stopEvent would be set, continue processing until
    # the queue is empty
    while not stopEvent.is_set():
        try:
            task = taskQueue.get(block=True, timeout=1)

            t=time.time()
            if task['function'] == 'dc_3obj':
                dc_3obj(task['seq'], SD, updateQueue)
            elif task['function'] == 'dc_5obj':
                dc_5obj(task['seq'], SD, updateQueue)
            else:
                raise Exception("Unknown task function: %s" % task['function'])
        except q.Empty:
            pass

def update_thread(updateQueue, SD, stopEvent):
    while not stopEvent.is_set():
        try:
            seq, Cmin, C = updateQueue.get(block=True, timeout=1)
            if args.inmemory and len(seq) == 3:
                SD['cache_3obj_storage'][tuple(seq)] = copy.deepcopy(C)
            if len(seq)==3:
                SD['cache_3obj'][seq] = Cmin
                if Cmin<np.inf:
                    SD['count_3seq_concats'].value = SD['count_3seq_concats'].value + 1

            elif len(seq)==5:
                SD['cache_5obj'][seq] = Cmin
                if Cmin<np.inf:
                    SD['count_5seq_concats'].value = SD['count_5seq_concats'].value + 1
                if Cmin < SD['CURR_MIN'].value:
                    SD['CURR_MIN'].value = Cmin
                    for idx in range(len(seq)): SD['CURR_MIN_SEQ'][idx] = seq[idx]
                SD['processed_count'].value = SD['processed_count'].value + 1
        except q.Empty:
            pass

# Start the worker threads
workers = list()
for _ in range(N_THREADS):
    workers.append(Process(target=worker_thread, args=(taskQueue, updateQueue, SD, stopEvent)))
    workers[-1].start()

# Start the update thread
updater = Process(target=update_thread, args=(updateQueue, SD, stopEvent))
updater.start()

# Start the main processes
total_count = len(objects)*(len(objects)-1)*(len(objects)-2)*(len(objects)-3)*(len(objects)-4)
iter = FullSequenceIterator(objects)

onhold_list = list()
last_report_time = 0.0
time_start = time.time()

# Gracefully handle premature SIGINTs
try:
    while len(onhold_list) > 0 or iter.served < iter.limit:

        # First fill in the on_hold list if neccessary and possible
        while iter.served < iter.limit and len(onhold_list) < 50:
            onhold_list.append(iter.__next__())

        # Wait to make sure that the updateQueue is (approximately) fully processed:
        while updateQueue.qsize() > 100:
            time.sleep(0.1)

        # Add new tasks until we fill the task queue capacity
        marked_for_removal = list()
        for onhold_idx in np.random.choice(np.arange(len(onhold_list)), size=len(onhold_list), replace=False):

            # if not taskQueue.full():
            sequence = onhold_list[onhold_idx]
            # Check if both 3-sequences are computed already (cache_3obj > 0). If they are not,
            # add them to the processing queue (if cache_3obj==-2). If they are already there (cache_3obj==-1)
            # do nothing. If they are processed already, remove the full sequence from the on-hold
            # list and add it to the processing queue.

            if SD['cache_3obj'][(sequence[0], sequence[1], sequence[2])] == -1:
                continue
            elif SD['cache_3obj'][(sequence[0], sequence[1], sequence[2])] == -2:
                seq = [sequence[0], sequence[1], sequence[2]]
                SD['cache_3obj'][tuple(seq)] = -1

                taskQueue.put({'function':'dc_3obj', 'seq':seq}, block=True)
                continue

            if SD['cache_3obj'][(sequence[2], sequence[3], sequence[4])] == -1:
                continue
            elif SD['cache_3obj'][(sequence[2], sequence[3], sequence[4])] == -2:
                seq = [sequence[2], sequence[3], sequence[4]]
                SD['cache_3obj'][tuple(seq)] = -1

                taskQueue.put({'function':'dc_3obj', 'seq':seq}, block=True)
                continue

            taskQueue.put({'function':'dc_5obj', 'seq':sequence}, block=True)
            marked_for_removal.append(sequence)

        for s in marked_for_removal: onhold_list.remove(s)

        if time.time()-last_report_time > 10.0:
            last_report_time=time.time()
            digits = int(np.ceil(np.log10(iter.limit)))
            remaining_time = (time.time() - time_start) * (iter.limit-SD['processed_count'].value) / max(SD['processed_count'].value,1) / 60.0
            cmDV = SD['CURR_MIN'].value
            cnt3 = SD['count_3seq_concats'].value
            cnt5 = SD['count_5seq_concats'].value
            cntProcessed = SD['processed_count'].value
            timestamp = '{date:%H:%M:%S}'.format(date=datetime.datetime.now())
            print(f"{timestamp}> "+
                  f"ACT CON 3: {cnt3:{digits}d} | " +
                  f"ACT CON 5: {cnt5:{digits}d} | " +
                  f"FULL SEQ: {cntProcessed:{digits}d} / {iter.limit} | " +
                  f"MIN DV: {cmDV:8.1f} | REM: {remaining_time:5.2f} [MIN]")

except KeyboardInterrupt:
    print("\nSIGINT DETECTED! CLOSING THREADS AND SAVING DATA!\n")

# Wait for the threads to finish
while SD['processed_count'].value < iter.limit:
    time.sleep(1)
    print("Waiting for the jobs to finish")

# Ensure that the last jobs have time to finish
time.sleep(10)
stopEvent.set()
print("stopEvent set")
for p in workers:
    p.join()
updater.join()
print("Threads joined")

# Print the results
print("Update Queue processed")
print("FINISHED all %d/%d sequences!" % (SD['processed_count'].value, iter.limit))
print("MIN DV: ", SD['CURR_MIN'].value)
print("MIN DV SEQ: ", SD['CURR_MIN_SEQ'][:])
print("Actual concatenations (3obj)", SD['count_3seq_concats'].value)
print("Actual concatenations (5obj)", SD['count_5seq_concats'].value)

# Save the data

# Prune the cache_5obj by removing all entries with inf values
marked_for_removal = list()
for k,v in SD['cache_5obj'].items():
    if np.isinf(v): marked_for_removal.append(k)
for k in marked_for_removal: SD['cache_5obj'].pop(k)

sorted_sequences = dict(sorted(SD['cache_5obj'].items(), key=lambda k: k[1]))

filename = args.results
with open(filename, 'w') as outfile:
    for seq,val in sorted_sequences.items():
        outfile.write(str(seq) + ": " + str(val) + "\n")
print("Results saved to: %s" % filename)
