SPRITES_DIR = ./sprites
ICONS_DIR   = ./icons

.PHONY: sprites sprite-1x sprite-2x sprite-64 sprite-sdf sprite-sdf-2x icon retina clean serve sprites-build runtime-icon-pack refresh-assets detect-missing-icons fetch-missing-icons check-id-tagging-schema mark-id-tagging-schema-synced generate-id-tagging-import-candidates sprites-64

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

icon:
	./scripts/check-icon-sizes.sh
	mkdir -p ./sprites
	spreet ./icons ./sprites/sprites
	./scripts/merge_vendor_sprite_keys.py --ratio 1

retina:
	./scripts/check-icon-sizes.sh
	spreet --retina ./icons ./sprites/sprites@2x
	./scripts/merge_vendor_sprite_keys.py --ratio 2
	./scripts/build_runtime_icon_pack.py

sprites-build: icon retina
	./scripts/build_sprites_64.py

runtime-icon-pack:
	./scripts/build_runtime_icon_pack.py

refresh-assets:
	./scripts/refresh_sprites_and_runtime.py

detect-missing-icons:
	./scripts/fetch_missing_icons.py

fetch-missing-icons:
	./scripts/fetch_missing_icons.py --apply

check-id-tagging-schema:
	./scripts/check_id_tagging_schema_updates.py

mark-id-tagging-schema-synced:
	./scripts/mark_id_tagging_schema_synced.py

generate-id-tagging-import-candidates:
	./scripts/generate_id_schema_import_candidates.py

sprites-64:
	./scripts/build_sprites_64.py

clean:
	rm -f $(SPRITES_DIR)/sprites*.json $(SPRITES_DIR)/sprites*.png

serve:
	http-server
