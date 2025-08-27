#!/usr/bin/env python3

VERSION = "v0.0.2/2025-08-26"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

"""
CodeCommit functions for automating CodeCommit management.
"""

import subprocess
import sys
import click
from typing import Dict, Optional, List, Tuple

from lib.aws_session import AWSSessionManager, TokenRetrievalError

from .logger import Log
from .tools import Colorize

class CodeCommitUtils:

	def __init__(self, profile: Optional[str] = None, region: Optional[str] = None, no_browser: Optional[bool] = False):
		self.profile = profile
		self.region = region
		self.no_browser = no_browser
		self.aws_session = AWSSessionManager(self.profile, self.region, self.no_browser)
		self.region = self.aws_session.get_region()
		self.client = self.aws_session.get_client('codecommit', self.region)

	def get_repo_tags(self, repo_name):
		"""
		Get tags for a CodeCommit repository.
		:param repo_name: Name of the repository.
		:return: Dictionary of tags.
		"""
		try:
			# First verify the repository exists and get its ARN
			repo_info = self.client.get_repository(repositoryName=repo_name)
			resource_arn = repo_info['repositoryMetadata']['Arn']
			
			response = self.client.list_tags_for_resource(
				resourceArn=resource_arn
			)

			# Tags are already in dictionary format
			tags = response.get('tags', {})
			return tags
		except TokenRetrievalError as e:
			Log.error(f"Token retrieval error: {str(e)}")
			raise
		except Exception as e:
			Log.error(f"Error retrieving tags for repository {repo_name}: {str(e)}")
			raise

