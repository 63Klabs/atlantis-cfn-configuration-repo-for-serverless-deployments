#!/usr/bin/env python3

# https://pygithub.readthedocs.io/en/latest/introduction.html

VERSION = "v0.1.0/2025-02-28"
# Created by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

import os
import boto3
import tempfile
import shutil
from github import Github, Auth
from pathlib import Path
import zipfile

def list_s3_zips(bucket_name):
    """List all zip files in the specified S3 bucket"""
    s3_client = boto3.client('s3')
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' not in response:
            return []
        
        return [obj['Key'] for obj in response['Contents'] 
                if obj['Key'].endswith('.zip')]
    except Exception as e:
        print(f"Error listing S3 bucket contents: {str(e)}")
        return []

def download_and_extract_zip(bucket_name, zip_key, temp_dir):
    """Download zip from S3 and extract to temporary directory"""
    s3_client = boto3.client('s3')
    zip_path = os.path.join(temp_dir, 'template.zip')
    
    try:
        s3_client.download_file(bucket_name, zip_key, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
    except Exception as e:
        print(f"Error downloading/extracting zip: {str(e)}")
        raise

def create_github_repo(github_token, repo_name, is_private=True):
    """Create a new GitHub repository"""
    g = Github(github_token)
    user = g.get_user()
    
    try:
        repo = user.create_repo(
            repo_name,
            private=is_private,
            auto_init=False
        )
        return repo
    except Exception as e:
        print(f"Error creating GitHub repository: {str(e)}")
        raise

def push_to_github(repo_url, local_dir, github_token):
    """Initialize git repo and push to GitHub"""
    import git
    try:
        repo = git.Repo.init(local_dir)
        repo.git.add(A=True)
        repo.git.commit('-m', 'Initial commit')
        
        # Set up the remote with authentication
        remote_url = f"https://x-access-token:{github_token}@github.com/{repo_url[19:]}"
        origin = repo.create_remote('origin', remote_url)
        origin.push('master')
    except Exception as e:
        print(f"Error pushing to GitHub: {str(e)}")
        raise

def main():
    # Get GitHub token from environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        return
    
    # Get S3 bucket name from settings or environment
    bucket_name = os.getenv('CONFIG_S3_BUCKET')
    if not bucket_name:
        print("Error: CONFIG_S3_BUCKET environment variable not set")
        return

    # List available zip files
    zip_files = list_s3_zips(bucket_name)
    if not zip_files:
        print("No zip files found in the bucket")
        return

    # Display available templates
    print("\nAvailable templates:")
    for idx, zip_file in enumerate(zip_files, 1):
        print(f"{idx}. {zip_file}")

    # Get user selection
    selection = int(input("\nSelect template number: ")) - 1
    if selection < 0 or selection >= len(zip_files):
        print("Invalid selection")
        return

    # Get repository name
    repo_name = input("Enter new repository name: ")

    # Create temporary directory for files
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Download and extract selected zip
            print(f"\nDownloading and extracting {zip_files[selection]}...")
            download_and_extract_zip(bucket_name, zip_files[selection], temp_dir)

            # Create GitHub repository
            print(f"Creating GitHub repository '{repo_name}'...")
            repo = create_github_repo(github_token, repo_name)

            # Push files to GitHub
            print("Pushing files to GitHub...")
            push_to_github(repo.clone_url, temp_dir, github_token)

            print(f"\nSuccess! Repository created at: {repo.html_url}")

        except Exception as e:
            print(f"Error: {str(e)}")
            return

if __name__ == "__main__":
    main()
