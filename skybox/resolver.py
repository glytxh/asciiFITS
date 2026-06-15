from dataclasses import dataclass

from astropy.coordinates import SkyCoord
import astropy.units as u
from astroquery.simbad import Simbad


@dataclass
class Target:
    name: str
    ra_deg: float
    dec_deg: float
    source: str


def looks_like_decimal_coords(text: str) -> bool:
    parts = text.replace(",", " ").split()
    if len(parts) != 2:
        return False

    try:
        float(parts[0])
        float(parts[1])
        return True
    except ValueError:
        return False


def looks_like_sexagesimal_coords(text: str) -> bool:
    parts = text.replace(",", " ").split()
    return len(parts) == 6


def resolve_manual_decimal(query: str) -> Target:
    ra_txt, dec_txt = query.replace(",", " ").split()

    coord = SkyCoord(
        float(ra_txt) * u.deg,
        float(dec_txt) * u.deg,
        frame="icrs",
    )

    return Target(
        name=query,
        ra_deg=float(coord.ra.deg),
        dec_deg=float(coord.dec.deg),
        source="manual decimal coordinates",
    )


def resolve_manual_sexagesimal(query: str) -> Target:
    parts = query.replace(",", " ").split()

    ra_text = " ".join(parts[0:3])
    dec_text = " ".join(parts[3:6])

    coord = SkyCoord(
        ra_text,
        dec_text,
        unit=(u.hourangle, u.deg),
        frame="icrs",
    )

    return Target(
        name=query,
        ra_deg=float(coord.ra.deg),
        dec_deg=float(coord.dec.deg),
        source="manual sexagesimal coordinates",
    )


def parse_simbad_coord(ra_value, dec_value):
    """
    Astroquery/SIMBAD versions differ.

    Some return RA/Dec as sexagesimal strings.
    Some return RA/Dec as decimal degrees.

    This parser handles both.
    """
    ra_text = str(ra_value).strip()
    dec_text = str(dec_value).strip()

    # Decimal-degree SIMBAD case.
    try:
        ra_float = float(ra_text)
        dec_float = float(dec_text)

        coord = SkyCoord(
            ra_float * u.deg,
            dec_float * u.deg,
            frame="icrs",
        )

        return coord

    except ValueError:
        pass

    # Sexagesimal SIMBAD case.
    coord = SkyCoord(
        ra_text,
        dec_text,
        unit=(u.hourangle, u.deg),
        frame="icrs",
    )

    return coord


def resolve_target(query: str) -> Target:
    query = query.strip()

    if looks_like_decimal_coords(query):
        return resolve_manual_decimal(query)

    if looks_like_sexagesimal_coords(query):
        return resolve_manual_sexagesimal(query)

    result = Simbad.query_object(query)

    if result is None or len(result) == 0:
        raise ValueError(f'Could not resolve target "{query}" through SIMBAD.')

    row = result[0]

    ra_value = row["ra"]
    dec_value = row["dec"]

    coord = parse_simbad_coord(ra_value, dec_value)

    return Target(
        name=query,
        ra_deg=float(coord.ra.deg),
        dec_deg=float(coord.dec.deg),
        source="SIMBAD",
    )
