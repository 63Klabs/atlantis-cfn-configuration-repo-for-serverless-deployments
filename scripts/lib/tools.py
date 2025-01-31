#!/usr/bin/env python3

VERSION = "v0.1.0/2025-02-22"
# Developed by Chad Kluck with AI assistance from Amazon Q Developer
# GitHub Copilot assisted in color formats of output and prompts

"""
Utility functions for command line tools and formatting.
Provides consistent formatting, terminal handling, and common string operations.
"""


# Install:
#
# `sudo pip install click`
# ---------- OR ----------
# `sudo apt install python3-tomli python3-click`
#

import os
import click
from typing import Dict, List

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
        import random
        import string
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
        import datetime
        return datetime.datetime.now().strftime(format)

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
