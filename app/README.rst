===========================================================
Burn Out
===========================================================

BurnOut is a cross-platform desktop application for analyzing metadata
in video files.  In particular BurnOut can read both KLV metadata streams
and parse metadata "burned" into the pixels of the video.  BurnOut can
extract the metadata to various file formats and also mask out or in-paint
the burned in metadata in the video to remove it.


Installing
-----------------------------------------------------------

Install the application

.. code-block:: console
    # optional, activate a venv
    python3.8 -m venv .venv && source .venv/bin/activate
    pip install -e .

Temporary: install the kwiver wheel from ci artifacts of https://gitlab.kitware.com/kwiver/kwiver

Run the application

.. code-block:: console

    burn-out

    burn-out --hot-reload

    burn-out --server --use-tk --data ../videos/09172008flight1tape3_2.mpg