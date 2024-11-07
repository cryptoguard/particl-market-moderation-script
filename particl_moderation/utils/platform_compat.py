import os
import platform
import subprocess
import sys

from typing import Optional, List

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

def get_config_directory():
    if is_windows():
        return os.path.join(os.environ.get('APPDATA'), 'ParticlModeration')
    elif is_macos():
        return os.path.join(get_home_directory(), 'Library', 'Application Support', 'ParticlModeration')
    else:  # Linux and others
        return os.path.join(get_home_directory(), '.config', 'particl_moderation')

def create_directory_if_not_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def run_command(command: List[str], shell: bool = False) -> Optional[str]:
    """Execute a command with proper Windows encoding handling"""
    try:
        # Handle Windows executable extension
        if is_windows() and command and command[0].endswith('particl-cli'):
            command[0] = command[0] + '.exe'
            command[0] = os.path.normpath(command[0])

        # Create startup info for Windows
        startupinfo = None
        if is_windows():
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # Use different approach for Windows vs Unix
        if is_windows():
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=shell,
                startupinfo=startupinfo,
                universal_newlines=False  # Use binary mode
            )
            stdout_data, stderr_data = process.communicate()
            
            # Handle binary output with fallback encodings
            try:
                stdout = stdout_data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    stdout = stdout_data.decode('cp1252', errors='replace')
                except UnicodeDecodeError:
                    stdout = stdout_data.decode('latin1', errors='replace')
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command)
                
            return stdout.strip()
        else:
            # Unix systems - use default UTF-8
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                shell=shell
            )
            return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error running command: {e}", file=sys.stderr)
        if is_windows():
            print(f"Command attempted: {command[0]}", file=sys.stderr)
            if os.path.exists(command[0]):
                print(f"File exists at: {command[0]}", file=sys.stderr)
            else:
                print(f"File not found at: {command[0]}", file=sys.stderr)
        return None

def get_particl_data_dir():
    if is_windows():
        return os.path.join(os.environ.get('APPDATA'), 'Particl')
    elif is_macos():
        return os.path.join(get_home_directory(), 'Library', 'Application Support', 'Particl')
    else:  # Linux and others
        return os.path.join(get_home_directory(), '.particl')