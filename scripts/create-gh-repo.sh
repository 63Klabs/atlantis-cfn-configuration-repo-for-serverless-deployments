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
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <repository-name> <source-url> [aws-profile]"
    echo "source-url can be either an S3 URL (s3://) or GitHub URL (https://github.com/)"
    exit 1
fi

REPO_NAME=$1
SOURCE_URL=$2
AWS_PROFILE=${3:-default}  # Use provided profile or 'default' if not specified

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

# Download content based on URL type
echo "Downloading content..."
if [[ "$SOURCE_URL" == s3://* ]]; then
    echo "Downloading from S3..."
    aws s3 cp "$SOURCE_URL" "$TEMP_DIR/content.zip" --profile "$AWS_PROFILE" || {
        echo "Failed to download from S3"
        exit 1
    }
elif [[ "$SOURCE_URL" == https://github.com/* ]]; then
    echo "Downloading from GitHub..."
    # Extract the archive URL from the GitHub repository URL
    # Convert URL from https://github.com/owner/repo to https://github.com/owner/repo/archive/refs/heads/main.zip
    GITHUB_ARCHIVE_URL="${SOURCE_URL%/}/archive/refs/heads/main.zip"
    curl -L "$GITHUB_ARCHIVE_URL" -o "$TEMP_DIR/content.zip" || {
        echo "Failed to download from GitHub"
        exit 1
    }
else
    echo "Error: Invalid URL format. Must start with 's3://' or 'https://github.com/'. If downloading from GitHub only include the repository URL, not the ZIP download URL"
    exit 1
fi

echo "Extracting content..."
cd "$TEMP_DIR" || exit 1
unzip -q content.zip || {
    echo "Failed to extract zip file"
    exit 1
}
rm content.zip

# If downloaded from GitHub, content will be in a subdirectory
if [[ "$SOURCE_URL" == https://github.com/* ]]; then
    # Move contents from the subdirectory up one level
    mv */* . 2>/dev/null || true
    # Clean up empty subdirectory
    rm -rf */
fi

# Initialize git and push content
echo "Initializing git repository and pushing content..."
git init
git add .
git commit -m "Initial commit from template"
git branch -M main
git remote add origin "https://github.com/$(gh api user -q .login)/$REPO_NAME.git"
git push -u origin main

# Get and display the HTTPS clone URL
CLONE_URL="https://github.com/$(gh api user -q .login)/$REPO_NAME.git"
echo "Repository setup complete!"
echo "HTTPS Clone URL: $CLONE_URL"
