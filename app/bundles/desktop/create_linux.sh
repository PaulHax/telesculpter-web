#!/bin/bash

CURRENT_DIR=`dirname "$0"`

python -m PyInstaller \
    --clean --noconfirm \
    --hidden-import kwiver.vital.plugins \
    --hidden-import numpy \
    --hidden-import pkgutil \
    --collect-data trame_quasar \
    --collect-data trame_rca \
    --collect-data trame_client \
    --collect-data burn_out \
    --collect-data kwiver \
    "$CURRENT_DIR/burn-out.py"
