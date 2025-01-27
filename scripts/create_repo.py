import boto3
import tempfile
import zipfile
import base64
import os
import argparse
import sys
from urllib.parse import urlparse

def parse_s3_url(s3_url):
    """Parse an S3 URL into bucket and key."""
    parsed = urlparse(s3_url)
    if parsed.scheme != 's3':
        raise ValueError("URL must be an S3 URL starting with 's3://'")
    return parsed.netloc, parsed.path.lstrip('/')

def create_and_seed_repository(repo_name: str, s3_url: str, profile: str):
    # Create boto3 session with specified profile
    try:
        session = boto3.Session(profile_name=profile)
        codecommit = session.client('codecommit')
        s3 = session.client('s3')
    except Exception as e:
        print(f"Error creating AWS session with profile '{profile}': {str(e)}")
        sys.exit(1)

    # Parse S3 URL
    try:
        s3_bucket, s3_key = parse_s3_url(s3_url)
    except ValueError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    
    # Create the repository
    try:
        print(f"Creating repository: {repo_name}")
        response = codecommit.create_repository(
            repositoryName=repo_name,
            repositoryDescription=f'Repository seeded from {s3_url}'
        )
        print(f"Repository created: {response['repositoryMetadata']['cloneUrlHttp']}")
    except codecommit.exceptions.RepositoryNameExistsException:
        print(f"Error: Repository {repo_name} already exists")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating repository: {str(e)}")
        sys.exit(1)
    
    # Download and process the zip file
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, 'source.zip')
        
        try:
            print(f"Downloading zip from S3: {s3_url}")
            s3.download_file(s3_bucket, s3_key, zip_path)
        except Exception as e:
            print(f"Error downloading zip file: {str(e)}")
            codecommit.delete_repository(repositoryName=repo_name)
            sys.exit(1)
        
        # Extract files
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            os.remove(zip_path)  # Remove the zip file to not include it
        except Exception as e:
            print(f"Error extracting zip file: {str(e)}")
            codecommit.delete_repository(repositoryName=repo_name)
            sys.exit(1)

        # Prepare files for commit
        put_files = []
        for root, _, files in os.walk(temp_dir):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, temp_dir)
                
                try:
                    with open(full_path, 'rb') as f:
                        content = f.read()
                        put_files.append({
                            'filePath': relative_path,
                            'fileContent': base64.b64encode(content).decode('utf-8')
                        })
                except Exception as e:
                    print(f"Error processing file {relative_path}: {str(e)}")
                    codecommit.delete_repository(repositoryName=repo_name)
                    sys.exit(1)

        # Create initial commit
        try:
            print("Creating initial commit")
            codecommit.create_commit(
                repositoryName=repo_name,
                branchName='main',
                putFiles=put_files,
                commitMessage=f'Initial commit: Seeded from {s3_url}'
            )
            print(f"\nRepository {repo_name} seeded successfully!")
            print(f"Clone URL (HTTPS): {response['repositoryMetadata']['cloneUrlHttp']}")
            print(f"Clone URL (SSH): {response['repositoryMetadata']['cloneUrlSsh']}")
        except Exception as e:
            print(f"Error creating initial commit: {str(e)}")
            codecommit.delete_repository(repositoryName=repo_name)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Create and seed a CodeCommit repository from an S3 zip file')
    parser.add_argument('repository_name', help='Name of the CodeCommit repository to create')
    parser.add_argument('s3_url', help='S3 URL of the zip file (e.g., s3://bucket-name/path/to/file.zip)')
    parser.add_argument('profile', help='AWS profile name to use')
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Validate AWS profile exists
    try:
        session = boto3.Session(profile_name=args.profile)
        session.client('sts').get_caller_identity()
    except Exception as e:
        print(f"Error: Invalid AWS profile '{args.profile}': {str(e)}")
        sys.exit(1)

    create_and_seed_repository(args.repository_name, args.s3_url, args.profile)

if __name__ == "__main__":
    main()
