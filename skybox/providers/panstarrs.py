from dataclasses import dataclass
from pathlib import Path
import re

import requests


PS1_FILENAMES_URL = "https://ps1images.stsci.edu/cgi-bin/ps1filenames.py"
PS1_FITSCUT_URL = "https://ps1images.stsci.edu/cgi-bin/fitscut.cgi"

PS1_PIXEL_SCALE_ARCSEC = 0.25

FIELD_PRESETS = {
    "core": 900,
    "field": 2400,
    "wide": 6000,
}

LEGACY_FIELD_NAMES = {
    "tight": "core",
    "normal": "field",
}


@dataclass
class FetchResult:
    path: Path
    requested_field: str
    actual_fov_deg: float
    size_px: int
    note: str = ""


def normalise_field_name(field_preset: str) -> str:
    field_preset = field_preset.strip().lower()
    return LEGACY_FIELD_NAMES.get(field_preset, field_preset)


def safe_filename(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def preset_to_pixels(field_preset: str) -> tuple[int, float]:
    field_preset = normalise_field_name(field_preset)

    if field_preset not in FIELD_PRESETS:
        allowed = ", ".join(FIELD_PRESETS.keys())
        raise ValueError(f"Unknown native field preset {field_preset!r}. Use: {allowed}")

    size_px = FIELD_PRESETS[field_preset]
    actual_fov_deg = (size_px * PS1_PIXEL_SCALE_ARCSEC) / 3600.0

    return size_px, actual_fov_deg


def parse_filename_table(text: str, wanted_filter: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if len(lines) < 2:
        raise RuntimeError("Pan-STARRS filename service returned no image rows.")

    header = lines[0].split()
    rows = lines[1:]

    try:
        filter_index = header.index("filter")
        filename_index = header.index("filename")
    except ValueError as exc:
        raise RuntimeError(
            "Could not parse Pan-STARRS filename table header: " + lines[0]
        ) from exc

    for row in rows:
        parts = row.split()

        if len(parts) <= max(filter_index, filename_index):
            continue

        if parts[filter_index] == wanted_filter:
            return parts[filename_index]

    raise RuntimeError(f"No Pan-STARRS image found for filter {wanted_filter!r}.")


def get_ps1_filename(ra_deg: float, dec_deg: float, ps1_filter: str, size_px: int) -> str:
    params = {
        "ra": ra_deg,
        "dec": dec_deg,
        "size": size_px,
        "format": "text",
        "filters": ps1_filter,
    }

    response = requests.get(PS1_FILENAMES_URL, params=params, timeout=60)
    response.raise_for_status()

    return parse_filename_table(response.text, ps1_filter)


def download_ps1_fits(
    target,
    survey,
    field_preset: str,
    cache_dir: str,
) -> FetchResult:
    field_preset = normalise_field_name(field_preset)

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    size_px, actual_fov_deg = preset_to_pixels(field_preset)

    filename = (
        f"{safe_filename(target.name)}_"
        f"ps1_{survey.ps1_filter}_"
        f"{field_preset}_"
        f"{size_px}px_"
        f"{actual_fov_deg:.3f}deg.fits"
    )

    output_path = cache_path / filename

    if output_path.exists():
        return FetchResult(
            path=output_path,
            requested_field=field_preset,
            actual_fov_deg=actual_fov_deg,
            size_px=size_px,
            note="cache",
        )

    ps1_filename = get_ps1_filename(
        ra_deg=target.ra_deg,
        dec_deg=target.dec_deg,
        ps1_filter=survey.ps1_filter,
        size_px=size_px,
    )

    params = {
        "ra": target.ra_deg,
        "dec": target.dec_deg,
        "size": size_px,
        "format": "fits",
        "red": ps1_filename,
    }

    response = requests.get(PS1_FITSCUT_URL, params=params, timeout=120)

    if response.status_code != 200:
        raise RuntimeError(
            f"Pan-STARRS FITS cutout failed with status {response.status_code}: "
            f"{response.text[:300]}"
        )

    if not response.content.startswith(b"SIMPLE"):
        raise RuntimeError(
            "Pan-STARRS did not return a FITS file. "
            f"Response began with: {response.content[:120]!r}"
        )

    output_path.write_bytes(response.content)

    return FetchResult(
        path=output_path,
        requested_field=field_preset,
        actual_fov_deg=actual_fov_deg,
        size_px=size_px,
        note="MAST PS1 native FITS",
    )
