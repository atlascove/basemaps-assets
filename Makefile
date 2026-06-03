SPRITES_DIR = ./sprites
ICONS_DIR   = ./icons
PRESET_I18N_LANGS = am ar bg bn cs de el es fa fil fr he hi hr hu hy id it ja ka ko pl pt_br ro ru sr sw ta th tr uk ur vi zh_hans zh_hant

.PHONY: sprites sprite-1x sprite-2x sprite-64 sprite-sdf sprite-sdf-2x icon retina clean serve sprites-build runtime-icon-pack refresh-assets deploy-cdn-assets detect-missing-icons fetch-missing-icons check-id-tagging-schema mark-id-tagging-schema-synced generate-id-tagging-import-candidates generate-presets-i18n $(PRESET_I18N_LANGS:%=generate-presets-%) validate-presets-i18n validate-presets-i18n-all $(PRESET_I18N_LANGS:%=validate-presets-%) sprites-64

sprites: check-sprite-deps sprite-1x sprite-2x sprite-64 sprite-sdf sprite-sdf-2x verify-sprites

sprite-1x:
	@mkdir -p $(SPRITES_DIR)
	spreet --minify-index-file $(ICONS_DIR) $(SPRITES_DIR)/sprites
	./scripts/merge_vendor_sprite_keys.py --ratio 1

sprite-2x:
	spreet --retina --minify-index-file $(ICONS_DIR) $(SPRITES_DIR)/sprites@2x
	./scripts/merge_vendor_sprite_keys.py --ratio 2

sprite-64:
	./scripts/build_sprites_64.py

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

check-sprite-deps:
	./scripts/check-icon-sizes.sh

verify-sprites:
	./scripts/verify_sprite_vendor_keys.py

deploy-cdn-assets:
	./scripts/deploy_cdn_assets.sh

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

generate-presets-i18n:
	@for lang in $(PRESET_I18N_LANGS); do \
		./scripts/generate_presets_i18n_machine.py --lang $$lang || exit $$?; \
	done

generate-presets-%:
	./scripts/generate_presets_i18n_machine.py --lang $*

validate-presets-i18n-all:
	@for lang in $(PRESET_I18N_LANGS); do \
		./scripts/validate_presets_i18n.py --localization ./meta/presets_$$lang.json || exit $$?; \
	done

validate-presets-i18n: validate-presets-i18n-all

validate-presets-%:
	./scripts/validate_presets_i18n.py --localization ./meta/presets_$*.json

sprites-64:
	./scripts/build_sprites_64.py

clean:
	rm -f $(SPRITES_DIR)/sprites*.json $(SPRITES_DIR)/sprites*.png

serve:
	http-server
