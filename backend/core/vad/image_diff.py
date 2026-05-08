"""
Visual Diff Engine
====================
Compares two screenshots (expected vs actual) and highlights the differences.
Useful for visual regression testing and post-test verification.
"""

from __future__ import annotations

import base64
import io
from typing import Dict, Any, Tuple

from PIL import Image, ImageChops, ImageDraw
import numpy as np


class VisualDiffEngine:
    """
    Compares two images and generates a diff image with differences highlighted.
    """

    def __init__(self, tolerance: int = 15):
        self.tolerance = tolerance

    def compare_base64(self, expected_b64: str, actual_b64: str) -> Dict[str, Any]:
        """Compares two base64 encoded images."""
        img1 = self._decode_base64(expected_b64)
        img2 = self._decode_base64(actual_b64)
        return self.compare(img1, img2)

    def compare_files(self, expected_path: str, actual_path: str) -> Dict[str, Any]:
        """Compares two images from file paths."""
        img1 = Image.open(expected_path).convert("RGB")
        img2 = Image.open(actual_path).convert("RGB")
        return self.compare(img1, img2)

    def compare(self, img1: Image.Image, img2: Image.Image) -> Dict[str, Any]:
        """
        Compare two PIL Images.
        Returns a dictionary with match percentage and the base64 of the diff image.
        """
        # Ensure images are the same size
        if img1.size != img2.size:
            # Resize the actual image to match the expected image for comparison
            # In a real scenario, different sizes might mean a critical failure
            img2 = img2.resize(img1.size, Image.LANCZOS)

        # Calculate pixel-by-pixel difference
        diff = ImageChops.difference(img1, img2)
        diff_array = np.array(diff)
        
        # Calculate grayscale difference magnitude
        # Use maximum difference across RGB channels
        diff_magnitude = np.max(diff_array, axis=2)
        
        # Create a mask of significant differences (above tolerance)
        mask = diff_magnitude > self.tolerance
        
        # Calculate mismatch percentage
        total_pixels = img1.width * img1.height
        mismatch_pixels = np.sum(mask)
        mismatch_ratio = float(mismatch_pixels) / total_pixels
        match_percentage = max(0.0, 100.0 - (mismatch_ratio * 100.0))

        # Create the diff visualization
        # Start with a grayscale version of the expected image (faded)
        diff_vis = img1.convert("L").convert("RGB")
        vis_array = np.array(diff_vis)
        
        # Fade the background
        vis_array = (vis_array * 0.5).astype(np.uint8)
        
        # Highlight differences in bright red
        vis_array[mask] = [255, 0, 0]
        
        diff_img = Image.fromarray(vis_array)

        return {
            "match_percentage": round(match_percentage, 2),
            "mismatch_pixels": int(mismatch_pixels),
            "total_pixels": total_pixels,
            "is_match": match_percentage >= 99.0, # Accept 1% antialiasing/rendering difference
            "diff_image_base64": self._encode_base64(diff_img)
        }

    def _decode_base64(self, b64_str: str) -> Image.Image:
        raw = b64_str
        if "," in raw:
            raw = raw.split(",", 1)[1]
        image_bytes = base64.b64decode(raw)
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")

    def _encode_base64(self, img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
