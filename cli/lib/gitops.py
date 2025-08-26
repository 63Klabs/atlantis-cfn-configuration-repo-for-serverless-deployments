#!/usr/bin/env python3

VERSION = "v0.0.1/2025-08-24"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

"""
Git functions for automating script based Git operations.
"""

import subprocess
import sys
import click

from .logger import Log
from .tools import Colorize

class Git:

    @staticmethod
    def prompt_git_pull() -> None:
        """Prompt user if git pull should be performed"""
        if click.confirm(Colorize.question("Perform git pull before proceeding?")):
            try:
                result = subprocess.run(['git', 'pull'], capture_output=True, text=True, check=True)
                click.echo(Colorize.success("Git pull completed successfully"))
                Log.info("Git pull completed successfully")
            except subprocess.CalledProcessError as e:
                click.echo(Colorize.error(f"Git pull failed: {e.stderr}"))
                Log.error(f"Git pull failed: {e.stderr}")
                if not click.confirm("Continue despite git pull failure?"):
                    sys.exit(1)
                    
    @staticmethod
    def git_commit_and_push(commit_message) -> None:
        """Perform git commit and push"""
        try:
            # Add changes
            subprocess.run(['git', 'add', '.'], check=True)
            
            # Commit
            subprocess.run(['git', 'commit', '-m', commit_message], check=True)
            
            # Push
            subprocess.run(['git', 'push'], check=True)
            
            click.echo(Colorize.success("Git commit and push completed"))
            Log.info("Git commit and push completed")
            
        except subprocess.CalledProcessError as e:
            click.echo(Colorize.error(f"Git operation failed: {str(e)}"))
            Log.error(f"Git operation failed: {str(e)}")
