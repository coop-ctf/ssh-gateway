from dataclasses import dataclass


@dataclass
class PtyDimensions:
    term: str
    width: int
    height: int
    width_pixels: int
    height_pixels: int
