echo "SAMPLING THE DV MATRICES FOR DT 80"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/batch_Lambert_sampling.py --dt 80 --njobs 16 --output /data/DV_20obj_dt80_raw --objects 20

echo "SAMPLING THE DV MATRICES FOR DT 40"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/batch_Lambert_sampling.py --dt 40 --njobs 16 --output /data/DV_20obj_dt40_raw --objects 20

echo "SAMPLING THE DV MATRICES FOR DT 20"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/batch_Lambert_sampling.py --dt 20 --njobs 16 --output /data/DV_20obj_dt20_raw --objects 20

echo "SAMPLING THE DV MATRICES FOR DT 10"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/batch_Lambert_sampling.py --dt 10 --njobs 16 --output /data/DV_20obj_dt10_raw --objects 20

echo "APPLYING WAIT ADJUSTMENT FOR DT 80"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/wait_adjusting.py --njobs 16 --input /data/DV_20obj_dt80_raw --output /data/DV_20obj_dt80_wa

echo "APPLYING WAIT ADJUSTMENT FOR DT 40"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/wait_adjusting.py --njobs 16 --input /data/DV_20obj_dt40_raw --output /data/DV_20obj_dt40_wa

echo "APPLYING WAIT ADJUSTMENT FOR DT 20"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/wait_adjusting.py --njobs 16 --input /data/DV_20obj_dt20_raw --output /data/DV_20obj_dt20_wa

echo "APPLYING WAIT ADJUSTMENT FOR DT 10"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/wait_adjusting.py --njobs 16 --input /data/DV_20obj_dt10_raw --output /data/DV_20obj_dt10_wa

echo "STARTING DIRECT CONCATENATION FOR DT 80"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/main.py --njobs 16 --input /data/DV_20obj_dt80_wa --output /data/DV_20obj_dt80_dced --dvtol 10000 --objects 20 --results /data/20obj_dt80_results.yml --inmemory true

echo "STARTING DIRECT CONCATENATION FOR DT 40"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/main.py --njobs 16 --input /data/DV_20obj_dt40_wa --output /data/DV_20obj_dt40_dced --dvtol 10000 --objects 20 --results /data/20obj_dt40_results.yml --inmemory true

echo "STARTING DIRECT CONCATENATION FOR DT 20"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/main.py --njobs 16 --input /data/DV_20obj_dt20_wa --output /data/DV_20obj_dt20_dced --dvtol 10000 --objects 20 --results /data/20obj_dt20_results.yml --inmemory true

echo "STARTING DIRECT CONCATENATION FOR DT 10"
docker run -it -v "$(pwd)":/data -m=20g --cpus=16 --rm aleksandarpetrov/traj-opt python3.7 /files/main.py --njobs 16 --input /data/DV_20obj_dt10_wa --output /data/DV_20obj_dt10_dced --dvtol 10000 --objects 20 --results /data/20obj_dt10_results.yml --inmemory true
