from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich.text import Text
from skybox.version import APP_NAME, APP_VERSION, APP_CODENAME

from skybox.config import SURVEYS


FRAME_WIDTH = 100
PANEL_WIDTH = 104

console = Console(soft_wrap=False)


def heavy_box_line(left, fill, right, width=FRAME_WIDTH):
    return left + (fill * width) + right


def show_title():
    console.clear()

    logo = [
        "███████╗██╗  ██╗██╗   ██╗██████╗  ██████╗ ██╗  ██╗",
        "██╔════╝██║ ██╔╝╚██╗ ██╔╝██╔══██╗██╔═══██╗╚██╗██╔╝",
        "███████╗█████╔╝  ╚████╔╝ ██████╔╝██║   ██║ ╚███╔╝ ",
        "╚════██║██╔═██╗   ╚██╔╝  ██╔══██╗██║   ██║ ██╔██╗ ",
        "███████║██║  ██╗   ██║   ██████╔╝╚██████╔╝██╔╝ ██╗",
        "╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═════╝  ╚═════╝ ╚═╝  ╚═╝",
    ]

    gradient = [
        "rgb(60,220,255)",
        "rgb(80,190,255)",
        "rgb(110,155,255)",
        "rgb(150,120,255)",
        "rgb(200,95,255)",
        "rgb(245,95,220)",
    ]

    body = Text()
    body.append("\n")

    for index, line in enumerate(logo):
        body.append(line, style=f"bold {gradient[index % len(gradient)]}")
        body.append("\n")

    body.append("\n")
    body.append(f"v{APP_VERSION}", style="bold rgb(235,235,245)")
    body.append(" · ", style="dim")
    body.append(APP_CODENAME, style="bold rgb(245,95,220)")
    body.append("\n\n")

    body.append("Object name", style="rgb(220,235,245)")
    body.append("  /  ", style="dim rgb(120,150,170)")
    body.append("ICRS coordinates", style="rgb(220,235,245)")
    body.append("  /  ", style="dim rgb(120,150,170)")
    body.append("catalog", style="bold rgb(95,220,255)")
    body.append("  →  ", style="dim rgb(120,150,170)")
    body.append("ASCII skybox", style="rgb(220,235,245)")
    body.append("\n")
    body.append("Type ", style="dim rgb(150,165,185)")
    body.append("c", style="bold rgb(95,220,255)")
    body.append(" or ", style="dim rgb(150,165,185)")
    body.append("catalog", style="bold rgb(95,220,255)")
    body.append(" to browse built-in targets", style="dim rgb(150,165,185)")
    body.append("\n\n")

    body.append("Bands: ", style="dim rgb(150,165,185)")
    body.append("short", style="bold rgb(60,190,255)")
    body.append(" / ", style="dim")
    body.append("mid", style="bold rgb(235,235,245)")
    body.append(" / ", style="dim")
    body.append("long", style="bold rgb(255,105,95)")
    body.append(" / ", style="dim")
    body.append("blend", style="bold rgb(245,95,220)")

    body.append("\n")

    body.append("Render: ", style="dim rgb(150,165,185)")
    body.append("basic", style="rgb(220,235,245)")
    body.append(" · ", style="dim")
    body.append("rich", style="bold rgb(95,220,255)")
    body.append(" · ", style="dim")
    body.append("block", style="bold rgb(190,120,255)")

    body.append("      ", style="dim")

    body.append("View: ", style="dim rgb(150,165,185)")
    body.append("small", style="rgb(220,235,245)")
    body.append(" · ", style="dim")
    body.append("wide", style="bold rgb(95,220,255)")
    body.append("\n")

    panel = Panel(
        Align.center(body),
        subtitle=Text("public sky-survey terminal viewer", style="dim rgb(150,165,185)"),
        border_style="rgb(80,190,255)",
        padding=(1, 4),
        width=86,
    )

    console.print()
    console.print(Align.center(panel))
    console.print()

def choose_survey():
    table = Table(
        title="Band mode",
        width=PANEL_WIDTH,
        show_lines=False,
        border_style="white",
    )

    table.add_column("Key", no_wrap=True, style="bold")
    table.add_column("Role", no_wrap=True)
    table.add_column("Data")

    for key, survey in SURVEYS.items():
        if survey.ps1_filter:
            band = f"Pan-STARRS {survey.ps1_filter}"
        else:
            band = "Pan-STARRS DR1 colour"

        table.add_row(key, survey.wavelength, band)

    console.print(table)

    console.print("[bold yellow]Note:[/bold yellow] blend mode only works with [bold]atlas[/bold] or [bold]survey[/bold] field scales.", style="dim")
    choice = console.input("\n[bold cyan]Select band[/bold cyan] [short/mid/long/blend] › ").strip().lower()

    if choice in {"q", "quit", "exit"}:
        raise KeyboardInterrupt

    if choice == "":
        choice = "blend"

    if choice not in SURVEYS:
        raise ValueError(f"Unknown band mode: {choice}")

    return SURVEYS[choice]


def choose_field_preset():
    table = Table(
        title="Field size",
        width=PANEL_WIDTH,
        show_lines=False,
        border_style="white",
    )

    table.add_column("Key", no_wrap=True, style="bold")
    table.add_column("Width", no_wrap=True)
    table.add_column("Source")
    table.add_column("Use")

    table.add_row("core", "0.062°", "native PS1 FITS", "close target / core")
    table.add_row("field", "0.167°", "native PS1 FITS", "standard object field")
    table.add_row("wide", "0.417°", "native PS1 FITS", "widest native cutout")
    table.add_row("atlas", "0.800°", "Pan-STARRS HiPS", "large-object morphology")
    table.add_row("survey", "2.400°", "Pan-STARRS HiPS", "broad context")

    console.print(table)

    console.print("[bold yellow]Note:[/bold yellow] blend requires [bold]atlas[/bold] or [bold]survey[/bold]. Use short/mid/long for core, field, or wide.", style="dim")
    choice = console.input("\n[bold cyan]Select field[/bold cyan] [core/field/wide/atlas/survey] › ").strip().lower()

    if choice in {"q", "quit", "exit"}:
        raise KeyboardInterrupt

    if choice == "":
        choice = "atlas"

    legacy = {
        "tight": "core",
        "normal": "field",
        "grand": "survey",
    }

    choice = legacy.get(choice, choice)

    if choice not in {"core", "field", "wide", "atlas", "survey"}:
        raise ValueError("Unknown field preset. Use core, field, wide, atlas, or survey.")

    return choice


def format_icrs(target):
    coord = SkyCoord(
        ra=target.ra_deg * u.deg,
        dec=target.dec_deg * u.deg,
        frame="icrs",
    )

    compact = coord.to_string(
        "hmsdms",
        sep=" ",
        precision=2,
        alwayssign=True,
        pad=True,
    )

    return {
        "compact": compact,
        "ra_deg": f"{target.ra_deg:.6f}",
        "dec_deg": f"{target.dec_deg:.6f}",
    }


def crop_or_pad_text_line(line, width):
    if isinstance(line, Text):
        plain = line.plain[:width]
        result = Text()

        for index, char in enumerate(plain):
            try:
                style = line.get_style_at_offset(console, index)
            except Exception:
                style = None
            result.append(char, style=style)

        visible_width = result.cell_len

        if visible_width < width:
            result.append(" " * (width - visible_width))

        return result

    text = str(line)[:width].ljust(width)
    return Text(text)



def show_ascii_frame(lines, frame_width=None):
    frame_width = frame_width or FRAME_WIDTH

    console.print(Text("╔" + ("═" * frame_width) + "╗", style="bold cyan"))

    for line in lines:
        safe_line = crop_or_pad_text_line(line, frame_width)
        console.print(Text("║", style="bold cyan") + safe_line + Text("║", style="bold cyan"))

    console.print(Text("╚" + ("═" * frame_width) + "╝", style="bold cyan"))

def compact_path(path):
    text = str(path)
    if len(text) <= 56:
        return text
    return "…" + text[-55:]


def clean_source_note(note):
    note = str(note)
    note = note.replace(" via CDS HiPS.", "")
    note = note.replace(" from cache.", " cache")
    return note


def show_metadata(target, survey, fetch_result, metadata):
    icrs = format_icrs(target)

    target_table = Table(show_header=False, box=None, width=49)
    target_table.add_column("Field", style="bold", no_wrap=True, width=10)
    target_table.add_column("Value", overflow="fold")

    target_table.add_row("Object", str(target.name))
    target_table.add_row("Type", str(metadata.get("object_type", "unknown")))
    target_table.add_row("ICRS", icrs["compact"])
    target_table.add_row("Degrees", f"{icrs['ra_deg']}  {icrs['dec_deg']}")

    survey_table = Table(show_header=False, box=None, width=49)
    survey_table.add_column("Field", style="bold", no_wrap=True, width=12)
    survey_table.add_column("Value", overflow="fold")

    if survey.ps1_filter:
        band_text = survey.ps1_filter
    else:
        band_text = "+".join(survey.ps1_filters)

    survey_table.add_row("Mode", survey.key)
    survey_table.add_row("Band", band_text)
    survey_table.add_row("Field", f"{fetch_result.requested_field} / {fetch_result.actual_fov_deg:.3f}°")
    survey_table.add_row("Source", clean_source_note(fetch_result.note))
    survey_table.add_row("File", compact_path(fetch_result.path))

    outer = Table.grid(expand=False)
    outer.add_column(width=51)
    outer.add_column(width=51)

    outer.add_row(
        Panel(target_table, title="Target", border_style="white", width=51),
        Panel(survey_table, title="Image", border_style="white", width=51),
    )

    console.print(outer)


def show_error(error):
    console.print(Panel(Text(str(error)), title="ERROR", border_style="red", width=PANEL_WIDTH))



def show_ascii_frame_with_overlay(lines, overlay_lines=None, overlay_x=3, overlay_y=3, frame_width=None):
    frame_width = frame_width or FRAME_WIDTH
    working = [crop_or_pad_text_line(line, frame_width) for line in lines]

    def stamp_segment(row_index, x_start, segment_text, style):
        if not (0 <= row_index < len(working)):
            return

        if x_start >= frame_width:
            return

        segment_text = segment_text[: max(0, frame_width - x_start)]
        if not segment_text:
            return

        base_text = working[row_index]
        x_end = x_start + len(segment_text)

        before = base_text[:x_start]
        after = base_text[x_end:]

        new_line = Text()
        new_line.append_text(before)
        new_line.append(segment_text, style=style)
        new_line.append_text(after)

        working[row_index] = crop_or_pad_text_line(new_line, frame_width)

    if overlay_lines:
        card_h = len(overlay_lines)
        card_w = max(len(line) for line in overlay_lines)

        shadow_style = "white on grey7"

        for i in range(card_h):
            y = overlay_y + i + 1
            x = overlay_x + card_w
            stamp_segment(y, x, "  ", shadow_style)

        y = overlay_y + card_h
        x = overlay_x + 2
        stamp_segment(y, x, " " * max(0, card_w - 1), shadow_style)

        for i, overlay_line in enumerate(overlay_lines):
            y = overlay_y + i
            fragment = overlay_line[: max(0, frame_width - overlay_x)]
            stamp_segment(y, overlay_x, fragment, "bold white on grey11")

    console.print(Text("╔" + ("═" * frame_width) + "╗", style="bold cyan"))

    for line in working:
        console.print(Text("║", style="bold cyan") + line + Text("║", style="bold cyan"))

    console.print(Text("╚" + ("═" * frame_width) + "╝", style="bold cyan"))

def metadata_overlay_lines(target, survey, fetch_result, metadata):
    """
    Compact metadata card designed to be stamped over the image.
    Does not assume a specific Target object shape.
    """
    object_type = metadata.get("object_type") or "unknown"
    file_name = fetch_result.path.name

    ra_deg = getattr(target, "ra_deg", None)
    dec_deg = getattr(target, "dec_deg", None)

    if ra_deg is None:
        ra_deg = getattr(target, "ra", None)

    if dec_deg is None:
        dec_deg = getattr(target, "dec", None)

    if ra_deg is not None and dec_deg is not None:
        coord_text = f"RA {float(ra_deg):.5f}  Dec {float(dec_deg):+.5f}"
    else:
        coord_text = "unknown"

    fov = getattr(fetch_result, "actual_fov_deg", None)
    size_px = getattr(fetch_result, "size_px", None)

    if fov is not None and size_px is not None:
        fov_text = f"{float(fov):.3f} deg · {size_px}px"
    elif fov is not None:
        fov_text = f"{float(fov):.3f} deg"
    else:
        fov_text = fetch_result.requested_field

    rows = [
        "┌──────────────────────────────────────────────┐",
        "│ SKYBOX METADATA                              │",
        "├──────────────────────────────────────────────┤",
        f"│ Object : {target.name[:35]:<35} │",
        f"│ Type   : {object_type[:35]:<35} │",
        f"│ ICRS   : {coord_text[:35]:<35} │",
        f"│ Band   : {survey.key[:35]:<35} │",
        f"│ Field  : {fetch_result.requested_field[:35]:<35} │",
        f"│ FOV    : {fov_text[:35]:<35} │",
        f"│ File   : {file_name[:35]:<35} │",
        "└──────────────────────────────────────────────┘",
    ]

    return rows



def help_overlay_lines():
    width = 38

    lines = [
        "SKYBOX HELP",
        "",
        "z zoom      b brightness",
        "c contrast  r render mode",
        "w view size m metadata",
        "k cache     n new target",
        "h help      q quit",
        "",
        "render: basic / rich / block",
        "view:   small / wide",
    ]

    return [line[:width].ljust(width) for line in lines]

def cache_overlay_lines(cache_rows):
    """
    Compact cache card for the image viewer.
    """
    rows = [
        "┌──────────────────────────────────────────────┐",
        "│ SKYBOX FITS CACHE                            │",
        "├──────────────────────────────────────────────┤",
    ]

    if not cache_rows:
        rows.append("│ Cache is empty.                              │")
    else:
        for index, item in enumerate(cache_rows, start=1):
            name = item["name"]
            size_mb = item["size_mb"]
            line = f"{index}. {name[:30]:<30} {size_mb:>5.1f}MB"
            rows.append(f"│ {line[:44]:<44} │")

    rows.extend(
        [
            "├──────────────────────────────────────────────┤",
            "│ Keeps newest 5 FITS files automatically.     │",
            "└──────────────────────────────────────────────┘",
        ]
    )

    return rows
