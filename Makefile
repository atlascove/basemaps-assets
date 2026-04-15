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

	#serve static files
serve:
	http-server
