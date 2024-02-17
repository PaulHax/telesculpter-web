# Build instructions 

The following scripts operate under the current directory.

Other requirements:
- Your trame Python 3.8 virtual-environment need to be activated
- Python dev library available for kwiver to build

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
