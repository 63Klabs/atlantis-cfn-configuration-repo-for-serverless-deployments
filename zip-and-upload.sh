#!/bin/bash

# This script will zip and upload each of the application-infrastructure-examples 
# to an s3 bucket for use in the download-and-unzip command.
# Usage: ./zip-and-upload.sh <s3-bucket-name>
# 
# Important Notes:
# - Make this script executable: chmod +x zip-and-upload.sh
# - Ensure you have the AWS CLI installed and configured with appropriate permissions
# - The AWS credentials should have permission to upload to the specified S3 bucket [3]
# - The script uses a temporary directory for processing which is automatically cleaned up
# - You can include this script in your CI/CD pipeline

# Check if aws-cli is installed
if ! command -v aws &> /dev/null; then
    echo "Error: aws-cli is not installed. Please install it and configure your credentials."
    exit 1
fi
#!/bin/bash

# Check if bucket name and profile are provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <s3-bucket-name> <aws-profile>"
    exit 1
fi

BUCKET_NAME="$1"
AWS_PROFILE="$2"
BASE_DIR="application-infrastructure-examples"

# Check if aws-cli is installed
if ! command -v aws &> /dev/null; then
    echo "Error: aws-cli is not installed. Please install it and configure your credentials."
    exit 1
fi

# Check if the profile exists
if ! aws configure list --profile "$AWS_PROFILE" &> /dev/null; then
    echo "Error: AWS profile '$AWS_PROFILE' not found"
    exit 1
fi

# Check if the base directory exists
if [ ! -d "$BASE_DIR" ]; then
    echo "Error: Directory $BASE_DIR not found"
    exit 1
fi

# Create a temporary directory for our work
TEMP_DIR=$(mktemp -d)

# Function to clean up temp directory
cleanup() {
    rm -rf "$TEMP_DIR"
}

# Register cleanup function to run on script exit
trap cleanup EXIT

# Go into the base directory
cd "$BASE_DIR" || exit 1

# Process each directory
for dir in */; do
    # Remove trailing slash from directory name
    dir_name=${dir%/}
    
    # Create a temporary work directory for this specific directory
    WORK_DIR="$TEMP_DIR/$dir_name"
    mkdir -p "$WORK_DIR"
    
    # Copy contents to work directory
    cp -r "$dir_name"/* "$WORK_DIR"
    
    # Create zip file from work directory contents
    (cd "$WORK_DIR" && zip -r "$TEMP_DIR/$dir_name.zip" .)
    
    # Upload to S3 with specified profile
    echo "Uploading $dir_name.zip to S3..."
    aws s3 cp "$TEMP_DIR/$dir_name.zip" "s3://$BUCKET_NAME/starter-app/$dir_name.zip" --profile $AWS_PROFILE
    
    # Check if upload was successful
    if [ $? -eq 0 ]; then
        echo "Successfully uploaded $dir_name.zip"
    else
        echo "Failed to upload $dir_name.zip"
    fi
    
    # Clean up the work directory
    rm -rf "$WORK_DIR"
done

echo "All directories processed and uploaded to S3"
