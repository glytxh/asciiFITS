from astropy.coordinates import SkyCoord
import astropy.units as u
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from skybox.version import APP_NAME, APP_VERSION, APP_CODENAME

from skybox.config import SURVEYS


FRAME_WIDTH = 100
PANEL_WIDTH = 104

console = Console(width=PANEL_WIDTH, soft_wrap=False)


def heavy_box_line(left, fill, right, width=FRAME_WIDTH):
    return left + (fill * width) + right


def show_title():
    import select
    import sys
    import termios
    import time
    import tty

    # Warm restrained palette.
    accent = "rgb(214,157,82)"
    accent_dim = "rgb(150,103,61)"
    bone = "rgb(230,221,199)"
    eye_red = "rgb(210,64,48)"

    def append_icon_row(panel_text, row, style):
        panel_text.append("  ", style=style)

        for char in row:
            if char in {"O", "○", "◉", "◎"}:
                panel_text.append(char, style=f"bold {eye_red}")
            else:
                panel_text.append(char, style=style)

        panel_text.append("  ", style=style)

    def build_panel(icon):
        title = Text()
        title.append("\n")
        title.append("  ███████╗██╗  ██╗██╗   ██╗██████╗  ██████╗ ██╗  ██╗\n", style=f"bold {accent}")
        title.append("  ██╔════╝██║ ██╔╝╚██╗ ██╔╝██╔══██╗██╔═══██╗╚██╗██╔╝\n", style=f"bold {accent}")
        title.append("  ███████╗█████╔╝  ╚████╔╝ ██████╔╝██║   ██║ ╚███╔╝ \n", style=f"bold {accent}")
        title.append("  ╚════██║██╔═██╗   ╚██╔╝  ██╔══██╗██║   ██║ ██╔██╗ \n", style=f"bold {accent}")
        title.append("  ███████║██║  ██╗   ██║   ██████╔╝╚██████╔╝██╔╝ ██╗\n", style=f"bold {accent}")
        title.append("  ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═════╝  ╚═════╝ ╚═╝  ╚═╝\n", style=f"bold {accent}")

        panel_text = Text()
        panel_text.append("\n")

        append_icon_row(panel_text, icon[0], f"bold {bone}")
        panel_text.append("SKY SURVEY TERMINAL", style=f"bold {accent_dim}")
        panel_text.append("\n")

        append_icon_row(panel_text, icon[1], f"bold {accent}")
        panel_text.append("Pan-STARRS / FITS / ASCII", style="dim")
        panel_text.append("\n")

        append_icon_row(panel_text, icon[2], f"bold {bone}")
        panel_text.append("archive cutout instrument", style="dim")
        panel_text.append("\n")

        panel_text.append(title)
        panel_text.append("\n")
        panel_text.append(f"  {APP_NAME} v{APP_VERSION} · {APP_CODENAME}", style=f"bold {bone}")
        panel_text.append("\n")
        panel_text.append("  Pan-STARRS terminal FITS viewer", style=f"bold {bone}")
        panel_text.append("\n")
        panel_text.append("  Object name or ICRS coordinates → FITS cutout → rich ASCII skybox", style="dim")
        panel_text.append("\n\n")
        panel_text.append("  DATA  ", style=f"bold {accent}")
        panel_text.append("Pan-STARRS DR1 · MAST PS1 · CDS HiPS · SIMBAD", style=bone)
        panel_text.append("\n")
        panel_text.append("  CACHE ", style=f"bold {accent}")
        panel_text.append("keeps newest five FITS files", style=bone)
        panel_text.append("\n")
        panel_text.append("  START ", style=f"bold {accent}")
        panel_text.append("press any key to skip scan", style="dim")

        return Panel(
            panel_text,
            border_style=accent,
            padding=(0, 1),
            width=PANEL_WIDTH,
        )

    normal_frames = [
        ["┌·┐", "·O·", "└·┘"],
        ["┌─┐", "·O·", "└─┘"],
        ["┌·┐", "─O─", "└·┘"],
        ["┌─┐", "·O·", "└─┘"],
    ]

    glance_left = ["┌·┐", "O··", "└·┘"]
    glance_right = ["┌·┐", "··O", "└·┘"]

    def key_pressed():
        readable, _, _ = select.select([sys.stdin], [], [], 0)
        if readable:
            sys.stdin.read(1)
            return True
        return False

    old_settings = None

    try:
        if sys.stdin.isatty():
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin)

        for loop_index in range(1, 5):
            if loop_index == 3:
                glance_icon = glance_left
            elif loop_index == 4:
                glance_icon = glance_right
            else:
                glance_icon = None

            for frame_index, icon in enumerate(normal_frames):
                if glance_icon is not None and frame_index in {1, 2}:
                    icon = glance_icon

                console.clear()
                console.print(build_panel(icon))
                try:
                    console.file.flush()
                except Exception:
                    pass

                # Wait in tiny slices so keypress reacts quickly.
                wait_until = time.time() + 0.22
                while time.time() < wait_until:
                    if key_pressed():
                        raise KeyboardInterrupt
                    time.sleep(0.02)

    except KeyboardInterrupt:
        pass

    finally:
        if old_settings is not None:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    # Leave final normal frame on screen for the actual input prompt.
    console.clear()
    console.print(build_panel(normal_frames[0]))
    try:
        console.file.flush()
    except Exception:
        pass


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


def show_ascii_frame(lines):
    border_top = heavy_box_line("╔", "═", "╗")
    border_bottom = heavy_box_line("╚", "═", "╝")

    console.print(Text(border_top))

    for line in lines[:50]:
        safe_line = crop_or_pad_text_line(line, FRAME_WIDTH)

        framed = Text("║")
        framed.append(safe_line)
        framed.append("║")

        console.print(framed, overflow="crop", crop=True, soft_wrap=False)

    if len(lines) < 50:
        for _ in range(50 - len(lines)):
            console.print(Text("║" + (" " * FRAME_WIDTH) + "║"))

    console.print(Text(border_bottom))


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


def show_ascii_frame_with_overlay(lines, overlay_lines=None, overlay_x=3, overlay_y=3):
    """
    Draw ASCII image frame with an optional metadata card stamped
    into the image area.

    This version preserves original Rich colour styling outside:
    - the metadata card
    - the small one-cell drop shadow
    """
    working = [crop_or_pad_text_line(line, FRAME_WIDTH) for line in lines]

    def stamp_segment(row_index, x_start, segment_text, style):
        """
        Replace a short segment in one Rich Text row while preserving
        all styling before and after the segment.
        """
        if not (0 <= row_index < len(working)):
            return

        if x_start >= FRAME_WIDTH:
            return

        segment_text = segment_text[: max(0, FRAME_WIDTH - x_start)]
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

        working[row_index] = crop_or_pad_text_line(new_line, FRAME_WIDTH)

    if overlay_lines:
        card_h = len(overlay_lines)
        card_w = max(len(line) for line in overlay_lines)

        shadow_style = "white on grey7"

        # Right-hand shadow: a thin vertical offset edge.
        for i in range(card_h):
            y = overlay_y + i + 1
            x = overlay_x + card_w
            stamp_segment(y, x, "  ", shadow_style)

        # Lower shadow: a thin horizontal offset edge.
        y = overlay_y + card_h
        x = overlay_x + 2
        stamp_segment(y, x, " " * max(0, card_w - 1), shadow_style)

        # Main metadata card.
        for i, overlay_line in enumerate(overlay_lines):
            y = overlay_y + i
            fragment = overlay_line[: max(0, FRAME_WIDTH - overlay_x)]
            stamp_segment(y, overlay_x, fragment, "bold white on grey11")

    console.print(Text("╔" + ("═" * FRAME_WIDTH) + "╗", style="bold cyan"))
    for line in working:
        console.print(Text("║", style="bold cyan") + line + Text("║", style="bold cyan"))
    console.print(Text("╚" + ("═" * FRAME_WIDTH) + "╝", style="bold cyan"))


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
    """
    Compact help card for the image viewer.
    """
    return [
        "┌──────────────────────────────────────────────┐",
        "│ SKYBOX HELP                                  │",
        "├──────────────────────────────────────────────┤",
        "│ z  zoom: 1x → 2x → 3x                       │",
        "│ b  brightness: low / med / bright           │",
        "│ c  contrast: soft / med / hard              │",
        "│ m  metadata overlay                         │",
        "│ h  hide/show this help                      │",
        "│ n  new target                               │",
        "│ q  quit                                     │",
        "├──────────────────────────────────────────────┤",
        "│ Type one letter, then press Enter.           │",
        "└──────────────────────────────────────────────┘",
    ]


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
