import os
import subprocess
import json
import requests
import platform
import time
import yaml

from typing import Optional, List, Dict, Any
from rich.console import Console
from particl_moderation.utils.config import set_config
from prompt_toolkit import prompt


console = Console()

class ParticlCoreManager:
    def __init__(self):
        """Initialize ParticlCoreManager with fixed config path"""
        self.project_root = self.find_project_root()
        self.config_file = os.path.join(self.project_root, 'config', 'config.yaml')
        
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config file: {e}[/yellow]")
            self.config = {}
        
        self.set_default_paths()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return default config"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return yaml.safe_load(f) or {}
            return {}
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config file: {e}[/yellow]")
            return {}

    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            # Get the absolute path to the app root directory
            app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_file = os.path.join(app_root, 'config', 'config.yaml')
            
            # Save the config only if it has changed
            current_config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    current_config = yaml.safe_load(f) or {}
                    
            if current_config != self.config:
                # Save the config
                with open(config_file, 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False)
                    
                print("[green]Configuration saved successfully.[/green]")
        except Exception as e:
            print(f"[bold red]Error saving config: {str(e)}[/bold red]")

    def find_project_root(self):
        """Find the project root directory by looking for pyproject.toml"""
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.exists(os.path.join(current_dir, "pyproject.toml")):
            raise FileNotFoundError("Could not find project root (no pyproject.toml found)")
        return current_dir

    def load_paths(self):
        """Load paths from existing config"""
        version = self.config.get('particl', {}).get('version')
        if not version:
            console.print("[red]Error: Particl Core version not set in config[/red]")
            return
            
        core_dir = os.path.join(self.project_root, "core")
        version_dir = os.path.join(core_dir, f"particl-{version}")
        
        # Create absolute paths
        self.particl_folder = os.path.abspath(version_dir)
        self.particld_path = os.path.abspath(os.path.join(self.particl_folder, "bin", "particld"))
        self.cli_path = os.path.abspath(os.path.join(self.particl_folder, "bin", "particl-cli"))
        
        # Ensure the core directory exists
        os.makedirs(core_dir, exist_ok=True)

        # Update config with new paths
        set_config("particl.folder", self.particl_folder)
        set_config("particl.daemon_path", self.particld_path)
        set_config("particl.cli_path", self.cli_path)


    def set_default_paths(self) -> None:
        """Set default paths for Particl Core binaries"""
        version = self.config.get('particl', {}).get('version')
        if not version:
            return
            
        default_folder = os.path.join(self.project_root, "core", f"particl-{version}")
        
        if not self.config.get('particl'):
            self.config['particl'] = {}

        # Set default paths if they don't exist
        self.particl_folder = self.config['particl'].get('folder', default_folder)
        
        if platform.system().lower() == "windows":
            self.particld_path = self.config['particl'].get('daemon_path', 
                                                          os.path.join(self.particl_folder, "bin", "particld.exe"))
            self.cli_path = self.config['particl'].get('cli_path', 
                                                     os.path.join(self.particl_folder, "bin", "particl-cli.exe"))
        else:
            self.particld_path = self.config['particl'].get('daemon_path', 
                                                          os.path.join(self.particl_folder, "bin", "particld"))
            self.cli_path = self.config['particl'].get('cli_path', 
                                                     os.path.join(self.particl_folder, "bin", "particl-cli"))

        # Update config with current paths
        self.config['particl'].update({
            'folder': self.particl_folder,
            'daemon_path': self.particld_path,
            'cli_path': self.cli_path
        })

    def get_github_releases(self) -> Optional[List[Dict[str, Any]]]:
        """Get list of all releases from GitHub"""
        try:
            response = requests.get("https://api.github.com/repos/particl/particl-core/releases")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            console.print(f"[red]Error fetching releases: {str(e)}[/red]")
            return None

    def check_version_exists(self, version: str) -> bool:
        """Check if a specific version exists in GitHub releases"""
        releases = self.get_github_releases()
        if not releases:
            return False
        
        return any(release['tag_name'] == f"v{version}" for release in releases)

    def get_latest_version(self) -> Optional[str]:
        """Get latest version from GitHub releases"""
        releases = self.get_github_releases()
        if not releases:
            return None
        
        # First release in the list is the latest
        latest = releases[0]
        return latest['tag_name'].lstrip('v')

    def update_core_version(self, new_version: str) -> bool:
        """Update core version in config and update paths"""
        if not self.check_version_exists(new_version):
            return False
            
        # Update version in config
        self.config['particl']['version'] = new_version
        
        # Update paths
        self.set_default_paths()
        
        # Save config
        self.save_config()
        return True

    def download_particl_core(self, target_version: Optional[str] = None) -> bool:
        download_path = None
        version = target_version or self.config.get('particl', {}).get('version')
        if not version:
            console.print("[red]Error: Particl Core version not set in config[/red]")
            return False
            
        # Store current version in case we need to revert
        current_version = self.config.get('particl', {}).get('version')
            
        try:
            os_type = platform.system().lower()
            
            # Determine download URL and archive type
            if os_type == "windows":
                is_64bits = platform.machine().endswith('64')
                arch_suffix = "win64" if is_64bits else "win32"
                url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-{arch_suffix}.zip"
                is_zip = True
                console.print(f"Detected {arch_suffix} Windows system")
            elif os_type == "linux":
                if platform.machine().lower() in ["x86_64", "amd64"]:
                    url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-x86_64-linux-gnu.tar.gz"
                    is_zip = False
                elif platform.machine().lower() == "aarch64":
                    url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-aarch64-linux-gnu.tar.gz"
                    is_zip = False
                else:
                    raise ValueError(f"Unsupported Linux architecture: {platform.machine()}")
            elif os_type == "darwin":
                if platform.machine().lower() == "x86_64":
                    url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-x86_64-apple-darwin18.tar.gz"
                    is_zip = False
                elif platform.machine().lower() == "arm64":
                    url = f"https://github.com/particl/particl-core/releases/download/v{version}/particl-{version}-x86_64-apple-darwin18.tar.gz"
                    is_zip = False
                else:
                    raise ValueError(f"Unsupported macOS architecture: {platform.machine()}")
            else:
                raise ValueError(f"Unsupported operating system: {platform.system()}")

            console.print(f"[cyan]Downloading Particl Core v{version}...[/cyan]")
            console.print(f"[cyan]Download URL: {url}[/cyan]")

            # Download the file
            response = requests.get(url, stream=True)
            response.raise_for_status()
            filename = url.split('/')[-1]

            app_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            download_path = os.path.join(app_root, filename)
            
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
                        console.print(f"Download progress: {percent}%", end='\r')
            
            console.print("\n[green]Download completed.[/green]")
            console.print("[cyan]Extracting Particl Core...[/cyan]")

            extract_dir = os.path.join(app_root, "core")
            os.makedirs(extract_dir, exist_ok=True)

            # Extract files
            if is_zip:
                import zipfile
                with zipfile.ZipFile(download_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            else:
                import tarfile
                with tarfile.open(download_path, 'r:*') as tar:
                    tar.extractall(path=extract_dir)

            # Update paths
            self.particl_folder = os.path.abspath(os.path.join(extract_dir, f"particl-{version}"))
            if os_type == "windows":
                self.particld_path = os.path.join(self.particl_folder, "bin", "particld.exe")
                self.cli_path = os.path.join(self.particl_folder, "bin", "particl-cli.exe")
            else:
                self.particld_path = os.path.join(self.particl_folder, "bin", "particld")
                self.cli_path = os.path.join(self.particl_folder, "bin", "particl-cli")

            # Verify the binaries exist
            if not os.path.exists(self.particld_path) or not os.path.exists(self.cli_path):
                raise FileNotFoundError("Particl Core binaries not found after extraction")

            # Only update version in config after successful download and extraction
            if target_version:
                self.config['particl']['version'] = target_version

            # Update config with new paths
            self.config.setdefault('particl', {}).update({
                'folder': self.particl_folder,
                'daemon_path': self.particld_path,
                'cli_path': self.cli_path
            })

            # Save config
            self.save_config()

            console.print(f"[green]Particl Core v{version} downloaded and extracted successfully to:[/green]")
            console.print(f"[green]{self.particl_folder}[/green]")
            
            return True

        except Exception as e:
            # If anything fails, revert to previous version if we were updating
            if target_version and current_version:
                self.config['particl']['version'] = current_version
                self.set_default_paths()
                self.save_config()
                
            console.print(f"[bold red]Error during Particl Core installation: {str(e)}[/bold red]")
            return False

        finally:
            # Always clean up the temporary download file
            if download_path and os.path.exists(download_path):
                try:
                    os.remove(download_path)
                    console.print("[green]Temporary download file cleaned up successfully.[/green]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not remove temporary file {download_path}: {str(e)}[/yellow]")

    def _run_particl_command(self, command: List[str], wallet: str = None, silent: bool = False) -> Optional[str]:
        if not self.check_cli_path(silent=silent):
            if not silent:
                console.print("[bold red]Particl Core is not properly installed.[/bold red]")
                console.print("Please install it through Settings > Particl Wallet and Node Settings > Download/Update Particl Core")
            return None

        full_command = [self.cli_path]
        if wallet:
            full_command.append(f"-rpcwallet={wallet}")
        full_command.extend(command)
        
        try:
            result = subprocess.run(full_command, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error running Particl command: {e}[/bold red]")
            if e.stderr:
                console.print(f"Details: {e.stderr}")
            return None
        except OSError as e:
            if hasattr(e, 'winerror') and e.winerror == 193:  # Windows error for "not a valid Win32 application"
                console.print("\n[bold red]Error: Invalid Particl Core executable detected.[/bold red]")
                console.print("[yellow]This usually means either:[/yellow]")
                console.print("1. Particl Core has not been downloaded yet")
                console.print("2. The wrong version (Linux/Mac) was downloaded instead of Windows")
                console.print("\n[green]To fix this, please:[/green]")
                console.print("1. Go to Settings > Particl Wallet and Node Settings")
                console.print("2. Select 'Download/Update Particl Core'")
            # else:
            #     console.print(f"\n[bold red]Error accessing Particl Core executable: {e}[/bold red]")
            #     console.print("[yellow]Please ensure Particl Core is properly installed via the Settings menu.[/yellow]")
            return None
        except Exception as e:
            console.print(f"[bold red]Unexpected error running Particl command: {e}[/bold red]")
            console.print("[yellow]Please verify your Particl Core installation in Settings.[/yellow]")
            return None

    def start_particl_daemon(self) -> bool:
        """Start the Particl daemon"""
        try:
            if not self.check_cli_path():
                console.print("[red]Cannot start daemon: Particl Core not properly installed.[/red]")
                console.print("[yellow]Please install Particl Core through the Settings menu first.[/yellow]")
                return False

            if self.is_daemon_running():
                console.print("[yellow]Daemon is already running.[/yellow]")
                return True
            
            if platform.system().lower() == "windows":
                # Setup startup info to hide the window
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                # Start the process detached from the current terminal
                subprocess.Popen(
                    [self.particld_path],
                    startupinfo=startupinfo,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE
                )
            else:
                # For non-Windows systems, use the standard daemon flag
                subprocess.Popen([self.particld_path, "-daemon"])

            # Wait for daemon to start
            attempts = 0
            max_attempts = 30  # 30 seconds timeout
            while attempts < max_attempts:
                if self.is_daemon_running():
                    console.print("[green]Particl daemon started successfully.[/green]")
                    return True
                time.sleep(1)
                attempts += 1
                
                # Show progress every 5 seconds
                if attempts % 5 == 0:
                    console.print(f"[yellow]Waiting for daemon to start... ({attempts} seconds)[/yellow]")

            console.print("[red]Failed to confirm daemon start within timeout period.[/red]")
            return False

        except Exception as e:
            console.print(f"[bold red]Error starting daemon: {str(e)}[/bold red]")
            return False

    def stop_particl_daemon(self):
        console.clear()
        if not os.path.exists(self.cli_path):
            print(f"Error: particl-cli not found at {self.cli_path}")
            return False

        subprocess.run([self.cli_path, "stop"])
        if self.wait_for_daemon_stop():
            console.print("[green]Particl daemon stopped successfully.[/green]")
            input("Press Enter to continue...")
            return True
        return False

    def check_particl_core_exists(self):
        return os.path.exists(self.cli_path)

    def check_cli_path(self, silent: bool = False) -> bool:
        if not self.cli_path:
            if not silent:
                print("Particl CLI path is not set. Please set it in the configuration.")
            return False
        if not os.path.exists(self.cli_path):
            if not silent:
                print(f"Particl CLI not found at {self.cli_path}. Please check the path.")
            return False
        if not os.access(self.cli_path, os.X_OK):
            if not silent:
                print(f"Particl CLI at {self.cli_path} is not executable. Please check file permissions.")
            return False
        return True

    def is_daemon_running(self, silent: bool = False) -> bool:
        if not self.check_cli_path(silent=silent):
            return False
        try:
            subprocess.check_output([self.cli_path, "getblockcount"], stderr=subprocess.STDOUT, text=True)
            return True
        except subprocess.CalledProcessError:
            return False
        except PermissionError:
            if not silent:
                print(f"Permission denied when trying to execute {self.cli_path}. Please check file permissions.")
            return False

    def wait_for_daemon_start(self, timeout=60):
        for _ in range(timeout):
            if self.is_daemon_running():
                return True
            time.sleep(1)
        print("Failed to confirm Particl daemon start within the timeout period.")
        return False

    def wait_for_daemon_stop(self, timeout=30):
        for _ in range(timeout):
            if not self.is_daemon_running():
                return True
            time.sleep(1)
        print("Failed to confirm Particl daemon stop within the timeout period.")
        return False

    def get_sync_status(self) -> str:
        if not self.check_cli_path():
            return "N/A"
        try:
            output = subprocess.check_output([self.cli_path, "getblockchaininfo"], text=True)
            info = json.loads(output)
            progress = info.get('verificationprogress', 0)
            if isinstance(progress, (int, float)):
                return f"{progress*100:.2f}%"
            else:
                return "N/A"
        except subprocess.CalledProcessError:
            return "Error"
        except PermissionError:
            print(f"Permission denied when trying to execute {self.cli_path}. Please check file permissions.")
            return "Error"
        except json.JSONDecodeError:
            return "Error: Invalid JSON response"
        except Exception as e:
            return f"Error: {str(e)}"

if __name__ == "__main__":
    manager = ParticlCoreManager()
    
    if not manager.particld_path:
        manager.download_particl_core()
    
    if not manager.is_daemon_running():
        manager.start_particl_daemon()
    
    print(f"Sync status: {manager.get_sync_status()}")
    
    wallet_name = "moderation_wallet"
    success, wallet = manager.initialize_wallet(wallet_name)
    if success:
        manager.verify_and_update_wallet(wallet)
    
    manager.stop_particl_daemon()