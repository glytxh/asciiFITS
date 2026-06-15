import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import rotate
from rich.text import Text
from rich.console import Console


ASCII_RAMP = "     ...,,,:::;;;iiiIII!!!+++***###%%%@@@"


def clean_image(data):
    data = np.array(data, dtype=float)
    return np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)


def load_image_and_header(fits_path):
    with fits.open(fits_path) as hdul:
        for hdu in hdul:
            if hdu.data is None:
                continue

            data = clean_image(hdu.data)
            header = hdu.header

            if data.ndim == 2:
                return data, header

            if data.ndim == 3:
                # RGB/RGBA first axis: (3/4, H, W)
                if data.shape[0] in (3, 4):
                    rgb = data[:3]
                    rgb = np.moveaxis(rgb, 0, -1)
                    return rgb, header

                # RGB/RGBA last axis: (H, W, 3/4)
                if data.shape[-1] in (3, 4):
                    rgb = data[..., :3]
                    return rgb, header

                return data[0], header

    raise ValueError("No image data found in FITS file.")


def luminance(data):
    data = clean_image(data)

    if data.ndim == 2:
        return data

    r = data[..., 0]
    g = data[..., 1]
    b = data[..., 2]

    return 0.30 * r + 0.59 * g + 0.11 * b


def calculate_north_up_rotation_deg(header, image_shape):
    try:
        wcs = WCS(header).celestial

        height, width = image_shape[:2]
        cx = width / 2.0
        cy = height / 2.0

        sky_center = wcs.pixel_to_world(cx, cy)
        sky_up_pixel = wcs.pixel_to_world(cx, cy - 1)

        current_up_pa = sky_center.position_angle(sky_up_pixel).deg

        if not np.isfinite(current_up_pa):
            return 0.0

        return float(current_up_pa)

    except Exception:
        return 0.0


def rotate_north_up(data, header):
    angle = calculate_north_up_rotation_deg(header, data.shape)

    if abs(angle) < 0.01:
        return data

    if data.ndim == 2:
        return rotate(
            data,
            angle=angle,
            reshape=False,
            order=1,
            mode="nearest",
            prefilter=False,
        )

    channels = []

    for channel in range(data.shape[-1]):
        rotated = rotate(
            data[..., channel],
            angle=angle,
            reshape=False,
            order=1,
            mode="nearest",
            prefilter=False,
        )
        channels.append(rotated)

    return np.stack(channels, axis=-1)


def resize_by_block(data, out_height, out_width, mode="mean"):
    data = clean_image(data)

    if data.ndim == 3:
        channels = []
        for channel in range(data.shape[-1]):
            channels.append(resize_by_block(data[..., channel], out_height, out_width, mode))
        return np.stack(channels, axis=-1)

    in_height, in_width = data.shape

    y_edges = np.linspace(0, in_height, out_height + 1).astype(int)
    x_edges = np.linspace(0, in_width, out_width + 1).astype(int)

    small = np.zeros((out_height, out_width), dtype=float)

    for y in range(out_height):
        for x in range(out_width):
            block = data[y_edges[y]:y_edges[y + 1], x_edges[x]:x_edges[x + 1]]

            if not block.size:
                small[y, x] = 0.0
            elif mode == "median":
                small[y, x] = float(np.median(block))
            else:
                small[y, x] = float(np.mean(block))

    return small


def soft_blur(small):
    if small.ndim == 3:
        channels = []
        for channel in range(small.shape[-1]):
            channels.append(soft_blur(small[..., channel]))
        return np.stack(channels, axis=-1)

    padded = np.pad(small, 1, mode="edge")

    return (
        padded[:-2, :-2] + padded[:-2, 1:-1] + padded[:-2, 2:] +
        padded[1:-1, :-2] + padded[1:-1, 1:-1] + padded[1:-1, 2:] +
        padded[2:, :-2] + padded[2:, 1:-1] + padded[2:, 2:]
    ) / 9.0


def normalize_scalar(data, low_p=1, high_p=99.8, stretch=5, gamma=0.70, floor=0.03):
    data = clean_image(data)
    valid = data[np.isfinite(data)]

    if valid.size == 0:
        return np.zeros_like(data)

    low = np.percentile(valid, low_p)
    high = np.percentile(valid, high_p)

    if high <= low:
        return np.zeros_like(data)

    data = np.clip(data, low, high)
    data = (data - low) / (high - low)

    data = np.arcsinh(data * stretch) / np.arcsinh(stretch)
    data = np.power(data, gamma)
    data = np.clip((data - floor) / (1.0 - floor), 0, 1)

    return np.clip(data, 0, 1)


def normalize_rgb(data):
    """
    Preserve real Pan-STARRS colour balance, but scale channels enough
    to survive terminal display.
    """
    data = clean_image(data)

    channels = []

    for channel in range(3):
        channels.append(
            normalize_scalar(
                data[..., channel],
                low_p=1,
                high_p=99.8,
                stretch=5,
                gamma=0.72,
                floor=0.025,
            )
        )

    rgb = np.stack(channels, axis=-1)

    # Use luminance to keep dark sky dark and bright sky bright.
    lum = luminance(rgb)
    lum = normalize_scalar(lum, low_p=1, high_p=99.8, stretch=4, gamma=0.72, floor=0.025)

    # Avoid washed-out low-level colour fog.
    rgb = rgb * (0.35 + 0.65 * lum[..., None])

    return np.clip(rgb, 0, 1)


def local_contrast_boost(small, amount=0.10):
    blurred = soft_blur(small)
    boosted = small + amount * (small - blurred)
    return np.clip(boosted, 0, 1)


def infer_single_band_colour(fits_path):
    path = str(fits_path)

    if "_ps1_g_" in path:
        return "blue"

    if "_ps1_y_" in path:
        return "red"

    return "white"


def colour_for_single_band(value, colour_mode):
    value = float(np.clip(value, 0, 1))

    # Keep dark sky dark.
    base = int(12 + value * 243)

    if colour_mode == "blue":
        r = int(10 + value * 70)
        g = int(25 + value * 130)
        b = int(45 + value * 210)
        return r, g, b

    if colour_mode == "red":
        r = int(45 + value * 210)
        g = int(12 + value * 80)
        b = int(10 + value * 55)
        return r, g, b

    return base, base, base


def char_for_value(value):
    value = float(np.clip(value, 0, 1))
    idx = int(value * (len(ASCII_RAMP) - 1))
    return ASCII_RAMP[idx]


def palette_from_fits_path(fits_path):
    """
    Infer single-band colour palette from SKYBOX cached FITS filename.

    short / g = blue
    mid / i   = white
    long / y  = red
    """
    name = str(fits_path).lower()

    if "_ps1_g_" in name or "_panstarrs_g_" in name or "_g_" in name:
        return "blue"

    if "_ps1_y_" in name or "_panstarrs_y_" in name or "_y_" in name:
        return "red"

    if "_ps1_i_" in name or "_panstarrs_i_" in name or "_i_" in name:
        return "white"

    return "white"



def text_lines_from_scalar(small, palette="white"):
    """
    Convert a normalized 2D array into Rich-coloured ASCII lines.
    Stable simple palette version.

    palette:
      blue  = short / g
      white = mid / i
      red   = long / y
    """
    lines = []

    for row in small:
        line = Text()

        for value in row:
            value = float(np.clip(value, 0, 1))
            index = min(len(ASCII_RAMP) - 1, int(value * (len(ASCII_RAMP) - 1)))
            char = ASCII_RAMP[index]

            if palette == "blue":
                r = int(10 + value * 70)
                g = int(25 + value * 130)
                b = int(45 + value * 210)

            elif palette == "red":
                r = int(45 + value * 210)
                g = int(12 + value * 80)
                b = int(10 + value * 55)

            else:
                base = int(12 + value * 243)
                r = base
                g = base
                b = base

            line.append(char, style=f"rgb({r},{g},{b})")

        lines.append(line)

    return lines


def apply_rgb_display_settings(rgb, settings):
    """
    Apply brightness/contrast controls to colour blend mode.

    This adjusts luminance while preserving colour balance.
    """
    rgb = np.clip(rgb, 0, 1)

    lum = luminance(rgb)
    adjusted_lum = normalize_scalar(
        lum,
        low_p=1,
        high_p=99.8,
        stretch=tuned_stretch(5, settings),
        gamma=tuned_gamma(0.70, settings),
        floor=tuned_floor(0.03, settings),
    )

    old_lum = np.clip(lum, 0.001, 1)
    ratio = adjusted_lum / old_lum

    rgb = rgb * ratio[..., None]

    return np.clip(rgb, 0, 1)


def text_lines_from_rgb(rgb):
    intensity = luminance(rgb)
    intensity = np.clip(intensity, 0, 1)

    lines = []

    for y in range(rgb.shape[0]):
        text = Text()

        for x in range(rgb.shape[1]):
            value = float(intensity[y, x])
            char = char_for_value(value)

            r = int(np.clip(rgb[y, x, 0], 0, 1) * 255)
            g = int(np.clip(rgb[y, x, 1], 0, 1) * 255)
            b = int(np.clip(rgb[y, x, 2], 0, 1) * 255)

            # Keep near-black regions genuinely dark.
            if value < 0.025:
                r, g, b = 8, 8, 8

            text.append(char, style=f"rgb({r},{g},{b})")

        lines.append(text)

    return lines


def lock_lines(lines, width=100, height=50):
    locked = []

    for line in lines[:height]:
        if isinstance(line, Text):
            plain = line.plain[:width]
            new_line = Text()

            for index, char in enumerate(plain):
                style = line.get_style_at_offset(Console(), index)
                new_line.append(char, style=style)

            if new_line.cell_len < width:
                new_line.append(" " * (width - new_line.cell_len))

            locked.append(new_line)
        else:
            locked.append(str(line)[:width].ljust(width))

    while len(locked) < height:
        locked.append(" " * width)

    return locked


def crop_for_zoom(data, zoom_level):
    """
    Centre crop before rendering.

    zoom_level:
      1 = full image
      2 = centre 60%
      3 = centre 35%
    """
    if zoom_level <= 1:
        return data

    crop_fraction = {
        2: 0.60,
        3: 0.35,
    }.get(zoom_level, 1.0)

    height, width = data.shape[:2]

    crop_h = max(1, int(height * crop_fraction))
    crop_w = max(1, int(width * crop_fraction))

    y0 = max(0, (height - crop_h) // 2)
    x0 = max(0, (width - crop_w) // 2)

    if data.ndim == 3:
        return data[y0:y0 + crop_h, x0:x0 + crop_w, :]

    return data[y0:y0 + crop_h, x0:x0 + crop_w]


def display_settings(brightness="med", contrast="med"):
    brightness_options = {
        "low": {
            "floor_adjust": 0.075,
            "gamma_adjust": 0.28,
        },
        "med": {
            "floor_adjust": 0.0,
            "gamma_adjust": 0.0,
        },
        "bright": {
            "floor_adjust": -0.045,
            "gamma_adjust": -0.24,
        },
    }

    contrast_options = {
        "soft": {
            "stretch_mult": 0.55,
            "local_mult": 0.25,
        },
        "med": {
            "stretch_mult": 1.0,
            "local_mult": 1.0,
        },
        "hard": {
            "stretch_mult": 1.75,
            "local_mult": 2.20,
        },
    }

    return {
        **brightness_options.get(brightness, brightness_options["med"]),
        **contrast_options.get(contrast, contrast_options["med"]),
    }


def tuned_floor(base_floor, settings):
    return max(0.0, min(0.25, base_floor + settings["floor_adjust"]))


def tuned_gamma(base_gamma, settings):
    return max(0.25, min(1.40, base_gamma + settings["gamma_adjust"]))


def tuned_stretch(base_stretch, settings):
    return max(1.0, base_stretch * settings["stretch_mult"])


def tuned_local(base_local, settings):
    return max(0.0, min(0.60, base_local * settings["local_mult"]))


def image_to_ascii(fits_path, width=100, height=50, render_profile=None, zoom_level=1, brightness='med', contrast='med', band_key=None):
    settings = display_settings(brightness=brightness, contrast=contrast)

    if band_key == "short":
        selected_palette = "blue"
    elif band_key == "long":
        selected_palette = "red"
    else:
        selected_palette = "white"

    data, header = load_image_and_header(fits_path)
    data = rotate_north_up(data, header)

    # Match Aladin-style sky display:
    # north up, east left.
    data = np.fliplr(data)

    # Viewer zoom: crop after orientation correction.
    data = crop_for_zoom(data, zoom_level)

    path_text = str(fits_path)

    # Exact Pan-STARRS colour layer / blend mode.
    if "_ps1_color_" in path_text:
        small_rgb = resize_by_block(data, height, width, mode="mean")
        small_rgb = normalize_rgb(small_rgb)
        small_rgb = apply_rgb_display_settings(small_rgb, settings)
        small_rgb = local_contrast_boost(small_rgb, amount=tuned_local(0.10, settings))
        return lock_lines(text_lines_from_rgb(small_rgb), width, height)

    # Single-band modes: short/mid/long.
    scalar = luminance(data)

    if render_profile == "atlas":
        small = resize_by_block(scalar, height, width, mode="mean")
        small = soft_blur(small)
        small = normalize_scalar(
            small,
            low_p=5,
            high_p=99.4,
            stretch=tuned_stretch(7, settings),
            gamma=tuned_gamma(0.58, settings),
            floor=tuned_floor(0.06, settings),
        )
        small = local_contrast_boost(small, amount=tuned_local(0.08, settings))
        return lock_lines(text_lines_from_scalar(small, palette=selected_palette), width, height)

    if render_profile == "diffuse":
        small = resize_by_block(scalar, height, width, mode="mean")
        small = soft_blur(small)
        small = normalize_scalar(
            small,
            low_p=3,
            high_p=99.7,
            stretch=tuned_stretch(8, settings),
            gamma=tuned_gamma(0.55, settings),
            floor=tuned_floor(0.04, settings),
        )
        small = local_contrast_boost(small, amount=tuned_local(0.05, settings))
        return lock_lines(text_lines_from_scalar(small, palette=selected_palette), width, height)

    scalar = normalize_scalar(
        scalar,
        low_p=45,
        high_p=99.85,
        stretch=tuned_stretch(10, settings),
        gamma=tuned_gamma(0.82, settings),
        floor=tuned_floor(0.045, settings),
    )
    small = resize_by_block(scalar, height, width, mode="mean")
    small = local_contrast_boost(small, amount=tuned_local(0.30, settings))

    return lock_lines(text_lines_from_scalar(small, palette=selected_palette), width, height)
