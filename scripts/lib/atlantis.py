#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-22"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer

from typing import List

from .logger import Log

# -------------------------------------------------------------------------
# - File Name List Utilities
# -------------------------------------------------------------------------

class FileNameListUtils:
	
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
