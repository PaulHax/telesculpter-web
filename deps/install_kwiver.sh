#!/usr/bin/env bash

set -e

readonly kwiver_repo="https://gitlab.kitware.com/kwiver/kwiver.git"
readonly kwiver_commit="89715ee4def77d3b2df97e6fc0a6f21473bc5dd8"

readonly work_dir="$PWD"

readonly kwiver_root="$work_dir/kwiver"
readonly kwiver_src="$kwiver_root/src"
readonly kwiver_build="$kwiver_root/build"
readonly kwiver_prefix="$work_dir/opt/kwiver"

if [ ! -d "$kwiver_src" ]; 
then
  git clone "$kwiver_repo" "$kwiver_src"
fi
git -C "$kwiver_src" checkout "$kwiver_commit"

# make sure trame venv is activated
if [ -z "${VIRTUAL_ENV}" ]
then
  echo "Virtual environment should be enabled"
  exit 1
fi
pip install -r "$kwiver_src/.gitlab/ci/requirements_dev.txt"


export CMAKE_PREFIX_PATH="$work_dir/opt/fletch"
cmake \
  -B "$kwiver_build" \
  -GNinja \
  -Dfletch_ENABLED_Eigen=ON \
  -DKWIVER_ENABLE_C_BINDINGS=ON \
  -DKWIVER_ENABLE_PYTHON=ON \
  -DKWIVER_ENABLE_TOOLS=ON \
  -DKWIVER_ENABLE_TESTS=ON \
  -DKWIVER_ENABLE_PYTHON_TESTS=ON\
  -DKWIVER_ENABLE_ARROWS=ON \
  -DKWIVER_ENABLE_DBOW2=OFF \
  -DKWIVER_ENABLE_FFMPEG=ON \
  -DKWIVER_ENABLE_KLV=ON \
  -DKWIVER_ENABLE_MVG=ON \
  -DKWIVER_ENABLE_ZLIB=ON \
  -DKWIVER_ENABLE_GDAL=OFF \
  -DKWIVER_ENABLE_OPENCV=ON \
  -DKWIVER_ENABLE_PDAL=OFF \
  -DKWIVER_ENABLE_PROJ=OFF \
  -DKWIVER_ENABLE_SERIALIZE_JSON=ON \
  -S "$kwiver_src"
cmake --build "$kwiver_build"
