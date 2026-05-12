SPRITES_DIR = ./sprites
ICONS_DIR   = ./icons

.PHONY: sprites sprite-1x sprite-2x sprite-64 sprite-sdf sprite-sdf-2x icon retina clean serve

sprites: sprite-1x sprite-2x sprite-64 sprite-sdf sprite-sdf-2x

sprite-1x:
	@mkdir -p $(SPRITES_DIR)
	spreet --minify-index-file $(ICONS_DIR) $(SPRITES_DIR)/sprites

sprite-2x:
	spreet --retina --minify-index-file $(ICONS_DIR) $(SPRITES_DIR)/sprites@2x

sprite-64:
	spreet --ratio 4 --minify-index-file $(ICONS_DIR) $(SPRITES_DIR)/sprites@64

sprite-sdf:
	spreet --sdf --minify-index-file $(ICONS_DIR) $(SPRITES_DIR)/sprites-sdf

sprite-sdf-2x:
	spreet --sdf --retina --minify-index-file $(ICONS_DIR) $(SPRITES_DIR)/sprites-sdf@2x

icon: sprite-1x
retina: sprite-2x

clean:
	rm -f $(SPRITES_DIR)/sprites*.json $(SPRITES_DIR)/sprites*.png

serve:
	http-server
