#!/bin/sh
# This is assumed to be running from the root of the repo
echo "[pages] running in: $PWD"

# Ensure the documentation build directory is present
mkdir -p ./docs/build

# Copy the current README over and change any image locations for it
# NOTE currently no images are used.
# cp README.md docs/source/getting_started.md
# sed -i 's/\.\/docs\/source\///' docs/source/getting_started.md
# sed -i 's|src="\./resources/images|src="./_static/images|'  docs/source/getting_started.md

# Process any data dictionary files
# NOTE USED TO PARSE TABLES 
# mkdir -p docs/source/data_dict
# for i in ./resources/data_dict/*.txt; do
#     outfile="$(basename "$i" | sed 's/\.txt/.rst/')"
#     doc-column-list "$i" ./docs/source/data_dict/"$outfile"
# done

# Copy the images over to the source static directory
# mkdir -p docs/source/_static
# cp ./resources/images/*.png ./docs/source/_static/

cd docs
make html
cd ..
echo "[pages] removing public"

echo "[pages] removing public"
if [[ -e public ]]; then
    rm -r public
fi
echo "[pages] creating public"
mkdir -p public
echo "[pages] moving HTML to public"
mv docs/build/html/* public/
echo "[pages] PWD: $PWD"
echo "[pages] contents of public"
ls "$PWD"/public
