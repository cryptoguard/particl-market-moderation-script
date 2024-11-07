import os
import subprocess
import json

from typing import List, Optional
from prompt_toolkit import Application, ANSI, prompt
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from particl_moderation.utils.config import get_config, set_config, get_full_path
from particl_moderation.utils.platform_compat import is_windows
from particl_moderation.utils.error_handler import handle_keyboard_interrupt, initialize_error_handling
from particl_moderation.utils.queue_utils import process_queue, clear_queue 
from particl_moderation.utils.continuous_mode import continuous_mode
from particl_moderation.utils.generate_test_prompts import generate_test_prompts
from particl_moderation.particl.wallet import ParticlWallet, display_wallet_qr, DEFAULT_MARKET_ADDRESS
from particl_moderation.particl.search import particl_search
from particl_moderation.particl.particl_core_manager import ParticlCoreManager
from particl_moderation.cli.display_listings import display_processed_listings as display_listings
from particl_moderation.moderation.rules import initialize_rules
from particl_moderation.moderation.voting import broadcast_moderation_decisions as broadcast_decisions

initialize_error_handling()

console = Console()

APP_VERSION = "0.0.1"

def clear_screen():
    if is_windows():
        os.system('cls')
    else:
        os.system('clear')

def print_header():
    console.print(Panel(f"[bold yellow]Particl Marketplace Moderation Tool v{APP_VERSION}[/bold yellow]"))

def get_queue_file() -> str:
    return get_config("paths.queue_file", "queue.txt")

def get_cache_file():
    return get_config("paths.cache_file", "listing_cache.txt")

@handle_keyboard_interrupt
def process_test_listings():
    try:
        success = generate_test_prompts()
        if success:
            console.print("[green]Test prompts generated successfully.[/green]")
            console.print("[green]Queue populated with test listings.[/green]")
            console.print("[yellow]Now processing the generated test listings...[/yellow]")
            process_queue()
        else:
            console.print("[bold red]Failed to generate test prompts or populate queue.[/bold red]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Test listing processing interrupted. Returning to previous menu...[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error processing test listings: {str(e)}[/bold red]")
        console.print("[yellow]Please check the dummy_listings.txt file for correct formatting.[/yellow]")
    finally:
        prompt("Press Enter to return to the menu")

def clear_cache():
    cache_file = get_cache_file()
    open(cache_file, 'w').close()
    console.print("[green]Cache file cleared.[/green]")

def clear_results():
    results_file = get_full_path("paths.results_file")
    try:
        open(results_file, 'w').close()
        console.print("[green]Results file cleared.[/green]")
    except IOError as e:
        console.print(f"[bold red]Error clearing results file: {e}[/bold red]")

def get_status_text():
    core_manager = ParticlCoreManager()
    wallet = ParticlWallet()
    
    daemon_running = "YES" if core_manager.is_daemon_running() else "NO"
    daemon_status = f"[green]YES[/green]" if daemon_running == "YES" else f"[red]NO[/red]"
    
    sync_status = core_manager.get_sync_status()
    sync_color = "green" if sync_status != "Error" and sync_status != "N/A" and float(sync_status[:-1]) >= 99 else "yellow"
    
    marketplace_status = "[green]Connected[/green]" if wallet.is_connected_to_marketplace() else "[red]Disconnected[/red]"
    
    balance = wallet.get_balance() if wallet.active_wallet else "N/A"
    wallet_info = f"Wallet: {wallet.active_wallet} | Balance: {balance:.8f} PART" if wallet.active_wallet else "[red]No active wallet[/red]"
    
    return f"Daemon: {daemon_status} | Sync: [{sync_color}]{sync_status}[/] | Marketplace: {marketplace_status} | {wallet_info}"

def create_header():
    core_manager = ParticlCoreManager()
    wallet = ParticlWallet()
    
    daemon_running = "YES" if core_manager.is_daemon_running() else "NO"
    daemon_status = f"[green]YES[/green]" if daemon_running == "YES" else f"[red]NO[/red]"
    
    sync_status = core_manager.get_sync_status()
    sync_color = "green" if sync_status != "Error" and sync_status != "N/A" and float(sync_status[:-1]) >= 99 else "yellow"
    
    marketplace_status = "[green]Connected[/green]" if wallet.is_connected_to_marketplace() else "[red]Disconnected[/red]"
    
    balance = wallet.get_balance() if wallet.active_wallet else "N/A"
    wallet_info = f"Wallet: {wallet.active_wallet} | Balance: {balance:.8f} PART" if wallet.active_wallet else "[red]No active wallet[/red]"
    
    header_text = f"""
┌────────────────────────────────────────────────────────────────────────────┐
│ Particl Marketplace Moderation Tool v{APP_VERSION:<41} │
├────────────────────────────────────────────────────────────────────────────┤
│ Daemon: {daemon_status:<10} | Sync: [{sync_color}]{sync_status:<8}[/] | Marketplace: {marketplace_status:<15} │
│ {wallet_info:<72} │
└────────────────────────────────────────────────────────────────────────────┘
"""
    return FormattedTextControl(ANSI(header_text))

def create_menu(title, options):
    menu_text = f"\n{title}\n\n"
    for i, option in enumerate(options, 1):
        menu_text += f"{i}. {option}\n"
    menu_text += "\nChoose an option: "
    return FormattedTextControl(ANSI(menu_text))

def get_header_content():
    """Generate a beautiful header with current system status"""
    core_manager = ParticlCoreManager()
    wallet = ParticlWallet()
    
    # Silent check for core installation and version
    cli_exists = os.path.exists(core_manager.cli_path) if hasattr(core_manager, 'cli_path') else False
    core_version = core_manager.config.get('particl', {}).get('version', 'N/A')
    version_style = "class:status-ok" if cli_exists else "class:status-error"
    
    # Check if daemon is running
    try:
        daemon_running = core_manager.is_daemon_running(silent=True) if cli_exists else False
    except Exception:
        daemon_running = False
    daemon_status = "●" if daemon_running else "○"
    daemon_style = "class:status-ok" if daemon_running else "class:status-error"
    
    if daemon_running:
        # Sync status check
        try:
            sync_status = core_manager.get_sync_status()
            sync_ok = sync_status != "Error" and sync_status != "N/A" and float(sync_status[:-1]) >= 99
        except Exception:
            sync_status = "N/A"
            sync_ok = False
        sync_style = "class:status-ok" if sync_ok else "class:status-warning"
        
        # Market status check - explicitly check SMSG keys
        try:
            smsg_result = wallet._run_particl_command(["smsglocalkeys"])
            if smsg_result:
                smsg_data = json.loads(smsg_result)
                market_connected = False
                
                # Check wallet_keys
                if 'wallet_keys' in smsg_data:
                    for key in smsg_data['wallet_keys']:
                        if key.get('address') == DEFAULT_MARKET_ADDRESS:
                            market_connected = True
                            break
                            
                # Check smsg_keys if not found in wallet_keys
                if not market_connected and 'smsg_keys' in smsg_data:
                    for key in smsg_data['smsg_keys']:
                        if key.get('address') == DEFAULT_MARKET_ADDRESS:
                            market_connected = True
                            break
            else:
                market_connected = False
        except Exception:
            market_connected = False
            
        market_status = "●" if market_connected else "○"
        market_style = "class:status-ok" if market_connected else "class:status-error"
        
        try:
            balance = wallet.get_balance() if wallet.active_wallet else 0.0
            wallet_name = wallet.active_wallet if wallet.active_wallet else "No Wallet"
        except Exception:
            balance = 0.0
            wallet_name = "Offline"
    else:
        # Default values when daemon is not running
        sync_status = "N/A"
        sync_style = "class:status-warning"
        market_status = "○"
        market_style = "class:status-warning"
        balance = 0.0
        # Get wallet name from config even if daemon is not running
        wallet_name = wallet.active_wallet if wallet.active_wallet else "No Wallet"
    
    wallet_style = "class:status-ok" if daemon_running and wallet.active_wallet else "class:status-error"

    header = [
        ("class:border", "╭" + "─" * 78 + "╮\n"),
        ("class:border", "│"),
        ("class:header-title", f" Particl Marketplace Moderation Tool v{APP_VERSION}"),
        ("class:border", " " * (78 - len(f" Particl Marketplace Moderation Tool v{APP_VERSION}")) + "│\n"),
        ("class:border", "├" + "─" * 78 + "┤\n"),
        ("class:border", "│"),
        ("class:label", " Daemon: "),
        (daemon_style, f"{daemon_status}"),
        ("class:label", " │ Sync: "),
        (sync_style, f"{sync_status}"),
        ("class:label", " │ Market: "),
        (market_style, f"{market_status}"),
        ("class:border", " " * (78 - len(f" Daemon: {daemon_status} │ Sync: {sync_status} │ Market: {market_status}")) + "│\n"),
        ("class:border", "│"),
        ("class:label", " Wallet: "),
        (wallet_style, f"{wallet_name}"),
        ("class:label", " │ Balance: "),
        (wallet_style, f"{balance:.8f} PART"),
        ("class:label", " │ Core: "),
        (version_style, f"v{core_version}"),
        ("class:border", " " * (78 - len(f" Wallet: {wallet_name} │ Balance: {balance:.8f} PART │ Core: v{core_version}")) + "│\n"),
        ("class:border", "╰" + "─" * 78 + "╯\n")
    ]
    
    return header

def create_menu_application(title, options, kb):
    def get_formatted_text():
        menu = [
            ("", "\n"),  
            ("class:menu-title", "   " + "═" * 40 + "\n"),
            ("class:menu-title", f"   {title.center(40)}\n"),
            ("class:menu-title", "   " + "═" * 40 + "\n\n")
        ]
        # Add menu options with proper spacing
        for i, option in enumerate(options, 1):
            menu.append(("class:menu-item", f"     {i}. {option}\n"))
        return menu

    header_window = Window(
        content=FormattedTextControl(get_header_content),
        height=6,
    )

    menu_window = Window(
        content=FormattedTextControl(get_formatted_text),
    )

    layout = Layout(HSplit([
        header_window,
        menu_window,
    ]))

    # Define style with proper class names
    style_dict = {
        # Header styles
        'header-title': 'bold yellow',
        'border': '#00AFFF',
        'label': 'white',
        'status-ok': '#00FF00',
        'status-error': '#FF0000',
        'status-warning': '#FFFF00',
        # Menu styles
        'menu-title': 'yellow',
        'menu-item': 'white',
    }

    return Application(
        layout=layout,
        key_bindings=kb,
        style=Style.from_dict(style_dict),
        full_screen=True,
        refresh_interval=1
    )

@handle_keyboard_interrupt
def main_menu():
    clear_screen() 
    options = [
        "Scan and Process Listings",
        "Broadcast Moderation Decisions",
        "Display Processed Listings",
        "Start Continuous Mode",
        "Settings",
        "Exit"
    ]
    
    kb = KeyBindings()
    
    @kb.add('c-c')
    def _(event):
        event.app.exit(result="exit")
    
    for i in range(1, len(options) + 1):
        @kb.add(str(i))
        def _(event, i=i):
            event.app.exit(result=i)

    while True:
        try:
            app = create_menu_application("Main Menu", options, kb)
            result = app.run()
            if result == "exit":
                console.print("\n[yellow]Exiting the application. Goodbye![/yellow]")
                return
            elif result == 1:
                scan_and_process_listings()
            elif result == 2:
                broadcast_moderation_decisions()
            elif result == 3:
                display_listings()
            elif result == 4:
                start_continuous_mode()
            elif result == 5:
                settings_menu()
            elif result == 6:
                console.print("\nExiting the application. Goodbye!")
                return
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation interrupted. Returning to main menu...[/yellow]")


@handle_keyboard_interrupt
def scan_and_process_listings():
    console.clear()
    if not validate_ollama_model():
        console.print("[yellow]Please configure a valid LLM model before processing listings.[/yellow]")
        prompt("Press Enter to return to menu...")
        return

    options = [
        "Run on Particl Marketplace",
        "Run on Test Listings",
        "Process listing queue without scanning",
        "Clear queue",
        "Clear cache",
        "Clear Results",
        "Back to main menu"
    ]
    
    kb = KeyBindings()
    
    @kb.add('c-c')
    def _(event):
        event.app.exit(result="exit")
    
    for i in range(1, len(options) + 1):
        @kb.add(str(i))
        def _(event, i=i):
            event.app.exit(result=i)

    while True:
        try:
            app = create_menu_application("Scan and Process Listings", options, kb)
            result = app.run()
            if result == "exit":
                return
            elif result == 1:
                console.clear()
                particl_search()
                process_queue()
            elif result == 2:
                console.clear()
                process_test_listings()
            elif result == 3:
                console.clear()
                process_queue()
            elif result == 4:
                console.clear()
                clear_queue()
            elif result == 5:
                console.clear()
                clear_cache()
            elif result == 6:
                console.clear()
                clear_results()
            elif result == 7:
                return
            prompt("Press Enter to continue")
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation interrupted. Returning to previous menu...[/yellow]")
            return
        
@handle_keyboard_interrupt
def broadcast_moderation_decisions():
    console.clear()
    try:
        console.print("[bold]Broadcasting Moderation Decisions[/bold]")
        broadcast_decisions()
        console.print("[green]Broadcasting completed.[/green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Broadcasting interrupted. Returning to previous menu...[/yellow]")
    finally:
        prompt("Press Enter to return to the main menu")

def start_continuous_mode():
    console.clear()
    console.print("[bold]Starting Continuous Mode[/bold]")
    continuous_mode()
    console.print("[yellow]Continuous mode stopped. Returning to main menu.[/yellow]")
    input("Press Enter to continue...")

@handle_keyboard_interrupt
def settings_menu():
    console.clear()
    options = [
        "Particl Wallet and Node Settings",
        "Moderation Settings",
        "Back to Main Menu"
    ]
    
    kb = KeyBindings()
    
    @kb.add('c-c')
    def _(event):
        event.app.exit(result="exit")
    
    for i in range(1, len(options) + 1):
        @kb.add(str(i))
        def _(event, i=i):
            event.app.exit(result=i)

    while True:
        try:
            app = create_menu_application("Settings Menu", options, kb)
            result = app.run()
            if result == "exit":
                return
            elif result == 1:
                particl_settings()
            elif result == 2:
                moderation_settings()
            elif result == 3:
                return
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation interrupted. Returning to main menu...[/yellow]")
            return

@handle_keyboard_interrupt
def particl_settings():
    console.clear()
    core_manager = ParticlCoreManager()
    wallet = ParticlWallet()
    
    options = [
        "Manage Wallet",
        "Start/Stop Particl Daemon",
        "Check Sync Status",
        "Download/Update Particl Core",
        "Update Particl Core Version",  
        "Back to Settings Menu"
    ]
    
    kb = KeyBindings()
    
    @kb.add('c-c')
    def _(event):
        event.app.exit(result="exit")
    
    for i in range(1, len(options) + 1):
        @kb.add(str(i))
        def _(event, i=i):
            event.app.exit(result=i)

    while True:
        try:
            app = create_menu_application("Particl Wallet and Node Settings", options, kb)
            result = app.run()
            if result == "exit":
                console.clear()
                console.print("\n[yellow]Operation interrupted. Returning to previous menu...[/yellow]")
                return
            elif result == 1:
                console.clear()
                manage_wallet(wallet)
            elif result == 2:
                console.clear()
                if core_manager.is_daemon_running():
                    core_manager.stop_particl_daemon()
                else:
                    core_manager.start_particl_daemon()
            elif result == 3:
                sync_status = core_manager.get_sync_status()
                console.clear()
                console.print(f"[bold]Current sync status:[/bold] {sync_status}")
                prompt("Press Enter to continue")
            elif result == 4:
                console.clear()
                core_manager.download_particl_core()
            elif result == 5:
                update_core_version(core_manager)
            elif result == 6:
                return
            # prompt("Press Enter to continue")
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation interrupted. Returning to previous menu...[/yellow]")
            return

def update_core_version(core_manager: ParticlCoreManager):
    console.clear()    
    current_version = core_manager.config.get('particl', {}).get('version', 'unknown')
    console.print(f"\n[bold]Current Particl Core version:[/bold] v{current_version}")
    
    options = [
        "Check for updates",
        "Enter version manually",
        "Back"
    ]
    
    kb = KeyBindings()
    
    @kb.add('c-c')
    def _(event):
        event.app.exit(result="exit")
    
    for i in range(1, len(options) + 1):
        @kb.add(str(i))
        def _(event, i=i):
            event.app.exit(result=i)

    while True:
        try:
            app = create_menu_application("Update Particl Core Version", options, kb)
            result = app.run()
            
            if result == "exit" or result == 3:
                return
                
            if result == 1: 
                console.clear()
                console.print("\n[cyan]Checking for updates...[/cyan]")
                latest = core_manager.get_latest_version()
                
                if not latest:
                    console.print("[red]Failed to check for updates.[/red]")
                    continue
                    
                if latest == current_version:
                    console.print("[green]You are already running the latest version.[/green]")
                else:
                    console.print(f"[yellow]New version available: v{latest}[/yellow]")
                    if console.input("Would you like to update? (y/n): ").lower() == 'y':
                        if core_manager.download_particl_core(latest):
                            console.print(f"[green]Successfully updated to version {latest}[/green]")
                        else:
                            console.print("[red]Failed to update version.[/red]")
                
            elif result == 2: 
                console.clear()
                version = console.input("\nEnter version number (e.g., 23.2.7.0): ")
                if not version:
                    continue
                    
                console.print("[cyan]Checking if version exists...[/cyan]")
                if core_manager.check_version_exists(version):
                    console.print(f"[green]Version {version} exists.[/green]")  
                    if console.input("Would you like to download this version now? (y/n): ").lower() == 'y':
                        if core_manager.download_particl_core(version):
                            console.print(f"[green]Successfully updated to version {version}[/green]")
                        else:
                            console.print("[red]Failed to update version.[/red]")
                else:
                    console.print(f"[red]Version {version} not found in releases.[/red]")
            
            prompt("Press Enter to continue")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Version update cancelled.[/yellow]")
            return

@handle_keyboard_interrupt
def manage_wallet(wallet: ParticlWallet):
    options = [
        "Display Wallet Info",
        "Generate New Deposit Address",
        "Deposit (Show QR Code)",
        "Withdraw",
        "Initialize/Select Wallet",
        "Back to Particl Settings"
    ]
    
    kb = KeyBindings()
    
    @kb.add('c-c')
    def _(event):
        event.app.exit(result="exit")
    
    for i in range(1, len(options) + 1):
        @kb.add(str(i))
        def _(event, i=i):
            event.app.exit(result=i)

    while True:
        try:
            app = create_menu_application("Wallet Management", options, kb)
            result = app.run()

            if result == "exit":
                return
            elif result == 1:
                wallet.display_wallet_info()
            elif result == 2:
                console.clear()
                new_address = wallet.get_new_address("deposit")
                if new_address:
                    console.print(f"[green]New deposit address generated: {new_address}[/green]")
                else:
                    console.print("[red]Failed to generate new address.[/red]")
            elif result == 3:
                display_wallet_qr(wallet)
            elif result == 4:
                wallet.withdraw_with_coin_control()
            elif result == 5:
                options_init = ["Use existing wallet", "Create new wallet", "Back to Previous Menu"]
                kb_init = KeyBindings()
                
                @kb_init.add('c-c')
                def _(event):
                    event.app.exit(result="exit")
                
                for i in range(1, len(options_init) + 1):
                    @kb_init.add(str(i))
                    def _(event, i=i):
                        event.app.exit(result=i)

                while True:
                    app_init = create_menu_application("Wallet Initialization", options_init, kb_init)
                    result_init = app_init.run()
                    
                    if result_init == "exit" or result_init == 3:
                        break
                        
                    if result_init == 1:  # Use existing wallet
                        wallets = ParticlCoreManager()._run_particl_command(["listwallets"])
                        if wallets:
                            wallet_list = json.loads(wallets)
                            console.print("\n[bold]Available wallets:[/bold]")
                            for idx, w in enumerate(wallet_list, 1):
                                console.print(f"{idx}. {w}")
                            wallet_choice = console.input("Enter the number of the wallet to use (or 'q' to cancel): ")
                            if wallet_choice.lower() == 'q':
                                continue
                            try:
                                selected_wallet = wallet_list[int(wallet_choice) - 1]
                                new_wallet = initialize_wallet_with_name(selected_wallet)
                                if new_wallet:
                                    wallet = new_wallet
                                    console.print(f"[green]Wallet initialized: {wallet.active_wallet}[/green]")
                                break
                            except (ValueError, IndexError):
                                console.print("[red]Invalid selection. Please try again.[/red]")
                        else:
                            console.print("[yellow]No existing wallets found.[/yellow]")
                            
                    elif result_init == 2:  # Create new wallet
                        wallet_name = console.input("Enter a name for the new wallet: ")
                        if not wallet_name:
                            continue
                        new_wallet = initialize_wallet_with_name(wallet_name, create=True)
                        if new_wallet:
                            wallet = new_wallet
                            console.print(f"[green]Wallet initialized: {wallet.active_wallet}[/green]")
                        break

            elif result == 6:
                return
            prompt("Press Enter to continue")
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation interrupted. Returning to previous menu...[/yellow]")
            return

def initialize_wallet_with_name(wallet_name: str, create: bool = False) -> Optional[ParticlWallet]:
    manager = ParticlCoreManager()
    temp_wallet = ParticlWallet() 
    
    if create:
        create_result = manager._run_particl_command([
            "-named", "createwallet", 
            f"wallet_name={wallet_name}", 
            "descriptors=false", 
            "load_on_startup=true", 
            "disable_private_keys=false"
        ])
        
        if create_result:
            mnemonic_result = json.loads(manager._run_particl_command(["mnemonic", "new"], wallet=wallet_name))
            master_key = mnemonic_result['master']
            mnemonic = mnemonic_result['mnemonic']
            
            console.print(Panel(f"[green]{mnemonic}[/green]", title="Generated mnemonic", expand=False))
            console.print("[yellow]Please write down this mnemonic and keep it safe. It's crucial for wallet recovery.[/yellow]")
            input("Press Enter after you have safely stored the mnemonic to initialize the wallet for marketplace use...")
            
            import_result = manager._run_particl_command(["extkeyimportmaster", master_key], wallet=wallet_name)
            if not import_result:
                console.print("[red]Failed to import master key.[/red]")
                return None
    
    if temp_wallet.verify_and_update_wallet(wallet_name): 
        set_config("particl.active_wallet", wallet_name)
        return ParticlWallet()
    return None

@handle_keyboard_interrupt
def moderation_settings():
    options = [
        "Set Moderation Policies",
        "Choose LLM Model",
        "Back to Settings Menu"
    ]
    
    kb = KeyBindings()
    
    @kb.add('c-c')
    def _(event):
        event.app.exit(result="exit")
    
    for i in range(1, len(options) + 1):
        @kb.add(str(i))
        def _(event, i=i):
            event.app.exit(result=i)

    while True:
        try:
            app = create_menu_application("Moderation Settings", options, kb)
            result = app.run()
            if result == "exit":
                console.print("\n[yellow]Operation interrupted. Returning to previous menu...[/yellow]")
                return
            elif result == 1:
                initialize_rules()
            elif result == 2:
                choose_llm_model()
            elif result == 3:
                return
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation interrupted. Returning to previous menu...[/yellow]")
            return

@handle_keyboard_interrupt
def set_moderation_policies():
    clear_screen()
    console.print("[bold]Setting Moderation Policies[/bold]")
    rules = ModerationRules()
    rules.configure_rules("Select all...")
    console.print("[green]Moderation policies updated.[/green]")
    prompt("Press Enter to continue...")

@handle_keyboard_interrupt
def get_installed_ollama_models() -> List[str]:
    """Get list of installed Ollama models"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            # Parse the output to extract model names
            lines = result.stdout.strip().split('\n')[1:]  # Skip header line
            models = []
            for line in lines:
                if line.strip():
                    # First word in each line is the model name
                    model_name = line.split()[0]
                    models.append(model_name)
            return models
    except subprocess.CalledProcessError:
        console.print("[red]Error: Failed to get list of Ollama models[/red]")
    except Exception as e:
        console.print(f"[red]Error checking Ollama models: {str(e)}[/red]")
    return []

def validate_ollama_model() -> bool:
    """Check if the configured model is installed"""
    current_model = get_config("llm.model", "")
    if not current_model:
        console.print("[bold red]No LLM model configured. Please set a model in Moderation Settings.[/bold red]")
        return False

    installed_models = get_installed_ollama_models()
    if not installed_models:
        console.print("[bold red]No Ollama models found. Please install a model in Moderation Settings.[/bold red]")
        return False

    if current_model not in installed_models:
        console.print(f"[bold red]Configured model '{current_model}' is not installed.[/bold red]")
        console.print("[yellow]Please set an available model in Moderation Settings.[/yellow]")
        return False

    return True

def install_ollama_model(model_name: str) -> bool:
    """Install an Ollama model"""
    console.print(f"[yellow]Installing model {model_name}...[/yellow]")
    try:
        # Run ollama pull with direct output to terminal
        process = subprocess.run(
            ['ollama', 'pull', model_name],
            check=True,  # Raises CalledProcessError if return code is non-zero
            text=True    # Use text mode for output
        )
        
        console.print(f"[green]Successfully installed model {model_name}[/green]")
        return True
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to install model {model_name}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Error installing model: {str(e)}[/red]")
        return False
    
def choose_llm_model():
    models = ["gemma2:2b", "Back to Previous Menu"]  # Added Back option
    options = models
    
    kb = KeyBindings()
    
    @kb.add('c-c')
    def _(event):
        event.app.exit(result="exit")
    
    for i in range(1, len(options) + 1):
        @kb.add(str(i))
        def _(event, i=i):
            event.app.exit(result=i)

    while True:
        try:
            app = create_menu_application("Choose LLM Model", options, kb)
            result = app.run()
            
            if result == "exit":
                return
            
            if result == len(models):  # If user selected the last option (Back)
                return
            elif 1 <= result <= len(models) - 1:  # If user selected a model
                selected_model = models[result - 1]
            else:
                console.print("[yellow]Invalid selection. Please try again.[/yellow]")
                continue

            # Check if model is installed
            installed_models = get_installed_ollama_models()
            if selected_model not in installed_models:
                if console.input(f"Model {selected_model} is not installed. Install it now? (y/n): ").lower() == 'y':
                    if not install_ollama_model(selected_model):
                        continue
                else:
                    continue

            # Set the model in config
            set_config("llm.model", selected_model)
            console.print(f"[green]Model set to: {selected_model}[/green]")
            return  # Return to previous menu after successful selection
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Model selection cancelled. Returning to previous menu...[/yellow]")
            return

def main():
    initialize_error_handling()
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]Application interrupted. Exiting...[/yellow]")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {str(e)}[/bold red]")
    finally:
        console.print("[green]Thank you for using Particl Marketplace Moderation Tool.[/green]")

if __name__ == "__main__":
    main()
