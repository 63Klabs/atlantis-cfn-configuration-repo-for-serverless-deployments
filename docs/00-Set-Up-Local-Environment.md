# Local Environment Requirements

The commands and cli used in these tutorials assume a Linux-like environment and some familiarity with Command Line Interface (CLI) via the terminal. On Windows, [Git for Windows](https://gitforwindows.org/) or [Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/about) can be used.

> Note: If you already have AWS CLI and SAM installed, skip to the Python section as you will need to use `pip` to install some Python libraries used by the cli.

## AWS CLI Installation:

The AWS Command Line Interface (AWS CLI) is a unified tool to manage your AWS services from the command line. You'll need version 2, which is the current major version.

Installation steps vary by operating system:

- For Linux/macOS: Install via package managers (apt) or the bundled installer
- For Windows: Use the MSI installer
- For Docker: Official Docker images are available

```bash
# Check AWS CLI version
aws --version
```

After installation, configure AWS CLI with your credentials:

```bash
aws configure
```

You'll need to provide:

- AWS Access Key ID
- AWS Secret Access Key
- Default region name (e.g., us-east-1)
- Default output format (json recommended)

## AWS SAM CLI Installation:

AWS SAM (Serverless Application Model) CLI is a tool for building and testing serverless applications. It requires Docker and AWS CLI as prerequisites.

Installation steps:

- For Linux/macOS: Use package managers (pip)
- For Windows: Use the MSI installer

Verify installations with:

```bash
# Check SAM CLI version
sam --version
```

## Detailed AWS CLI and AWS SAM CLI Instructions and Troubleshooting

For detailed installation instructions and troubleshooting, you can refer to the official AWS documentation for AWS CLI and AWS SAM CLI.

Both tools are essential for serverless development on AWS, as:

AWS CLI provides direct access to AWS services

AWS SAM CLI enables local testing and deployment of serverless applications

Make sure you have appropriate AWS credentials and permissions set up to use these tools effectively.

## If Using GitHub

If you are using GitHub for your repositories, in order to use the GitHub cli provided you must have GitHub CLI installed.

## Set Up Python

Make sure you have at least Python 3.12 installed. The cli use the `python3` command to execute. So you will need to set up an alias for `python3` if you currently use `py` or `python`.

This repository contains a variety of cli scripts which use Python libraries.

All the libraries necessary are listed in `./cli/requirements.txt`.

Depending on how your system is set up, you can use one of two methods to install the required libraries via `pip`.

It is recommended you use a Virtual Python Environment so you don't have conflicts with other projects on your machine. Instructions are in the Virtual [Python Environment section](#virtual-python-environment).

After activating your python virtual environment, or to install without a virtual environment:

```bash
pip install -r requirements.txt
```

### Virtual Python Environment

The requirements file includes AWS SDK (boto3), AWS SAM CLI, and other dependencies needed for the project. The virtual environment will keep these dependencies isolated from your system Python installation.

Create and activate a virtual environment in your repository directory:

```bash
# Create the virtual environment
python3 -m venv .ve

# Activate the virtual environment
# On Linux/macOS:
source .ve/bin/activate

# On Windows:
# .ve\Scripts\activate
```

Now you can safely install the requirements:

```bash
# Make sure your virtual environment is activated
# (.ve) user@host ~/path/to/repo:
pip install -r cli/requirements.txt
```

Using the virtual environment:

Once activated, you'll see (ve) at the beginning of your command prompt. This indicates that you're working within the virtual environment. Any Python packages you install will be isolated to this environment.

To run Python scripts using this environment:

```bash
# Example: Running a script from the cli directory
python3 cli/deploy.py
```

When you're done working with the virtual environment, you can deactivate it:

```bash
deactivate
```

To reactivate it later, just run the activation command again:

```bash
source .ve/bin/activate
```

Some important notes:

- The virtual environment (.ve) should be created in your local copy of the repository
- Each time you open a new terminal and want to work on the project, you'll need to activate the virtual environment again
- The virtual environment keeps your project dependencies isolated from your system Python
- Make sure to add .ve to your .gitignore file if you haven't already

This is the recommended way to manage Python packages as it prevents conflicts with system packages and allows you to have different versions of packages for different projects.
