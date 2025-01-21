#!/bin/bash

# Find all Python files recursively, excluding venv directories,
# count lines in each file, and store results in a temporary file
find . -name "*.py" -type f -not -path "*/venv/*" | while read -r file; do
    # Get relative path by removing "./" prefix
    rel_path=${file#./}
    # Count number of lines in file
    num_lines=$(wc -l < "$file")
    # Output to temporary file with padding for proper sorting
    printf "%08d %s\n" "$num_lines" "$rel_path"
done | sort -nr | while read -r line; do
    # Remove padding and format output with no leading zeros
    count=${line%% *}            # Get the padded number
    count=$((10#${count}))       # Convert to decimal, removing leading zeros
    path=${line:8}              # Get the file path
    echo "$path: $count lines"
done