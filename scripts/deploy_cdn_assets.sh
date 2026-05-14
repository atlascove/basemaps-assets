#!/usr/bin/env bash
set -euo pipefail

bucket="${FOTOSHI_ASSETS_BUCKET:-fotoshi-api-dev-images-berhnarv}"
prefix="${FOTOSHI_ASSETS_PREFIX:-assets}"
distribution_id="${FOTOSHI_CDN_DISTRIBUTION_ID:-E6X9B0BNEVD21}"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

aws s3 cp "$root/sprites" "s3://$bucket/$prefix/sprites" --recursive

for sprite_file in "$root"/sprites/sprites*.json "$root"/sprites/sprites*.png; do
  [[ -e "$sprite_file" ]] || continue
  name="$(basename "$sprite_file")"
  case "$name" in
    *.json) content_type="application/json" ;;
    *.png) content_type="image/png" ;;
    *) content_type="application/octet-stream" ;;
  esac

  aws s3 cp "$sprite_file" "s3://$bucket/$prefix/sprites/$name" \
    --cache-control "public, max-age=300, must-revalidate" \
    --content-type "$content_type"
done

aws s3 sync "$root/fonts" "s3://$bucket/$prefix/fonts" \
  --exclude "fonts.json" \
  --cache-control "public, max-age=31536000, immutable"

if [[ -f "$root/fonts/fonts.json" ]]; then
  aws s3 cp "$root/fonts/fonts.json" "s3://$bucket/$prefix/fonts/fonts.json" \
    --cache-control "public, max-age=300, must-revalidate" \
    --content-type "application/json"
fi

if [[ -n "$distribution_id" ]]; then
  aws cloudfront create-invalidation \
    --distribution-id "$distribution_id" \
    --paths "/$prefix/sprites/*" "/$prefix/fonts/*"
fi
