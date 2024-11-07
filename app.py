#!/usr/bin/env python3

from particl_moderation.cli import menu
from particl_moderation.utils.error_handler import initialize_error_handling, handle_keyboard_interrupt
from particl_moderation.particl.particl_core_manager import ParticlCoreManager
from rich.console import Console

console = Console()
initialize_error_handling()

@handle_keyboard_interrupt
def main():
    # Initialize core manager and start daemon if not running
    core_manager = ParticlCoreManager()
    
    if not core_manager.is_daemon_running(silent=True):
        console.print("[yellow]Particl daemon not running. Starting it now...[/yellow]")
        if core_manager.start_particl_daemon():
            console.print("[green]Particl daemon started successfully.[/green]")
        else:
            console.print("[red]Failed to start Particl daemon. Some features may not work properly.[/red]")
    
    menu.main_menu()

if __name__ == "__main__":
    main()