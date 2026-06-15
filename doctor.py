from pathlib import Path
import importlib
import sys
import warnings

warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL.*",
)

try:
    from skybox.version import APP_NAME, APP_VERSION, APP_CODENAME
except Exception:
    APP_NAME = "SKYBOX"
    APP_VERSION = "unknown"
    APP_CODENAME = "unknown"


REQUIRED_MODULES = [
    "numpy",
    "requests",
    "rich",
    "astropy",
    "astroquery",
    "PIL",
    "scipy",
]


def check_python_version():
    print("Checking Python version...")
    version = sys.version_info
    print(f"  Python {version.major}.{version.minor}.{version.micro}")

    if version.major == 3 and version.minor >= 9:
        print("  OK   Python version is suitable")
        return True

    print("  FAIL Python 3.9+ recommended")
    return False


def check_imports():
    print("\nChecking Python imports...")
    ok = True

    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
            print(f"  OK   {module_name}")
        except Exception as error:
            ok = False
            print(f"  FAIL {module_name}: {error}")

    return ok


def check_paths():
    print("\nChecking project paths...")
    ok = True

    paths = [
        Path("run.py"),
        Path("skybox"),
        Path("skybox/app.py"),
        Path("skybox/ui.py"),
        Path("skybox/ascii_render.py"),
        Path("skybox/providers/panstarrs.py"),
        Path("skybox/providers/panstarrs_atlas.py"),
        Path("cache/fits"),
        Path("cache/metadata"),
    ]

    for path in paths:
        if path.exists():
            print(f"  OK   {path}")
        else:
            ok = False
            print(f"  FAIL missing {path}")

    return ok


def check_cache():
    print("\nChecking FITS cache...")

    cache_dir = Path("cache/fits")
    cache_dir.mkdir(parents=True, exist_ok=True)

    fits_files = []

    for pattern in ("*.fits", "*.fit", "*.fits.gz", "*.fit.gz"):
        fits_files.extend(cache_dir.glob(pattern))

    fits_files = [p for p in fits_files if p.is_file()]
    fits_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    total_mb = sum(p.stat().st_size for p in fits_files) / (1024 * 1024)

    print(f"  FITS files: {len(fits_files)}")
    print(f"  Total size: {total_mb:.1f} MB")

    if len(fits_files) > 5:
        print("  WARN cache has more than five FITS files; app should prune on next startup.")
    else:
        print("  OK   cache count within limit")

    for path in fits_files[:5]:
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"       {path.name} - {size_mb:.1f} MB")

    return True


def main():
    print(f"{APP_NAME} v{APP_VERSION} - {APP_CODENAME} doctor")
    print("=" * 42)

    results = [
        check_python_version(),
        check_imports(),
        check_paths(),
        check_cache(),
    ]

    print("\nResult")
    print("=" * 42)

    if all(results):
        print("OK: SKYBOX looks ready.")
    else:
        print("FAIL: one or more checks need attention.")


if __name__ == "__main__":
    main()
