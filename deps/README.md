# Build instructions 
The following scripts operate under the current directory
```
bash install_fletch.sh
bash install_kwiver.sh
```
To use the cli version of dump-klv:
```
source kwiver/ci-venv/bin/activate
source kwiver/build/setup_KWIVER.sh
python kwiver/build/bin/dump_klv.py kwiver/src/test_data/videos/aphill_klv_10s.ts
```
