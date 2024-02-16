#!/usr/bin/sh

set -e

readonly fletch_repo="https://github.com/Kitware/fletch"
# use commit from master
readonly fletch_commit="f0d9628661bfdff9e7961454d1ef887dab03b9c3"

readonly work_dir="$PWD"

readonly fletch_root="$work_dir/fletch"
readonly fletch_src="$fletch_root/src"
readonly fletch_build="$fletch_root/build"
readonly fletch_prefix="$work_dir/opt/fletch"

git clone "$fletch_repo" "$fletch_src"
git -C "$fletch_src" checkout "$fletch_commit"

# enable if we want pre-merged PRs
#git -C "$fletch_src" config user.name "kwiver Developers"
#git -C "$fletch_src" config user.email "kwiver-developers@kitware.com"
#
## Fix rpath for tiff, gtest, proj, and sqlite
## https://github.com/Kitware/fletch/pull/743
#git -C "$fletch_src" fetch origin refs/pull/743/head
#git -C "$fletch_src" merge --no-ff FETCH_HEAD

cmake \
  -B "$fletch_build" \
  "-Dfletch_BUILD_INSTALL_PREFIX=$fletch_prefix" \
  -Dfletch_BUILD_WITH_PYTHON=ON \
  -Dfletch_BUILD_WITH_CX11=ON \
  -Dfletch_ENABLE_Eigen=ON \
  -Dfletch_ENABLE_pybind11=ON \
  -Dpybind11_SELECT_VERSION="2.10.3" \
  -Dfletch_ENABLE_FFmpeg=ON \
  -Dfletch_ENABLE_GTest=ON \
  -Dfletch_ENABLE_OpenCV=ON \
  -Dfletch_ENABLE_PDAL=OFF \
  -Dfletch_ENABLE_GDAL=OFF \
  -Dfletch_ENABLE_PROJ=OFF \
  -Dfletch_ENABLE_libjpeg-turbo=OFF \
  -Dfletch_ENABLE_libgeotiff=OFF \
  -Dfletch_ENABLE_libtiff=OFF \
  -Dfletch_ENABLE_GEOS=OFF \
  -Dfletch_ENABLE_SQLite3=OFF \
  -Dfletch_ENABLE_x264=OFF \
  -Dfletch_ENABLE_x265=OFF \
  -S "$fletch_src"
cmake --build "$fletch_build" --parallel "$(nproc)"

# Clean up.
rm -rf "$fletch_root"
