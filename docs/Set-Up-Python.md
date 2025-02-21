# Set Up Python

This repository contains a variety of scripts which use Python libraries.

All the libraries necessary are listed in `./scripts/requirements.txt`.

Make sure you have at least Python 3.12 installed. The scripts use the `python3` command to execute. So you will need to set up an alias for `python3` if you currently use `py` or `python`.

Depending on how your system is set up, you can use one of two methods to install the required libraries via `pip`.

It is recommended you use a Virtual Python Environment so you don't have conflicts with other projects on your machine. Instructions are below.

After activating your python virtual environment, or to install without a virtual environment:

```bash
pip install -r requirements.txt
```

## Virtual Python Environment

1. First, make sure you have python3-venv installed:

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

- The virtual environment (.venv) should be created in your project directory [3]
- Each time you open a new terminal and want to work on the project, you'll need to activate the virtual environment again
- The virtual environment keeps your project dependencies isolated from your system Python
- Make sure to add .venv to your .gitignore file if you haven't already

This is the recommended way to manage Python packages as it prevents conflicts with system packages and allows you to have different versions of packages for different projects.
