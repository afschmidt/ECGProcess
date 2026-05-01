#!/usr/bin/env bash
# NOTE execute from the build directory
set -euo pipefail

META="meta.yaml"

# Extract build number (assumes simple format)
BUILD_NUM=$(grep -E '^\s*number:\s*[0-9]+' "$META" | awk '{print $2}')
echo "Current build number is: $BUILD_NUM"

read -p "Would you like to (i)ncrement, (d)ecrement, (k)eep as is? [i/d/k] " REPLY

case $REPLY in
  i)
    NEW_NUM=$((BUILD_NUM + 1))
    ;;
  d)
    NEW_NUM=$((BUILD_NUM - 1))
    if [ "$NEW_NUM" -lt 0 ]; then
      echo "Build number cannot be negative."
      exit 1
    fi
    ;;
  k)
    echo "Keeping build number at $BUILD_NUM"
    NEW_NUM=$BUILD_NUM
    ;;
  *)
    echo "Invalid input. Please choose i/d/k."
    exit 1
    ;;
esac

if [ "$NEW_NUM" != "$BUILD_NUM" ]; then
  echo "Updating build number to $NEW_NUM..."
  sed -i "s/^\(\s*number:\s*\)$BUILD_NUM/\1$NEW_NUM/" "$META"
fi

echo "Running conda build..."
conda build .

