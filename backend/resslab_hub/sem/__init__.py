"""
SEM images of the ductile-fracture coupons: conversion and CDN upload.

``artifacts`` turns a folder of TIFs into WebPs, dimple JSONs and a manifest,
all in memory. ``cdn`` writes them to a folder or uploads them to the EPFL
enacit4r-cdn. ``process_sem`` is the lab's measurement algorithm.

Used today by ``data/precompute_sem.py`` (the maintainer script, run through
``make precompute-sem``), and by the submission pipeline when it takes images.
The heavy dependencies (OpenCV, scikit-image, Pillow, exifread) live in the
``sem`` dependency group, so nothing in the running app may import this package
until that group moves into the image. See docs/src/sem-images.md.
"""
