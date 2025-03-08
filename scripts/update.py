import os
import shutil
import subprocess
from pathlib import Path

def init_git_repo(repo_url):
    """Initialize git repository if not already initialized"""
    if not os.path.exists('.git'):
        subprocess.run(['git', 'init'])
        subprocess.run(['git', 'remote', 'add', 'origin', repo_url])
    
def update_from_git(target_dirs, repo_url):
    """Update specified directories from git repository"""
    try:
        # Initialize repository if needed
        init_git_repo(repo_url)
        
        # Fetch latest changes
        subprocess.run(['git', 'fetch', 'origin'])
        
        # For each target directory
        for directory in target_dirs:
            if os.path.exists(directory):
                # Checkout the specific directory from origin
                subprocess.run(['git', 'checkout', 'origin/main', '--', directory])
        
        # Specifically update README.md
        if os.path.exists('README.md'):
            subprocess.run(['git', 'checkout', 'origin/main', '--', 'README.md'])
            
    except Exception as e:
        print(f"Error updating from git: {str(e)}")
        return False
    
    return True

def update_from_zip(zip_path, target_dirs):
    """Update specified directories from zip file"""
    try:
        import zipfile
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract only the directories we want
            for file_info in zip_ref.filelist:
                for target_dir in target_dirs:
                    if file_info.filename.startswith(target_dir + '/'):
                        zip_ref.extract(file_info)
                
                # Extract README.md if it exists
                if file_info.filename == 'README.md':
                    zip_ref.extract(file_info)
                    
    except Exception as e:
        print(f"Error updating from zip: {str(e)}")
        return False
    
    return True

def main():
    # Directories to update
    target_dirs = ['docs', 'scripts']
    
    # Get source type and location from environment variables
    source_type = os.getenv('UPDATE_SOURCE_TYPE', 'git')  # 'git' or 'zip'
    source_location = os.getenv('SOURCE_LOCATION')
    
    if not source_location:
        print("Error: SOURCE_LOCATION environment variable not set")
        return False
    
    success = False
    if source_type.lower() == 'git':
        success = update_from_git(target_dirs, source_location)
    elif source_type.lower() == 'zip':
        success = update_from_zip(source_location, target_dirs)
    else:
        print(f"Error: Unknown source type: {source_type}")
        return False
    
    if success:
        print("Update completed successfully")
    else:
        print("Update failed")
    
    return success

if __name__ == "__main__":
    main()
