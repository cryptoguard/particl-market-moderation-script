import sys
import signal
import threading

from functools import wraps
from rich.console import Console

console = Console()

interrupt_received = threading.Event()

def handle_interrupt(signum, frame):
    interrupt_received.set()
    console.print("\n[yellow]Interrupt received. Attempting to exit gracefully...[/yellow]")

def check_for_interrupt():
    if interrupt_received.is_set():
        raise KeyboardInterrupt("Operation interrupted by user")

def handle_keyboard_interrupt(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation interrupted by user. Exiting...[/yellow]")
            sys.exit(0)
    return wrapper

def setup_interrupt_handler():
    signal.signal(signal.SIGINT, handle_interrupt)

def global_exception_handler(exctype, value, traceback):
    if exctype is KeyboardInterrupt:
        console.print("\n[yellow]Operation interrupted by user. Exiting...[/yellow]")
    else:
        console.print(f"[bold red]An unexpected error occurred: {exctype.__name__}: {value}[/bold red]")
        console.print("[cyan]Traceback:[/cyan]")
        console.print_exception(show_locals=True)
    sys.exit(1)

def initialize_error_handling():
    setup_interrupt_handler()
    sys.excepthook = global_exception_handler