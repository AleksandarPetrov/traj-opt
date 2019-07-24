import numpy as np
import os
import glob
from pathos.multiprocessing import ProcessingPool

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--input', help='input folder')
parser.add_argument('--output', help='output folder')
parser.add_argument('--njobs', help='number of threads')
args = parser.parse_args()

input_folder = args.input
output_folder = args.output

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

matrix_files = list()
for file in glob.glob(input_folder+"/*.npy"):
    matrix_files.append(file)

def wait_adjust(M):
    """Wait-adjusting by rows"""
    d = M.shape[0]
    h = M.shape[1]

    for row_to_update in range(1, d):
        M[row_to_update,0:h-1] = np.minimum(M[row_to_update,0:h-1], M[row_to_update-1,1:h])

    return M

def full_process(filename):
    M = np.load(filename)
    M = wait_adjust(M)
    np.save(output_folder+"/"+filename.split('/')[-1], M)

p = ProcessingPool(int(args.njobs))
p.map(full_process, matrix_files)
