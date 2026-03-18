#!/bin/bash

set -o errexit
set -o nounset
set -o xtrace

cd "$(dirname "$0")" || exit 1

cp -f TSAF.md ../beatunes-dbviewer
cp -f src/djay_tsaf_parser/lib_tsaf_parser.py ../beatunes-dbviewer/src/music_stuff/lib/
