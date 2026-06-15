from dataclasses import dataclass
from pathlib import Path
import re

import requests


HIPS2FITS_URL = "https://alasky.cds.unistra.fr/hips-image-services/hips2fits"

PANSTARRS_HIPS_BY_FILTER = {
    "g": "CDS/P/PanSTARRS/DR1/g",
    "i": "CDS/P/PanSTARRS/DR1/i",
    "y": "CDS/P/PanSTARRS/DR1/y",
}

PANSTARRS_COLOR_HIPS = "CDS/P/PanSTARRS/DR1/color-z-zg-g"

ATLAS_FIELDS = {
    "atlas": {
        "fov_deg": 0.8,
        "width_px": 1200,
        "height_px": 800,
        "label": "Pan-STARRS atlas morphology field",
    },
    "survey": {
        "fov_deg": 2.4,
        "width_px": 1200,
        "height_px": 800,
        "label": "Pan-STARRS survey context field",
    },
}

LEGACY_FIELD_NAMES = {
    "grand": "survey",
}


@dataclass
class AtlasFetchResult:
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


def fetch_hips(target, hips_id: str, field: dict) -> bytes:
    params = {
        "hips": hips_id,
        "ra": target.ra_deg,
        "dec": target.dec_deg,
        "fov": field["fov_deg"],
        "width": field["width_px"],
        "height": field["height_px"],
        "projection": "TAN",
        "format": "fits",
    }

    response = requests.get(HIPS2FITS_URL, params=params, timeout=90)

    if response.status_code != 200:
        raise RuntimeError(
            f"Pan-STARRS atlas request failed with status {response.status_code}: "
            f"{response.text[:300]}"
        )

    if not response.content.startswith(b"SIMPLE"):
        raise RuntimeError(
            "Pan-STARRS atlas service did not return a FITS file. "
            f"Response began with: {response.content[:120]!r}"
        )

    return response.content


def download_ps1_atlas_fits(target, survey, field_preset: str, cache_dir: str) -> AtlasFetchResult:
    field_preset = normalise_field_name(field_preset)

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    if field_preset not in ATLAS_FIELDS:
        raise RuntimeError(f"Unknown atlas field preset: {field_preset}")

    field = ATLAS_FIELDS[field_preset]
    fov_deg = field["fov_deg"]
    width_px = field["width_px"]

    if survey.key == "blend":
        filter_label = "color"
        hips_id = PANSTARRS_COLOR_HIPS
        product_note = "Pan-STARRS DR1 colour HiPS"
    else:
        filter_label = survey.ps1_filter
        hips_id = PANSTARRS_HIPS_BY_FILTER.get(survey.ps1_filter)
        product_note = f"Pan-STARRS {survey.ps1_filter} HiPS"

    if hips_id is None:
        raise RuntimeError(f"No Pan-STARRS HiPS layer for survey {survey.key!r}")

    filename = (
        f"{safe_filename(target.name)}_"
        f"ps1_{filter_label}_"
        f"{field_preset}_"
        f"{fov_deg:.1f}deg.fits"
    )

    output_path = cache_path / filename

    if output_path.exists():
        return AtlasFetchResult(
            path=output_path,
            requested_field=field_preset,
            actual_fov_deg=fov_deg,
            size_px=width_px,
            note="cache",
        )

    output_path.write_bytes(fetch_hips(target, hips_id, field))

    return AtlasFetchResult(
        path=output_path,
        requested_field=field_preset,
        actual_fov_deg=fov_deg,
        size_px=width_px,
        note=product_note,
    )
