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

	#serve static files
serve:
	http-server
