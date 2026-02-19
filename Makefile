icon:
	./scripts/check-icon-sizes.sh
	mkdir -p ./sprites
	spreet ./icons ./sprites/sprites
	./scripts/build_sdf_icons.py ./icons ./icons_sdf64
	spreet --sdf ./icons_sdf64 ./sprites/sprites_sdf

retina:
	./scripts/check-icon-sizes.sh
	spreet --retina ./icons ./sprites/sprites@2x
	./scripts/build_sdf_icons.py ./icons ./icons_sdf64
	spreet --sdf --retina ./icons_sdf64 ./sprites/sprites_sdf@2x

sdf:
	mkdir -p ./sprites
	./scripts/build_sdf_icons.py ./icons ./icons_sdf64
	spreet --sdf ./icons_sdf64 ./sprites/sprites_sdf

sdf_retina:
	./scripts/build_sdf_icons.py ./icons ./icons_sdf64
	spreet --sdf --retina ./icons_sdf64 ./sprites/sprites_sdf@2x

	#serve static files
serve:
	http-server
