python -m PyInstaller ^
  --windowed ^
  --hidden-import pkgutil ^
  --hidden-import numpy ^
  --hidden-import pkgutil ^
  --collect-data trame_quasar ^
  --collect-data trame_rca ^
  --collect-data trame_client ^
  --collect-data burn_out ^
  --additional-hooks-dir="." ^
  .\burn-out.py
