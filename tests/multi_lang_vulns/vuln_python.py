import os

def run_backup(filename):
    """
    Vulnerability: Command Injection
    Description: Using os.system with unsanitized user input.
    """
    # BAD: Directly using input in a shell command
    print(f"Backing up {filename}...")
    os.system(f"cp {filename} {filename}.bak")

if __name__ == "__main__":
    user_file = input("Enter file to backup: ")
    run_backup(user_file)
