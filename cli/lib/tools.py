#!/usr/bin/env python3

VERSION = "v0.1.2/2025-05-21"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

"""
Utility functions for command line tools and formatting.
Provides consistent formatting, terminal handling, and common string operations.
"""

import os
import click
import requests
import datetime
import random
import string
import tempfile
import subprocess
import json


from typing import Dict, List, Optional

from lib.tools_colors import (
    COLOR_PROMPT,
    COLOR_OPTION,
    COLOR_OUTPUT,
    COLOR_OUTPUT_VALUE,
    COLOR_SUCCESS,
    COLOR_ERROR,
    COLOR_WARNING,
    COLOR_INFO,
    COLOR_BOX_TEXT
)

class Strings:

    @classmethod
    def indent(self, spaces: int = 4, prepend: str = '') -> str:
        """
        Create an indentation string with specified number of spaces.
        
        Args:
            spaces (int): Number of spaces to indent
            prepend (str): String to prepend to the spaces
        
        Returns:
            str: The indentation string
        """
        return prepend + " " * spaces

    @classmethod
    def break_lines(self, string: str, indent: str = "", break_at: int = 80) -> str:
        """
        Break a string into lines no longer than specified width, breaking only on whitespace.
        Handles terminal width adjustments and proper indentation.
        
        Args:
            string (str): The string to break into lines
            indent (str): String to prepend to each new line
            break_at (int): Maximum line length before breaking
        
        Returns:
            str: Formatted string with appropriate line breaks
        """
        lines = []
        line = ""
        
        # Adjust break point based on terminal width
        break_at = self.get_terminal_width(break_at)

        # Break the string into words and loop through each
        words = string.split(" ")
        for word in words:
            if len(line) + len(word) >= break_at:
                lines.append(line.rstrip())
                line = indent
            line += word + " "

        # Add the final line
        lines.append(line)

        # Join lines with newlines, removing trailing whitespace
        lines = "\n".join(lines)

        return lines

    @classmethod
    def print_char_str(self, char: str, num: int, **kwargs) -> str:
        """
        Print and return a string of repeated characters with optional formatting.
        
        Args:
            char (str): Character to repeat
            num (int): Number of times to repeat character
            **kwargs: Optional formatting parameters:
                text (str): Text to insert in the line
                centered (bool): Center the text in the line
                bookend (str): String to place at start/end
                newline (bool): Add single newline at end
                newlines (bool): Add newlines before and after
        
        Returns:
            str: The formatted string
        """
        line = self.char_str(char, num, **kwargs)
        print(line)
        return line

    @classmethod
    def char_str(self, char: str, num: int, **kwargs) -> str:
        """
        Create a string of repeated characters with optional formatting.
        
        Args:
            char (str): Character to repeat
            num (int): Number of times to repeat character
            **kwargs: Optional formatting parameters:
                text (str): Text to insert in the line
                centered (bool): Center the text in the line
                bookend (str): String to place at start/end
                newline (bool): Add single newline at end
                newlines (bool): Add newlines before and after
        
        Returns:
            str: The formatted string
        """
        line = char*num

        text = kwargs.get('text', None)
        centered = kwargs.get('centered', None)
        bookend = kwargs.get('bookend', None)
        newline = kwargs.get('newline', None)
        newlines = kwargs.get('newlines', None)

        if text is not None:
            text = " "+text+" "
            if centered:
                line = text.center(num, char)
            else:
                n = 5
                if char == " ":
                    n = 1
                if bookend is not None and len(bookend) > n:
                    n = len(bookend)
                text = self.char_str(char, n) + text
                line = text.ljust(num, char)
                
        if bookend is not None:
            n = len(bookend)
            # Remove bookend width from start and end
            line = line[n:-n]
            # Add bookend at start and reversed at end
            line = bookend + line + bookend[::-1]

        if newline:
            line = line + "\n"

        if newlines:
            line = "\n" + line + "\n"

        return line

    @classmethod
    def get_terminal_width(self, max_width: int = 80) -> int:
        """
        Get the current terminal width, with a maximum limit.
        
        Args:
            max_width (int): Maximum width to return, defaults to 80
        
        Returns:
            int: Terminal width or max_width, whichever is smaller
        """
        try:
            term_width = os.get_terminal_size().columns
            return min(term_width, max_width)
        except OSError:
            return max_width

    @classmethod
    def generate_random_string(self, length: int) -> str:
        """
        Generate a random string of specified length using ASCII letters.
        
        Args:
            length (int): Length of string to generate
        
        Returns:
            str: Random string of specified length
        """

        return ''.join(random.choice(string.ascii_letters) for i in range(length))

    @classmethod
    def get_date_stamp(self, format: str = "%Y%m%d%H%M%S") -> str:
        """
        Get current date/time stamp in specified format.
        
        Args:
            format (str): DateTime format string, defaults to "YYYYMMDDhhmmss"
        
        Returns:
            str: Formatted date/time stamp
        """
        return datetime.datetime.now().strftime(format)

    @staticmethod
    def find_longest_string_length_in_column(two_dim_array: List[List[str]], column: int = 0) -> int:
        """Find the length of the longest string in a 2 dimensional list column.
        
        Args:
            filename_pairs (List[List[str]]): List of [filename, full_path] pairs
            
        Returns:
            int: Length of the longest string in column
            
        Example:
            Input: [['file.zip', 'File Zip'], 
                    ['longer_file.zip', 'Longer File Zip']]
            Output: 14  # length of 'longer_file.zip' if column 0, 15 if column 1
        """
        if not two_dim_array:
            return 0
            
        # Get the length of each filename (first element of each pair)
        # and return the maximum
        return max(len(pair[column]) for pair in two_dim_array)

    @staticmethod
    def pad_string(text: str, str_length: int) -> str:
        """Pad a string with spaces at end to reach the specified length.
        
        Args:
            text (str): The text string to pad
            str_length (int): The desired total length after padding
            
        Returns:
            str: The padded string
            
        Example:
            Input: text="test.zip", str_length=10
            Output: "test.zip  " (padded with spaces to length 10)
        """
        return text.ljust(str_length)

# =============================================================================
# ----- GITHUB API ------------------------------------------------------------
# =============================================================================

class GitHubApi:

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
            Dict: Dictionary containing 'clone_url_https' and 'clone_url_ssh' keys
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
            
            # Parse the JSON output
            output = json.loads(result.stdout)
            print(output)
            
            return {
                "clone_url_https": output["url"],
                "clone_url_ssh": output["sshUrl"]
            }
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create repository: {e.stderr}")
        except Exception as e:
            raise Exception(f"Failed to create repository: {str(e)}")
        
    @staticmethod
    def repository_exists(repo_name: str) -> bool:
        """
        Check if a GitHub repository exists
        Args:
            repo_name (str): Repository name
        
        Returns:
            bool: True if repository exists, False otherwise
        """
        try:
            # Query the GitHub API for the repository
            response = requests.get(
                f"https://api.github.com/repos/{repo_name}",
                headers={
                    'Accept': 'application/vnd.github.v3+json'
                }
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to check repository existence: {str(e)}")
        
        
# =============================================================================
# ----- TERMINAL COLORS -------------------------------------------------------
# =============================================================================

class Colorize:

    # Imported from lib.tools_colors
    PROMPT = COLOR_PROMPT
    OPTION = COLOR_OPTION
    OUTPUT = COLOR_OUTPUT
    OUTPUT_VALUE = COLOR_OUTPUT_VALUE
    SUCCESS = COLOR_SUCCESS
    ERROR = COLOR_ERROR
    WARNING = COLOR_WARNING
    INFO = COLOR_INFO
    BOX_TEXT = COLOR_BOX_TEXT

    @classmethod
    def prompt(self, prompt_text: str, default_value: str, value_type: type = str, show_default: bool = False) -> str:
        """
        Format an interactive prompt with consistent styling.
        
        Args:
            prompt_text (str): The prompt text to display
            default_value (str): Default value if user enters nothing
            value_type (type): Expected type of the input value
            show_default (bool): Whether to show default value in prompt
        
        Returns:
            str: User's input or default value
        """
        formatted_text = ''
        
        if default_value != '':
            formatted_text = click.style(f"{prompt_text} [", fg=COLOR_PROMPT, bold=True) + \
                            click.style(f"{default_value}", fg=COLOR_OPTION) + \
                            click.style("]", fg=COLOR_PROMPT, bold=True)
        else:
            formatted_text = click.style(f"{prompt_text}", fg=COLOR_PROMPT, bold=True)

        return click.prompt(formatted_text, type=value_type, default=default_value, show_default=show_default)

    @classmethod
    def question(self, question_text: str) -> str:
        """Format a question with consistent styling"""
        return click.style(f"{question_text} ", fg=COLOR_PROMPT, bold=True)

    @classmethod
    def option(self, option_text: str) -> str:
        """Format an option with consistent styling"""
        return click.style(f"{option_text} ", fg=COLOR_OPTION)

    @classmethod
    def output_with_value(self, response_text: str, response_value: str) -> str:
        """
        Format output text with an associated value using consistent styling.
        
        Args:
            response_text (str): The label or description text
            response_value (str): The value to display
        
        Returns:
            str: Formatted string with label and value
        """
        return click.style(f"{response_text.strip()} ", fg=COLOR_OUTPUT, bold=True) + \
            click.style(f"{response_value}", fg=COLOR_OUTPUT_VALUE)

    @classmethod
    def output_bold(self, response_text: str) -> str:
        """Format output text in bold with consistent styling"""
        return click.style(f"{response_text} ", fg=COLOR_OUTPUT, bold=True)

    @classmethod
    def output(self, response_text: str) -> str:
        """Format output text with consistent styling"""
        return click.style(f"{response_text} ", fg=COLOR_OUTPUT)

    @classmethod
    def success(self, response_text: str) -> str:
        """Format success message text with consistent styling"""
        return click.style(f"{response_text} ", fg=COLOR_SUCCESS)

    @classmethod
    def error(self, response_text: str) -> str:
        """Format error message with consistent styling"""
        return click.style(f"{response_text} ", fg=COLOR_ERROR, bold=True)

    @classmethod
    def warning(self, response_text: str) -> str:
        """Format warning message with consistent styling"""
        return click.style(f"{response_text} ", fg=COLOR_WARNING, bold=True)

    @classmethod
    def info(self, response_text: str) -> str:
        """Format informational message with consistent styling"""
        return click.style(f"{response_text} ", fg=COLOR_INFO, bold=True)

    @classmethod
    def divider(self, char: str = '-', num: int = 80, *, fg=COLOR_OUTPUT) -> str:
        """
        Create a formatted divider line.
        
        Args:
            char (str): Character to use for divider
            num (int): Length of divider
            fg (str): Color to use for divider
        
        Returns:
            str: Formatted divider line
        """
        return click.style(f"{char * Strings.get_terminal_width(num)}", fg=fg, bold=True)

    @classmethod
    def box_info(self, sections: List[Dict], *, width=80) -> None:
        """
        Display information in a formatted box with info styling.
        
        Args:
            sections (List[Dict]): List of sections to display
            width (int): Maximum width of box
        """
        fg = COLOR_BOX_TEXT
        bg = COLOR_INFO
        self.box(sections, width=width, fg=fg, bg=bg)

    @classmethod
    def box_warning(self, sections: List[Dict], *, width=80) -> None:
        """Display warning message in a formatted box"""
        fg = "black"  # For better contrast
        bg = COLOR_WARNING
        self.box(sections, width=width, fg=fg, bg=bg)

    @classmethod
    def box_error(self, sections: List[Dict], *, width=80) -> None:
        """Display error message in a formatted box"""
        fg = COLOR_BOX_TEXT
        bg = COLOR_ERROR
        self.box(sections, width=width, fg=fg, bg=bg)

    @classmethod
    def box_output(self, sections: List[Dict], *, width=80) -> None:
        """Display output in a formatted box"""
        fg = COLOR_OUTPUT
        bg = COLOR_BOX_TEXT
        self.box(sections, width=width, fg=fg, bg=bg)

    @classmethod
    def box(self, sections: List[Dict], *, width=80, fg=COLOR_BOX_TEXT, bg=COLOR_INFO) -> None:
        """
        Create a formatted box with multiple sections.
        
        Args:
            sections (List[Dict]): List of sections, each containing:
                - header (str, optional): Section header
                - text (str): Section content
            width (int): Maximum width of box
            fg (str): Foreground color
            bg (str): Background color
        """
        width = Strings.get_terminal_width(width)
        i = 0

        for section in sections:
            i += 1
            header = section.get("header", None)
            if header:
                if i > 1:
                    self.box_divider(' ', width=width, fg=fg, bg=bg)
                self.box_header(header, width=width, fg=fg, bg=bg)
            else:
                self.box_divider('~', width=width, fg=fg, bg=bg)
            text = section.get("text", "")
            self.box_text(text, width=width, fg=fg, bg=bg)
        self.box_divider('~', width=width, fg=fg, bg=bg)

    @classmethod
    def box_header(self, heading_text: str, *, width=80, fg=COLOR_BOX_TEXT, bg=COLOR_INFO) -> None:
        """Format a box header with consistent styling"""
        width = Strings.get_terminal_width(width)
        text = f"~~~~~~ {heading_text} "
        text += Strings.char_str("~", (width - len(text)))
        click.echo(click.style(text, fg=fg, bg=bg, bold=True))

    @classmethod
    def box_divider(self, char: str = '~', *, width=80, fg=COLOR_BOX_TEXT, bg=COLOR_INFO) -> None:
        """Create a divider line in a formatted box"""
        click.echo(click.style(f"{char * Strings.get_terminal_width(width)}", fg=fg, bg=bg, bold=True))

    @classmethod
    def box_text(self, text: str, *, width=80, fg=COLOR_BOX_TEXT, bg=COLOR_INFO) -> None:
        """Format text content in a formatted box"""
        width = Strings.get_terminal_width(width)
        text_multi_line = Strings.break_lines(text).split('\n', width)
        for line in text_multi_line:
            click.echo(click.style(f"{line.rstrip():<{width}}", fg=fg, bg=bg))
