#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-22"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer

from typing import List, Optional
import sys

import click

from .logger import Log
from .tools import Colorize

# -------------------------------------------------------------------------
# - File Name List Utilities
# -------------------------------------------------------------------------

class FileNameListUtils:

    @staticmethod
    def select_from_file_list(file_list: List[str], 
                              allow_none: Optional[bool] = False, 
                              *, 
                              heading_text="Available files",
                              prompt_text="Enter file number") -> str:
        """List available files and prompt the user to choose one.

        Args:
            file_list (List[str]): List of files to use
            allow_none (Optional[bool]): List 0. None as an option
            
        Returns:
            str: Selected file
        """

        if not file_list:
            Log.error("No files found")
            click.echo(Colorize.error("No files found"))
            if not allow_none:
                sys.exit(1)
        
        # Sort file_list for consistent ordering
        file_list.sort()

        # We want to put the filename first and pad out to make it easy to view
        selection_list = FileNameListUtils.extract_filenames_from_paths(file_list)
        max_filename = FileNameListUtils.find_longest_filename(selection_list)
        
        # Display numbered list
        click.echo(Colorize.question(f"{heading_text}:"))
        if (allow_none): click.echo(Colorize.option("0. None"))
        for idx, line_item in enumerate(selection_list, 1):
            line = f"{idx}. {FileNameListUtils.pad_filename(line_item[0], max_filename)} | {line_item[1]}"
            click.echo(Colorize.option(line))
        
        print()

        while True:
            try:
                default = ''

                choice = Colorize.prompt(prompt_text, default, str)
                # Check if input is a number
                sel_idx = int(choice) - 1

                min = -1 if allow_none else 0
                
                # Validate the index is within range
                if min <= sel_idx < len(selection_list):

                    selected = None

                    if(sel_idx >= 0):
                        selected = selection_list[sel_idx][1]
                                                
                    return selected
                else:
                    click.echo(Colorize.error(f"Please enter a number between {min} and {len(selection_list)}"))
            except ValueError:
                click.echo(Colorize.error("Please enter a valid number"))
            except KeyboardInterrupt:
                click.echo(Colorize.info("File selection cancelled"))
                sys.exit(1)

        
    @staticmethod
    def extract_filenames_from_paths(paths: List[str]) -> List[List[str]]:
        """Takes a list of S3 URLs and returns a list of [filename, full_path] pairs.

        Args:
            paths (List[str]): List of S3 URLs (e.g., ['s3://bucket/path/file.zip', ...])

        Returns:
            List[List[str]]: List of [filename, full_path] pairs maintaining original order

        Example:
            Input: ['s3://bucket/path/file.zip', 's3://bucket/other/doc.pdf']
            Output: [['file.zip', 's3://bucket/path/file.zip'], 
                    ['doc.pdf', 's3://bucket/other/doc.pdf']]
        """
        try:
            result = []
            for path in paths:
                # Extract the filename from the full path
                filename = path.split('/')[-1]
                # Create pair and append to result
                result.append([filename, path])
            return result
        except Exception as e:
            Log.error(f"Error processing S3 URLs: {str(e)}")
            raise

    @staticmethod
    def find_longest_filename(filename_pairs: List[List[str]]) -> int:
        """Find the length of the longest filename in the list of filename pairs.
        
        Args:
            filename_pairs (List[List[str]]): List of [filename, full_path] pairs
            
        Returns:
            int: Length of the longest filename
            
        Example:
            Input: [['file.zip', 's3://bucket/path/file.zip'], 
                    ['longer_file.zip', 's3://bucket/other/longer_file.zip']]
            Output: 14  # length of 'longer_file.zip'
        """
        try:
            if not filename_pairs:
                return 0
                
            # Get the length of each filename (first element of each pair)
            # and return the maximum
            return max(len(pair[0]) for pair in filename_pairs)
            
        except Exception as e:
            Log.error(f"Error finding longest filename: {str(e)}")
            raise

    @staticmethod
    def pad_filename(file_name: str, str_length: int) -> str:
        """Pad a filename with spaces to reach the specified length.
        
        Args:
            file_name (str): The filename to pad
            str_length (int): The desired total length after padding
            
        Returns:
            str: The padded filename
            
        Example:
            Input: file_name="test.zip", str_length=10
            Output: "test.zip  " (padded with spaces to length 10)
        """
        try:
            return file_name.ljust(str_length)
        except Exception as e:
            Log.error(f"Error padding filename: {str(e)}")
            raise
