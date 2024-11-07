import json
import shlex
import subprocess
import os
import hashlib

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from particl_moderation.utils.config import get_config, get_full_path
from particl_moderation.utils.platform_compat import run_command, is_windows
from particl_moderation.utils.log import log_marketplace_action
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()

VOTE_QUEUE_FILE = get_full_path("paths.vote_queue_file")
PARTICL_CLI = get_config("particl.cli_path") 
ACTIVE_WALLET = get_config("particl.active_wallet")
DEFAULT_MARKET_ADDRESS = "PZijh4WzjCWLbSgBkMUtLHZBaU6dSSmkqN"

def log(message: str, style: str = ""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    console.print(f"[cyan][{timestamp}][/cyan] {message}", style=style)

def log_json(data: Any):
    json_str = json.dumps(data, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(syntax)

def execute_particl_cli(command: str) -> Optional[str]:
    """Execute Particl CLI command using the path from config"""
    if not PARTICL_CLI:
        log("Error: Particl CLI path not configured.", style="bold red")
        return None

    if not os.path.exists(PARTICL_CLI):
        log(f"Error: Particl CLI not found at configured path: {PARTICL_CLI}", style="bold red")
        return None

    # Get wallet from config
    active_wallet = get_config("particl.active_wallet")
    if not active_wallet:
        log("[red]No active wallet configured in config.[/red]")
        return None

    try:
        if is_windows():
            cli_path = os.path.normpath(PARTICL_CLI)
            if not cli_path.endswith('.exe'):
                cli_path += '.exe'

            if 'smsgsend' in command:
                parts = shlex.split(command)
                command_args = [
                    cli_path,
                    f"-rpcwallet={active_wallet}",  # Add wallet from config
                    parts[0],  # 'smsgsend'
                    parts[1].strip('"'),  # from address
                    parts[2].strip('"'),  # to address
                    parts[3].strip('"'),  # message
                    'false',
                    '2'
                ]
            else:
                command_args = [
                    cli_path,
                    f"-rpcwallet={active_wallet}",  # Add wallet from config
                    *shlex.split(command)
                ]

            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.run(
                command_args,
                capture_output=True,
                text=True,
                shell=False,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo
            )
        else:
            # Unix-like systems (Linux and macOS)
            command_args = [
                PARTICL_CLI,
                f"-rpcwallet={active_wallet}",  # Add wallet from config
                *shlex.split(command)
            ]
            
            process = subprocess.run(
                command_args,
                capture_output=True,
                text=True,
                shell=False
            )
        
        if process.stderr:
            log(f"[yellow]Command stderr: {process.stderr}[/yellow]")
        
        return process.stdout.strip() if process.returncode == 0 else None
            
    except subprocess.CalledProcessError as e:
        log(f"Error executing command: {e}", style="bold red")
        if e.stderr:
            log(f"Error output: {e.stderr}", style="bold red")
        return None
    except Exception as e:
        log(f"Unexpected error: {str(e)}", style="bold red")
        return None

def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def read_vote_queue() -> List[List[str]]:
    if not os.path.exists(VOTE_QUEUE_FILE):
        log(f"[yellow]Vote queue file not found: {VOTE_QUEUE_FILE}[/yellow]")
        return []
    
    queue = []
    try:
        with open(VOTE_QUEUE_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        queue.append(parts[:5])
                    else:
                        log(f"[yellow]Skipping invalid line in vote queue: {line}[/yellow]")
    except UnicodeDecodeError:
        with open(VOTE_QUEUE_FILE, 'r', encoding='cp1252') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if len(parts) >= 5:
                        queue.append(parts[:5])
                    else:
                        log(f"[yellow]Skipping invalid line in vote queue: {line}[/yellow]")
    
    return queue

def get_existing_proposals(listing_hash: str) -> Optional[Dict[str, Any]]:
   
    command = 'smsginbox all "MPA_PROPOSAL_ADD"'
    result = execute_particl_cli(command)
   
    if not result:
        log(f"[yellow]No proposal messages found[/yellow]")
        return None
   
    try:
        data = json.loads(result)
        messages = data.get('messages', [])
        valid_proposals = []
       
        for msg in messages:
            try:
                text = msg.get('text', '')
                text_data = json.loads(text)
                # Check if this proposal's target matches our listing hash
                if (text_data['action']['type'] == 'MPA_PROPOSAL_ADD' and
                    text_data['action']['target'] == listing_hash):  # Changed from title to target
                    received = int(msg.get('received', 0))
                    valid_proposals.append((received, text_data['action']))
            except (json.JSONDecodeError, KeyError):
                continue

        if not valid_proposals:
            log(f"[yellow]No valid proposals found for listing hash: '{listing_hash}'[/yellow]")
            return None

        oldest_proposal = sorted(valid_proposals, key=lambda x: x[0])[0][1]
        log(f"[green]Found existing proposal for listing hash: '{listing_hash}'[/green]")
        log(f"[bold cyan]Proposal hash: {oldest_proposal['hash']}[/bold cyan]")
        return oldest_proposal

    except json.JSONDecodeError:
        log(f"[bold red]Error decoding JSON from smsginbox command[/bold red]")
        return None

def get_addresses_with_coins() -> List[Dict[str, Any]]:
    command = 'listunspent'
    result = execute_particl_cli(command)
    if not result:
        return []
    unspent = json.loads(result)
    addresses = []
    for tx in unspent:
        if tx['amount'] > 0 and tx['address'] != DEFAULT_MARKET_ADDRESS:
            addresses.append({"address": tx['address'], "balance": tx['amount']})
    
    if addresses:
        table = Table(title="[bold green]Addresses with Coins[/bold green]", show_header=True, header_style="bold magenta")
        table.add_column("Address", style="dim", width=50)
        table.add_column("Balance", justify="right", style="green")
        for addr in addresses:
            table.add_row(addr['address'], f"{addr['balance']} PART")
        console.print(table)
    else:
        log("[bold yellow]No addresses with coins found.[/bold yellow]")
    return addresses

def remove_from_queue(hash_to_remove: str):
    with open(VOTE_QUEUE_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    with open(VOTE_QUEUE_FILE, 'w', encoding='utf-8') as f:
        f.writelines(line for line in lines if not line.startswith(hash_to_remove))

def prepare_proposal_data(hash: str, title: str, description: str, market_address: str, action: str, submitter_address: str) -> Tuple[Optional[Dict[str, Any]], str, str, str]:
    if not submitter_address:
        return None, "", "", ""

    hash_input = json.dumps({
        "network": "PARTICL",
        "proposalCategory": "ITEM_VOTE",
        "proposalDescription": f"This ListingItem should be {action.lower()}d.",
        "proposalMarket": market_address,
        "proposalOptions": "0:KEEP:1:REMOVE:",
        "proposalSubmitter": submitter_address,
        "proposalTarget": hash,
        "proposalTitle": hash
    }, separators=(',', ':'))

    proposal_hash = sha256(hash_input)
    
    option_hash_keep = sha256(json.dumps({
        "network": "PARTICL",
        "proposalOptionDescription": "KEEP",
        "proposalOptionId": 0,
        "proposalOptionProposalHash": proposal_hash
    }, separators=(',', ':')))

    option_hash_remove = sha256(json.dumps({
        "network": "PARTICL",
        "proposalOptionDescription": "REMOVE",
        "proposalOptionId": 1,
        "proposalOptionProposalHash": proposal_hash
    }, separators=(',', ':')))

    proposal_data = {
        "version": "3.3.1",
        "action": {
            "type": "MPA_PROPOSAL_ADD",
            "submitter": submitter_address,
            "title": hash,
            "description": f"This ListingItem should be {action.lower()}d.",
            "options": [
                {"optionId": 0, "description": "KEEP", "hash": option_hash_keep},
                {"optionId": 1, "description": "REMOVE", "hash": option_hash_remove}
            ],
            "category": "ITEM_VOTE",
            "target": hash,
            "hash": proposal_hash
        }
    }

    return proposal_data, submitter_address, option_hash_keep, option_hash_remove

def send_proposal(proposal_data: Dict[str, Any], market_address: str) -> bool:
    proposal_json = json.dumps(proposal_data).replace('"', '\\"')
    command = f'smsgsend "{market_address}" "{market_address}" "{proposal_json}" false 2'
    
    result = execute_particl_cli(command)
    if result:
        log(f"[green]Proposal sent successfully. Transaction ID: {result}[/green]")
        # Log the proposal with the hash
        log_marketplace_action(
            proposal_data['action']['title'], 
            "Proposal",
            proposal_data['action']['target']  
        )
        return True
    return False
def prepare_vote_data(proposal_hash: str, option_hash: str, submitter_address: str) -> Optional[Dict[str, Any]]:
    vote_sig_msg = {
        "proposalHash": proposal_hash,
        "proposalOptionHash": option_hash,
        "address": submitter_address
    }
    
    # Ensure consistent JSON formatting
    vote_sig_msg_str = json.dumps(vote_sig_msg, separators=(',', ':'), ensure_ascii=True)
    
    # Create bug string by splitting each character and sorting
    bug_str = ','.join(sorted(vote_sig_msg_str))
    
    # Sign the message
    signature = execute_particl_cli(f'signmessage "{submitter_address}" {shlex.quote(bug_str)}')
    if not signature:
        log("[bold red]Failed to sign message[/bold red]")
        return None

    vote_data = {
        "version": "3.3.1",
        "action": {
            "type": "MPA_VOTE",
            "proposalHash": proposal_hash,
            "proposalOptionHash": option_hash,
            "signature": signature,
            "voter": submitter_address
        }
    }

    log("[bold green]Prepared vote data:[/bold green]")
    log_json(vote_data)

    return vote_data

def send_vote(vote_data: Dict[str, Any], submitter_address: str, market_address: str, title: str, action: str) -> bool:
    vote_json = json.dumps(vote_data, separators=(',', ':'))
    escaped_json = vote_json.replace('"', '\\"')
    command = f'smsgsend "{submitter_address}" "{market_address}" "{escaped_json}" false 2'
    
    result = execute_particl_cli(command)
    if result:
        log(f"[green]Vote sent successfully. Transaction ID: {result}[/green]")
        return True
    return False

def verify_vote_data(vote_data: Dict[str, Any]) -> bool:
    required_fields = ['version', 'action']
    action_fields = ['type', 'proposalHash', 'proposalOptionHash', 'signature', 'voter']
    
    if not all(field in vote_data for field in required_fields):
        log("[red]Vote data is missing required fields[/red]")
        return False
    
    if not all(field in vote_data['action'] for field in action_fields):
        log("[red]Vote action is missing required fields[/red]")
        return False
    
    if vote_data['action']['type'] != "MPA_VOTE":
        log("[red]Incorrect action type in vote data[/red]")
        return False
    
    return True

def process_vote_queue():
    queue = read_vote_queue()
    if not queue:
        log("[yellow]Vote queue is empty. No votes to process.[/yellow]")
        return

    # Add a set to track logged votes
    logged_votes = set()

    log(f"[bold blue]Processing {len(queue)} items in the vote queue...[/bold blue]")

    addresses_with_coins = get_addresses_with_coins()

    if not addresses_with_coins:
        log("[bold red]No addresses with sufficient coins found. Cannot process votes.[/bold red]")
        return

    for item in queue:
        hash, title, description, market_address, action = item

        market_address = market_address if market_address and market_address != "null" else DEFAULT_MARKET_ADDRESS

        console.print(Panel(f"[bold]Processing Listing[/bold]\n[cyan]{title}[/cyan]", expand=False))
        log(f"[bold]Hash:[/bold] {hash}")
        log(f"[bold]Action:[/bold] {action}")

        existing_proposal = get_existing_proposals(hash)

        if existing_proposal:
            proposal_hash = existing_proposal['hash']
            option_hash = next((opt['hash'] for opt in existing_proposal['options'] if opt['description'] == action.upper()), None)
            if not option_hash:
                log(f"[bold red]Could not find matching option hash for action {action}. Skipping this item.[/bold red]")
                continue
        else:
            log(f"[bold yellow]No existing proposal found for '{title}'. Creating a new proposal.[/bold yellow]")
            submitter_address = addresses_with_coins[0]['address']  # Use the first address with coins
            proposal_data, submitter_address, option_hash_keep, option_hash_remove = prepare_proposal_data(hash, title, description, market_address, action, submitter_address)
            
            if not proposal_data:
                log(f"[bold red]Failed to prepare proposal data for '{title}'. Skipping this item.[/bold red]")
                continue
            
            if send_proposal(proposal_data, market_address):
                log(f"[bold green]New proposal created and sent for '{title}'.[/bold green]")
                proposal_hash = proposal_data['action']['hash']
                option_hash = option_hash_remove if action.upper() == "REMOVE" else option_hash_keep
            else:
                log(f"[bold red]Failed to send new proposal for '{title}'. Skipping this item.[/bold red]")
                continue

        for address_info in addresses_with_coins:
            submitter_address = address_info['address']
            vote_data = prepare_vote_data(proposal_hash, option_hash, submitter_address)

            if not vote_data:
                log(f"[bold red]Failed to prepare vote data for address {submitter_address}. Skipping this vote.[/bold red]")
                continue

            log(f"[yellow]Sending vote from address {submitter_address}...[/yellow]")
            if send_vote(vote_data, submitter_address, market_address, title, action):
                log(f"[bold green]Vote sent successfully from address {submitter_address}[/bold green]")
                # Only log the vote once per listing
                if hash not in logged_votes:
                    log_marketplace_action(
                        title,
                        "Upvote" if action.upper() == "KEEP" else "Downvote",
                        hash
                    )
                    logged_votes.add(hash)
            else:
                log(f"[bold red]Failed to send vote from address {submitter_address}[/bold red]")

        remove_from_queue(hash)
        log(f"[green]Processed and removed item from queue: {hash}[/green]")

    log("[bold green]Vote queue processing complete.[/bold green]")

def broadcast_moderation_decisions():
    console.print(Panel.fit("[bold magenta]Broadcasting Moderation Decisions[/bold magenta]"))
    process_vote_queue()
    console.print(Panel.fit("[bold green]Moderation decisions broadcast completed[/bold green]"))

if __name__ == "__main__":
    console.print(Panel.fit("[bold blue]Starting Market Voting Process[/bold blue]"))
    broadcast_moderation_decisions()
