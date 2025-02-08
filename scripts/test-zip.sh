#!/bin/bash

# Check if name parameter is provided
if [ $# -ne 3 ]; then
    echo "Usage: $0 <bucket> <profile> <name>"
    echo "Example: $0 mybucket default myapp"
    exit 1
fi

PROFILE=$2
NAME=$3
BUCKET=$1
PREFIX="atlantis/app-starters/v2"
TEMP_DIR=$(mktemp -d)
S3_PATH="s3://${BUCKET}/${PREFIX}/${NAME}.zip"

# Change to temp directory
cd "$TEMP_DIR" || exit 1

# Create test.txt with content
echo "Hello, World from $NAME" > test.txt

# Create zip file
zip "${NAME}.zip" test.txt

# Upload to S3
if aws s3 cp "${NAME}.zip" "$S3_PATH" --profile $PROFILE; then
    echo "Successfully uploaded to $S3_PATH"
else
    echo "Failed to upload to $S3_PATH"
    exit 1
fi

# Cleanup
rm -rf "$TEMP_DIR"
