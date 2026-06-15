from astroquery.simbad import Simbad


def get_basic_metadata(target_name: str):
    custom = Simbad()
    custom.add_votable_fields("otype", "flux(V)", "flux(B)", "flux(R)")

    result = custom.query_object(target_name)

    if result is None or len(result) == 0:
        return {
            "object_type": "unknown",
            "mag_v": "unknown",
            "mag_b": "unknown",
            "mag_r": "unknown",
        }

    row = result[0]

    def clean(value):
        if value is None:
            return "unknown"
        text = str(value)
        if text in ("--", "nan", "None"):
            return "unknown"
        return text

    return {
        "object_type": clean(row.get("otype", "unknown")),
        "mag_v": clean(row.get("FLUX_V", "unknown")),
        "mag_b": clean(row.get("FLUX_B", "unknown")),
        "mag_r": clean(row.get("FLUX_R", "unknown")),
    }
