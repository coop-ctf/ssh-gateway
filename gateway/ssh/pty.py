from dataclasses import dataclass


@dataclass
class PtyDimensions:
    width: int
    height: int
    width_pixels: int
    height_pixels: int
