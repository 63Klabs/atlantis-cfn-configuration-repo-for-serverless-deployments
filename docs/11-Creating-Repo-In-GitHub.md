# Creating Repository in GitHub and Seeding with Application Starter

## Requirements:

- GitHub account
- GitHub CLI installed
- Git installed

To create a GitHub repository using the CLI and seed it with a zip file, first create an empty repository on GitHub using `gh repo create` and then extract the contents of your zip file into the local directory, initialize it as a Git repository with `git init`, add all files, commit them, and finally push the changes to your new remote repository on GitHub.

You can use the script `./script/create-gh-repo.sh` to automate this task.

## Using create-gh-repo.sh Script

Provide a repository name and S3 location of of the application starter zip file.

```bash
./create-repo.sh my-new-repo s3://my-bucket/template.zip
```

Then navigate to the directory you wish to clone the new repository to and perform `git clone` using the clone URL listed by the script.

The script creates a private repository. You can go to the repository in GitHub to switch it to public if you wish.

## Manually

### 1. Create an empty repository on GitHub:

- Open your terminal and navigate to the directory where you want to create the local repository.
- Run the command to create a new repository: 

```bash
gh repo create my-new-repo --private  
```

Replace `my-new-repo` with the desired name for your repository. 

You can switch `--private` to `--public` if you want a public repository. 

### 2. Extract the zip file:

- Download the application starter zip file to the local directory.
- Unzip the file using your preferred method (e.g., `unzip <filename.zip>`) 

You can download from an S3 bucket by using the command: 

```bash
aws s3 cp
```

Or download from GitHub:

```bash
```

3. Initialize Git repository:
  - Navigate into the extracted directory using cd <directory-name>. 
  - Initialize a Git repository in the current directory: 

```bash
git init
```

4. Stage and commit files:
  - Add all files in the current directory to the staging area: 

```bash
git add .
```

5. Commit the changes with a descriptive message: 

```bash
git commit -m "Initial commit from zip file"
```

6. Push to remote repository:
  - Get the remote URL for your newly created GitHub repository: 

```bash
gh repo clone <repository-name> --no-checkout
```

7. Add the remote origin.

```bash
git remote add origin <repository-url>
```

8. Push your local commits to the remote repository: 

```bash
git push origin main
```

## Key points:

- GitHub CLI:  Make sure you have the GitHub CLI installed on your system to use the gh command. 
- Directory structure: Ensure the extracted zip file contains the correct file structure you want in your repository. 
Version control: If you need to make further changes to your project, use standard Git commands like git add, git commit, and git push to manage your code. 

## More Information:

[GitHub CLI: Quickstart for Repositories](https://docs.github.com/en/repositories/creating-and-managing-repositories/quickstart-for-repositories)