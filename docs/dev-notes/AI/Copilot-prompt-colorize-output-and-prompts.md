> is there a way to add color to python output on command line?

Yes, you can add color to Python output on the command line using libraries like colorama or termcolor. Here's an example using colorama:

First, install the colorama library if you haven't already:

pip install colorama

Then, you can use it in your code as follows:

```python
import hashlib
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

template_path = self.templates_dir / template_path

try:
    # Read the file content in binary mode
    with open(template_path, "rb") as f:
        # get SHA256 hash of template file
        sha256_hash = hashlib.sha256()
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        full_hash = sha256_hash.hexdigest()
        self.template_hash = full_hash
        self.template_hash_id = full_hash[-6:]

        # let user know what template is being used with colored output
        print(f"{Fore.GREEN}Using template file: {template_path}")
        print(f"{Fore.BLUE}Template hash: {full_hash}")
        print(f"{Fore.YELLOW}Template hash ID: {self.template_hash_id}")

        # Go back to start of file to process contents
        f.seek(0)

        # Look for the Parameters section
        parameters_section = ""
        in_parameters = False

        for line in f:
            line = line.decode('utf-8')  # Decode each line to process as text
            if line.startswith('Parameters:'):
                in_parameters = True
                parameters_section = line
            elif line.startswith('# v'):
                if 'v' in line and '/' in line:
                    self.template_version = line.strip('# ').strip()
            elif in_parameters:
                # Check if we've moved to a new top-level section
                if line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                    break
                parameters_section += line
except Exception as e:
    logging.error(f"Error parsing template file {template_path}: {e}")

```

In this example, colorama is used to add color to the output. The init(autoreset=True) call ensures that the color settings are reset after each print statement. The Fore module provides various color options like Fore.GREEN, Fore.BLUE, and Fore.YELLOW.

> what is the difference between colorama and termcolor?

Both colorama and termcolor are Python libraries used to add color to text output in the terminal, but they have some differences in functionality and usage.

colorama
Platform Support: colorama is designed to work on Windows, macOS, and Linux. It provides a consistent interface for coloring text across different platforms.
Initialization: Requires initialization with colorama.init(), especially on Windows, to enable color support.
Features: Provides more comprehensive support for text styling, including foreground and background colors, as well as text styles like bold and underline.

```python
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

print(Fore.RED + 'This is red text')
print(Back.GREEN + 'This is text with a green background')
print(Style.BRIGHT + 'This is bright text')
```

termcolor
Platform Support: Primarily designed for Unix-like systems (Linux, macOS). It may not work as expected on Windows without additional configuration.
Initialization: Does not require initialization.
Features: Focuses on providing a simple interface for setting text colors and attributes. It supports basic text styling like bold and underline.

```python
from termcolor import colored

print(colored('This is red text', 'red'))
print(colored('This is text with a green background', 'white', 'on_green'))
print(colored('This is bold text', 'white', attrs=['bold']))
```
Summary
colorama: More comprehensive and cross-platform, requires initialization.
termcolor: Simpler and more straightforward, but primarily for Unix-like systems.

> Does the python library click have coloring? (I'm already using it anyway)

Yes, the click library in Python supports colored output. You can use the click.style function to add color and other styles to your text. Here's an example of how to use it:

```python
import click

# Example usage of click.style
click.echo(click.style('Hello, World!', fg='green'))
click.echo(click.style('Warning!', fg='yellow', bold=True))
click.echo(click.style('Error!', fg='red', bg='white', underline=True))
```

In your existing code, you can use click.style to add color to the output messages. Here's an example:

```python
import hashlib
import click

template_path = self.templates_dir / template_path

try:
    # Read the file content in binary mode
    with open(template_path, "rb") as f:
        # get SHA256 hash of template file
        sha256_hash = hashlib.sha256()
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        full_hash = sha256_hash.hexdigest()
        self.template_hash = full_hash
        self.template_hash_id = full_hash[-6:]

        # let user know what template is being used with colored output
        click.echo(click.style(f"Using template file: {template_path}", fg='green'))
        click.echo(click.style(f"Template hash: {full_hash}", fg='blue'))
        click.echo(click.style(f"Template hash ID: {self.template_hash_id}", fg='yellow'))

        # Go back to start of file to process contents
        f.seek(0)

        # Look for the Parameters section
        parameters_section = ""
        in_parameters = False

        for line in f:
            line = line.decode('utf-8')  # Decode each line to process as text
            if line.startswith('Parameters:'):
                in_parameters = True
                parameters_section = line
            elif line.startswith('# v'):
                if 'v' in line and '/' in line:
                    self.template_version = line.strip('# ').strip()
            elif in_parameters:
                # Check if we've moved to a new top-level section
                if line.strip() and not line.startswith(' ') and line.strip().endswith(':'):
                    break
                parameters_section += line
except Exception as e:
    logging.error(f"Error parsing template file {template_path}: {e}")
```

In this example, click.style is used to add color to the output messages. The fg parameter sets the foreground color, and you can also use other parameters like bg for background color, bold, underline, etc.

> Write a function for the selected code so that we can provide a consistent format for the prompt. The function should accept the prompt text, default value, and type and then return the value of click.prompt(). The prompt text should be in the format of {text} [{default_value}] with the text and brackets [] being bold cyan, and the default_value within the [] being magenta

```python
import click

def formatted_prompt(prompt_text: str, default_value: str, value_type: type):
    formatted_text = click.style(f"{prompt_text} [", fg='cyan', bold=True) + \
                     click.style(f"{default_value}", fg='magenta') + \
                     click.style("]", fg='cyan', bold=True)
    return click.prompt(formatted_text, type=value_type, default=default_value, show_default=False)

# Example usage in your existing code
global_params = {}

# Get S3 bucket for deployments
global_params['s3_bucket'] = formatted_prompt(
    "S3 bucket for deployments",
    global_defaults.get('s3_bucket', os.getenv('SAM_DEPLOY_BUCKET', '')),
    str
)

# Get AWS region
global_params['region'] = formatted_prompt(
    "AWS region",
    global_defaults.get('region', os.getenv('AWS_REGION', 'us-east-1')),
    str
)

# Confirm changeset prompt
global_params['confirm_changeset'] = formatted_prompt(
    "Confirm changeset before deploy",
    'true' if global_defaults.get('confirm_changeset', True) else 'false',
    str
)

# Get role ARN if this is a pipeline deployment
if infra_type == 'pipeline':
    global_params['role_arn'] = formatted_prompt(
        "IAM role ARN for deployments",
        global_defaults.get('role_arn', os.getenv('SAM_DEPLOY_ROLE', '')),
        str
    )
```