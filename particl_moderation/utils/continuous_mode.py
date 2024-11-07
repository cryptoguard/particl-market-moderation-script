import time

from particl_moderation.particl.search import particl_search
from particl_moderation.utils.queue_utils import process_queue
from particl_moderation.moderation.voting import process_vote_queue
from particl_moderation.utils.error_handler import handle_keyboard_interrupt
from rich.console import Console

console = Console()

@handle_keyboard_interrupt
def continuous_mode():
    console.print("[bold cyan]Starting Continuous Mode[/bold cyan]")
    try:
        while True:
            console.print("\n[bold]--- Starting new cycle ---[/bold]")
            
            console.print("[yellow]Scanning for new listings...[/yellow]")
            particl_search()
            
            console.print("[yellow]Processing queue...[/yellow]")
            process_queue()
            
            console.print("[yellow]Generating and moderating...[/yellow]")

            # multiple_llm_calls("", "")
            
            console.print("[yellow]Processing vote queue...[/yellow]")
            process_vote_queue()
            
            console.print("[green]Cycle completed. Waiting before next cycle...[/green]")
            time.sleep(60)
    
    except KeyboardInterrupt:
        console.print("\n[bold red]Continuous mode interrupted. Exiting...[/bold red]")
    
    console.print("[bold cyan]Continuous mode ended.[/bold cyan]")
