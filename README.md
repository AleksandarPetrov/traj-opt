# Optimizing multi-rendezvous spacecraft trajectories: ∆V matrices and sequence selection

Code for the experiments.

## Installation

This code uses ephemeris data and Lambert targeting from [pyKEP](https://github.com/esa/pykep) so pyKEP needs to be installed. Also required are: [pygmo](https://github.com/esa/pagmo2) [pathos](https://github.com/uqfoundation/pathos) and [pyYAML](https://github.com/yaml/pyyaml):

```
pip3 install pygmo pathos pyYAML pykep
```

A Docker container with everything neccessary installed is also provided at `aleksandarpetrov/traj-opt`.


## Getting Started

Running an experiment consists of:
1. Generating ∆V matrices with the `batch_Lambert_sampling.py` script, e.g.:
```
python3 batch_Lambert_sampling.py --dt 80 --njobs 8 --output data/DV_20obj_dt80_raw --objects 20
```

2. Applying wait-adjustment to the generated matrices with the `wait_adjusting.py` script, e.g.:
```
python3 wait_adjusting.py --njobs 8 --input data/DV_20obj_dt80_raw --output data/DV_20obj_dt80_wa
```

3. Computing sequences of 5 objects via direct concatenation with the `main.py` script, e.g.:
```
python3 main.py --njobs 8 --input data/DV_20obj_dt80_wa --output data/DV_20obj_dt80_dced --dvtol 10000 --objects 20 --results data/20obj_dt80_results.yml --inmemory true
```

All this can be run in the provided Docker container by using the provided `run_all.sh` as a template. Note that you'd need to have Docker installed to be able to use it.

## Authors

* Aleksandar Petrov

## License

Contact the authors
