# Basemaps Assets AI Context

This repo contains the icon SVGs, presets, and sprite build pipeline for Fotoshi basemaps.
Use this as the point-of-entry for any AI or contributor.

## Mission
- Keep the icon set clean, consistent, and correctly rendered in sprites.
- Ensure presets reference valid icons and map cleanly to OSM/Overture tags.
- Avoid breaking sprite builds or map rendering.

## Always Run
- **After any icon or preset changes, run:**
  - `make`
  - `make retina`

The 2x sprites are required for production parity. Do not skip.

## Icon Rules
- **Size:** all icons are **15x15**.
- **Color:** black (`#000000`) unless explicitly specified (e.g., custom tree icon).
- **ViewBox:** normalized and clean. If an SVG is malformed (duplicate xmlns, etc.), fix it.
- **Output:** SVGs live in `icons/`, sprites in `sprites/`.

## Sprite Build
- Uses `spreet` to build sprites and JSON.
- `make` builds 1x sprites.
- `make retina` builds 2x sprites.

## Presets
- Presets live in `meta/presets.json`.
- Every preset **must** reference a valid icon name (without `.svg`).
- Keep IDs stable. Only append new IDs.

## Common Tasks
- **Add or replace an icon:**
  1) Add SVG under `icons/` with correct size/color.
  2) Update the preset icon reference if needed.
  3) Run `make` and `make retina`.

- **New preset:**
  1) Decide tags + icon.
  2) Add to `meta/presets.json` with next ID.
  3) Run `make` and `make retina`.

## Notes
- If sprites look wrong, verify SVG sizing first.
- If MapLibre reports missing images, check the icon name in presets and sprite JSON.
- Avoid keeping temporary or staging icon folders in the repo.
