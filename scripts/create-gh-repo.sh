#!/bin/bash

# Prerequisites:
# - GitHub CLI ( gh) installed and authenticated
# - AWS CLI installed and configured
# - Git installed
# - Appropriate permissions to access the S3 bucket

# The script:
# - Creates a new private GitHub repository
# - Creates a temporary directory
# - Downloads and extracts the S3 content
# - Initializes a git repository
# - Commits and pushes the content
# - Cleans up the temporary directory

# Error handling is included for each major step, and the 
# temporary directory is cleaned up whether the script succeeds or fails.

# Check if two arguments are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <repository-name> <s3-url>"
    exit 1
fi

REPO_NAME=$1
S3_URL=$2
TEMP_DIR=$(mktemp -d)

# Exit if temp directory creation failed
if [ ! -d "$TEMP_DIR" ]; then
    echo "Failed to create temp directory"
    exit 1
fi

# Cleanup function
cleanup() {
    echo "Cleaning up temporary directory..."
    rm -rf "$TEMP_DIR"
}

# Set trap to ensure cleanup on script exit
trap cleanup EXIT

# Create GitHub repository
echo "Creating GitHub repository: $REPO_NAME"
gh repo create "$REPO_NAME" --private --confirm || {
    echo "Failed to create repository"
    exit 1
}

# Download and extract the S3 content
echo "Downloading content from S3..."
aws s3 cp "$S3_URL" "$TEMP_DIR/content.zip" || {
    echo "Failed to download from S3"
    exit 1
}

echo "Extracting content..."
cd "$TEMP_DIR" || exit 1
unzip -q content.zip || {
    echo "Failed to extract zip file"
    exit 1
}
rm content.zip

# Initialize git and push content
echo "Initializing git repository and pushing content..."
git init
git add .
git commit -m "Initial commit from S3 template"
git branch -M main
git remote add origin "https://github.com/$(gh api user -q .login)/$REPO_NAME.git"
git push -u origin main

# Get and display the HTTPS clone URL
CLONE_URL="https://github.com/$(gh api user -q .login)/$REPO_NAME.git"
echo "Repository setup complete!"
echo "HTTPS Clone URL: $CLONE_URL"
