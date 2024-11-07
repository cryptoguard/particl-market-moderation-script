import os
import sys

from datetime import datetime
from particl_moderation.utils.config import get_config

def get_log_file() -> str:
    return get_config("paths.results_file", "results.txt")

def get_vote_queue_file() -> str:
    return get_config("paths.vote_queue_file", "vote_queue.txt")

def get_moderation_log_file() -> str:
    return get_config("logging.file", "/home/mint/Applications/particl_moderation/config/moderation.log")

DEFAULT_MARKET_ADDRESS = "PZijh4WzjCWLbSgBkMUtLHZBaU6dSSmkqN"

def ensure_file_exists(file_path: str) -> None:
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            pass
        os.chmod(file_path, 0o644)

def validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        return True
    except ValueError:
        return False

def log_marketplace_action(listing_title: str, action_type: str, listing_hash: str) -> None:
    log_file = get_moderation_log_file()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Format based on action type
    if action_type == "Proposal":
        log_entry = f"[{timestamp}] Proposal | {listing_title} | {listing_hash}\n"
    elif action_type in ["Upvote", "Downvote"]:
        log_entry = f"[{timestamp}] {action_type} | {listing_title} | {listing_hash}\n"
    else:
        return  # Don't log other action types
    
    # Write in binary mode for cross-platform compatibility
    with open(log_file, 'ab') as f:
        f.write(log_entry.encode('utf-8'))

def add_log_entry(hash: str, title: str, description: str, date: str, type: str, llm_response: str, counts: str) -> bool:
    log_file = get_log_file()
    vote_queue_file = get_vote_queue_file()
    ensure_file_exists(log_file)
    ensure_file_exists(vote_queue_file)

    if type not in ["downvote", "upvote", "ignore"]:
        print("Error: Type must be 'downvote', 'upvote', or 'ignore'.", file=sys.stderr)
        return False

    if not validate_date(date):
        date = datetime.now().strftime("%d-%m-%Y")

    title = ' '.join(title.split())
    description = ' '.join(description.split())

    try:
        # Write to log file in binary mode
        log_entry = f"[{date}] {type} | {hash} | {title} | {description} | {llm_response} | Counts: {counts}\n"
        with open(log_file, 'ab') as f:
            f.write(log_entry.encode('utf-8'))

        if type in ["upvote", "downvote"]:
            action = "KEEP" if type == "upvote" else "REMOVE"
            vote_entry = f"{hash}|{title}|{description}|{DEFAULT_MARKET_ADDRESS}|{action}\n"
            with open(vote_queue_file, 'ab') as f:
                f.write(vote_entry.encode('utf-8'))

        return True
    except Exception as e:
        print(f"Error writing to log file: {str(e)}", file=sys.stderr)
        return False

def ensure_file_exists(file_path: str) -> None:
    """Create file if it doesn't exist and ensure UTF-8 encoding"""
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            pass
        os.chmod(file_path, 0o644)

def view_log_entries(type: str = None, lines: int = None) -> None:
    log_file = get_log_file()
    ensure_file_exists(log_file)

    try:
        with open(log_file, 'rb') as f:
            content = f.read()
            try:
                log_entries = content.decode('utf-8').splitlines()
            except UnicodeDecodeError:
                log_entries = content.decode('latin1', errors='replace').splitlines()
    except Exception as e:
        print(f"Error reading log file: {str(e)}", file=sys.stderr)
        return

    if type:
        if type not in ["downvote", "upvote", "ignore"]:
            print("Error: Type must be 'downvote', 'upvote', or 'ignore'.", file=sys.stderr)
            return
        log_entries = [entry for entry in log_entries if f"] {type}" in entry]

    if lines:
        log_entries = log_entries[-lines:]

    for entry in log_entries:
        date = entry.split(']')[0][1:]
        content = '|'.join(entry.split('|')[1:])
        if "downvote" in entry:
            print(f"\033[0;31m[{date}]{content}\033[0m")
        elif "upvote" in entry:
            print(f"\033[0;32m[{date}]{content}\033[0m")
        else:
            print(f"\033[0;37m[{date}]{content}\033[0m")

def clear_log() -> None:
    log_file = get_log_file()
    if os.path.exists(log_file):
        with open(log_file, 'w') as f:
            pass
        print("Log cleared successfully.")
    else:
        print("Log file does not exist.")

if __name__ == "__main__":
    add_log_entry("1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef", "Test Title", "Test Description", "01-01-2024", "upvote", "LLM Response", "5|3|2")
    view_log_entries()
    view_log_entries("upvote", 5)
    clear_log()
