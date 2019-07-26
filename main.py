import numpy as np
import itertools
import time
import os
import datetime
# from pathos.pools import _ThreadPool
from multiprocessing import Process, Manager, Value, Queue, Event, Array
import queue as q
from direct_concatenation import direct_concatenation

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
args = parser.parse_args()

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
# lock = manager.Lock()
SD = dict()
taskQueue = Queue(maxsize=POOL_LIMIT_TASKS)
updateQueue = Queue()
stopEvent = Event()
SD['CURR_MIN'] = Value('f', np.inf)
SD['CURR_MIN_SEQ'] = None
SD['input_prefix'] = input_prefix
SD['tmp_prefix'] = tmp_prefix
SD['processed_count'] = 0
SD['count_3seq_concats'] = 0
SD['count_5seq_concats'] = 0
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

SD['cache_5obj'] = dict()


# Create a 5-obj iterator
class FullSequenceIterator:
    def __init__(self, objects, seq_len=5):
        # self.simple_iterator = itertools.product(objects, repeat=seq_len)
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
        # Sample from the simple iterator until a sequence with unique entries is found
        # while True:
        #     candidate_seq = self.simple_iterator.__next__()
        #     if len(np.unique(candidate_seq)) == self.seq_len:
        #         break
        candidate_seq = self.seq_list[self.served]
        self.served+=1
        return candidate_seq


# Task definition: dict with
#   'function': 'dc_3obj' or 'dc_5obj'
#   'seq': the actual sequence to process

def dc_3obj(seq, SD, updateQueue):
    # Check if it has any chance to participate in a sequnce that reduces the current total min DV
    if SD['cache_2obj'][(seq[0], seq[1])] + SD['cache_2obj'][(seq[1], seq[2])] <= SD['CURR_MIN'].value  + SD['DV_TOLERANCE']:
        t = time.time()
        A = np.load(SD['input_prefix']+'_'.join(tuple(map(lambda x: str(x).zfill(3),seq[:2])))+'.npy')
        B = np.load(SD['input_prefix']+'_'.join(tuple(map(lambda x: str(x).zfill(3),seq[1:])))+'.npy')
        # print("LOADING TIME %.4f" % (time.time()-t))
        t = time.time()
        C = direct_concatenation(A, B)
        # print("CONCAT TIME %.4f" % (time.time()-t))
        t = time.time()
        np.save(SD['tmp_prefix']+"_".join(tuple(map(lambda x: str(x).zfill(3),seq))), C)
        # print("SAVE TIME %.4f" % (time.time()-t))
        Cmin = np.min(C.flatten())
    else:
        Cmin = np.inf

    updateQueue.put((tuple(seq), Cmin))

def dc_5obj(seq, SD, updateQueue):
    # Check if it has any chance to participate in a sequnce that reduces the current total min DV
    # print("CURR MIN: %.04f, this best shot: %.04f" %(SD['CURR_MIN'].value, SD['cache_3obj'][(seq[0], seq[1], seq[2])] + SD['cache_3obj'][(seq[2], seq[3], seq[4])]))
    if SD['cache_3obj'][(seq[0], seq[1], seq[2])] + SD['cache_3obj'][(seq[2], seq[3], seq[4])] <= SD['CURR_MIN'].value + SD['DV_TOLERANCE']:
        A = np.load(SD['tmp_prefix']+'_'.join(tuple(map(lambda x: str(x).zfill(3),seq[:3])))+'.npy')
        B = np.load(SD['tmp_prefix']+'_'.join(tuple(map(lambda x: str(x).zfill(3),seq[2:])))+'.npy')
        C = direct_concatenation(A, B)
        Cmin = np.min(C.flatten())

        # save if the the min is within DV_TOLERANCE of the current min
        if Cmin <= SD['CURR_MIN'].value + SD['DV_TOLERANCE']:
            np.save(SD['tmp_prefix']+"_".join(tuple(map(lambda x: str(x).zfill(3),seq))), C)

    else:
        Cmin = np.inf

    updateQueue.put((tuple(seq), Cmin))

def worker_thread(taskQueue, updateQueue, SD, stopEvent):
    # Continuously check if there are new tasks and process them if there are
    # After finishing adding tasks stopEvent would be set, continue processing until
    # the queue is empty
    while not (stopEvent.is_set() and taskQueue.empty()):
        try:
            task = taskQueue.get(block=True, timeout=1)

            t=time.time()
            if task['function'] == 'dc_3obj':
                dc_3obj(task['seq'], SD, updateQueue)
            elif task['function'] == 'dc_5obj':
                dc_5obj(task['seq'], SD, updateQueue)
            else:
                raise Exception("Unknown task function: %s" % task['function'])
            # print("task processing time: %.06f" % (time.time()-t))
        except q.Empty:
            pass

def processUpdateQueue():
    try:
        while True:
            seq, Cmin = updateQueue.get_nowait()
            if len(seq)==3:
                SD['cache_3obj'][seq] = Cmin
                if Cmin<np.inf:
                    SD['count_3seq_concats'] += 1

            elif len(seq)==5:
                SD['cache_5obj'][seq] = Cmin
                if Cmin<np.inf:
                    SD['count_5seq_concats'] += 1
                if Cmin < SD['CURR_MIN'].value:
                    SD['CURR_MIN'].value = Cmin
                    SD['CURR_MIN_SEQ'] = seq
                SD['processed_count'] += 1

            # print("Processed: %s, min DV=%.02f" % (str(seq), Cmin))
    except q.Empty:
        pass

# Start the worker threads
workers = list()
for _ in range(N_THREADS):
    workers.append(Process(target=worker_thread, args=(taskQueue, updateQueue, SD, stopEvent)))
    workers[-1].start()

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

        # Add new tasks until we fill the task queue capacity
        marked_for_removal = list()
        for onhold_idx in np.random.choice(np.arange(len(onhold_list)), size=len(onhold_list), replace=False):

            # Continuously check if anything is processed and needs to be updated in the caches:
            processUpdateQueue()

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

            # print("Adding %s to the pool" % str(sequence))
            taskQueue.put({'function':'dc_5obj', 'seq':sequence}, block=True)
            marked_for_removal.append(sequence)

        for s in marked_for_removal: onhold_list.remove(s)

        if time.time()-last_report_time > 10.0:
            last_report_time=time.time()
            digits = int(np.ceil(np.log10(iter.limit)))
            remaining_time = (time.time() - time_start) * (iter.limit-SD['processed_count']) / max(SD['processed_count'],1) / 60.0
            cmDV = SD['CURR_MIN'].value
            timestamp = '{date:%H:%M:%S}'.format(date=datetime.datetime.now())
            print(f"{timestamp}> "+
                  f"ACT CON 3: {SD['count_3seq_concats']:{digits}d} | " +
                  f"ACT CON 5: {SD['count_5seq_concats']:{digits}d} | " +
                  f"FULL SEQ: {SD['processed_count']:{digits}d} / {iter.limit} | " +
                  f"MIN DV: {cmDV:8.1f} | REM: {remaining_time:5.2f} [MIN]")

except KeyboardInterrupt:
    print("\nSIGINT DETECTED! CLOSING THREADS AND SAVING DATA!\n")
# Wait for the threads to finish
stopEvent.set()
for p in workers:
    p.join()
# Record the last results
processUpdateQueue()

print("FINISHED all %d/%d sequences!" % (SD['processed_count'], iter.limit))
print("MIN DV: ", SD['CURR_MIN'].value)
print("MIN DV SEQ: ", SD['CURR_MIN_SEQ'])
print("Actual concatenations (3obj)", SD['count_3seq_concats'])
print("Actual concatenations (5obj)", SD['count_5seq_concats'])

# Save the data

# Prune the cache_5obj by removing all entries with inf values
marked_for_removal = list()
for k,v in SD['cache_5obj'].items():
    if np.isinf(v): marked_for_removal.append(k)
for k in marked_for_removal: SD['cache_5obj'].pop(k)

sorted_sequences = dict(sorted(SD['cache_5obj'].items(), key=lambda k: k[1]))

# filename = 'results_{date:%Y-%m-%d_%H:%M:%S}.yml'.format(date=datetime.datetime.now())
filename = args.results
with open(filename, 'w') as outfile:
    for seq,val in sorted_sequences.items():
        outfile.write(str(seq) + ": " + str(val) + "\n")
print("Results saved to: %s" % filename)
