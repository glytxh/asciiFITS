from skybox.ascii_render import image_to_ascii
from skybox.cache import prune_fits_cache, list_fits_cache, fits_cache_size_mb, ensure_cache_dirs
from skybox.config import ASCII_HEIGHT, ASCII_WIDTH, CACHE_FITS_DIR
from skybox.fetcher import fetch_fits_cutout
from skybox.loading import loading_task
from skybox.export_png import export_view_png
from skybox.catalog import catalog_entries
from skybox.metadata import get_basic_metadata
from skybox.resolver import resolve_target
from rich.text import Text
from rich.table import Table

from skybox.ui import (
    choose_field_preset,
    choose_survey,
    console,
    show_ascii_frame,
    show_ascii_frame_with_overlay,
    show_error,
    show_metadata,
    show_title,
    metadata_overlay_lines,
    help_overlay_lines,
    cache_overlay_lines,
)


def render_profile_for_target(target_name, field_preset):
    if field_preset in {"atlas", "survey", "grand"}:
        return "atlas"

    name = target_name.lower()

    if name in {"m31", "m33", "m42", "m51", "m81", "m82", "m101"}:
        return "diffuse"

    return "point"


def cycle_value(current, values):
    index = values.index(current)
    index = (index + 1) % len(values)
    return values[index]


VIEWPORT_PRESETS = {
    "small": {
        "label": "small",
        "width": ASCII_WIDTH,
        "height": ASCII_HEIGHT,
    },
    "wide": {
        "label": "wide",
        "width": 132,
        "height": ASCII_HEIGHT,
    },
}


def viewport_preset(viewport_mode):
    return VIEWPORT_PRESETS.get(viewport_mode, VIEWPORT_PRESETS["small"])


def safe_viewport(viewport_mode):
    preset = dict(viewport_preset(viewport_mode))
    terminal_width = max(80, console.size.width)

    # The frame uses two border characters, so keep the image safely inside
    # the current terminal width. This prevents wrapping in smaller windows.
    preset["width"] = min(preset["width"], max(60, terminal_width - 4))

    return preset


WIDE_FIELD_MAP = {
    "tight": "field",
    "core": "field",
    "normal": "wide",
    "field": "wide",
    "wide": "atlas",
    "atlas": "atlas",
    "grand": "survey",
    "survey": "survey",
}


def field_for_viewport(base_field_preset, viewport_mode):
    base = (base_field_preset or "field").strip().lower()

    if viewport_mode == "wide":
        return WIDE_FIELD_MAP.get(base, "survey")

    return base


def crop_line_center(line, width):
    plain = line.plain if isinstance(line, Text) else str(line)

    if len(plain) <= width:
        return line

    start = max(0, (len(plain) - width) // 2)
    end = start + width

    if isinstance(line, Text):
        return line[start:end]

    return plain[start:end]


def crop_lines_center(lines, width):
    return [crop_line_center(line, width) for line in lines]


def choose_catalog_target():
    entries = catalog_entries()

    table = Table(
        title="SKYBOX object catalog",
        width=104,
        show_lines=False,
        border_style="white",
    )

    table.add_column("#", justify="right", no_wrap=True, style="bold")
    table.add_column("Object", no_wrap=True, style="bold cyan")
    table.add_column("Name", no_wrap=True)
    table.add_column("Group", no_wrap=True)
    table.add_column("Field note")

    for index, entry in enumerate(entries, start=1):
        table.add_row(
            str(index),
            entry["object"],
            entry["name"],
            entry["group"],
            entry["note"],
        )

    console.print()
    console.print(table)
    console.print("[dim]Pick a number, type an object name, or q to cancel.[/dim]")

    while True:
        choice = console.input("\n[bold cyan]Catalog target[/bold cyan] › ").strip()

        if choice.lower() in {"q", "quit", "exit"}:
            return None

        if choice.isdigit():
            index = int(choice)

            if 1 <= index <= len(entries):
                return entries[index - 1]["object"]

        normalised = choice.lower()

        for entry in entries:
            if normalised in {
                entry["object"].lower(),
                entry["name"].lower(),
            }:
                return entry["object"]

        console.print("[red]Unknown catalog choice. Enter a listed number, object name, or q.[/red]")


def ask_export_metadata():
    console.print()
    console.print("[bold]Export PNG[/bold]  Include metadata overlay?")
    console.print("[bold]1[/bold] yes   [bold]2[/bold] no   [bold]q[/bold] cancel", style="dim")

    while True:
        choice = console.input("[bold cyan]Metadata overlay[/bold cyan] › ").strip().lower()

        if choice in {"q", "quit", "exit"}:
            return None

        if choice in {"1", "y", "yes", "metadata", "with metadata"}:
            return True

        if choice in {"2", "n", "no", "clean", "without metadata"}:
            return False

        console.print("[red]Choose 1, 2, or q.[/red]")


class CachedFetchResult:
    def __init__(self, path, requested_field, note="cache"):
        self.path = path
        self.requested_field = requested_field
        self.actual_fov_deg = None
        self.size_px = None
        self.note = note


def cached_field_from_name(file_name):
    name = file_name.lower()

    for field in ["survey", "atlas", "wide", "field", "core"]:
        if f"_{field}_" in name or name.endswith(f"_{field}.fits"):
            return field

    if "2.4deg" in name:
        return "survey"

    if "0.8deg" in name:
        return "atlas"

    if "6000px" in name or "0.417deg" in name:
        return "wide"

    return "cache"


def cached_band_from_name(file_name, fallback):
    name = file_name.lower()

    if "_color_" in name or "_blend_" in name:
        return "blend"

    if "_g_" in name:
        return "short"

    if "_i_" in name:
        return "mid"

    if "_y_" in name:
        return "long"

    return getattr(fallback, "key", "cache")


def cached_fetch_result_from_row(row):
    file_path = row["path"]
    field = cached_field_from_name(row["name"])

    return CachedFetchResult(
        path=file_path,
        requested_field=field,
        note="cache",
    )


def cached_fits_by_number(choice):
    cache_rows = list_fits_cache(CACHE_FITS_DIR, limit=15)

    if not choice.isdigit():
        return None

    index = int(choice)

    if not (1 <= index <= len(cache_rows)):
        console.print("[red]No cached FITS with that number.[/red]")
        return None

    return cached_fetch_result_from_row(cache_rows[index - 1])


def choose_cached_fits():
    cache_rows = list_fits_cache(CACHE_FITS_DIR, limit=15)

    if not cache_rows:
        console.print("[yellow]FITS cache is empty.[/yellow]")
        return None

    table = Table(
        title="SKYBOX cache manager",
        width=104,
        show_lines=False,
        border_style="white",
    )

    table.add_column("#", justify="right", no_wrap=True, style="bold")
    table.add_column("Cached FITS", no_wrap=True, style="bold cyan")
    table.add_column("Size", justify="right", no_wrap=True)
    table.add_column("Field", no_wrap=True)
    table.add_column("Band", no_wrap=True)

    for index, row in enumerate(cache_rows, start=1):
        name = row["name"]
        table.add_row(
            str(index),
            name[:58],
            f"{row['size_mb']:.1f} MB",
            cached_field_from_name(name),
            cached_band_from_name(name, type("FallbackSurvey", (), {"key": "cache"})()),
        )

    console.print()
    console.print(table)
    console.print("[dim]Pick a number, or q to cancel.[/dim]")

    while True:
        choice = console.input("\n[bold cyan]Cached FITS[/bold cyan] › ").strip().lower()

        if choice in {"q", "quit", "exit"}:
            return None

        if choice.isdigit():
            index = int(choice)

            if 1 <= index <= len(cache_rows):
                return cached_fetch_result_from_row(cache_rows[index - 1])

        console.print("[red]Choose a listed number, or q.[/red]")


def render_view(
    fetch_result,
    target,
    survey,
    metadata,
    field_preset,
    zoom_level,
    brightness,
    contrast,
    render_mode,
    viewport_mode,
    show_meta,
    show_help,
    show_cache,
):
    viewport = safe_viewport(viewport_mode)
    wide_viewport = safe_viewport("wide")
    viewport_label = viewport["label"]

    # Render once using the wide canvas. Small view is a centre crop of
    # the same rendered sky field, not a separately squashed resample.
    render_width = wide_viewport["width"]
    render_height = viewport["height"]
    frame_width = viewport["width"]

    try:
        fits_size_mb = fetch_result.path.stat().st_size / (1024 * 1024)
    except Exception:
        fits_size_mb = 0.0

    with loading_task(f"Rendering image · {fits_size_mb:.1f} MB · view {viewport_label} · zoom {zoom_level}x · {brightness} · {contrast} · {render_mode}"):
        ascii_lines = image_to_ascii(
            fits_path=fetch_result.path,
            width=render_width,
            height=render_height,
            render_profile=render_profile_for_target(target.name, field_preset),
            zoom_level=zoom_level,
            brightness=brightness,
            contrast=contrast,
            band_key=survey.key,
            render_mode=render_mode,
        )

    if frame_width < render_width:
        ascii_lines = crop_lines_center(ascii_lines, frame_width)

    console.clear()

    if show_cache:
        overlay = cache_overlay_lines(list_fits_cache(CACHE_FITS_DIR, limit=15))
        show_ascii_frame_with_overlay(ascii_lines, overlay_lines=overlay, overlay_x=3, overlay_y=3, frame_width=frame_width)
    elif show_help:
        overlay = help_overlay_lines()
        show_ascii_frame_with_overlay(ascii_lines, overlay_lines=overlay, overlay_x=3, overlay_y=3, frame_width=frame_width)
    elif show_meta:
        overlay = metadata_overlay_lines(target, survey, fetch_result, metadata)
        show_ascii_frame_with_overlay(ascii_lines, overlay_lines=overlay, overlay_x=3, overlay_y=3, frame_width=frame_width)
    else:
        show_ascii_frame(ascii_lines, frame_width=frame_width)

    console.print(
        "\n[bold]Controls[/bold]  "
        "[bold]z[/bold]=zoom  "
        "[bold]b[/bold]=brightness  "
        "[bold]c[/bold]=contrast  "
        "[bold]r[/bold]=render  "
        "[bold]w[/bold]=view  "
        "[bold]e[/bold]=export  "
        "[bold]m[/bold]=metadata  "
        "[bold]h[/bold]=help  "
        "[bold]k[/bold]=cache  "
        "[bold]o[/bold]=open cache  "
        "[bold]n[/bold]=new target  "
        "[bold]q[/bold]=quit",
        style="dim",
    )
    source_state = getattr(fetch_result, "note", "") or "unknown source"

    console.print(
        f"View state: view {viewport_label} · zoom {zoom_level}x · brightness {brightness} · contrast {contrast} · render {render_mode} · metadata {'on' if show_meta else 'off'} · help {'on' if show_help else 'off'} · cache {'on' if show_cache else 'off'} · {source_state}",
        style="dim",
    )

    return {
        "ascii_lines": ascii_lines,
        "frame_width": frame_width,
        "viewport_label": viewport_label,
    }


def run_query_once():
    show_title()

    target_query = console.input("[bold cyan]Target[/bold cyan] name, ICRS coordinates, or [bold]c[/bold] catalog › ").strip()

    if target_query.lower() in {"q", "quit", "exit"}:
        return None

    if target_query.lower() in {"c", "catalog", "list", "objects"}:
        target_query = choose_catalog_target()

        if target_query is None:
            return None

    if not target_query:
        raise ValueError("No target entered.")

    survey = choose_survey()
    field_preset = choose_field_preset()

    if survey.key == "blend" and field_preset not in {"atlas", "survey", "grand"}:
        raise ValueError("Blend mode is only available with atlas or survey field scales.")

    with loading_task("Resolving target"):
        target = resolve_target(target_query)

    cache_before_mb = fits_cache_size_mb(CACHE_FITS_DIR)

    with loading_task(f"Fetching Pan-STARRS FITS · cache {cache_before_mb:.1f} MB"):
        try:
            fetch_result = fetch_fits_cutout(
                target=target,
                survey=survey,
                field_preset=field_preset,
                cache_dir=CACHE_FITS_DIR,
            )
        except Exception as error:
            raise RuntimeError(
                "Could not fetch remote FITS data. "
                "Check network, target spelling, or try a cached/recent object. "
                f"Original error: {error}"
            )

    prune_fits_cache(CACHE_FITS_DIR, keep=15)

    with loading_task("Fetching target metadata"):
        metadata = get_basic_metadata(target.name)

    return target, survey, field_preset, fetch_result, metadata


def viewer_loop(target, survey, field_preset, fetch_result, metadata):
    zoom_level = 1
    brightness = "med"
    contrast = "med"
    render_mode = "basic"
    viewport_mode = "small"
    show_meta = False
    show_help = False
    show_cache = False

    source_field_preset = field_for_viewport(field_preset, "wide")

    if source_field_preset == field_preset:
        source_fetch_result = fetch_result
    else:
        with loading_task(f"Fetching shared view source · field {source_field_preset}"):
            source_fetch_result = fetch_fits_cutout(
                target=target,
                survey=survey,
                field_preset=source_field_preset,
                cache_dir=CACHE_FITS_DIR,
            )

    while True:
        active_fetch_result = source_fetch_result
        active_field_preset = source_field_preset

        last_render = render_view(
            fetch_result=active_fetch_result,
            target=target,
            survey=survey,
            metadata=metadata,
            field_preset=active_field_preset,
            zoom_level=zoom_level,
            brightness=brightness,
            contrast=contrast,
            render_mode=render_mode,
            viewport_mode=viewport_mode,
            show_meta=show_meta,
            show_help=show_help,
            show_cache=show_cache,
        )

        command = console.input("\nPress key then Enter [z/b/c/r/w/e/m/h/k/o/n/q or cache #]: ").strip().lower()

        if show_cache and command.isdigit():
            cached_fetch_result = cached_fits_by_number(command)

            if cached_fetch_result is not None:
                source_fetch_result = cached_fetch_result
                source_field_preset = cached_fetch_result.requested_field
                show_meta = False
                show_help = False
                show_cache = False
                console.print(f"[green]Opened cached FITS:[/green] {cached_fetch_result.path.name}")
                continue

        if command in {"z", "zoom"}:
            zoom_level += 1
            if zoom_level > 3:
                zoom_level = 1

        elif command in {"b", "brightness"}:
            brightness = cycle_value(brightness, ["low", "med", "bright"])

        elif command in {"c", "contrast"}:
            contrast = cycle_value(contrast, ["soft", "med", "hard"])

        elif command in {"r", "render", "mode", "render mode"}:
            render_mode = cycle_value(render_mode, ["basic", "rich", "block"])

        elif command in {"w", "wide", "view", "view size", "viewport"}:
            viewport_mode = cycle_value(viewport_mode, ["small", "wide"])

        elif command in {"e", "export", "png", "image", "save"}:
            include_metadata = ask_export_metadata()

            if include_metadata is not None:
                overlay = None

                if include_metadata:
                    overlay = metadata_overlay_lines(
                        target,
                        survey,
                        active_fetch_result,
                        metadata,
                    )

                output_path = export_view_png(
                    ascii_lines=last_render["ascii_lines"],
                    target=target,
                    survey=survey,
                    fetch_result=active_fetch_result,
                    metadata=metadata,
                    render_mode=render_mode,
                    viewport_mode=viewport_mode,
                    frame_width=last_render["frame_width"],
                    include_metadata=include_metadata,
                    overlay_lines=overlay,
                )

                console.print(f"[green]Exported PNG:[/green] {output_path}")

        elif command in {"m", "meta", "metadata"}:
            show_meta = not show_meta
            if show_meta:
                show_help = False
                show_cache = False

        elif command in {"h", "help", "?"}:
            show_help = not show_help
            if show_help:
                show_meta = False
                show_cache = False

        elif command in {"o", "open", "open cache", "cache manager", "cached"}:
            cached_fetch_result = choose_cached_fits()

            if cached_fetch_result is not None:
                source_fetch_result = cached_fetch_result
                source_field_preset = cached_fetch_result.requested_field
                show_meta = False
                show_help = False
                show_cache = False
                console.print(f"[green]Opened cached FITS:[/green] {cached_fetch_result.path.name}")
                continue

        elif command in {"k", "cache"}:
            show_cache = not show_cache
            if show_cache:
                show_meta = False
                show_help = False

        elif command in {"n", "new", "new target", "target"}:
            return "new"

        elif command in {"q", "quit", "exit"}:
            return "quit"

        elif command == "":
            continue

        else:
            console.print("Unknown command. Type z, b, c, r, w, e, m, h, k, o, n, or q, then press Enter.", style="red")


def run_app():
    ensure_cache_dirs()
    prune_fits_cache(CACHE_FITS_DIR, keep=15)

    while True:
        try:
            query_result = run_query_once()

            if query_result is None:
                break

            target, survey, field_preset, fetch_result, metadata = query_result
            result = viewer_loop(target, survey, field_preset, fetch_result, metadata)

            if result == "quit":
                console.clear()
                console.print("SKYBOX closed.", style="dim")
                return

        except KeyboardInterrupt:
            console.clear()
            console.print("SKYBOX closed.", style="dim")
            return

        except Exception as error:
            show_error(error)
            command = console.input("\n[n] new target  [q] quit: ").strip().lower()
            if command in {"q", "quit", "exit"}:
                return
