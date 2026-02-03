icon:
	./scripts/check-icon-sizes.sh
	mkdir -p ./sprites
	spreet ./icons ./sprites/sprites

retina:
	./scripts/check-icon-sizes.sh
	spreet --retina ./icons ./sprites/sprites@2x

	#serve static files
serve:
	http-server
