import numpy as np

from pathos.multiprocessing import ProcessingPool
from sample_Lambert import process_single_pair

dt = 10 # descretization step, in days
output_prefix = 'DVmatrices_gtoc2gr2/'

range_departure_date = (dt, 10000) # in MJD2000
range_transfer_duration = (dt, 1000 ) # in days

departure_dates = np.arange(start=range_departure_date[0], stop=range_departure_date[1]+1e-5, step=dt)
transfer_durations = np.arange(start=range_transfer_duration[0], stop=range_transfer_duration[1]+1e-5, step=dt)

def full_process(obj_idx_tuple):
    print(obj_idx_tuple)
    id_start = int(obj_idx_tuple[0])
    id_end = int(obj_idx_tuple[1])


    DV_matrix = process_single_pair(id_start=id_start, id_end=id_end,
                                    departure_dates=departure_dates,
                                    transfer_durations=transfer_durations,
                                    dt=dt)
    np.save(output_prefix+str(id_start).zfill(3)+'_'+str(id_end).zfill(3), DV_matrix)

# gtoc2gr2_objects = np.arange(96,271+1)
gtoc2gr2_objects = np.arange(96,96+20)
all_pairs = list()
for i in gtoc2gr2_objects:
    for j in gtoc2gr2_objects:
        if i != j:
            all_pairs.append((i,j))

p = ProcessingPool(4)
p.map(full_process, all_pairs)
