#!/bin/bash

# Directory to search for TeX files
DIRECTORY=${1:-.}

# Find and compile TeX files
find "$DIRECTORY" -name "*.tex" -print0 | xargs -0 -I {} pdflatex -interaction=nonstopmode {}

echo "Compilation complete."
