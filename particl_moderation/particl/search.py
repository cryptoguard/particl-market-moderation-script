import json
import os
import subprocess
import re

from datetime import datetime
from typing import Optional, Dict, Any, List
from rich.console import Console
from datetime import datetime
from particl_moderation.utils.config import get_config, get_full_path
from particl_moderation.utils.platform_compat import is_windows
from particl_moderation.particl.particl_core_manager import ParticlCoreManager
from particl_moderation.utils.error_handler import handle_keyboard_interrupt, initialize_error_handling

console = Console()

initialize_error_handling()

def ensure_file_exists(file_path: str) -> None:
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            pass 
        os.chmod(file_path, 0o644)  

def _run_particl_command(command: List[str], active_wallet: Optional[str] = None) -> Optional[str]:
    core_manager = ParticlCoreManager()
    # if not core_manager.check_particl_core_exists():
    #     console.print("[bold red]Particl Core is not installed. Please install it from the settings menu.[/bold red]")
    #     return None

    cli_path = core_manager.cli_path
    wallet_param = f"-rpcwallet={active_wallet}" if active_wallet else ""
    full_command = [cli_path] + ([wallet_param] if wallet_param else []) + command

    try:
        # Use specific encoding settings for Windows
        if is_windows():
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.run(
                full_command,
                check=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo
            )
        else:
            process = subprocess.run(
                full_command,
                check=True,
                capture_output=True,
                text=True
            )
        
        return process.stdout.strip() if process.stdout else None

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Error running command: {e}[/bold red]")
        return None
    except PermissionError:
        console.print(f"[bold red]Permission denied when trying to execute {cli_path}. Please check file permissions.[/bold red]")
        return None


@handle_keyboard_interrupt
def particl_search() -> None:
    try:
        active_wallet = get_config("particl.active_wallet")

        if not active_wallet:
            console.print("[bold yellow]No active wallet set. Attempting to get the default wallet...[/bold yellow]")
            active_wallet = get_default_wallet()
            if not active_wallet:
                console.print("[bold red]Error: No active wallet found. Please set an active wallet in the settings menu.[/bold red]")
                return

        # Scan SMSG buckets
        result = _run_particl_command(["smsgscanbuckets"], active_wallet)
        if result is None:
            console.print("[bold red]Failed to scan SMSG buckets. Please check your Particl Core installation and wallet status.[/bold red]")
            return

        console.print("[green]Successfully scanned SMSG buckets.[/green]")

        # Get SMSG inbox
        console.print("[cyan]Executing command: smsginbox all[/cyan]")
        smsg_inbox = _run_particl_command(["smsginbox", "all"], active_wallet)
        if not smsg_inbox:
            console.print("[bold red]Failed to retrieve SMSG inbox. Please check your Particl Core installation and wallet status.[/bold red]")
            return

        # Process listings
        messages = json.loads(smsg_inbox).get('messages', [])
        for smsg in messages:
            process_smsg(smsg)

        console.print("[green]Finished processing SMSG inbox.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user. Returning to main menu...[/yellow]")

def get_default_wallet() -> Optional[str]:
    result = _run_particl_command(["listwallets"])
    if result:
        wallets = json.loads(result)
        return wallets[0] if wallets else None
    return None

def process_smsg(smsg: Dict[str, Any]) -> None:
    try:
        text = json.loads(smsg.get('text', '{}'))
        action_type = text.get('action', {}).get('type')
        
        if action_type != "MPA_LISTING_ADD_03":
            return

        hash = text.get('action', {}).get('hash')
        title = text.get('action', {}).get('item', {}).get('information', {}).get('title')
        short_description = text.get('action', {}).get('item', {}).get('information', {}).get('shortDescription', '')
        long_description = text.get('action', {}).get('item', {}).get('information', {}).get('longDescription', '')

        if not hash or not title:
            return

        # Clean up the title and descriptions: remove newlines and extra spaces
        title = ' '.join(title.strip().replace('\n', ' ').replace('\r', ' ').split())
        short_description = ' '.join(short_description.strip().replace('\n', ' ').replace('\r', ' ').split())
        long_description = ' '.join(long_description.strip().replace('\n', ' ').replace('\r', ' ').split())
        description = f"{short_description} {long_description}".strip()

        title = title.replace('|', '\\|')
        description = description.replace('|', '\\|')

        # Validate hash (64-character hexadecimal string)
        if not re.match(r'^[a-fA-F0-9]{64}$', hash):
            console.print(f"[yellow]Error: Invalid hash format for listing. Skipping.[/yellow]")
            return

        cache_file = get_full_path("paths.cache_file")
        ensure_file_exists(cache_file)

        with open(cache_file, 'r', encoding='utf-8', errors='replace') as cache:
            if hash in cache.read().splitlines():
                console.print(f"[yellow]Listing hash {hash} already exists in cache. Skipping.[/yellow]")
                return

        with open(cache_file, 'a', encoding='utf-8') as cache:
            cache.write(f"{hash}\n")

        queue_file = get_full_path("paths.queue_file")
        ensure_file_exists(queue_file)

        # Write the cleaned up entry to the queue
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(queue_file, 'a', encoding='utf-8') as queue:
            queue.write(f"[{date}] | {hash} | {title} | {description}\n")

        console.print("[green]Item added to queue successfully.[/green]")
        console.print(f"Hash: {hash}")
        console.print(f"Title: {title}")
        console.print(f"Description: {description}")
        console.print(f"Date: {date}")

    except json.JSONDecodeError:
        console.print(f"[yellow]Error decoding JSON for message: {smsg.get('msgid', 'unknown')}[/yellow]")
    except KeyError as e:
        console.print(f"[yellow]Missing key in message structure: {e}[/yellow]")
    except Exception as e:
        console.print(f"[red]Error processing message: {str(e)}[/red]")

if __name__ == "__main__":
    particl_search()