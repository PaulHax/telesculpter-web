python -m PyInstaller ^
  --windowed ^
  --hidden-import pkgutil ^
  --hidden-import kwiver.vital.plugins ^
  --hidden-import numpy ^
  --hidden-import pkgutil ^
  --collect-data trame_quasar ^
  --collect-data trame_rca ^
  --collect-data trame_client ^
  --collect-data burn_out ^
  --collect-data kwiver ^
  .\burn-out.py
