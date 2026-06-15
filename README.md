# SKYBOX

SKYBOX v1.1 Reticle

A Mac-first terminal FITS viewer for Pan-STARRS sky-survey data.

SKYBOX resolves an object name or ICRS coordinate, fetches a Pan-STARRS FITS cutout, and renders it as a rich ASCII skybox in the terminal.


## Bands

- short: Pan-STARRS g
- mid: Pan-STARRS i
- long: Pan-STARRS y
- blend: Pan-STARRS DR1 colour HiPS

Blend mode only works with atlas or survey field scales.

## Fields

- core
- field
- wide
- atlas
- survey

## Viewer controls

- z: zoom
- b: brightness
- c: contrast
- m: metadata overlay
- h: help overlay
- k: cache overlay
- n: new target
- q: quit

## Cache

SKYBOX keeps only the newest five FITS files in cache/fits.

## Status

Ready for Mac app wrapping.
