import os
import sys
import subprocess
import time

# Add the current directory to the path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.app import run_application

VENV_NAME = 'TLC'
REQUIREMENTS = 'requirements.txt'

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    """
    Call in a loop to create a terminal progress bar
    """
    percent = "{0:.1f}".format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    if iteration == total: 
        print()

def setup_environment():
    # Check if virtual environment exists
    venv_path = os.path.join(os.getcwd(), VENV_NAME)
    if not os.path.exists(venv_path):
        print(f"Creating virtual environment '{VENV_NAME}'...")
        # Show progress bar for venv creation
        for i in range(101):
            print_progress_bar(i, 100, prefix='Progress:', suffix='Complete', length=50)
            time.sleep(0.01)  # Simulate work
            if i == 50:  # At midpoint, actually create the venv
                subprocess.check_call([sys.executable, '-m', 'venv', VENV_NAME])
    
    # Update pip first
    print("\nUpdating pip...")
    python_executable = os.path.join(venv_path, 'Scripts', 'python.exe')
    try:
        # Show progress bar for pip update
        for i in range(101):
            print_progress_bar(i, 100, prefix='Progress:', suffix='Complete', length=50)
            time.sleep(0.01)  # Simulate work
            if i == 50:  # At midpoint, actually update pip
                subprocess.check_call([python_executable, '-m', 'pip', 'install', '--upgrade', 'pip'])
    except subprocess.CalledProcessError as e:
        print(f"\nWarning: Failed to update pip: {e}")
        print("Continuing with installation...")
        # Continue execution even if pip update fails
    
    # Install requirements
    print("\nInstalling dependencies...")
    # Show progress bar for dependency installation
    for i in range(101):
        print_progress_bar(i, 100, prefix='Progress:', suffix='Complete', length=50)
        time.sleep(0.01)  # Simulate work
        if i == 50:  # At midpoint, actually install dependencies
            subprocess.check_call([python_executable, '-m', 'pip', 'install', '-r', REQUIREMENTS])

if __name__ == '__main__':
    try:
        setup_environment()
        print("\nStarting application...")
        # Show progress bar for application startup
        for i in range(101):
            print_progress_bar(i, 100, prefix='Loading:', suffix='Complete', length=50)
            time.sleep(0.01)  # Simulate work
            if i == 100:  # At the end, actually start the app
                # Run application using venv python
                python_executable = os.path.join(VENV_NAME, 'Scripts', 'python.exe')
                subprocess.check_call([python_executable, '-m', 'src.app'])
    except subprocess.CalledProcessError as e:
        print(f"\nError during setup: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
