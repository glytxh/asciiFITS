from pathlib import Path
import sys

import numpy as np
from astropy.io import fits


def describe(path):
    print(f"\nFILE: {path}\n")

    with fits.open(path) as hdul:
        hdul.info()

        for i, hdu in enumerate(hdul):
            if hdu.data is None:
                continue

            data = np.array(hdu.data, dtype=float)
            print(f"\nHDU {i}")
            print(f"shape: {data.shape}")
            print(f"ndim:  {data.ndim}")

            finite = data[np.isfinite(data)]

            if finite.size == 0:
                print("no finite values")
                continue

            print(f"min:   {np.min(finite)}")
            print(f"max:   {np.max(finite)}")
            print(f"mean:  {np.mean(finite)}")
            print(f"std:   {np.std(finite)}")

            for p in [0, 1, 5, 10, 25, 50, 75, 90, 95, 98, 99, 99.5, 99.9, 100]:
                print(f"p{p:>5}: {np.percentile(finite, p)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python inspect_fits.py path/to/file.fits")
        raise SystemExit(1)

    describe(Path(sys.argv[1]))
