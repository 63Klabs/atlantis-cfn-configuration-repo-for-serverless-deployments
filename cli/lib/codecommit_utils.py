#!/usr/bin/env python3

VERSION = "v0.0.1/2025-08-24"
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
		self.aws_session = AWSSessionManager(profile, region, no_browser)
		self.client = self.aws_session.get_client('codecommit', self.region)


	@classmethod
	def get_repo_tags(self, repo_name):
		"""
		Get tags for a CodeCommit repository.
		:param repo_name: Name of the repository.
		:return: Dictionary of tags.
		"""
		try:
			response = self.client.list_tags_for_resource(
				resourceArn=f'arn:aws:codecommit:{self.region}:{self.aws_session.get_account_id()}:repository/{repo_name}'
			)
			tags = {tag['key']: tag['value'] for tag in response.get('tags', [])}
			return tags
		except TokenRetrievalError as e:
			Log.error(f"Token retrieval error: {str(e)}")
			raise
		except Exception as e:
			Log.error(f"Error retrieving tags for repository {repo_name}: {str(e)}")
			raise

