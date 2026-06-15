from skybox.providers.panstarrs import download_ps1_fits
from skybox.providers.panstarrs_atlas import download_ps1_atlas_fits


ATLAS_FIELDS = {"atlas", "survey", "grand"}
NATIVE_FIELDS = {"core", "field", "wide", "tight", "normal"}


def fetch_fits_cutout(target, survey, field_preset: str, cache_dir: str):
    if survey.provider != "panstarrs":
        raise RuntimeError(f"No provider implemented for {survey.provider!r}.")

    field_preset = field_preset.strip().lower()

    if field_preset in ATLAS_FIELDS:
        return download_ps1_atlas_fits(
            target=target,
            survey=survey,
            field_preset=field_preset,
            cache_dir=cache_dir,
        )

    if survey.key == "blend":
        raise RuntimeError(
            "Blend mode uses the Pan-STARRS colour HiPS layer. "
            "Use field preset: atlas or survey."
        )

    if field_preset in NATIVE_FIELDS:
        return download_ps1_fits(
            target=target,
            survey=survey,
            field_preset=field_preset,
            cache_dir=cache_dir,
        )

    raise RuntimeError(
        "Unknown field preset. Use core, field, wide, atlas, or survey."
    )
