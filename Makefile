icon:
	mkdir -p ./sprites
	spreet ./icons ./sprites/sprites

retina:
	spreet --retina ./icons ./sprites/sprites@2x

	#serve static files
serve:
	http-server
