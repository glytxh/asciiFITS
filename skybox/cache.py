from pathlib import Path


def prune_fits_cache(cache_dir, keep=5):
    """
    Keep only the newest FITS files in the cache directory.

    Deletes older:
    - .fits
    - .fit
    - .fits.gz
    - .fit.gz

    This is intentionally simple and safe: it only touches files
    directly inside the FITS cache folder.
    """
    cache_path = Path(cache_dir)

    if not cache_path.exists():
        return []

    fits_files = []

    for pattern in ("*.fits", "*.fit", "*.fits.gz", "*.fit.gz"):
        fits_files.extend(cache_path.glob(pattern))

    fits_files = [p for p in fits_files if p.is_file()]

    if len(fits_files) <= keep:
        return []

    fits_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    to_delete = fits_files[keep:]
    deleted = []

    for file_path in to_delete:
        try:
            file_path.unlink()
            deleted.append(file_path.name)
        except OSError:
            pass

    return deleted


def list_fits_cache(cache_dir, limit=5):
    """
    Return newest cached FITS files as simple dictionaries.
    """
    cache_path = Path(cache_dir)

    if not cache_path.exists():
        return []

    fits_files = []

    for pattern in ("*.fits", "*.fit", "*.fits.gz", "*.fit.gz"):
        fits_files.extend(cache_path.glob(pattern))

    fits_files = [p for p in fits_files if p.is_file()]
    fits_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    rows = []

    for file_path in fits_files[:limit]:
        stat = file_path.stat()
        size_mb = stat.st_size / (1024 * 1024)

        rows.append(
            {
                "name": file_path.name,
                "size_mb": size_mb,
            }
        )

    return rows


def fits_cache_size_mb(cache_dir):
    """
    Return total size of cached FITS files in MB.
    """
    cache_path = Path(cache_dir)

    if not cache_path.exists():
        return 0.0

    total_bytes = 0

    for pattern in ("*.fits", "*.fit", "*.fits.gz", "*.fit.gz"):
        for file_path in cache_path.glob(pattern):
            if file_path.is_file():
                total_bytes += file_path.stat().st_size

    return total_bytes / (1024 * 1024)


def ensure_cache_dirs():
    """
    Ensure SKYBOX cache folders exist.
    Useful when the project is copied, packaged, or launched fresh.
    """
    Path("cache/fits").mkdir(parents=True, exist_ok=True)
    Path("cache/metadata").mkdir(parents=True, exist_ok=True)
