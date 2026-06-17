from skybox.ascii_render import image_to_ascii
from skybox.cache import prune_fits_cache, list_fits_cache, fits_cache_size_mb, ensure_cache_dirs
from skybox.config import ASCII_HEIGHT, ASCII_WIDTH, CACHE_FITS_DIR
from skybox.fetcher import fetch_fits_cutout
from skybox.loading import loading_task
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
        overlay = cache_overlay_lines(list_fits_cache(CACHE_FITS_DIR, limit=5))
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
        "[bold]m[/bold]=metadata  "
        "[bold]h[/bold]=help  "
        "[bold]k[/bold]=cache  "
        "[bold]n[/bold]=new target  "
        "[bold]q[/bold]=quit",
        style="dim",
    )
    source_state = getattr(fetch_result, "note", "") or "unknown source"

    console.print(
        f"View state: view {viewport_label} · zoom {zoom_level}x · brightness {brightness} · contrast {contrast} · render {render_mode} · metadata {'on' if show_meta else 'off'} · help {'on' if show_help else 'off'} · cache {'on' if show_cache else 'off'} · {source_state}",
        style="dim",
    )


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

    prune_fits_cache(CACHE_FITS_DIR, keep=5)

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

        render_view(
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

        command = console.input("\nPress key then Enter [z/b/c/r/w/m/h/k/n/q]: ").strip().lower()

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
            console.print("Unknown command. Type z, b, c, r, m, h, k, n, or q, then press Enter.", style="red")


def run_app():
    ensure_cache_dirs()
    prune_fits_cache(CACHE_FITS_DIR, keep=5)

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
