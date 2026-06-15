from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class Survey:
    key: str
    label: str
    wavelength: str
    provider: str
    ps1_filter: Optional[str]
    ps1_filters: Tuple[str, ...]
    default_fov_deg: float


SURVEYS = {
    "short": Survey(
        key="short",
        label="Pan-STARRS short",
        wavelength="short optical / g band",
        provider="panstarrs",
        ps1_filter="g",
        ps1_filters=("g",),
        default_fov_deg=0.25,
    ),
    "mid": Survey(
        key="mid",
        label="Pan-STARRS mid",
        wavelength="mid optical / i band",
        provider="panstarrs",
        ps1_filter="i",
        ps1_filters=("i",),
        default_fov_deg=0.25,
    ),
    "long": Survey(
        key="long",
        label="Pan-STARRS long",
        wavelength="long optical / y band",
        provider="panstarrs",
        ps1_filter="y",
        ps1_filters=("y",),
        default_fov_deg=0.25,
    ),
    "blend": Survey(
        key="blend",
        label="Pan-STARRS blend",
        wavelength="g+i+y composite luminance",
        provider="panstarrs",
        ps1_filter=None,
        ps1_filters=("g", "i", "y"),
        default_fov_deg=0.25,
    ),
}


ASCII_WIDTH = 100
ASCII_HEIGHT = 50
CACHE_FITS_DIR = "cache/fits"
CACHE_METADATA_DIR = "cache/metadata"
