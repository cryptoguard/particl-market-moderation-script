import subprocess
import sys
import site
import os

def install_yaml():
    print("Installing required PyYAML package...")
    try:
        # Try installing with --user flag
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'PyYAML==6.0.1'])
        
        # Add user site-packages to Python path
        user_site = site.getusersitepackages()
        if user_site not in sys.path:
            sys.path.append(user_site)
            
        import yaml
        return True
    except subprocess.CalledProcessError:
        print("Trying with pip3...")
        try:
            subprocess.check_call(['pip3', 'install', '--user', 'PyYAML==6.0.1'])
            
            # Add user site-packages to Python path
            user_site = site.getusersitepackages()
            if user_site not in sys.path:
                sys.path.append(user_site)
                
            import yaml
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install PyYAML: {e}")
            return False

try:
    import yaml
except ImportError:
    if not install_yaml():
        sys.exit(1)

def install_requests():
    print("Installing required requests package...")
    try:
        # Try installing with --user flag
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '--user', 'requests'])
        
        # Add user site-packages to Python path
        user_site = site.getusersitepackages()
        if user_site not in sys.path:
            sys.path.append(user_site)
            
        import requests
        return True
    except subprocess.CalledProcessError:
        print("Trying with pip3...")
        try:
            subprocess.check_call(['pip3', 'install', '--user', 'requests'])
            
            # Add user site-packages to Python path
            user_site = site.getusersitepackages()
            if user_site not in sys.path:
                sys.path.append(user_site)
                
            import requests
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install requests: {e}")
            return False

try:
    import requests
except ImportError:
    if not install_requests():
        sys.exit(1)

import venv
import tempfile
import stat
import json
import platform
import shutil
from typing import Dict, Any

# Platform compatibility functions needed for setup
def get_platform():
    return platform.system().lower()

def is_windows():
    return get_platform() == 'windows'

def is_macos():
    return get_platform() == 'darwin'

def is_linux():
    return get_platform() == 'linux'

def get_home_directory():
    return os.path.expanduser("~")

def find_project_root():
    """Find the project root directory by looking for pyproject.toml"""
    current_dir = os.path.abspath(os.path.dirname(__file__))
    while True:
        if os.path.exists(os.path.join(current_dir, "pyproject.toml")):
            return current_dir
        parent_dir = os.path.dirname(current_dir)
        if parent_dir == current_dir:
            raise FileNotFoundError("Could not find project root")
        current_dir = parent_dir

def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def setup_config_paths() -> Dict[str, Any]:
    """Set up the configuration with correct absolute paths"""
    project_root = find_project_root()
    config_dir = os.path.join(project_root, "config")
    create_directory_if_not_exists(config_dir)

    # Get Particl version
    particl_version = "23.2.7.0"
    core_dir = os.path.join(project_root, "core", f"particl-{particl_version}")

    # Create the base configuration
    config = {
        "particl": {
            "version": particl_version, 
            "folder": os.path.abspath(core_dir),
            "daemon_path": os.path.abspath(os.path.join(core_dir, "bin", "particld")),
            "cli_path": os.path.abspath(os.path.join(core_dir, "bin", "particl-cli")),
            "active_wallet": "",
            "data_dir": ""
        },
        "llm": {
            "model": "gemma2:2b",
            "ollama_path": ""
        },
        "logging": {
            "file": os.path.abspath(os.path.join(config_dir, "moderation.log"))
        },
        "paths": {
            "cache_file": os.path.abspath(os.path.join(config_dir, "listing_cache.txt")),
            "dummy_listings_file": os.path.abspath(os.path.join(config_dir, "dummy_listings.txt")),
            "queue_file": os.path.abspath(os.path.join(config_dir, "queue.txt")),
            "results_file": os.path.abspath(os.path.join(config_dir, "results.txt")),
            "test_prompts_file": os.path.abspath(os.path.join(config_dir, "test_prompts.txt")),
            "vote_queue_file": os.path.abspath(os.path.join(config_dir, "vote_queue.txt"))
        },
        "rules": {
            "config_file": os.path.abspath(os.path.join(config_dir, "rules_config.json")),
            "predefined_file": os.path.abspath(os.path.join(config_dir, "predefined_rules.json"))
        }
    }

    # Set paths based on version
    version = config['particl']['version']
    core_dir = os.path.join(project_root, "core", f"particl-{version}")
    config['particl']['folder'] = os.path.abspath(core_dir)
    
    if platform.system().lower() == "windows":
        config['particl']['daemon_path'] = os.path.abspath(os.path.join(core_dir, "bin", "particld.exe"))
        config['particl']['cli_path'] = os.path.abspath(os.path.join(core_dir, "bin", "particl-cli.exe"))
    else:
        config['particl']['daemon_path'] = os.path.abspath(os.path.join(core_dir, "bin", "particld"))
        config['particl']['cli_path'] = os.path.abspath(os.path.join(core_dir, "bin", "particl-cli"))

    # Create directories
    create_directory_if_not_exists(os.path.join(project_root, "core"))

    # Save configuration
    config_file = os.path.join(config_dir, "config.yaml")
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

    # Create rules config file
    default_rules = {
        "adult-content": {
            "downvote": [],
            "upvote": [],
            "ignore": []
        },
        "children": {
            "downvote": [],
            "upvote": [],
            "ignore": []
        },
        "drugs": {
            "downvote": [],
            "upvote": [],
            "ignore": []
        },
        "online-services": {
            "downvote": [],
            "upvote": [],
            "ignore": []
        },
        "personal-data": {
            "downvote": [],
            "upvote": [],
            "ignore": []
        },
        "weapons": {
            "downvote": [],
            "upvote": [],
            "ignore": []
        }
    }

    # Save default rules configuration
    rules_config_file = os.path.join(config_dir, "rules_config.json")
    with open(rules_config_file, 'w') as f:
        json.dump(default_rules, f, indent=2)

    return config


def run_command(command, shell=False):
    """Run a command and return its output, filtering out console mode messages"""
    try:
        result = subprocess.run(command, 
                              check=True, 
                              shell=shell, 
                              text=True, 
                              capture_output=True)
        # Filter out console mode error messages
        output_lines = [line for line in result.stdout.splitlines() 
                       if 'failed to get console mode' not in line]
        return '\n'.join(output_lines).strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return None

def install_dependencies(python_path: str):
    print("Upgrading pip...")
    subprocess.run([python_path, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)

    print("Installing dependencies from requirements.txt...")
    try:
        subprocess.run([python_path, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Some dependencies failed to install: {e}")
        print("Attempting to install dependencies individually...")
        
        with open('requirements.txt', 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        for req in requirements:
            if 'qrcode==8.0' in req and is_macos():
                continue  # Skip qrcode 8.0 on macOS, we'll handle it separately
            try:
                subprocess.run([python_path, '-m', 'pip', 'install', req], check=True)
            except subprocess.CalledProcessError:
                print(f"Warning: Failed to install {req}")

    print("Installing package in development mode...")
    subprocess.run([python_path, '-m', 'pip', 'install', '-e', '.'], check=True)

    if is_macos():
        print("Installing qrcode package for macOS...")
        try:
            subprocess.run([python_path, '-m', 'pip', 'install', 'qrcode'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to install qrcode: {e}")

def check_ollama():
    try:
        version = check_ollama_version()
        if version:
            print(f"[✓] Ollama is already installed and ready to use. Version: {version}")
            return True
        else:
            print("Ollama is not installed or not in PATH.")
            return False
    except FileNotFoundError:
        print("Ollama is not installed or not in PATH.")
        return False
    except Exception as e:
        print(f"Error checking Ollama installation: {e}")
        return False

def check_ollama_version():
    """Check if ollama command is available and return version if found"""
    try:
        # Using subprocess directly for better output control
        result = subprocess.run(['ollama', '--version'], 
                              capture_output=True, 
                              text=True)
        # Extract just the version number from the output
        version_text = result.stdout.strip()
        # Remove any error messages about console mode
        if 'ollama version is' in version_text:
            version = version_text.split('ollama version is')[-1].strip()
        else:
            version = version_text
        return version
    except:
        return None

def install_ollama_unix():
    print("Installing the latest version of Ollama...")
    try:
        script_url = "https://ollama.ai/install.sh"
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            subprocess.run(["curl", "-fsSL", script_url, "-o", temp_file.name], check=True)
        
        os.chmod(temp_file.name, os.stat(temp_file.name).st_mode | stat.S_IEXEC)
        
        run_command([temp_file.name], shell=True)
        
        print("Ollama installed successfully.")
        return True
    except Exception as e:
        print(f"Failed to install Ollama: {e}")
        return False

def install_ollama_windows():
    """Install Ollama on Windows with user confirmation"""
    print("\nWould you like the script to automatically download and install Ollama? (y/n)")
    choice = input().lower().strip()
    
    if choice != 'y':
        print("\nAutomated installation of Ollama is not available for Windows.")
        print("Please follow these steps to install Ollama manually:")
        print("1. Go to https://ollama.ai/download")
        print("2. Download the Windows installer")
        print("3. Run the installer and follow the prompts")
        print("4. After installation, restart your terminal or command prompt")
        return False

    print("\nDownloading Ollama installer...")
    download_url = "https://ollama.com/download/OllamaSetup.exe"
    installer_path = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")

    try:
        # Download the installer
        import urllib.request
        urllib.request.urlretrieve(download_url, installer_path)

        print("Running Ollama installer...")
        try:
            # Try to run silently first
            result = subprocess.run([installer_path, '/VERYSILENT'], 
                                 capture_output=True, 
                                 text=True)
            if result.returncode != 0:
                # If silent install fails, run normally
                os.startfile(installer_path)
                print("\nThe Ollama installer window should now open.")
                print("Please complete the installation process.")
                input("Press Enter once you have finished installing Ollama...")
        except Exception as e:
            print(f"\nCould not run installer silently: {e}")
            os.startfile(installer_path)
            print("\nThe Ollama installer window should now open.")
            print("Please complete the installation process.")
            input("Press Enter once you have finished installing Ollama...")

        # Clean up
        try:
            os.remove(installer_path)
        except Exception as e:
            print(f"Note: Could not remove temporary installer: {e}")

        print("\nChecking Ollama installation...")
        
        # Check if Ollama is now available
        version = check_ollama_version()
        if version:
            print(f"\n[✓] Ollama version {version} installed successfully and ready to use. No need to start a new terminal instance.")
        else:
            print("\n[!] Ollama has been installed but cannot be detected in the current terminal session.")
            print("    Please start a new terminal instance to use Ollama.")
            print("    You can verify the installation in the new terminal by running: ollama --version")

        return True

    except Exception as e:
        print(f"\nError during Ollama installation: {e}")
        if os.path.exists(installer_path):
            try:
                os.remove(installer_path)
            except:
                pass
        return False

def install_ollama_mac():
    """Install Ollama on macOS with user confirmation"""
    print("\nWould you like the script to automatically download and install Ollama? (y/n)")
    choice = input().lower().strip()
    
    if choice != 'y':
        print("\nSkipping automated installation.")
        print("Please follow these steps to install Ollama manually:")
        print("1. Go to https://ollama.ai/download")
        print("2. Download the macOS installer")
        print("3. Install the application")
        print("4. After installation, restart your terminal")
        return False

    print("\nInstalling Ollama for macOS...")
    
    download_url = "https://ollama.com/download/Ollama-darwin.zip"
    download_path = os.path.join(tempfile.gettempdir(), "Ollama-darwin.zip")
    app_path = "/Applications/Ollama.app"
    
    try:
        # Download the zip file
        print("Downloading Ollama...")
        subprocess.run(["curl", "-L", "-o", download_path, download_url], check=True)
        
        # Unzip to /Applications
        print("Extracting Ollama...")
        subprocess.run(["unzip", "-o", download_path, "-d", "/Applications/"], check=True)
        
        # Try to remove quarantine attribute if it exists
        print("Removing quarantine attribute if present...")
        try:
            result = subprocess.run(["xattr", app_path], capture_output=True, text=True)
            if "com.apple.quarantine" in result.stdout:
                subprocess.run(["xattr", "-d", "com.apple.quarantine", app_path], check=True)
        except subprocess.CalledProcessError:
            print("Note: Could not remove quarantine attribute. This is normal if it doesn't exist.")
        
        # Start Ollama
        print("Starting Ollama...")
        subprocess.run(["open", "-a", "Ollama"], check=True)
        
        # Clean up
        os.remove(download_path)
        
        print("\nOllama has been installed and started.")
        print("Note: You may need to allow Ollama in System Settings > Security & Privacy")
        print("      You may also need to right-click the app and select 'Open' the first time.")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error installing Ollama: {e}")
        if os.path.exists(download_path):
            os.remove(download_path)
        return False

def install_ollama():
    if is_windows():
        return install_ollama_windows()
    elif is_macos():
        return install_ollama_mac()
    else:  # Linux
        print("Installing the latest version of Ollama...")
        try:
            script_url = "https://ollama.ai/install.sh"
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                subprocess.run(["curl", "-fsSL", script_url, "-o", temp_file.name], check=True)
            
            os.chmod(temp_file.name, os.stat(temp_file.name).st_mode | stat.S_IEXEC)
            subprocess.run([temp_file.name], shell=True, check=True)
            
            os.unlink(temp_file.name)
            print("Ollama installed successfully. You You may need to start a new terminal instance.")
            return True
        except Exception as e:
            print(f"Failed to install Ollama: {e}")
            return False

def install_dependencies(python_path: str):
    """Install dependencies in the virtual environment."""
    print("Setting up pip...")
    try:
        # First properly initialize pip in the venv
        subprocess.run([python_path, '-m', 'ensurepip', '--default-pip'], check=True)
        
        # Get the venv's pip path
        venv_pip = os.path.join(os.path.dirname(python_path), 'pip3')
        if not os.path.exists(venv_pip):
            venv_pip = os.path.join(os.path.dirname(python_path), 'pip')

        # Upgrade pip using the venv's python
        subprocess.run([python_path, '-m', 'pip', 'install', '--upgrade', 'pip', '--no-cache-dir'], check=True)

        print("Installing dependencies from requirements.txt...")
        subprocess.run([python_path, '-m', 'pip', 'install', '-r', 'requirements.txt', '--no-cache-dir'], check=True)
        
        print("Installing package in development mode...")
        subprocess.run([python_path, '-m', 'pip', 'install', '-e', '.', '--no-cache-dir'], check=True)

        if is_macos():
            print("Installing qrcode package for macOS...")
            subprocess.run([python_path, '-m', 'pip', 'install', 'qrcode', '--no-cache-dir'], check=True)

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error during dependency installation: {e}")
        return False

def create_venv(venv_dir: str) -> bool:
    """Create a virtual environment using multiple fallback methods."""
    print("Creating virtual environment...")
    
    # First, try cleaning up any failed venv
    if os.path.exists(venv_dir):
        print("Removing existing virtual environment...")
        try:
            shutil.rmtree(venv_dir)
        except Exception as e:
            print(f"Warning: Could not remove existing venv: {e}")
            return False

    if is_macos():
        try:
            # Try using python3 -m venv directly first
            subprocess.run([sys.executable, '-m', 'venv', venv_dir], check=True)
            fix_venv_permissions(venv_dir)
            return True
        except subprocess.CalledProcessError:
            print("Standard venv creation failed, trying virtualenv...")
            
            # Install virtualenv if needed
            subprocess.run([sys.executable, '-m', 'pip', 'install', '--user', 'virtualenv'], check=True)
            
            # Use virtualenv from the user's bin directory
            user_bin = os.path.expanduser('~/Library/Python/3.8/bin')
            virtualenv_path = os.path.join(user_bin, 'virtualenv')
            
            try:
                subprocess.run([virtualenv_path, venv_dir], check=True)
                fix_venv_permissions(venv_dir)
                return True
            except Exception as e:
                print(f"Failed to create virtual environment: {e}")
                return False
    else:
        try:
            venv.create(venv_dir, with_pip=True)
            return True
        except Exception as e:
            print(f"Failed to create virtual environment: {e}")
            return False

def fix_venv_permissions(venv_dir: str):
    """Fix permissions in the virtual environment directory."""
    print("Fixing virtual environment permissions...")
    try:
        # Get current user
        import pwd
        user = pwd.getpwuid(os.getuid()).pw_name
        
        # Fix permissions recursively
        for root, dirs, files in os.walk(venv_dir):
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o755)
        
        # Set ownership
        subprocess.run(['chown', '-R', user, venv_dir], check=True)
    except Exception as e:
        print(f"Warning: Could not fix permissions: {e}")

def install_dependencies(python_path: str):
    """Install dependencies in the virtual environment."""
    print("Setting up pip...")
    try:
        # First, ensure pip is properly installed
        subprocess.run([python_path, '-m', 'ensurepip', '--upgrade'], check=True)
        subprocess.run([python_path, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not setup pip: {e}")
        return False

    print("Installing dependencies from requirements.txt...")
    try:
        subprocess.run([python_path, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Warning: Some dependencies failed to install: {e}")
        print("Attempting to install dependencies individually...")
        
        with open('requirements.txt', 'r') as f:
            requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        for req in requirements:
            if 'qrcode==8.0' in req and is_macos():
                continue  # Skip qrcode 8.0 on macOS, we'll handle it separately
            try:
                subprocess.run([python_path, '-m', 'pip', 'install', req], check=True)
            except subprocess.CalledProcessError:
                print(f"Warning: Failed to install {req}")

    print("Installing package in development mode...")
    subprocess.run([python_path, '-m', 'pip', 'install', '-e', '.'], check=True)

    if is_macos():
        print("Installing qrcode package for macOS...")
        try:
            subprocess.run([python_path, '-m', 'pip', 'install', 'qrcode'], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to install qrcode: {e}")
    if is_macos():
        print("Installing compatible urllib3 for macOS...")
        subprocess.run([python_path, '-m', 'pip', 'uninstall', '-y', 'urllib3'], check=True)
        subprocess.run([python_path, '-m', 'pip', 'install', 'urllib3<2.0.0', '--no-cache-dir'], check=True)

    return True

def download_particl_core(project_root: str, version: str) -> bool:
    """Download and extract Particl Core during initial setup"""
    print(f"\nDownloading Particl Core v{version}...")
    
    try:
        os_type = platform.system().lower()
        download_path = None
        
        # Determine download URL based on platform
        if os_type == "windows":
            is_64bits = platform.machine().endswith('64')
            arch_suffix = "win64" if is_64bits else "win32"
            url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-{arch_suffix}.zip"
            is_zip = True
            print(f"Detected {arch_suffix} Windows system")
        elif os_type == "linux":
            if platform.machine().lower() in ["x86_64", "amd64"]:
                url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-x86_64-linux-gnu.tar.gz"
                is_zip = False
            elif platform.machine().lower() == "aarch64":
                url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-aarch64-linux-gnu.tar.gz"
                is_zip = False
            else:
                print(f"Unsupported Linux architecture: {platform.machine()}")
                return False
        elif os_type == "darwin":
            if platform.machine().lower() == "x86_64":
                url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-x86_64-apple-darwin18.tar.gz"
                is_zip = False
            elif platform.machine().lower() == "arm64":
                url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-x86_64-apple-darwin18.tar.gz"
                is_zip = False
            else:
                print(f"Unsupported macOS architecture: {platform.machine()}")
                return False
        else:
            print(f"Unsupported operating system: {platform.system()}")
            return False

        print(f"Download URL: {url}")

        # Download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()
        filename = url.split('/')[-1]
        download_path = os.path.join(project_root, filename)
        
        # Download with progress indication
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        downloaded = 0
        
        with open(download_path, 'wb') as f:
            for data in response.iter_content(block_size):
                downloaded += len(data)
                f.write(data)
                if total_size:
                    percent = int((downloaded / total_size) * 100)
                    print(f"Download progress: {percent}%", end='\r')
        
        print("\nDownload completed. Extracting...")

        # Extract files
        extract_dir = os.path.join(project_root, "core")
        os.makedirs(extract_dir, exist_ok=True)

        if is_zip:
            import zipfile
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        else:
            import tarfile
            with tarfile.open(download_path, 'r:*') as tar:
                tar.extractall(path=extract_dir)

        # Clean up download file
        if os.path.exists(download_path):
            os.remove(download_path)
            print("Temporary download file cleaned up.")

        print(f"Particl Core v{version} installed successfully in: {extract_dir}")
        return True

    except Exception as e:
        print(f"Error downloading Particl Core: {str(e)}")
        if download_path and os.path.exists(download_path):
            os.remove(download_path)
        return False

def setup_environment():
    print("Setting up environment...")
    
    # Set up configuration and paths first
    project_root = find_project_root()
    config = setup_config_paths()
    print("Configuration files and directories created.")

    # Download Particl Core
    print("\nDownloading Particl Core...")
    version = config['particl']['version']
    if download_particl_core(project_root, version):
        print("Particl Core installation completed successfully.")
    else:
        print("Failed to download Particl Core. You can install it later through the settings menu.")

    # Create and set up virtual environment
    venv_dir = 'venv'
    if not create_venv(venv_dir):
        print("Failed to create virtual environment. Exiting.")
        sys.exit(1)

    if is_windows():
        python_path = os.path.join(venv_dir, 'Scripts', 'python.exe')
        activate_script = os.path.join(venv_dir, 'Scripts', 'activate')
    else:
        python_path = os.path.join(venv_dir, 'bin', 'python')
        activate_script = os.path.join(venv_dir, 'bin', 'activate')

    if not os.path.exists(python_path):
        print(f"Error: Virtual environment seems incomplete. Could not find {python_path}")
        sys.exit(1)

    # Install dependencies
    if not install_dependencies(python_path):
        print("Failed to install dependencies. Please check the error messages above.")
        sys.exit(1)

    # Check and install Ollama if needed
    if not check_ollama():
        if install_ollama():
            print("Ollama installation completed.")
        else:
            print("Failed to install Ollama automatically. Please install it manually.")

    print("\nSetup complete!")
    config_file = os.path.join(find_project_root(), "config", "config.yaml")
    print(f"Configuration has been written to: {config_file}")
    print("\nTo activate the virtual environment, run:")
    if is_windows():
        print(f"{activate_script}")
    else:
        print(f"source {activate_script}")

if __name__ == '__main__':
    setup_environment()