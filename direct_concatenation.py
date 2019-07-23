import numpy as np
import itertools

import time

def direct_concatenation(A, B):
    t=time.time()
    assert(A.shape == B.shape)

    d = A.shape[0]
    h = A.shape[1]
    C = np.zeros_like(A)

    t=time.time()
    for i in range(1,d+1):
        for j in range(1,h+1):
            ks = np.arange(1,min(h-j, i-1)+1)
            if len(ks) == 0:
                C[i-1, j-1] = np.inf
            else:
                C[i-1, j-1] = min(A[ks-1, j-1] + B[i-ks-1, j+ks-1])
    return C

def direct_concatenation_tracked(A,B):
    pass


def direct_concatenation_pooled(A, B, pool):
    assert(A.shape == B.shape)

    d = A.shape[0]
    h = A.shape[1]
    C = np.zeros_like(A)

    def subprocess(coordinates):
        i=coordinates[0]+1
        j=coordinates[1]+1
        ks = np.arange(1,min(h-j, i-1)+1)
        if len(ks) == 0:
            Cij = np.inf
        else:
            Cij = min(A[ks-1, j-1] + B[i-ks-1, j+ks-1])
        return Cij

    results = pool.map(subprocess, itertools.product(range(d), range(h)))
    C = np.array(results).reshape(A.shape)

    return C


if __name__ == '__main__':

    from plot_matrix import plot_matrix
    import time
    from pathos.multiprocessing import ProcessingPool

    dt = 10 # descretization step, in days

    range_departure_date = (dt, 10000) # in MJD2000
    range_transfer_duration = (dt, 1000 ) # in days

    departure_dates = np.arange(start=range_departure_date[0], stop=range_departure_date[1]+1e-5, step=dt)
    transfer_durations = np.arange(start=range_transfer_duration[0], stop=range_transfer_duration[1]+1e-5, step=dt)

    output_prefix = 'DVmatrices_gtoc2gr2_20_wait_adjusted/'
    filenameA='100_111'
    filenameB='111_112'

    A = np.load(output_prefix+filenameA+'.npy')
    B = np.load(output_prefix+filenameB+'.npy')
    # DC simple
    t = time.time()
    C_single = direct_concatenation(A, B)
    print("Single thread processing time: %.02f sec" % (time.time()-t))

    # DC multiprocessing
    pool = ProcessingPool(8)
    t = time.time()
    C = direct_concatenation_pooled(A, B, pool)
    print("Multi-thread processing time: %.02f sec" % (time.time()-t))
    assert(np.all(C==C_single))

    plot_matrix(A, departure_dates, transfer_durations, output_name="dc_test_A.png")
    plot_matrix(B, departure_dates, transfer_durations, output_name="dc_test_B.png")
    plot_matrix(C, departure_dates, transfer_durations, output_name="dc_test_C.png")
