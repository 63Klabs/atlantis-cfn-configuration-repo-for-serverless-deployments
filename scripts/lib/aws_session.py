#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-22"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer

# Usage:
# In your script:
# from lib.aws_session import AWSSessionManager

# # Create a session manager
# session_manager = AWSSessionManager(profile="my-profile")

# # Get a client for any AWS service
# s3_client = session_manager.get_client('s3')
# sts_client = session_manager.get_client('sts')


import os
import subprocess
import configparser
import time
import boto3
from typing import Optional, Any
from botocore.exceptions import ClientError, TokenRetrievalError

from lib.logger import ConsoleAndLog

class AWSSessionManager:
    def __init__(self, profile: Optional[str] = None) -> None:
        self.profile = profile
        self.session = None
        self.s3_client = None
        self.refresh_credentials()

    def refresh_credentials(self) -> None:
        """Initialize or refresh AWS credentials with support for both SSO and IAM"""
        if not self.profile:
            return
            
        ConsoleAndLog.info(f"Using AWS profile: {self.profile}")
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # First try to create a session with existing credentials
                self.session = boto3.Session(profile_name=self.profile)
                credentials = self.session.get_credentials()
                
                if not credentials:
                    raise TokenRetrievalError("No credentials found in profile")
                
                # Test if credentials are valid
                sts = self.session.client('sts')
                try:
                    sts.get_caller_identity()
                    # If we get here, credentials are valid
                    self.s3_client = self.session.client('s3')
                    ConsoleAndLog.info("Using existing valid credentials")
                    return
                except ClientError as e:
                    if 'ExpiredToken' in str(e) or 'InvalidClientTokenId' in str(e):
                        # Check if this is an SSO profile
                        if self._is_sso_profile():
                            self._refresh_sso_login()
                        else:
                            raise TokenRetrievalError(
                                "Credentials have expired. For IAM users, please update your credentials "
                                "using 'aws configure' or by setting environment variables."
                            )
                    else:
                        raise
                
                # Create new session and verify after potential refresh
                self.session = boto3.Session(profile_name=self.profile)
                self.s3_client = self.session.client('s3')
                return
                
            except Exception as e:
                retry_count += 1
                ConsoleAndLog.warning(f"Credential refresh attempt {retry_count}/{max_retries} failed: {str(e)}")
                
                if retry_count >= max_retries:
                    ConsoleAndLog.error("Failed to refresh credentials after maximum retries")
                    raise
                
                time.sleep(2)

    def _is_sso_profile(self) -> bool:
        """Check if the current profile is configured for SSO"""
        try:
            config = configparser.ConfigParser()
            config_path = os.path.expanduser("~/.aws/config")
            
            if not os.path.exists(config_path):
                return False
                
            config.read(config_path)
            profile_section = f"profile {self.profile}" if self.profile != "default" else "default"
            
            if profile_section not in config:
                return False
                
            # Check for SSO-specific configuration keys
            sso_keys = ['sso_start_url', 'sso_region', 'sso_account_id', 'sso_role_name']
            return any(key in config[profile_section] for key in sso_keys)
            
        except Exception as e:
            ConsoleAndLog.warning(f"Error checking SSO profile configuration: {str(e)}")
            return False

    def _refresh_sso_login(self) -> None:
        """Execute AWS SSO login command for specific profile"""
        try:
            ConsoleAndLog.info(f"Initiating SSO login for profile {self.profile}")
            
            result = subprocess.run(
                ["aws", "sso", "login", "--profile", self.profile],
                check=True,
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                ConsoleAndLog.info(f"SSO login output: {result.stdout}")
            if result.stderr:
                ConsoleAndLog.warning(f"SSO login warnings: {result.stderr}")
                
        except subprocess.CalledProcessError as e:
            error_msg = (
                f"SSO login failed for profile {self.profile}. "
                "If you're using IAM credentials, please ensure your profile is properly configured."
            )
            if e.stdout:
                error_msg += f"\nOutput: {e.stdout}"
            if e.stderr:
                error_msg += f"\nError: {e.stderr}"
            ConsoleAndLog.error(error_msg)
            raise TokenRetrievalError(error_msg)

    def get_session(self) -> boto3.Session:
        """Get the current boto3 session"""
        return self.session

    def get_client(self, service_name: str) -> Any:
        """Get a boto3 client for the specified service"""
        if not self.session:
            raise ValueError("No valid session available")
        return self.session.client(service_name)
