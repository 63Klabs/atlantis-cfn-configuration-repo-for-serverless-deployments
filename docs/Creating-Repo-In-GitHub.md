# Creating Repository in GitHub and Seeding with Application Starter

Requirements:

- GitHub account
- GitHub CLI installed

To create a GitHub repository using the CLI and seed it with a zip file, first create an empty repository on GitHub using `gh repo create` and then extract the contents of your zip file into the local directory, initialize it as a Git repository with `git init`, add all files, commit them, and finally push the changes to your new remote repository on GitHub.

## Steps:

1. Create an empty repository on GitHub:
  - Open your terminal and navigate to the directory where you want to create the local repository.
  - Run the command to create a new repository: 

```bash
gh repo create <repository-name> --public  
```

Replace `<repository-name>` with the desired name for your repository. 

You can add `--private` if you want a private repository. 

1. Extract the zip file:
  - Download your zip file to the local directory.
    - You can use `aws s3 cp`
  - Unzip the file using your preferred method (e.g., `unzip <filename.zip>`) 
2. Initialize Git repository:
  - Navigate into the extracted directory using cd <directory-name>. 
  - Initialize a Git repository in the current directory: 

```bash
git init
```

3. Stage and commit files:
  - Add all files in the current directory to the staging area: 

```bash
git add .
```

4. Commit the changes with a descriptive message: 

```bash
git commit -m "Initial commit from zip file"
```

5. Push to remote repository:
  - Get the remote URL for your newly created GitHub repository: 

```bash
gh repo clone <repository-name> --no-checkout
```

6. Add the remote origin.

```bash
git remote add origin <repository-url>
```

7. Push your local commits to the remote repository: 

```bash
git push origin main
```

## Key points:

- GitHub CLI:  Make sure you have the GitHub CLI installed on your system to use the gh command. 
- Directory structure: Ensure the extracted zip file contains the correct file structure you want in your repository. 
Version control: If you need to make further changes to your project, use standard Git commands like git add, git commit, and git push to manage your code. 

## More Information:

[GitHub CLI: Quickstart for Repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/quickstart-for-repositories)