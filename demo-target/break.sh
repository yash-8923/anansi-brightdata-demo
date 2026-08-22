#!/usr/bin/env bash
# Swap the live demo-target page between healthy and broken markup, so the
# self-heal moment in the demo video is real, not staged after the fact.
#
# Usage:
#   ./break.sh break      # deploy index-broken.html as the live index.html
#   ./break.sh restore    # deploy index-original.html as the live index.html
#
# Serve this folder with GitHub Pages (or any static host). Commit + push
# after each run so the live URL actually changes before you scrape/heal it.

set -euo pipefail
cd "$(dirname "$0")"

case "${1:-}" in
  break)
    cp index-broken.html index.html
    echo "index.html now serves the BROKEN markup."
    echo "Next: git add -A && git commit -m 'break demo page' && git push"
    echo 'Then: bdata scraper heal <collector_id> "price moved into a nested span, title class renamed" --url <your-pages-url> --pretty -o heal.json'
    ;;
  restore)
    cp index-original.html index.html
    echo "index.html restored to the ORIGINAL markup."
    echo "Next: git add -A && git commit -m 'restore demo page' && git push"
    ;;
  *)
    echo "Usage: $0 {break|restore}"
    exit 1
    ;;
esac
