icon:
	./scripts/check-icon-sizes.sh
	mkdir -p ./sprites
	spreet ./icons ./sprites/sprites
	./scripts/merge_vendor_sprite_keys.py --ratio 1

retina:
	./scripts/check-icon-sizes.sh
	spreet --retina ./icons ./sprites/sprites@2x
	./scripts/merge_vendor_sprite_keys.py --ratio 2

	#serve static files
serve:
	http-server
