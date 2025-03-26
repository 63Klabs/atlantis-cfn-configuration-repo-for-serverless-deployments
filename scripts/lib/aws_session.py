#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-28"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer

"""
AWS Session Manager for scripts using boto3
Automatically detects if a session needs to be refreshed and (if SSO) invokes the sso login

Usage:
In your script:
from lib.aws_session import AWSSessionManager

# Create a session manager
session_manager = AWSSessionManager(profile="my-profile")

# Get a client for any AWS service
s3_client = session_manager.get_client('s3')
sts_client = session_manager.get_client('sts')
"""


import os
import subprocess
import configparser
import time
import boto3
from typing import Optional, Any
import botocore.credentials
from botocore.exceptions import ClientError, TokenRetrievalError

from lib.logger import ConsoleAndLog

class TokenRetrievalError(Exception):
    """Custom exception for AWS token retrieval failures"""
    pass

class AWSSessionManager:
    def __init__(self, profile: Optional[str] = None, region: Optional[str] = None, no_browser: Optional[bool] = False) -> None:
        self.profile = profile
        self.region = region
        self.session = None
        self.no_browser = no_browser
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
                
                # Test if credentials are valid using STS
                try:
                    sts = self.session.client('sts')
                    sts.get_caller_identity()
                    ConsoleAndLog.info("Using existing valid credentials")
                    print()
                    return
                except ClientError as e:
                    error_message = str(e)
                    if ("ExpiredToken" in error_message or 
                        "InvalidClientTokenId" in error_message or 
                        "Token has expired" in error_message):
                        if self._is_sso_profile():
                            ConsoleAndLog.info("Token expired. Initiating SSO login...")
                            self._refresh_sso_login()
                            # Create new session after SSO login
                            self.session = boto3.Session(profile_name=self.profile)
                            # Verify the new session
                            sts = self.session.client('sts')
                            sts.get_caller_identity()
                            ConsoleAndLog.info("Successfully refreshed SSO credentials")
                            return
                        else:
                            raise TokenRetrievalError(
                                "Credentials have expired. For IAM users, please update your credentials "
                                "using 'aws configure' or by setting environment variables."
                            )
                    else:
                        raise
                        
            except Exception as e:
                if "Token has expired" in str(e) and self._is_sso_profile():
                    ConsoleAndLog.info("Token expired. Initiating SSO login...")
                    try:
                        self._refresh_sso_login()
                        self.session = boto3.Session(profile_name=self.profile)
                        sts = self.session.client('sts')
                        sts.get_caller_identity()
                        ConsoleAndLog.info("Successfully refreshed SSO credentials")
                        return
                    except Exception as login_error:
                        retry_count += 1
                        ConsoleAndLog.warning(f"SSO login attempt {retry_count}/{max_retries} failed: {str(login_error)}")
                else:
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

    # def _refresh_sso_login(self) -> None:
    #     """Execute AWS SSO login command for specific profile"""
    #     try:
    #         ConsoleAndLog.info(f"Initiating SSO login for profile {self.profile}")
            
    #         # First try to login
    #         result = subprocess.run(
    #             ["aws", "sso", "login", "--profile", self.profile],
    #             check=True,
    #             capture_output=True,
    #             text=True
    #         )
            
    #         if result.stdout:
    #             ConsoleAndLog.info(f"SSO login output: {result.stdout}")
    #         if result.stderr:
    #             ConsoleAndLog.warning(f"SSO login warnings: {result.stderr}")
                
    #         # Wait a moment for credentials to be properly saved
    #         time.sleep(2)
        # except subprocess.CalledProcessError as e:
        #     error_msg = (
        #         f"SSO login failed for profile {self.profile}. "
        #         "Please ensure your profile is properly configured and try again."
        #     )
        #     if e.stdout:
        #         error_msg += f"\nOutput: {e.stdout}"
        #     if e.stderr:
        #         error_msg += f"\nError: {e.stderr}"
        #     ConsoleAndLog.error(error_msg)
        #     raise TokenRetrievalError(error_msg)

    def _refresh_sso_login(self) -> None:
        """Execute AWS SSO login command for specific profile with browser fallback"""
        try:

            if not self._can_open_browser():
                ConsoleAndLog.warning("No display detected. Running in no-browser mode.")
                self.no_browser = True
        
            ConsoleAndLog.info(f"Initiating SSO login for profile {self.profile}")
            
            cmd = ["aws", "sso", "login", "--profile", self.profile]
            if self.no_browser:
                cmd.append("--no-browser")
                ConsoleAndLog.info("Running in no-browser mode. You will need to manually copy and paste the URL.")
            
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            
            # Check if the output contains a URL (indicating browser didn't open)
            if "https://" in result.stdout:
                ConsoleAndLog.info("Browser didn't open automatically. Please manually visit:")
                # Extract and display the URL
                for line in result.stdout.split('\n'):
                    if "https://" in line:
                        ConsoleAndLog.info(f"SSO URL: {line.strip()}")
                        ConsoleAndLog.info("After authentication, return here to continue...")
            
            if result.stdout:
                ConsoleAndLog.info(f"SSO login output: {result.stdout}")
            if result.stderr:
                ConsoleAndLog.warning(f"SSO login warnings: {result.stderr}")
                
            # Wait a moment for credentials to be properly saved
            time.sleep(2)
                
        except subprocess.CalledProcessError as e:
            error_msg = (
                f"SSO login failed for profile {self.profile}.\n"
                "Common issues:\n"
                "1. No internet connection\n"
                "2. Invalid SSO configuration\n"
                "3. Browser launch failed\n"
                "Try using --no-browser if you're in a terminal without display access."
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

    def get_client(self, service_name: str, region: Optional[str] = None) -> Any:
        """Get a boto3 client for the specified service"""
        if not self.session:
            raise ValueError("No valid session available")
        if not region:
            region = self.region
        return self.session.client(service_name, region)

    def _can_open_browser(self) -> bool:
        """Check if the current environment can open a browser"""
        # Check for DISPLAY variable on Unix-like systems
        if os.name == 'posix':
            return bool(os.environ.get('DISPLAY'))
        # On Windows, assume browser can be opened
        return os.name == 'nt'
