<img width="628" height="818" alt="starbox_2" src="https://github.com/user-attachments/assets/bd288968-c3b4-4428-9783-1b052bbb61e3" />
# SKYBOX

SKYBOX v1.9 Theme Cycle

A Mac-first terminal FITS viewer for Pan-STARRS sky-survey data.

SKYBOX resolves an object name, ICRS coordinate, or built-in catalog target, fetches a Pan-STARRS FITS cutout, and renders it as a rich framed ASCII skybox in the terminal.

## What it does

- Resolves named astronomical targets or ICRS coordinates.
- Includes a built-in curated object catalog.
- Fetches Pan-STARRS optical survey data.
- Renders the field as styled terminal ASCII.
- Supports small and wide viewer modes.
- Supports multiple ASCII render styles.
- Exports the viewer window as a PNG.
- Keeps a 15-file FITS cache.
- Allows cached FITS files to be reopened from the viewer.
- Cycles through eight boot-time UI colour themes.

## Starting SKYBOX

Run:

    python3 run.py

At the target prompt, enter one of:

- an object name, such as M101
- ICRS coordinates
- c or catalog to browse the built-in catalog
- q to quit

## Catalog

Catalog shortcuts:

    c
    catalog
    list
    objects

The catalog includes galaxies, nebulae, clusters, and a small deep/odd section. Pick a numbered entry or type an object name.

## Band selection

- 1: short — Pan-STARRS g
- 2: mid — Pan-STARRS i
- 3: long — Pan-STARRS y
- 4: blend — Pan-STARRS DR1 colour HiPS

Typed inputs still work: short, mid, long, blend.

Blend mode only works with atlas or survey field scales.

## Field selection

- 1: core — close target / core
- 2: field — standard object field
- 3: wide — widest native cutout
- 4: atlas — large-object morphology
- 5: survey — broad context

Typed inputs still work: core, field, wide, atlas, survey.

Legacy aliases still work: tight, normal, grand.

## Viewer controls

- z: zoom
- b: brightness
- c: contrast
- r: render mode
- w: view size
- e: export PNG
- m: metadata overlay
- h: help overlay
- k: cache overlay
- o: open cached FITS
- n: new target
- q: quit

## Render modes

- basic: original ASCII texture
- rich: denser character texture
- block: shaded block mosaic

## View size

- small: compact view
- wide: wider terminal view

Small view is a centre crop of the same wide-rendered source, so both modes keep matching geometry and rendering style.

## PNG export

Press e in the viewer to export the current viewer window as a PNG.

SKYBOX asks whether to include the metadata overlay:

    1 yes
    2 no
    q cancel

Exports are written to exports/png/.

The PNG contains the viewer frame only, with a black background. It does not include the control line, state line, or terminal prompt.

## Cache

SKYBOX keeps the newest 15 FITS files in cache/fits/.

Viewer cache controls:

- k: show/hide the cache overlay
- number while cache overlay is visible: open that cached FITS
- o: open the full numbered cache manager

The cache manager does not fetch remote data. It opens existing cached FITS files directly.

## Boot themes

SKYBOX chooses one UI theme per app launch and keeps it fixed until quit.

Current boot themes:

- amber
- ember
- brass
- rose-gold
- dusk
- green
- blue
- purple

The terminal sky viewer itself remains neutral so the astronomical field stays readable.

## Output folders

- FITS cache: cache/fits/
- Metadata cache: cache/metadata/
- PNG exports: exports/png/

## Current milestone

v1.9 unifies the visual design, adds boot-time theme cycling, keeps the main viewer frame neutral, and preserves the existing catalog, cache manager, and PNG export workflows.
