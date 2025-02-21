#!/bin/bash

# Remove existing content.txt if it exists
rm -f content.txt

# Find all .py files in current directory and subdirectories, excluding venv directories
find . -type f -name "*.py" -not -path "*/venv/*" | while read -r file; do
    # Add a separator line
    echo "=== $file ===" >> content.txt
    
    # Add an empty line for readability
    echo "" >> content.txt
    
    # Cat the content of the file
    cat "$file" >> content.txt
    
    # Add two empty lines between files for better readability
    echo -e "\n\n" >> content.txt
done

echo "All Python files (excluding venv) have been concatenated into content.txt"