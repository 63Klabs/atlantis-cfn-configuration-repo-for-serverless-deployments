#!/usr/bin/env python3

VERSION = "v0.0.1/2025-05-21"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer and GitHub Copilot

"""
Utility functions for interacting with GitHub repositories.
"""

import requests
import tempfile
import os
import shutil
import subprocess
import json

from typing import Dict, Optional

# =============================================================================
# ----- GITHUB UTILS ----------------------------------------------------------
# =============================================================================

class GitHubUtils:

    @staticmethod
    def parse_repo_info_from_url(url: str) -> Dict[str, str]:
        """
        Parse GitHub repository information from a URL.
        
        Args:
            url (str): GitHub repository URL
        
        Returns:
            Dict[str, str]: Dictionary containing 'owner', 'repo', and 'tag' keys
        """
        # Remove the protocol (http/https) and split by '/'
        parts = url.split("://")[-1].split("/")

        owner = None
        repo = None
        tag = None
        
        if parts[0] == "github.com":
        # Extract owner and repo name
            if len(parts) >= 3:
                owner = parts[1]
                repo = parts[2]
                # Extract tag if present: https://github.com/63Klabs/atlantis-cfn-configuration-repo-for-serverless-deployments/releases/tag/0.0.8-beta
                if len(parts) >= 5 and parts[3] == "releases" and parts[4] == "tag":
                    tag = parts[5]
                # https://github.com/63Klabs/atlantis-cfn-configuration-repo-for-serverless-deployments/archive/refs/tags/0.0.8-beta.zip
                elif len(parts) >= 7 and parts[3] == "archive" and parts[4] == "refs" and parts[5] == "tags":
                    tag = parts[6].split(".")[0]

                return {
                    "owner": owner,
                    "repo": repo,
                    "tag": tag
                }
            else:
                raise ValueError("Invalid GitHub URL format")
        else:
            raise ValueError("Invalid GitHub URL format")


    @staticmethod
    def get_latest_release(owner: str, repo: str) -> str:
        """
        Get the latest release tag from a GitHub repository
        
        Args:
            owner (str): GitHub repository owner
            repo (str): GitHub repository name
        
        Returns:
            str: Latest release tag (e.g. 'v1.0.0')
        """
        try:
            # Query the GitHub API for latest release
            response = requests.get(
                f"https://api.github.com/repos/{owner}/{repo}/releases/latest",
                headers={
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            response.raise_for_status()
            
            # Extract the tag name from the response
            return response.json()['tag_name']
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get latest release: {str(e)}")
        
    @staticmethod
    def download_zip_from_url(url: str, zip_path: Optional[str] = None) -> str:
        """
        Download a ZIP file from a GitHub repository URL
        Args:
            url (str): GitHub repository URL
        Returns:
            str: Path to the downloaded ZIP file
        """

        # Create a temporary file path with .zip extension
        if zip_path is None:
            zip_path = tempfile.mktemp(suffix='.zip')
       
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()  # Raise an exception for HTTP errors
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return zip_path
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to download ZIP file: {str(e)}")

    @staticmethod
    def create_repo(repo_name: str, private: bool = True, description: str = None) -> Dict:
        """
        Create a GitHub repository using the GitHub CLI

        Args:
            repo_name (str): Repository name
            private (bool): Whether the repository should be private
            description (str): Repository description

        Returns:
            Bool: True if repository was created successfully, False otherwise
            
        Raises:
            Exception: If the repository creation fails
        """
        try:
            
            # Build the command
            cmd = ["gh", "repo", "create", repo_name]

            if private:
                cmd.append("--private")
            else:
                cmd.append("--public")
                
            if description:
                cmd.extend(["--description", description])
                            
            # Execute the command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create repository: {e.stderr}")
        except Exception as e:
            raise Exception(f"Failed to create repository: {e}")
        
    @staticmethod
    def repository_exists(repo_name: str) -> bool:
        """
        Check if a GitHub repository exists using the GitHub CLI.
        Args:
            repo_name (str): Repository name (e.g., "owner/repo")
        
        Returns:
            bool: True if repository exists, False otherwise
        """
        try:
            # Use gh CLI to check if the repository exists
            result = subprocess.run(
                ["gh", "repo", "view", repo_name],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            raise Exception(f"Failed to check repository existence: {str(e)}")
        
    @staticmethod
    def get_repository(repo_name: str) -> Dict[str, str]:
        """
        Get information about a GitHub repository using the GitHub CLI.
        Args:
            repo_name (str): Repository name (e.g., "owner/repo")
        Returns:
            Dict[str, str]: Dictionary containing 'exists' and 'repositoryMetadata' keys
        """
        try:
            # Use gh CLI to get repository information
            result = subprocess.run(
                ["gh", "repo", "view", repo_name, "--json", "name,nameWithOwner,owner,repositoryTopics,sshUrl,isTemplate,templateRepository,visibility,url"],
                capture_output=True,
                text=True,
                check=True
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                info["cloneUrlHttp"] = f"{info.get('url')}.git"
                info["cloneUrlSsh"] = f"{info.get('sshUrl')}"
                return {
                    "exists": True,
                    "repositoryMetadata": info
                }
            else:
                raise Exception(f"Failed to get repository info: {result.stderr}")
        except Exception as e:
            raise Exception(f"Failed to get repository info: {str(e)}")
    
    @staticmethod
    def create_branch_structure(repo_name: str, readme_content: str, author: str, email: str):
        """
        Create main, test, and dev branches in a GitHub repo using the gh CLI.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            # Clone the repo
            subprocess.run(["gh", "repo", "clone", repo_name, temp_dir], check=True)
            os.chdir(temp_dir)

            # Set git user config
            subprocess.run(["git", "config", "user.name", author], check=True)
            subprocess.run(["git", "config", "user.email", email], check=True)

            # Ensure main branch exists and checkout
            subprocess.run(["git", "checkout", "-B", "main"], check=True)

            # Write README.md
            with open("README.md", "w") as f:
                f.write(readme_content)

            subprocess.run(["git", "add", "README.md"], check=True)
            subprocess.run(["git", "commit", "-m", "Initial README.md commit"], check=True)
            subprocess.run(["git", "push", "-u", "origin", "main"], check=True)

            # Create and push test branch from main
            subprocess.run(["git", "checkout", "-b", "test"], check=True)
            subprocess.run(["git", "push", "-u", "origin", "test"], check=True)

            # Create and push dev branch from test
            subprocess.run(["git", "checkout", "-b", "dev"], check=True)
            subprocess.run(["git", "push", "-u", "origin", "dev"], check=True)

        finally:
            os.chdir("/")
            shutil.rmtree(temp_dir, ignore_errors=True)
