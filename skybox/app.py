from skybox.ascii_render import image_to_ascii
from skybox.cache import prune_fits_cache, list_fits_cache, fits_cache_size_mb, ensure_cache_dirs
from skybox.config import ASCII_HEIGHT, ASCII_WIDTH, CACHE_FITS_DIR
from skybox.fetcher import fetch_fits_cutout
from skybox.loading import loading_task
from skybox.metadata import get_basic_metadata
from skybox.resolver import resolve_target
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


def render_view(
    fetch_result,
    target,
    survey,
    metadata,
    field_preset,
    zoom_level,
    brightness,
    contrast,
    show_meta,
    show_help,
    show_cache,
):
    try:
        fits_size_mb = fetch_result.path.stat().st_size / (1024 * 1024)
    except Exception:
        fits_size_mb = 0.0

    with loading_task(f"Rendering image · {fits_size_mb:.1f} MB · zoom {zoom_level}x · {brightness} · {contrast}"):
        ascii_lines = image_to_ascii(
            fits_path=fetch_result.path,
            width=ASCII_WIDTH,
            height=ASCII_HEIGHT,
            render_profile=render_profile_for_target(target.name, field_preset),
            zoom_level=zoom_level,
            brightness=brightness,
            contrast=contrast,
            band_key=survey.key,
        )

    console.clear()

    if show_cache:
        overlay = cache_overlay_lines(list_fits_cache(CACHE_FITS_DIR, limit=5))
        show_ascii_frame_with_overlay(ascii_lines, overlay_lines=overlay, overlay_x=3, overlay_y=3)
    elif show_help:
        overlay = help_overlay_lines()
        show_ascii_frame_with_overlay(ascii_lines, overlay_lines=overlay, overlay_x=3, overlay_y=3)
    elif show_meta:
        overlay = metadata_overlay_lines(target, survey, fetch_result, metadata)
        show_ascii_frame_with_overlay(ascii_lines, overlay_lines=overlay, overlay_x=3, overlay_y=3)
    else:
        show_ascii_frame(ascii_lines)

    console.print(
        "\n[bold]Controls[/bold]  "
        "[bold]z[/bold]=zoom  "
        "[bold]b[/bold]=brightness  "
        "[bold]c[/bold]=contrast  "
        "[bold]m[/bold]=metadata  "
        "[bold]h[/bold]=help  "
        "[bold]k[/bold]=cache  "
        "[bold]n[/bold]=new target  "
        "[bold]q[/bold]=quit",
        style="dim",
    )
    source_state = getattr(fetch_result, "note", "") or "unknown source"

    console.print(
        f"View state: zoom {zoom_level}x · brightness {brightness} · contrast {contrast} · metadata {'on' if show_meta else 'off'} · help {'on' if show_help else 'off'} · cache {'on' if show_cache else 'off'} · {source_state}",
        style="dim",
    )


def run_query_once():
    show_title()

    target_query = console.input("[bold cyan]Target[/bold cyan] name or ICRS coordinates › ").strip()

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
    show_meta = False
    show_help = False
    show_cache = False

    while True:
        render_view(
            fetch_result=fetch_result,
            target=target,
            survey=survey,
            metadata=metadata,
            field_preset=field_preset,
            zoom_level=zoom_level,
            brightness=brightness,
            contrast=contrast,
            show_meta=show_meta,
            show_help=show_help,
            show_cache=show_cache,
        )

        command = console.input("\nPress key then Enter [z/b/c/m/h/k/n/q]: ").strip().lower()

        if command in {"z", "zoom"}:
            zoom_level += 1
            if zoom_level > 3:
                zoom_level = 1

        elif command in {"b", "brightness"}:
            brightness = cycle_value(brightness, ["low", "med", "bright"])

        elif command in {"c", "contrast"}:
            contrast = cycle_value(contrast, ["soft", "med", "hard"])

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
            console.print("Unknown command. Type z, b, c, m, h, k, n, or q, then press Enter.", style="red")


def run_app():
    ensure_cache_dirs()
    prune_fits_cache(CACHE_FITS_DIR, keep=5)

    while True:
        try:
            target, survey, field_preset, fetch_result, metadata = run_query_once()
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
