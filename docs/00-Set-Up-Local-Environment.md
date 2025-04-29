# Local Environment Requirements

The commands and cli used in these tutorials assume a Linux-like environment and some familarity with Command Line Interface (CLI) via the terminal. On Windows, [Git for Windows](https://gitforwindows.org/) or [Windows Subsystem for Linux (WSL)](https://learn.microsoft.com/en-us/windows/wsl/about) can be used.

> Note: If you already have AWS CLI and SAM installed, skip to the Python section as you will need to use `pip` to install some Python libraries used by the cli.

## AWS CLI Installation:

The AWS Command Line Interface (AWS CLI) is a unified tool to manage your AWS services from the command line. You'll need version 2, which is the current major version.

Installation steps vary by operating system:

- For Linux/macOS: Install via package managers (apt, yum, brew) or the bundled installer
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

- For Linux/macOS: Use package managers (brew, pip)
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

This repository contains a variety of cli which use Python libraries.

All the libraries necessary are listed in `./cli/requirements.txt`.

Depending on how your system is set up, you can use one of two methods to install the required libraries via `pip`.

It is recommended you use a Virtual Python Environment so you don't have conflicts with other projects on your machine. Instructions are below.

After activating your python virtual environment, or to install without a virtual environment:

```bash
pip install -r requirements.txt
```

### Virtual Python Environment

First, make sure you have python3-venv installed:

```bash
sudo apt install python3-venv
```

Create a virtual environment in your "atlantis-cfn-configuration-repo-for-serverless-deployments" directory:

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Now you can safely install the requirements:

```bash
pip install -r requirements.txt
```

When you're done working, you can deactivate the virtual environment:

```bash
deactivate
```

Some important notes:

- The virtual environment (.venv) should be created in your project directory
- Each time you open a new terminal and want to work on the project, you'll need to activate the virtual environment again
- The virtual environment keeps your project dependencies isolated from your system Python
- Make sure to add .venv to your .gitignore file if you haven't already

This is the recommended way to manage Python packages as it prevents conflicts with system packages and allows you to have different versions of packages for different projects.
