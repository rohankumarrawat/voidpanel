#!/bin/bash
# Clean up Django source code files that were leaked into user public_html directories
set -euo pipefail

echo "=== Cleaning leaked Django source from user public_html directories ==="

DANGEROUS_FILES=(
    "settings.py"
    "views.py"
    "views.py.bak"
    "urls.py"
    "ai_api.py"
    "asgi.py"
    "wsgi.py"
    "context_processors.py"
    "domain_client.py"
    "provisioner.py"
    "__init__.py"
    "._views.py"
    ".DS_Store"
    "pothole_pollution_data.csv"
    "rf_landslide_classifier.pkl"
    "site_middleware.py"
)

DANGEROUS_DIRS=(
    "__pycache__"
    "management"
    "static"
)

cleaned=0

for user_dir in /home/*/public_html; do
    [ -d "$user_dir" ] || continue
    username=$(basename $(dirname "$user_dir"))

    # Skip system directories
    [[ "$username" == "voidonyx" || "$username" == "voidpanelc091" ]] && continue

    for f in "${DANGEROUS_FILES[@]}"; do
        target="$user_dir/$f"
        if [ -f "$target" ]; then
            rm -f "$target"
            echo "  Removed: $target"
            ((cleaned++)) || true
        fi
    done

    for d in "${DANGEROUS_DIRS[@]}"; do
        target="$user_dir/$d"
        if [ -d "$target" ]; then
            rm -rf "$target"
            echo "  Removed dir: $target"
            ((cleaned++)) || true
        fi
    done
done

echo ""
echo "=== Cleaned $cleaned leaked files/dirs ==="
