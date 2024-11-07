import os
import hashlib

from datetime import datetime
from rich.console import Console
from particl_moderation.utils.config import get_config
from particl_moderation.utils.error_handler import handle_keyboard_interrupt, initialize_error_handling, check_for_interrupt
from particl_moderation.utils.log import add_log_entry
from particl_moderation.llm.generate import multiple_llm_calls

initialize_error_handling()
console = Console()

def get_queue_file() -> str:
    return get_config("paths.queue_file", "queue.txt")

def get_cache_file() -> str:
    return get_config("paths.cache_file", "listing_cache.txt")

def ensure_file_exists(file_path: str) -> None:
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            pass

def add_to_queue(hash: str, title: str, description: str, type: str) -> bool:
    queue_file = get_queue_file()
    cache_file = get_cache_file()
    ensure_file_exists(queue_file)
    ensure_file_exists(cache_file)

    if type == "dummy":
        hash = hashlib.sha256(f"{hash}|{title}|{description}".encode()).hexdigest()
    elif len(hash) != 64 or not all(c in '0123456789abcdefABCDEF' for c in hash):
        console.print("[bold red]Error: Invalid hash format. Expected a 64-character hexadecimal string.[/bold red]")
        return False

    if type != "dummy":
        try:
            with open(cache_file, 'rb') as f:
                if hash.encode('utf-8') in f.read():
                    console.print(f"[yellow]Listing hash {hash} already exists in cache. Skipping.[/yellow]")
                    return False
        except Exception as e:
            console.print(f"[red]Error reading cache file: {str(e)}[/red]")
            return False

        try:
            with open(cache_file, 'ab') as f:
                f.write(f"{hash}\n".encode('utf-8'))
        except Exception as e:
            console.print(f"[red]Error writing to cache file: {str(e)}[/red]")
            return False

    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(queue_file, 'ab') as f:
            f.write(f"[{date}] | {hash} | {title} | {description}\n".encode('utf-8'))
    except Exception as e:
        console.print(f"[red]Error writing to queue file: {str(e)}[/red]")
        return False

    console.print("[green]Item added to queue successfully.[/green]")
    console.print(f"Hash: {hash}")
    console.print(f"Title: {title}")
    console.print(f"Description: {description}")
    console.print(f"Date: {date}")
    return True

def display_queue() -> None:
    queue_file = get_queue_file()
    ensure_file_exists(queue_file)
    try:
        with open(queue_file, 'rb') as f:
            content = f.read().decode('utf-8', errors='replace')
        if content:
            console.print("[bold]Current Queue:[/bold]")
            console.print(content)
        else:
            console.print("[yellow]The queue is empty.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error reading queue file: {str(e)}[/red]")

@handle_keyboard_interrupt
def execute_queue_item() -> bool:
    queue_file = get_queue_file()
    
    try:
        with open(queue_file, 'rb') as f:
            first_line = f.readline().decode('utf-8', errors='replace').strip()
    except Exception as e:
        console.print(f"[red]Error reading queue file: {str(e)}[/red]")
        return False

    if not first_line:
        console.print("[yellow]The queue is empty.[/yellow]")
        return False

    parts = first_line.split('|')
    if len(parts) < 4:
        console.print("[bold red]Invalid queue item format.[/bold red]")
        return False

    date = parts[0].strip()[1:-1]
    hash = parts[1].strip()
    title = parts[2].strip()
    description = parts[3].strip()

    console.print("\n[bold]Executing queue item:[/bold]")
    console.print(f"Title: {title}")

    if not title:
        add_log_entry(hash, title, description, datetime.now().strftime("%d-%m-%Y"), "ignore", "Empty title", "0|0|10")
        _remove_first_queue_item()
        console.print("[yellow]Item removed from queue.[/yellow]")
        console.print("[yellow]Empty title. Exiting.[/yellow]")
        return False

    try:
        true_count, false_count, ignore_count = multiple_llm_calls(title, description)
    except KeyboardInterrupt:
        console.print("\n[yellow]LLM calls interrupted by user.[/yellow]")
        return False

    if true_count >= 6:
        final_result = "upvote"
    elif false_count >= 6:
        final_result = "downvote"
    else:
        final_result = "ignore"

    console.print(f"[bold]Result:[/bold] {final_result}")
    console.print(f"[bold]Score:[/bold] (True: {true_count}, False: {false_count}, Ignore: {ignore_count})")

    add_log_entry(hash, title, description, datetime.now().strftime("%d-%m-%Y"), final_result, "Multiple LLM calls", f"{true_count}|{false_count}|{ignore_count}")

    _remove_first_queue_item()
    return True

def _remove_first_queue_item() -> None:
    queue_file = get_queue_file()
    try:
        with open(queue_file, 'rb') as f:
            lines = f.readlines()
        
        with open(queue_file, 'wb') as f:
            if len(lines) > 1:
                f.writelines(lines[1:])
            else:
                # If it was the last line, just clear the file
                pass

    except Exception as e:
        console.print(f"[red]Error updating queue file: {str(e)}[/red]")

@handle_keyboard_interrupt
def process_queue():
    queue_file = get_queue_file()
    if not os.path.exists(queue_file) or os.path.getsize(queue_file) == 0:
        console.print("[yellow]Queue is empty. No items to process.[/yellow]")
        return

    console.print("[bold]Processing queue...[/bold]")
    try:
        while True:
            check_for_interrupt()
            if not execute_queue_item():
                break
    except KeyboardInterrupt:
        console.print("\n[yellow]Queue processing interrupted by user.[/yellow]")
    finally:
        console.print("[green]Queue processing completed or interrupted.[/green]")

def clear_queue():
    queue_file = get_queue_file()
    try:
        with open(queue_file, 'wb') as f:
            pass
        console.print("[green]Queue file cleared.[/green]")
    except Exception as e:
        console.print(f"[red]Error clearing queue file: {str(e)}[/red]")

if __name__ == "__main__":
    add_to_queue("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef", "Test Title", "Test Description", "normal")
    display_queue()
    process_queue()
