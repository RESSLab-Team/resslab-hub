"""
SEM image processing primitives, refactored from ductile-fracture/SEM/process_SEM.py.

Pure numpy / opencv / skimage; no plotting or notebook integration.
"""
from typing import List, Tuple

import cv2
import numpy as np
import skimage.morphology

# Default parameters from process_SEM.py for the Skiadopoulos dataset.
DEFAULT_F_SIZE = 9
DEFAULT_CLAHE_SIZE = 5
DEFAULT_THRES = 50
DEFAULT_OPENING_SIZE = 10
# Pixel rows below this are the SEM legend strip and are cropped out before analysis.
DEFAULT_CROP_BOTTOM = 688


def find_contour_radius(
    binary_img: np.ndarray,
) -> Tuple[List[np.ndarray], List[float], List[float]]:
    """Return external contours of a binary image plus their areas and
    equivalent radii."""
    contours, _ = cv2.findContours(binary_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    areas: List[float] = []
    radii: List[float] = []
    for c in contours:
        a = cv2.contourArea(c)
        areas.append(a)
        radii.append(float(np.sqrt(a / np.pi)))
    return list(contours), areas, radii


def process_sem(
    img: np.ndarray,
    f_size: int = DEFAULT_F_SIZE,
    clahe_size: int = DEFAULT_CLAHE_SIZE,
    thres: int = DEFAULT_THRES,
    opening_size: int = DEFAULT_OPENING_SIZE,
) -> Tuple[List[float], List[float]]:
    """
    Segment voids ("dimples") in a SEM image and return their pixel areas and radii.

    Pipeline: median filter → CLAHE → threshold → morphological opening →
    contour extraction.
    Caller must convert pixel radius to physical units using the image's pixel size.
    """
    f_img = cv2.medianBlur(img, f_size)
    clahe = cv2.createCLAHE(tileGridSize=(clahe_size, clahe_size))
    cl_img = clahe.apply(f_img)
    o_img = skimage.morphology.opening(
        cl_img < thres, skimage.morphology.disk(opening_size), out=None
    )
    _, areas, radii = find_contour_radius(np.array(o_img, np.uint8))
    return areas, radii


def crop_legend(img: np.ndarray, crop_bottom: int = DEFAULT_CROP_BOTTOM) -> np.ndarray:
    """Drop the bottom legend strip baked into raw SEM TIFs."""
    return img[:crop_bottom, :]
