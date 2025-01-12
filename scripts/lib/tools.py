# This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, 
# either express or implied. See the License for the specific language governing permissions 
# and limitations under the License.
#
# Python Function Library
# Chad Kluck
# v2024.02.29 : lib/tools.py

import os

def indent(spaces=4, prepend=''):
    return prepend + " " * spaces

# A function that accepts a string and breaks it into lines that are no longer than 80 characters each, breaking only on a whitespace character
def break_lines(string: str, indent: str = "", break_at: int = 80):

    lines = []
    line = ""
    
    break_at = get_terminal_width(break_at)

    # Break the string into words and loop through each, creating a line that is no longer than 80 characters
    words = string.split(" ")
    for word in words:
        if len(line) + len(word) >= break_at:
            lines.append(line.rstrip())
            line = indent
        line += word + " "

    # Add the last line to the list of lines
    lines.append(line)

    # Convert the list of lines to a string where each line has trailing whitespace removed ends with \n except for the last line
    lines = "\n".join(lines)

    return lines

def printCharStr(char, num, **kwargs):
    line = charStr(char, num, **kwargs)
    print(line)
    return line

def charStr(char, num, **kwargs):
    line = char*num

    text = kwargs.get('text', None)
    centered = kwargs.get('centered', None)
    bookend = kwargs.get('bookend', None)
    newline = kwargs.get('newline', None)
    newlines = kwargs.get('newlines', None)

    if text != None:
        text = " "+text+" "
        if centered == True:
            line = text.center(num, char)
        else:
            n = 5
            if char == " ":
                n = 1
            if bookend != None and len(bookend) > n:
                n = len(bookend)
            text = charStr(char, n) + text
            line = text.ljust(num, char)
    if bookend != None:
        n = len(bookend)
        # remove n characters from the beginning and end of the line
        line = line[n:-n]
        # reverse string bookend
        line = bookend + line + bookend[::-1]

    if newline == True:
        line = line + "\n"

    if newlines == True:
        line = "\n" + line + "\n"

    return line

def get_terminal_width(max_width: int = 80) -> int:
    try:
        term_width = os.get_terminal_size().columns
        return (term_width if term_width < max_width else max_width)
    except OSError:
        return max_width
    
# A function that accepts the prompt parameter, whether it is an error or info, and displays help, description, and examples
def displayHelp(prompt, error):

    spaces = 5

    prepend = "??? "
    label = "INFO"
    message = prompt["name"]

    if error:
        prepend = ">>> "
        label = "ERROR"
        message = "MESSAGE: The value for parameter "+prompt["name"]+" is invalid.\n"+indent(spaces,prepend)+"Please try again."

    indentStr = indent(spaces, prepend)

    print("\n"+prepend+"------ "+label+" ------")
    print(prepend+message)
    print(break_lines(prepend+"REQUIREMENT: "+prompt["help"], indentStr))
    print(break_lines(prepend+"DESCRIPTION: "+prompt["description"], indentStr))
    print(break_lines(prepend+"EXAMPLE(S): "+prompt["examples"], indentStr))
    print("")

# generateRandomString(4)
def generateRandomString(length):
    import random
    import string
    return ''.join(random.choice(string.ascii_letters) for i in range(length))

# getDateStamp("%Y%m%d%H%M%S")
def getDateStamp(format):
    import datetime
    return datetime.datetime.now().strftime(format)