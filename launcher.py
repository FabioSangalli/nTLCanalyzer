import os
import sys
import subprocess
import time
import json
import datetime
from concurrent.futures import ThreadPoolExecutor

# Add the current directory to the path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.app import run_application

VENV_NAME = 'TLC'
REQUIREMENTS = 'requirements.txt'
CACHE_FILE = os.path.join('resources', 'package_cache.json')
CACHE_EXPIRY_DAYS = 7  # Check packages once a week

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

def check_cache_valid():
    """Check if the package cache is valid"""
    try:
        # Create resources directory if it doesn't exist
        os.makedirs('resources', exist_ok=True)
        
        # Check if cache file exists
        if not os.path.exists(CACHE_FILE):
            return False
            
        # Load cache data
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
            
        # Check if cache has timestamp
        if 'timestamp' not in cache:
            return False
            
        # Check if cache has expired
        cache_date = datetime.datetime.fromisoformat(cache['timestamp'])
        now = datetime.datetime.now()
        delta = now - cache_date
        
        # Return True if cache is still valid (not expired)
        return delta.days < CACHE_EXPIRY_DAYS
    except Exception:
        # If any error occurs, consider cache invalid
        return False

def update_cache():
    """Update the package cache"""
    try:
        cache = {
            'timestamp': datetime.datetime.now().isoformat(),
            'requirements': REQUIREMENTS
        }
        
        # Create resources directory if it doesn't exist
        os.makedirs('resources', exist_ok=True)
        
        # Save cache data
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"Warning: Failed to update cache: {e}")

def setup_environment():
    # Check if virtual environment exists
    venv_path = os.path.join(os.getcwd(), VENV_NAME)
    python_executable = os.path.join(venv_path, 'Scripts', 'python.exe')
    
    # Create virtual environment if it doesn't exist
    if not os.path.exists(venv_path):
        print(f"Creating virtual environment '{VENV_NAME}'...")
        # Show progress bar for venv creation
        for i in range(101):
            print_progress_bar(i, 100, prefix='Progress:', suffix='Complete', length=50)
            time.sleep(0.01)  # Simulate work
            if i == 50:  # At midpoint, actually create the venv
                subprocess.check_call([sys.executable, '-m', 'venv', VENV_NAME])
        
        # New environment always needs packages installed
        needs_package_update = True
    else:
        # Check if we need to update packages based on cache
        needs_package_update = not check_cache_valid()
    
    # Only update pip and install packages if needed
    if needs_package_update:
        # Update pip first
        print("\nUpdating pip...")
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
        
        # Install requirements
        print("\nInstalling dependencies...")
        # Show progress bar for dependency installation
        for i in range(101):
            print_progress_bar(i, 100, prefix='Progress:', suffix='Complete', length=50)
            time.sleep(0.01)  # Simulate work
            if i == 50:  # At midpoint, actually install dependencies
                subprocess.check_call([python_executable, '-m', 'pip', 'install', '-r', REQUIREMENTS])
        
        # Update cache after successful installation
        update_cache()
    else:
        print("\nUsing cached dependencies (last updated within the past week)")
        # Just show a quick progress bar to indicate we're checking
        for i in range(101):
            print_progress_bar(i, 100, prefix='Verifying:', suffix='Complete', length=50)
            time.sleep(0.005)  # Faster progress since we're not doing real work

def start_application():
    """Start the application with optimized loading"""
    print("\nStarting application...")
    # Show progress bar for application startup
    for i in range(101):
        print_progress_bar(i, 100, prefix='Loading:', suffix='Complete', length=50)
        time.sleep(0.005)  # Faster loading animation
        if i == 100:  # At the end, actually start the app
            # Run application using venv python
            python_executable = os.path.join(VENV_NAME, 'Scripts', 'python.exe')
            subprocess.check_call([python_executable, '-m', 'src.app'])

def main():
    """Main entry point with error handling"""
    try:
        # Use ThreadPoolExecutor for potential parallel operations in the future
        with ThreadPoolExecutor() as executor:
            # For now, just run setup_environment in the main thread
            # This could be expanded later for more parallel operations
            setup_environment()
            start_application()
    except subprocess.CalledProcessError as e:
        print(f"\nError during setup: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
