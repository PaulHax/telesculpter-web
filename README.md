# Burnout Web

## Install

With Python 3.8

```
python -m venv .venv
# Linux
.venv/bin/activate
# Windows
.venv\Scripts\Activate.ps1

cd app
pip install -e .
```

Download wheel for Linux or Windows
https://gitlab.kitware.com/kwiver/kwiver/-/packages/442

```
# with trame app venv active
pip install kwiver_*.whl
burn-out --use-tk
```
