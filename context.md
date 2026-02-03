# Basemaps Assets Context

## Icon rules
- Default icon size is 15x15 (set `width="15" height="15"` on the `<svg>` element).
- Keep a proper `viewBox` so scaling is consistent.
- Default color is solid black (`#000000`) with a transparent background.
- Only use non-black colors when explicitly requested (e.g. `fts-tree.svg`).
- Avoid embedded bitmaps; use pure vector paths.
- Keep SVGs simple (single path where possible) and remove unnecessary metadata.
- Ensure there are no duplicate `id` values inside SVGs.
- Filename (without `.svg`) must match the sprite icon name.

## Sprites
- Rebuild sprites after any icon or preset change:
  - `make`
  - `make retina`
- Sprite sheets are generated from `icons/`.
- Check `sprites/sprites.json` for unexpected large sizes; anything bigger than 15x15 is usually a mistake.
 - Quick check: `scripts/check-icon-sizes.sh`

## Presets & tags
- Preset `icon` value must match the SVG filename.
- Keep presets and tags consistent with OSM tags and overture categories.
- Use ASCII for new edits unless the file already uses Unicode.
