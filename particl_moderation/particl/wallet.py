import json
import subprocess
import qrcode

from decimal import Decimal, InvalidOperation
from typing import List, Dict, Optional, Tuple, Any
from particl_moderation.particl.particl_core_manager import ParticlCoreManager
from particl_moderation.utils.config import get_config, set_config
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

DEFAULT_MARKET_ADDRESS = "PZijh4WzjCWLbSgBkMUtLHZBaU6dSSmkqN"

class ParticlWallet:
    def __init__(self):
        self.core_manager = ParticlCoreManager()
        self.active_wallet = get_config("particl.active_wallet")
        if not self.active_wallet:
            self.active_wallet = self.get_active_wallet()
            if self.active_wallet:
                set_config("particl.active_wallet", self.active_wallet)

    def _run_particl_command(self, command: List[str], wallet: str = None) -> Optional[str]:
        """Execute a Particl command with comprehensive error handling"""
        # if not self.core_manager.check_particl_core_exists():
        #     console.print("[red]Particl Core is not installed. Please install it from the settings menu.[/red]")
        #     return None

        wallet_to_use = wallet if wallet else self.active_wallet
        full_command = [self.core_manager.cli_path]
        if wallet_to_use:
            full_command.append(f"-rpcwallet={wallet_to_use}")
        full_command.extend(command)

        try:
            result = subprocess.run(full_command, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            console.print(f"[bold red]Error running Particl command: {e}[/bold red]")
            if e.stderr:
                console.print(f"[red]Error output: {e.stderr}[/red]")
            return None
        except OSError as e:
            if hasattr(e, 'winerror') and e.winerror == 193:  # Windows error for "not a valid Win32 application"
                console.print("\n[bold red]Error: Invalid Particl Core executable detected.[/bold red]")
                console.print("[yellow]This usually means either:[/yellow]")
                console.print("1. Particl Core has not been downloaded yet")
                console.print("2. The wrong version (Linux/Mac) was downloaded instead of Windows")
                console.print("\n[green]Please download the correct version of Particl Core by:[/green]")
                console.print("1. Going to Settings > Particl Wallet and Node Settings")
                console.print("2. Selecting 'Download/Update Particl Core'")
                console.print("\nThis will automatically download the correct version for your system.")
            # else:
            #     console.print(f"\n[bold red]Error accessing Particl Core executable: {e}[/bold red]")
            #     console.print("[yellow]Please ensure Particl Core is properly installed via the Settings menu.[/yellow]")
            # return None
        except Exception as e:
            console.print(f"[bold red]Unexpected error running Particl command: {e}[/bold red]")
            return None

    def is_daemon_running(self) -> bool:
        return self.core_manager.is_daemon_running()

    def get_sync_status(self) -> str:
        return self.core_manager.get_sync_status()
    
    def get_active_wallet(self) -> Optional[str]:
        result = self._run_particl_command(["listwallets"])
        if result:
            wallets = json.loads(result)
            return wallets[0] if wallets else None
        return None

    def is_connected_to_marketplace(self, silent: bool = False) -> bool:
        """Check if wallet has market address in SMSG keys"""
        result = self._run_particl_command(["smsglocalkeys"], silent=silent)  # Pass silent parameter
        if not result:
            return False
            
        try:
            smsg_data = json.loads(result)
            
            # Check both wallet_keys and smsg_keys arrays
            if 'wallet_keys' in smsg_data:
                for key in smsg_data['wallet_keys']:
                    if key.get('address') == DEFAULT_MARKET_ADDRESS:
                        return True
                        
            if 'smsg_keys' in smsg_data:
                for key in smsg_data['smsg_keys']:
                    if key.get('address') == DEFAULT_MARKET_ADDRESS:
                        return True
                        
            return False
            
        except json.JSONDecodeError:
            return False
        except Exception:
            return False

    def verify_and_update_wallet(self, wallet_name: str) -> bool:
        console.clear()
        """Verify wallet has required market address and update if needed"""
        required_address = DEFAULT_MARKET_ADDRESS
        required_privkey = "4dgpQuxsDVxytK22ay8Ky7xTSDGJzPu2tnr14tyBoU7CmZC6dqM"
        
        try:
            # Check if address exists in SMSG keys
            smsg_check = self._run_particl_command(["smsglocalkeys"], wallet=wallet_name)
            if not smsg_check:
                return False
                
            smsg_data = json.loads(smsg_check)
            
            # Check both wallet_keys and smsg_keys arrays
            address_found = False
            if 'wallet_keys' in smsg_data:
                for key in smsg_data['wallet_keys']:
                    if key.get('address') == required_address:
                        address_found = True
                        break
                        
            if 'smsg_keys' in smsg_data and not address_found:
                for key in smsg_data['smsg_keys']:
                    if key.get('address') == required_address:
                        address_found = True
                        break

            # If address not found, set up market address
            if not address_found:
                console.print("[yellow]Market address not found or not owned by the wallet. Adding now, may take some time...[/yellow]")
                
                # Import private key if needed
                try:
                    address_check = self._run_particl_command(["getaddressinfo", required_address], wallet=wallet_name)
                    if address_check:
                        address_data = json.loads(address_check)
                        if not address_data.get('ismine', False):
                            import_result = self._run_particl_command(["importprivkey", required_privkey], wallet=wallet_name)
                            if not import_result:
                                return False
                except (json.JSONDecodeError, Exception):
                    # If getaddressinfo fails, try importing the private key
                    import_result = self._run_particl_command(["importprivkey", required_privkey], wallet=wallet_name)
                    if not import_result:
                        return False
                
                # Add to SMSG and scan buckets
                add_smsg = self._run_particl_command(["smsgaddlocaladdress", required_address], wallet=wallet_name)
                if not add_smsg:
                    return False
                    
                scan_result = self._run_particl_command(["smsgscanbuckets"], wallet=wallet_name)
                if not scan_result:
                    return False
                
                console.print("[green]Market key imported and SMSG buckets scanned successfully.[/green]")
            else:
                console.print("[green]Required market address and private key are already present in the wallet.[/green]")

            return True

        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing JSON response: {str(e)}[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Unexpected error during wallet verification: {str(e)}[/red]")
            return False

    def create_new_wallet(self, wallet_name: str) -> Tuple[bool, Optional[str]]:
            create_result = self._run_particl_command([
                "-named", "createwallet", f"wallet_name={wallet_name}",
                "descriptors=false", "load_on_startup=true", "disable_private_keys=false"
            ])
            if not create_result:
                console.print(f"[red]Error: Failed to create wallet '{wallet_name}'.[/red]")
                return False, None

            # Generate mnemonic
            mnemonic_result = self._run_particl_command(["mnemonic", "new"])
            if not mnemonic_result:
                console.print("[red]Error: Failed to generate mnemonic.[/red]")
                return False, None

            mnemonic_data = json.loads(mnemonic_result)
            master_key = mnemonic_data['master']
            mnemonic = mnemonic_data['mnemonic']

            console.print(f"\n[green]Generated mnemonic: {mnemonic}[/green]")
            console.print("[yellow]Please write down this mnemonic and keep it safe. It's crucial for wallet recovery.[/yellow]")
            input("Press Enter after you have safely stored the mnemonic to initialize the wallet for marketplace use...")

            console.print("[cyan]Initializing wallet. This may take a moment (do not stop this process)...[/cyan]")

            # Import master key
            import_result = self._run_particl_command(["extkeyimportmaster", master_key])
            if not import_result:
                console.print("[red]Error: Failed to import master key.[/red]")
                return False, None

            console.print("[green]Master key imported successfully.[/green]")
            console.print("\n[cyan]Setting up market address and SMSG...[/cyan]")

            # Import market key and set up SMSG
            try:
                # Import the specific private key for the market address
                import_privkey_result = self._run_particl_command([
                    "importprivkey", 
                    "4dgpQuxsDVxytK22ay8Ky7xTSDGJzPu2tnr14tyBoU7CmZC6dqM"
                ])
                if not import_privkey_result:
                    console.print("[red]Error: Failed to import market private key.[/red]")
                    return False, None
                console.print("[green]Market private key imported successfully.[/green]")

                # Add market address to SMSG
                add_smsg_result = self._run_particl_command([
                    "smsgaddlocaladdress",
                    DEFAULT_MARKET_ADDRESS
                ])
                if not add_smsg_result:
                    console.print("[red]Error: Failed to add market address to SMSG.[/red]")
                    return False, None
                console.print("[green]Market address added to SMSG successfully.[/green]")

                # Scan SMSG buckets
                scan_result = self._run_particl_command(["smsgscanbuckets"])
                if not scan_result:
                    console.print("[red]Error: Failed to scan SMSG buckets.[/red]")
                    return False, None
                console.print("[green]SMSG buckets scanned successfully.[/green]")

                # Verify the setup
                smsg_keys = self._run_particl_command(["smsglocalkeys"])
                if smsg_keys and DEFAULT_MARKET_ADDRESS in smsg_keys:
                    console.print("[green]Market address verified in SMSG keys.[/green]")
                else:
                    console.print("[yellow]Warning: Could not verify market address in SMSG keys.[/yellow]")

            except Exception as e:
                console.print(f"[red]Error during market address setup: {str(e)}[/red]")
                return False, None

            console.print(f"\n[green]Wallet '{wallet_name}' created and initialized successfully.[/green]")
            return True, wallet_name
        
    def get_addresses(self) -> List[Dict[str, Any]]:
        received = self._run_particl_command(["listreceivedbyaddress", "0", "true"])
        unspent = self._run_particl_command(["listunspent"])
        
        if not received or not unspent:
            return []
        
        received_addresses = json.loads(received)
        unspent_outputs = json.loads(unspent)
        
        address_balances = {}
        
        # Process unspent outputs first
        for utxo in unspent_outputs:
            if utxo['address'] != DEFAULT_MARKET_ADDRESS:
                if utxo['address'] in address_balances:
                    address_balances[utxo['address']] += utxo['amount']
                else:
                    address_balances[utxo['address']] = utxo['amount']
        
        # Process received addresses, but only add if not already in UTXO set
        for addr in received_addresses:
            if addr['address'] != DEFAULT_MARKET_ADDRESS and addr['address'] not in address_balances:
                address_balances[addr['address']] = addr['amount']
        
        # Convert to list of dictionaries and sort by amount in descending order
        sorted_addresses = [{"address": addr, "amount": balance} for addr, balance in address_balances.items()]
        sorted_addresses.sort(key=lambda x: x['amount'], reverse=True)
        
        return sorted_addresses

    def get_addresses_with_coins(self) -> List[str]:
        result = self._run_particl_command(["listunspent"])
        if not result:
            return []
        unspent = json.loads(result)
        addresses = [tx['address'] for tx in unspent if tx['amount'] > 0 and tx['address'] != DEFAULT_MARKET_ADDRESS]
        console.print(f"[cyan]Addresses with coins: {', '.join(addresses)}[/cyan]")
        return addresses
    
    def get_utxos(self) -> List[Dict[str, Any]]:
        result = self._run_particl_command(["listunspent"])
        if not result:
            return []
        utxos = json.loads(result)
        filtered_utxos = [utxo for utxo in utxos if utxo['address'] != DEFAULT_MARKET_ADDRESS]
        filtered_utxos.sort(key=lambda x: x['amount'], reverse=True)
        return filtered_utxos
    
    def withdraw_with_coin_control(self) -> None:
        console.clear()
        utxos = self.get_utxos()
        if not utxos:
            console.print("[red]No available UTXOs for withdrawal.[/red]")
            return

        console.print("[bold]Available UTXOs for withdrawal:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Index", style="dim", width=6)
        table.add_column("Address", style="dim")
        table.add_column("Amount (PART)", justify="right")
        table.add_column("Confirmations", justify="right")

        for idx, utxo in enumerate(utxos, 1):
            table.add_row(
                str(idx),
                utxo['address'],
                f"{utxo['amount']:.8f}",
                str(utxo['confirmations'])
            )

        console.print(table)

        while True:
            choice = console.input("Enter the number of the UTXO to use (or 'q' to cancel): ")
            if choice.lower() == 'q':
                return
            try:
                utxo_index = int(choice) - 1
                if 0 <= utxo_index < len(utxos):
                    selected_utxo = utxos[utxo_index]
                    break
                else:
                    console.print("[red]Invalid selection. Please try again.[/red]")
            except ValueError:
                console.print("[red]Invalid input. Please enter a number or 'q'.[/red]")

        recipient_address = console.input("Enter the Particl address to send to: ")
        
        while True:
            amount_input = console.input(f"Enter the amount to send (max {selected_utxo['amount']:.8f} PART): ")
            try:
                amount = Decimal(amount_input)
                if Decimal('0') < amount <= Decimal(str(selected_utxo['amount'])):
                    break
                else:
                    console.print("[red]Invalid amount. Please try again.[/red]")
            except InvalidOperation:
                console.print("[red]Invalid input. Please enter a valid number.[/red]")

        fee = self.estimate_fee()
        total_amount = amount + fee
        utxo_amount = Decimal(str(selected_utxo['amount']))

        if total_amount > utxo_amount:
            console.print(f"[red]Error: Total amount (including fee) exceeds available funds.[/red]")
            console.print(f"Amount: {amount:.8f} PART")
            console.print(f"Estimated fee: {fee:.8f} PART")
            console.print(f"Total: {total_amount:.8f} PART")
            console.print(f"Available: {utxo_amount:.8f} PART")
            return

        confirm = console.input(f"Send {amount:.8f} PART from {selected_utxo['address']} to {recipient_address}? (y/n): ")
        if confirm.lower() == 'y':
            try:
                # Create raw transaction
                inputs = [{"txid": selected_utxo['txid'], "vout": selected_utxo['vout']}]
                outputs = {
                    recipient_address: float(amount),
                    selected_utxo['address']: float(utxo_amount - total_amount)  # Change
                }
                raw_tx = self._run_particl_command(["createrawtransaction", json.dumps(inputs), json.dumps(outputs)])

                # Sign raw transaction
                signed_tx = self._run_particl_command(["signrawtransactionwithwallet", raw_tx])
                signed_tx_hex = json.loads(signed_tx)['hex']

                # Send raw transaction
                txid = self._run_particl_command(["sendrawtransaction", signed_tx_hex])

                console.print(f"[green]Transaction sent successfully. Transaction ID: {txid}[/green]")
            except Exception as e:
                console.print(f"[red]Error sending transaction: {str(e)}[/red]")
        else:
            console.print("[yellow]Transaction cancelled.[/yellow]")
        
    def estimate_fee(self) -> Decimal:
        return Decimal('0.0001')

    def display_wallet_info(self):
        console.clear()
        balance = self.get_balance()
        addresses = self.get_addresses()
        utxos = self.get_utxos()

        console.print(Panel(f"[bold]Wallet: {self.active_wallet}[/bold]", expand=False))
        console.print(f"[bold]Total Balance:[/bold] {balance:.8f} PART")

        address_table = Table(title="Addresses (Sorted by Balance)", show_header=True, header_style="bold magenta")
        address_table.add_column("Address", style="dim")
        address_table.add_column("Balance", justify="right")

        for addr in addresses:
            address_table.add_row(addr['address'], f"{addr['amount']:.8f} PART")

        console.print(address_table)

        utxo_table = Table(title="UTXOs (Sorted by Amount)", show_header=True, header_style="bold magenta")
        utxo_table.add_column("Address", style="dim")
        utxo_table.add_column("Amount", justify="right")
        utxo_table.add_column("Confirmations", justify="right")

        for utxo in utxos:
            utxo_table.add_row(utxo['address'], f"{utxo['amount']:.8f} PART", str(utxo['confirmations']))

        console.print(utxo_table)

    def get_balance(self) -> float:
        result = self._run_particl_command(["getbalance"])
        return float(result) if result else 0.0

    def get_new_address(self, label: str = "") -> Optional[str]:
        return self._run_particl_command(["getnewaddress", label])

    def send_to_address(self, address: str, amount: float) -> Optional[str]:
        return self._run_particl_command(["sendtoaddress", address, str(amount)])

def initialize_wallet() -> Optional[ParticlWallet]:
    manager = ParticlCoreManager()
    
    while True:
        console.print("\n[bold]Wallet Initialization[/bold]")
        console.print("1. Use existing wallet")
        console.print("2. Create new wallet")
        console.print("3. Cancel")
        
        choice = console.input("Enter your choice (1-3): ")
        
        if choice == '1':
            wallets = manager._run_particl_command(["listwallets"])
            if wallets:
                wallet_list = json.loads(wallets)
                console.print("\n[bold]Available wallets:[/bold]")
                for idx, w in enumerate(wallet_list, 1):
                    console.print(f"{idx}. {w}")
                wallet_choice = console.input("Enter the number of the wallet to use: ")
                try:
                    selected_wallet = wallet_list[int(wallet_choice) - 1]
                    if manager.verify_and_update_wallet(selected_wallet):
                        set_config("particl.active_wallet", selected_wallet)
                        return ParticlWallet()
                except (ValueError, IndexError):
                    console.print("[red]Invalid selection. Please try again.[/red]")
            else:
                console.print("[yellow]No existing wallets found.[/yellow]")
        elif choice == '2':
            console.clear()
            wallet_name = console.input("Enter a name for the new wallet: ")
            create_result = manager._run_particl_command(["-named", "createwallet", f"wallet_name={wallet_name}", "descriptors=false", "load_on_startup=true", "disable_private_keys=false"])
            if create_result:
                mnemonic_result = json.loads(manager._run_particl_command(["mnemonic", "new"], wallet=wallet_name))
                master_key = mnemonic_result['master']
                mnemonic = mnemonic_result['mnemonic']
                
                console.clear()
                console.print(Panel(f"[green]{mnemonic}[/green]", title="Generated mnemonic", expand=False))
                console.print("[yellow]Please write down this mnemonic and keep it safe. It's crucial for wallet recovery.[/yellow]")
                input("Press Enter after you have safely stored the mnemonic to initialize the wallet for marketplace use...")
                
                import_result = manager._run_particl_command(["extkeyimportmaster", master_key], wallet=wallet_name)
                if import_result:
                    console.print(f"\n[green]Wallet '{wallet_name}' created and initialized successfully.[/green]")
                    set_config("particl.active_wallet", wallet_name)
                    return ParticlWallet()
                else:
                    console.print("[red]Failed to import master key.[/red]")
            else:
                console.print("[red]Failed to create wallet.[/red]")
        elif choice == '3':
            return None
        else:
            console.print("[red]Invalid choice. Please try again.[/red]")

def display_wallet_qr(wallet: ParticlWallet) -> None:
    console.clear()
    address = wallet.get_new_address("deposit")
    if address:
        console.print(Panel(f"[bold green]Deposit address:[/bold green] {address}", title="Wallet Address", expand=False))
        
        qr = qrcode.QRCode(version=1, box_size=1, border=2)
        qr.add_data(address.replace("'", "").strip())
        qr.make(fit=True)
        qr_ascii = qr.get_matrix()
        
        console.print("")
        
        for row in qr_ascii:
            line = ""
            for cell in row:
                if cell:
                    line += "██"  
                else:
                    line += "  " 
            console.print(line)
        
        console.print("[yellow]Scan this QR code to get the deposit address.[/yellow]")
    else:
        console.print("[red]Failed to generate deposit address.[/red]")

if __name__ == "__main__":
    wallet = initialize_wallet()
    if wallet:
        console.print(f"[green]Wallet balance: {wallet.get_balance()} PART[/green]")
