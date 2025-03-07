# Atlascove Basemaps Assets

This repository contains the assets for the Atlascove basemaps.

## Directory Structure

* `fonts/`: Contains PBF glyphs generated by [font-maker](https://github.com/maplibre/font-maker)
  * Current fonts: `Noto Sans Regular`, `Noto Sans Medium`, `Noto Sans Italic`
 
* `sprites/sprites.json`: Contains spritesheets generated by [spreet](https://github.com/flother/spreet), for each major version
  * `light@x.png` - light and dark themed spritesheets at 1x and 2x pixel densities

## Linking to Assets in Styles

```
glyphs:'https://atlascove.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf'
```
## License

The license for each group of assets is contained within that directory:

* `fonts/`: [SIL Open Font License](fonts/OFL.txt)
* `sprites/`: derived from [MIT-licensed tangrams/icons](https://github.com/tangrams/icons/blob/master/LICENSE.md)
