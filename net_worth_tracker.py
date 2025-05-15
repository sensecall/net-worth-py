import json
import readchar # For reading single key presses
import sys # For sys.exit()
import os # For os.path.exists()
from datetime import datetime # For today's date
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.prompt import Confirm
from rich.panel import Panel
from rich import box

# Import our utility modules
from asset_utils import (
    DEFAULT_CATEGORIES, 
    AUTO_CATEGORIZE_RULES,
    guess_category, 
    set_asset_category_interactive, 
    set_asset_category, 
    categorize_assets,
    load_custom_categories_from_data,
    view_categories,
    load_custom_keywords
)
from menu_utils import show_menu

# Conditional import for charting
try:
    import chart_utils
    CHARTING_AVAILABLE = True
except ImportError:
    CHARTING_AVAILABLE = False

# Initialize Rich Console globally
console = Console()
DATA_FILENAME = "net_worth_data.json"
CURRENT_DATA_FILE = DATA_FILENAME  # Track the currently active data file

def check_existing_data():
    """Checks for existing data files and prompts user with options."""
    global CURRENT_DATA_FILE
    
    if os.path.exists(DATA_FILENAME):
        console.print(f"[yellow]We spotted a JSON file ([cyan]{DATA_FILENAME}[/cyan]) which looks like it contains your net worth history.[/yellow]")
        
        options = [
            "Load this existing file",
            "Start fresh (creates a new file, won't overwrite existing data)",
            "Open a different data file",
            "Exit application"
        ]
        
        menu_index, selected_option = show_menu(
            options,
            title="\nWhat would you like to do?",
            return_shortcut=False
        )
        
        # Handle ESC/q to exit
        if menu_index is None or selected_option == "Exit application":
            console.print("\n[yellow]Exiting application. Goodbye![/yellow]")
            sys.exit()
            
        if selected_option == "Load this existing file":
            console.print(f"\n[green]Loading data from [cyan]{DATA_FILENAME}[/cyan]...[/green]")
            CURRENT_DATA_FILE = DATA_FILENAME
            return load_historical_data()
        elif selected_option == "Start fresh":
            # Generate a new filename to avoid overwriting the existing file
            filename_without_ext = os.path.splitext(DATA_FILENAME)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{filename_without_ext}_new_{timestamp}.json"
            
            console.print(f"\n[yellow]Starting fresh with no historical data.[/yellow]")
            console.print(f"[green]Your new data will be saved to [cyan]{new_filename}[/cyan] to preserve your existing data.[/green]")
            
            CURRENT_DATA_FILE = new_filename
            return []
        elif selected_option == "Open a different file":
            different_file = console.input("\nEnter the path to your data file: ").strip()
            if different_file and os.path.exists(different_file):
                console.print(f"[green]Loading data from [cyan]{different_file}[/cyan]...[/green]")
                CURRENT_DATA_FILE = different_file
                return load_historical_data(different_file)
            
            # If file doesn't exist or no input provided
            console.print(f"[red]File not found: [cyan]{different_file}[/cyan]. Starting fresh.[/red]")
            # Generate a new filename since the specified file doesn't exist
            filename_without_ext = os.path.splitext(different_file)[0] if '.' in different_file else different_file
            CURRENT_DATA_FILE = f"{filename_without_ext}.json"
            console.print(f"[green]Your new data will be saved to [cyan]{CURRENT_DATA_FILE}[/cyan].[/green]")
            return []
    
    # No existing file found
    console.print("[yellow]No existing data file found. Starting fresh.[/yellow]")
    CURRENT_DATA_FILE = DATA_FILENAME
    return []

def display_assets(assets, show_balances=True, show_categories=True, table_title="Current Assets"):
    """Displays the current list of assets in a Rich Table with enhanced formatting."""
    if not assets:
        console.print("[yellow]No assets defined yet.[/yellow]")
        return

    # Create the main table
    table = Table(
        title=Text(table_title, style="bold"),
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE,
        padding=(0, 1)
    )
    
    # Add columns
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Asset Name", min_width=20, style="cyan")
    if show_balances:
        table.add_column("Balance", justify="right", min_width=15)
    if show_categories:
        table.add_column("Category", min_width=15, style="dim")
    table.add_column("Liquid", justify="center", min_width=8)

    # Add rows
    total_balance = 0.0
    liquid_balance = 0.0
    non_liquid_balance = 0.0

    for idx, asset in enumerate(assets, 1):
        row = [str(idx), asset["name"]]
        
        # Handle balance
        if show_balances:
            balance = asset.get('balance', 0.0)
            total_balance += balance
            if asset.get("liquid", False):
                liquid_balance += balance
            else:
                non_liquid_balance += balance
            
            balance_style = "green" if balance >= 0 else "red"
            balance_str = Text(f"£{balance:,.2f}", style=balance_style)
            row.append(balance_str)
        
        # Handle category
        if show_categories:
            row.append(asset.get("category", "Other"))
        
        # Handle liquid status
        liquid_status = Text("Yes", style="green") if asset.get("liquid", False) else Text("No", style="red")
        row.append(liquid_status)
        
        table.add_row(*row)

    # Add summary section if showing balances
    if show_balances and assets:
        # Add a separator
        table.add_section()
        
        # Add totals row
        summary_row = ["", Text("TOTAL", style="bold")]
        balance_style = "green" if total_balance >= 0 else "red"
        summary_row.append(Text(f"£{total_balance:,.2f}", style=balance_style))
        if show_categories:
            summary_row.append("")
        summary_row.append("")
        table.add_row(*summary_row)
        
        # Add liquid/non-liquid breakdown
        if liquid_balance != 0:
            liquid_row = ["", Text("Liquid Assets", style="dim")]
            liquid_row.append(Text(f"£{liquid_balance:,.2f}", style="green"))
            if show_categories:
                liquid_row.append("")
            liquid_row.append(Text("Yes", style="green"))
            table.add_row(*liquid_row)
        
        if non_liquid_balance != 0:
            non_liquid_row = ["", Text("Non-liquid Assets", style="dim")]
            non_liquid_style = "green" if non_liquid_balance >= 0 else "red"
            non_liquid_row.append(Text(f"£{non_liquid_balance:,.2f}", style=non_liquid_style))
            if show_categories:
                non_liquid_row.append("")
            non_liquid_row.append(Text("No", style="red"))
            table.add_row(*non_liquid_row)

    console.print(table)

def load_historical_data(filename=DATA_FILENAME):
    """Loads all historical records. Returns list of records, or empty list if error/not found."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)

        if isinstance(data, list): # Expected format: list of records
            # Basic validation of each record
            valid_records = []
            for i, record in enumerate(data):
                if isinstance(record, dict) and 'date' in record and 'assets' in record and isinstance(record['assets'], list):
                    # Further ensure assets within the record are valid
                    sanitized_assets = []
                    for asset_item in record['assets']:
                        if isinstance(asset_item, dict):
                            asset_item.setdefault('name', f'Unnamed Asset')
                            asset_item.setdefault('liquid', False)
                            asset_item.setdefault('balance', 0.0)
                            # If no category exists, try to guess one
                            if 'category' not in asset_item:
                                asset_item['category'] = guess_category(asset_item['name'])
                            sanitized_assets.append(asset_item)
                    record['assets'] = sanitized_assets
                    valid_records.append(record)
                else:
                    console.print(f"[yellow]Warning: Record {i+1} in [cyan]{filename}[/cyan] is malformed. Skipping.[/yellow]")
            
            # Load custom categories from the valid records
            load_custom_categories_from_data(valid_records)
            
            return sorted(valid_records, key=lambda x: x['date'], reverse=True) # Most recent first
        elif isinstance(data, dict) and 'date' in data and 'assets' in data: # Old single record format
            console.print(f"[yellow]Migrating old data format from [cyan]{filename}[/cyan] to new historical list format.[/yellow]")
            # Sanitize the single old record before wrapping it in a list
            assets_data = data.get('assets', [])
            sanitized_assets = []
            for asset_item in assets_data:
                if isinstance(asset_item, dict):
                    asset_item.setdefault('name', f'Unnamed Asset')
                    asset_item.setdefault('liquid', False)
                    asset_item.setdefault('balance', 0.0)
                    # If no category exists, try to guess one
                    if 'category' not in asset_item:
                        asset_item['category'] = guess_category(asset_item['name'])
                    sanitized_assets.append(asset_item)
            data['assets'] = sanitized_assets
            
            # Load any custom categories from this record
            load_custom_categories_from_data([data])
            
            return [data] # Return as a list with one record
        else:
            console.print(f"[red]Error: Data in [cyan]{filename}[/cyan] is not a recognized list of records or a valid old format. Starting fresh.[/red]")
            return []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        console.print(f"[bold red]Error: Corrupted JSON in [cyan]{filename}[/cyan]. Starting fresh.[/bold red]")
        return []
    except IOError as e:
        console.print(f"[bold red]Error reading [cyan]{filename}[/cyan]: {e}. Starting fresh.[/bold red]")
        return []

def get_asset_balances(assets):
    """Iterates through assets and prompts the user for their balances, allowing skips."""
    if not assets:
        return True  # Nothing to update

    console.print("\n[bold blue]Now, let's update the balances for your assets[/bold blue]")
    console.print("━" * 60, style="blue")
    console.print()

    # First show all assets in a single table
    display_assets(assets, table_title="Current Assets Overview")
    console.print()
    console.print("[cyan]Instructions:[/cyan]")
    console.print(" • Press [bold]Enter[/bold] to keep the current balance")
    console.print(" • Type a [bold]new amount[/bold] to update the balance directly")
    console.print(" • Type [bold]b[/bold] to go back to the previous asset")
    console.print(" • Type [bold]q[/bold] to finish and return to the menu")
    console.print(" [yellow]Note: Changes won't be saved until you complete the process[/yellow]")
    console.print()
    
    # Track which assets have been modified
    modified_assets = []
    
    # Loop through assets
    current_asset_index = 0
    while current_asset_index < len(assets):
        asset = assets[current_asset_index]
        current_balance = asset.get('balance', 0.0)
        
        console.print(f"[bold cyan]Asset {current_asset_index + 1} of {len(assets)}:[/bold cyan] [cyan]{asset['name']}[/cyan]")
        console.print(f"Current balance: [{'green' if current_balance >= 0 else 'red'}]£{current_balance:,.2f}[/{'green' if current_balance >= 0 else 'red'}]")
        console.print(f"Category: [yellow]{asset.get('category', 'Other')}[/yellow] | Liquid: [{'green' if asset['liquid'] else 'red'}]{('Yes' if asset['liquid'] else 'No')}[/{'green' if asset['liquid'] else 'red'}]")
        
        # Get user input
        user_input = console.input("\nEnter new balance (or Enter to keep current): ").strip()
        
        # Handle different inputs
        if not user_input:
            # Keep current balance (skip)
            console.print(f"[green]Keeping current balance: £{current_balance:,.2f}[/green]")
            current_asset_index += 1
        elif user_input.lower() == 'q':
            # Quit balance update
            if modified_assets:
                # Ask for confirmation if changes were made
                console.print("\n[yellow]Warning: You've made changes to asset balances.[/yellow]")
                if Confirm.ask("Save these changes before exiting?", default=True):
                    console.print("[green]Changes will be saved.[/green]")
                    return True
                else:
                    console.print("[red]Changes discarded. No updates were saved.[/red]")
                    return False
            else:
                console.print("[yellow]Finished without making any changes.[/yellow]")
                return False
        elif user_input.lower() == 'b' and current_asset_index > 0:
            # Go back to previous asset
            current_asset_index -= 1
            console.print("[yellow]Going back to previous asset.[/yellow]")
        else:
            # Try to parse as a new balance amount
            try:
                new_balance = float(user_input)
                asset['balance'] = new_balance
                console.print(f"Balance for '{asset['name']}' updated to [{'green' if new_balance >= 0 else 'red'}]£{new_balance:,.2f}[/{'green' if new_balance >= 0 else 'red'}]")
                modified_assets.append(asset)
                current_asset_index += 1
            except ValueError:
                console.print("[red]Invalid input. Please enter a number, 'b' to go back, or 'q' to finish.[/red]")
        
        console.print("─" * 60, style="dim")
    
    # Show summary of all assets after updating
    if modified_assets:
        console.print("\n[bold green]Summary of Updated Assets:[/bold green]")
        for asset in modified_assets:
            console.print(f"• [cyan]{asset['name']}[/cyan]: [{'green' if asset['balance'] >= 0 else 'red'}]£{asset['balance']:,.2f}[/{'green' if asset['balance'] >= 0 else 'red'}]")
        
        console.print("\n[green]Changes will be saved.[/green]")
    else:
        console.print("\n[yellow]No changes were made to any assets.[/yellow]")
    
    return True

def save_historical_data(all_records, current_entry_date, current_assets, filename=None):
    """Saves all historical data, updating or adding the current session's entry."""
    global CURRENT_DATA_FILE
    
    if filename is None:
        filename = CURRENT_DATA_FILE
    
    new_entry = {"date": current_entry_date, "assets": current_assets}
    
    entry_updated = False
    for i, record in enumerate(all_records):
        if record['date'] == current_entry_date:
            all_records[i] = new_entry
            entry_updated = True
            break
    if not entry_updated:
        all_records.append(new_entry)
    
    # Sort by date, most recent first, for consistent file structure
    all_records_sorted = sorted(all_records, key=lambda x: x.get('date', ''), reverse=True)

    try:
        with open(filename, 'w') as f:
            json.dump(all_records_sorted, f, indent=4)
        console.print(f"\n[green]Data for [cyan]{current_entry_date}[/cyan] (and all history) saved to [cyan]{filename}[/cyan][/green]")
    except IOError:
        console.print(f"\n[bold red]Error: Could not save data to [cyan]{filename}[/cyan][/bold red]")

def print_final_summary(entry_date, assets):
    """Prints a final summary including date, assets, and total net worth."""
    console.print("\n[bold green]------------------------------------[/bold green]")
    console.print(f"[bold green]Net Worth Summary for [cyan]{entry_date}[/cyan][/bold green]")
    if not assets:
        console.print("[yellow]No assets were entered for this date.[/yellow]")
    else:
        console.print("[bold blue]Your final assets and balances are:[/bold blue]")
        display_assets(assets, show_balances=True)
        total_net_worth = sum(asset.get('balance', 0.0) for asset in assets)
        console.print("\n------------------------------------")
        console.print(f"[bold white on blue] Total Net Worth: {total_net_worth:,.2f} [/bold white on blue]")
    console.print("[bold green]------------------------------------[/bold green]")

def manage_record_session(initial_assets, initial_date_str, all_historical_records):
    """
    Manages a session for editing/creating a record.
    
    Args:
        initial_assets: List of assets to start with
        initial_date_str: Date string for the record being edited (if any)
        all_historical_records: List of all historical records
        
    Returns:
        Updated list of historical records
    """
    current_assets = initial_assets.copy() if initial_assets else []
    loaded_record_date_for_editing = initial_date_str
    proceed_to_asset_editing = False
    action_choice = None
    
    # First, determine what the user wants to do with this record
    options = [
        "Add, remove or manage assets",
        "Update the values/balances of your existing assets",
        "Change asset categories",
        "Cancel and return to main menu"
    ]
    
    menu_index, selected_option = show_menu(
        options,
        title="\nWhat would you like to do with this record?",
        return_shortcut=False
    )
    
    if menu_index is None:
        console.print("\n[yellow]Returning to main menu without saving changes.[/yellow]")
        return all_historical_records
    
    if selected_option == "Add, remove or manage assets":
        proceed_to_asset_editing = True
        action_choice = 'e'
    elif selected_option == "Update the values/balances of your existing assets":
        proceed_to_asset_editing = False
        action_choice = 'u'
    elif selected_option == "Change asset categories":
        category_result = categorize_assets(current_assets, console)
        if category_result is False:
            # User wants to go back without saving category changes
            console.print("[yellow]Returning to main menu without saving category changes.[/yellow]")
            return all_historical_records
        # After categorizing, start over with the same menu
        return manage_record_session(current_assets, loaded_record_date_for_editing, all_historical_records)
    elif selected_option == "Cancel and return to main menu":
        console.print("\n[yellow]Returning to main menu without saving changes.[/yellow]")
        return all_historical_records

    if action_choice == 'u':
        console.print(f"\n[green]Proceeding to update balances for assets from [cyan]{loaded_record_date_for_editing or 'current session'}[/cyan].[/green]")

    # ---- Main Workflow for the session ----
    todays_date_str = datetime.now().strftime("%Y-%m-%d")

    if proceed_to_asset_editing:
        console.print("\n[bold blue]------------------------------------[/bold blue]")
        if loaded_record_date_for_editing:
            console.print(f"[bold blue]Step 1: Define/Edit Assets (for record originally from [cyan]{loaded_record_date_for_editing}[/cyan])[/bold blue]")
        else:
            console.print("[bold blue]Step 1: Define/Edit Assets (for new record)[/bold blue]")
        console.print("[bold blue]------------------------------------[/bold blue]")
        
        while True:
            display_assets(current_assets, show_balances=False, show_categories=True)
            
            # Prepare menu options
            options = [
                "Add a new asset",
                "Remove an asset",
                "Undo last addition",
                "Change category for an asset",
                "Done with asset editing",
                "Cancel and return to main menu"
            ]
            
            menu_index, selected_option = show_menu(
                options,
                title="\nChoose an action:",
                return_shortcut=False
            )
            
            # Handle ESC/q
            if menu_index is None:
                console.print("[yellow]Returning to main menu without saving changes.[/yellow]")
                return all_historical_records
                
            if selected_option == "Add a new asset":
                asset_name = console.input("[b magenta]Enter asset name: [/b magenta]").strip()
                if not asset_name:
                    console.print("[yellow]No asset name provided. Try again.[/yellow]")
                    continue
                    
                # Ask about liquidity
                while True:
                    is_liquid_input = console.input(f"Is [bold]'{asset_name}'[/bold] a liquid asset? (y/n): ").strip().lower()
                    if is_liquid_input in ['y', 'n']:
                        is_liquid = is_liquid_input == 'y'
                        break
                    else:
                        console.print("[red]Invalid input. Please enter 'y' for yes or 'n' for no.[/red]")
                
                # Ask for category
                category = set_asset_category_interactive(asset_name, console)
                
                current_assets.append({"name": asset_name, "liquid": is_liquid, "balance": 0.0, "category": category})
                console.print(f"[green]Asset '{asset_name}' defined with category '{category}'.[/green]\n")
                
            elif selected_option == "Remove an asset":
                if not current_assets:
                    console.print("[red]No assets to remove.[/red]")
                    continue
                    
                # Create a submenu of assets to remove
                asset_options = [asset["name"] for asset in current_assets]
                asset_options.append("Cancel removal")
                
                menu_index, selected_asset = show_menu(
                    asset_options,
                    title="\nSelect an asset to remove:",
                    return_shortcut=False
                )
                
                if menu_index is None or selected_asset == "Cancel removal":
                    console.print("[yellow]Asset removal cancelled.[/yellow]")
                    continue
                    
                removed_asset = current_assets.pop(asset_options.index(selected_asset))
                console.print(f"[yellow]Removed '{removed_asset['name']}'.[/yellow]\n")
                
            elif selected_option == "Undo last addition":
                if current_assets:
                    removed_asset = current_assets.pop()
                    console.print(f"[yellow]Undid adding '{removed_asset['name']}'.[/yellow]\n")
                else:
                    console.print("[red]No assets to undo.[/red]\n")
                    
            elif selected_option == "Change category for an asset":
                if not current_assets:
                    console.print("[red]No assets to categorize.[/red]")
                    continue
                    
                # Create a submenu of assets to categorize
                asset_options = [asset["name"] for asset in current_assets]
                asset_options.append("Cancel category change")
                
                menu_index, selected_asset = show_menu(
                    asset_options,
                    title="\nSelect an asset to change category:",
                    return_shortcut=False
                )
                
                if menu_index is None or selected_asset == "Cancel category change":
                    console.print("[yellow]Category change cancelled.[/yellow]")
                    continue
                    
                set_asset_category(current_assets[asset_options.index(selected_asset)], console)
                
            elif selected_option == "Done with asset editing":
                if not current_assets:
                    console.print("[yellow]No assets defined.[/yellow]")
                else:
                    console.print("[green]Finished defining/editing assets.[/green]")
                break
                
            elif selected_option == "Cancel and return to main menu":
                console.print("[yellow]Returning to main menu without saving changes.[/yellow]")
                return all_historical_records

    if current_assets:
        balance_result = get_asset_balances(current_assets)
        if balance_result is False:
            # User wants to go back without saving balance changes
            console.print("[yellow]Returning to main menu without saving balance changes.[/yellow]")
            return all_historical_records
    else:
        console.print("\n[yellow]No assets to update balances for.[/yellow]")

    final_entry_date = todays_date_str 
    if current_assets or all_historical_records: 
        console.print("\n[bold blue]------------------------------------[/bold blue]")
        console.print("[bold blue]Step 3: Set Date for This Record[/bold blue]")
        console.print("[bold blue]------------------------------------[/bold blue]")
        if loaded_record_date_for_editing and proceed_to_asset_editing is False : # Only show if updating specific loaded record
             console.print(f"([italic]The record being updated was originally for [cyan]{loaded_record_date_for_editing}[/cyan]. Defaulting save to today.[/italic])")
        elif loaded_record_date_for_editing and proceed_to_asset_editing is True:
             console.print(f"([italic]The record template was from [cyan]{loaded_record_date_for_editing}[/cyan]. Defaulting save to today.[/italic])")

        # Prepare date options
        options = [
            f"Use today's date: {todays_date_str}",
            "Enter a custom date",
            "Return to main menu without saving"
        ]
        
        # Add option to keep original date if we're editing an existing record
        if loaded_record_date_for_editing:
            options.insert(1, f"Keep original date: {loaded_record_date_for_editing}")
        
        menu_index, selected_option = show_menu(
            options,
            title="\nChoose a date option:",
            return_shortcut=False
        )
        
        # Handle ESC/q
        if menu_index is None:
            console.print("[yellow]Cancelled. Returning to main menu without saving.[/yellow]")
            return all_historical_records
            
        if selected_option == "Use today's date":
            final_entry_date = todays_date_str
            console.print(f"[green]Using today's date: [cyan]{final_entry_date}[/cyan].[/green]")
        elif selected_option == "Keep original date":
            final_entry_date = loaded_record_date_for_editing
            console.print(f"[green]Keeping original date: [cyan]{final_entry_date}[/cyan].[/green]")
        elif selected_option == "Enter a custom date":
            console.print("Enter a date in YYYY-MM-DD format:")
            user_date_input = console.input("Date: ").strip()
            
            if not user_date_input:
                console.print(f"[yellow]No date entered. Using today's date: [cyan]{todays_date_str}[/cyan].[/yellow]")
                final_entry_date = todays_date_str
            else:
                try:
                    datetime.strptime(user_date_input, "%Y-%m-%d")
                    final_entry_date = user_date_input
                    console.print(f"[green]Date for record set to [cyan]{final_entry_date}[/cyan].[/green]")
                except ValueError:
                    console.print(f"[red]Invalid date format for '{user_date_input}'. Using today's date: [cyan]{todays_date_str}[/cyan].[/red]")
                    final_entry_date = todays_date_str
        else:  # Return without saving
            console.print("[yellow]Cancelled. Returning to main menu without saving.[/yellow]")
            return all_historical_records
    else:
        console.print("\n[yellow]No assets defined and no prior data. Nothing to set a date for or save.[/yellow]")
        # If truly nothing, no summary or save needed.
        return all_historical_records

    print_final_summary(final_entry_date, current_assets)

    if current_assets: 
        save_historical_data(all_historical_records, final_entry_date, current_assets)
    elif os.path.exists(CURRENT_DATA_FILE) and Confirm.ask(f"No current assets defined. Do you want to save an empty asset list for [cyan]{final_entry_date}[/cyan] (this might clear existing data for this date if any)?", default=False, console=console):
        save_historical_data(all_historical_records, final_entry_date, [])
    else:
        console.print("\n[yellow]No changes or new assets to save for this session.[/yellow]")
    
    return all_historical_records # Return the updated full history

def calculate_summary_stats(assets, all_historical_records=None):
    """
    Calculate summary statistics from assets for the dashboard display.
    
    Args:
        assets: List of current assets
        all_historical_records: Optional list of all historical records for change calculation
        
    Returns:
        Dictionary with summary statistics
    """
    total_assets_value = sum(asset.get('balance', 0.0) for asset in assets if asset.get('balance', 0.0) > 0)
    total_debts_value = sum(asset.get('balance', 0.0) for asset in assets if asset.get('balance', 0.0) < 0)
    net_worth = total_assets_value + total_debts_value  # debts are already negative
    
    # Count liquid vs non-liquid assets
    liquid_assets_value = sum(asset.get('balance', 0.0) for asset in assets 
                             if asset.get('balance', 0.0) > 0 and asset.get('liquid', False))
    non_liquid_assets_value = sum(asset.get('balance', 0.0) for asset in assets 
                                 if asset.get('balance', 0.0) > 0 and not asset.get('liquid', False))
    
    # Count categories used
    categories_used = set()
    category_totals = {}
    
    for asset in assets:
        category = asset.get('category', 'Other')
        categories_used.add(category)
        
        # Track totals by category
        balance = asset.get('balance', 0.0)
        if category not in category_totals:
            category_totals[category] = 0
        category_totals[category] += balance
    
    # Find top categories by value
    top_categories = sorted(
        [(cat, value) for cat, value in category_totals.items() if value > 0],
        key=lambda x: x[1], 
        reverse=True
    )[:3]  # Top 3 categories
    
    # Calculate percentages
    if total_assets_value > 0:
        liquid_percentage = (liquid_assets_value / total_assets_value) * 100
    else:
        liquid_percentage = 0
        
    # Calculate month-to-month change if we have historical data
    change_value = 0
    change_percentage = 0
    previous_net_worth = None
    
    if all_historical_records and len(all_historical_records) > 1:
        # Current record is assumed to be the first one in the sorted list
        current_date = all_historical_records[0].get('date')
        
        # Find the previous record (not from the same date)
        for record in all_historical_records[1:]:
            if record.get('date') != current_date:
                prev_assets = record.get('assets', [])
                previous_net_worth = sum(asset.get('balance', 0.0) for asset in prev_assets)
                break
                
        if previous_net_worth is not None:
            change_value = net_worth - previous_net_worth
            if previous_net_worth != 0:
                change_percentage = (change_value / abs(previous_net_worth)) * 100
    
    return {
        "net_worth": net_worth,
        "total_assets_value": total_assets_value,
        "total_debts_value": total_debts_value,
        "liquid_assets_value": liquid_assets_value,
        "non_liquid_assets_value": non_liquid_assets_value,
        "liquid_percentage": liquid_percentage,
        "asset_count": len(assets),
        "category_count": len(categories_used),
        "top_categories": top_categories,
        "change_value": change_value,
        "change_percentage": change_percentage,
        "has_previous_data": previous_net_worth is not None
    }

def asset_management_screen(all_historical_records, current_assets, current_date):
    """
    Displays the asset management screen for viewing and editing assets.
    
    Args:
        all_historical_records: List of all historical records
        current_assets: List of current assets
        current_date: Current date string
        
    Returns:
        Tuple of (updated_assets, updated_historical_records, changes_made)
    """
    changes_made = False
    
    while True:
        # Display header
        console.print("\n[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
        console.print("[bold blue]ASSET MANAGEMENT[/bold blue]")
        console.print("[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
        
        # Calculate net worth summary
        total_assets = sum(asset.get('balance', 0.0) for asset in current_assets if asset.get('balance', 0.0) > 0)
        total_debts = sum(asset.get('balance', 0.0) for asset in current_assets if asset.get('balance', 0.0) < 0)
        net_worth = total_assets + total_debts  # debts are already negative
        liquid_assets = sum(asset.get('balance', 0.0) for asset in current_assets 
                          if asset.get('balance', 0.0) > 0 and asset.get('liquid', False))
        
        # Display net worth summary
        console.print()
        console.print(f"[bold]Net Worth:[/bold] [{'green' if net_worth >= 0 else 'red'}]£{net_worth:,.2f}[/{'green' if net_worth >= 0 else 'red'}]")
        console.print(f"[bold]Total Assets:[/bold] [green]£{total_assets:,.2f}[/green]")
        console.print(f"[bold]Total Debts:[/bold] [red]£{total_debts:,.2f}[/red]")
        console.print(f"[bold]Liquid Assets:[/bold] [cyan]£{liquid_assets:,.2f}[/cyan]")
        console.print()
        
        # Show assets in a simpler table format with better colours
        if current_assets:
            # Display assets in a Rich Table format
            table = Table(
                title=Text("Current Assets", style="bold"),
                show_header=True,
                header_style="bold",
                box=box.SIMPLE,
                padding=(0, 1)
            )
            
            table.add_column("#", style="dim", width=4, justify="right")
            table.add_column("Asset Name", min_width=20)
            table.add_column("Balance", justify="right", min_width=15)
            table.add_column("Category", min_width=15, style="dim")
            table.add_column("Liquid", justify="center", min_width=8)
            
            for idx, asset in enumerate(current_assets, 1):
                liquid_status = Text("Yes", style="green") if asset.get("liquid", False) else Text("No", style="red")
                balance = asset.get('balance', 0.0)
                balance_style = "green" if balance >= 0 else "red"
                balance_str = Text(f"£{balance:,.2f}", style=balance_style)
                category = asset.get("category", "Other")
                
                table.add_row(
                    str(idx),
                    asset["name"],
                    balance_str,
                    category,
                    liquid_status
                )
            
            console.print(table)
            
            # Instructions for the user
            console.print("\n[bold]Options:[/bold]")
            console.print(" • Enter [bold]asset number[/bold] to edit/manage that asset")
            console.print(" • Press [bold]a[/bold] to add a new asset")
            console.print(" • Press [bold]q[/bold] to return to dashboard")

            # Get direct input from user for asset selection
            user_input = console.input("\nEnter option: ").strip().lower()
            
            # Process user input
            if user_input == 'q':
                console.print("[yellow]Returning to dashboard...[/yellow]")
                return current_assets, all_historical_records, changes_made
            elif user_input == 'a':
                # Add new asset logic
                new_asset_added = add_new_asset(current_assets)
                if new_asset_added:
                    changes_made = True
                    save_historical_data(all_historical_records, current_date, current_assets)
                    console.print("[green]New asset added and saved successfully.[/green]")
                continue
            else:
                # Try to parse as an asset number
                try:
                    asset_idx = int(user_input) - 1  # Convert to 0-based index
                    if 0 <= asset_idx < len(current_assets):
                        # Show asset management options for the selected asset
                        changes_made_this_round = manage_single_asset(current_assets, asset_idx, all_historical_records, current_date)
                        if changes_made_this_round:
                            changes_made = True
                    else:
                        console.print(f"[red]Invalid asset number. Please enter a number between 1 and {len(current_assets)}.[/red]")
                except ValueError:
                    console.print("[red]Invalid input. Please enter an asset number, 'a' to add, or 'q' to quit.[/red]")
        else:
            console.print("[yellow]No assets defined yet.[/yellow]")
            
            # Options when no assets exist
            console.print("\n[bold]Options:[/bold]")
            console.print(" • Press [bold]a[/bold] to add a new asset")
            console.print(" • Press [bold]q[/bold] to return to dashboard")
            
            user_input = console.input("\nEnter option: ").strip().lower()
            
            if user_input == 'q':
                console.print("[yellow]Returning to dashboard...[/yellow]")
                return current_assets, all_historical_records, changes_made
            elif user_input == 'a':
                # Add new asset logic
                new_asset_added = add_new_asset(current_assets)
                if new_asset_added:
                    changes_made = True
                    save_historical_data(all_historical_records, current_date, current_assets)
                    console.print("[green]New asset added and saved successfully.[/green]")
                continue
            else:
                console.print("[red]Invalid input. Please enter 'a' to add an asset or 'q' to quit.[/red]")
    
    return current_assets, all_historical_records, changes_made

def add_new_asset(assets):
    """
    Add a new asset to the list of assets.
    
    Args:
        assets: List of assets to add to
        
    Returns:
        bool: True if an asset was added, False otherwise
    """
    asset_name = console.input("[b]Enter asset name: [/b]").strip()
    if not asset_name:
        console.print("[yellow]No asset name provided. Operation cancelled.[/yellow]")
        return False
        
    # Ask about liquidity
    while True:
        is_liquid_input = console.input(f"Is [bold]'{asset_name}'[/bold] a liquid asset? (y/n): ").strip().lower()
        if is_liquid_input in ['y', 'n']:
            is_liquid = is_liquid_input == 'y'
            break
        else:
            console.print("[red]Invalid input. Please enter 'y' for yes or 'n' for no.[/red]")
    
    # Ask for category
    category = set_asset_category_interactive(asset_name, console)
    
    # Ask for balance
    while True:
        balance_input = console.input(f"Enter balance for [bold]'{asset_name}'[/bold]: ").strip()
        if not balance_input:
            console.print("[yellow]No balance provided. Using 0.0.[/yellow]")
            balance = 0.0
            break
        try:
            balance = float(balance_input)
            break
        except ValueError:
            console.print("[red]Invalid balance. Please enter a numeric value.[/red]")
    
    # Add the new asset
    assets.append({
        "name": asset_name, 
        "liquid": is_liquid, 
        "balance": balance, 
        "category": category
    })
    
    console.print(f"[green]Asset '{asset_name}' added successfully.[/green]")
    return True

def update_asset_in_history(all_historical_records, asset_name, field_to_update, new_value):
    """
    Updates a specific field for an asset across all historical records.
    
    Args:
        all_historical_records: List of all historical records
        asset_name: Name of the asset to update
        field_to_update: Field name to update (e.g., 'liquid', 'category')
        new_value: New value to set for the field
        
    Returns:
        int: Number of records updated
    """
    records_updated = 0
    for record in all_historical_records:
        for asset in record.get('assets', []):
            if asset.get('name', '').lower() == asset_name.lower():
                if asset.get(field_to_update) != new_value:
                    asset[field_to_update] = new_value
                    records_updated += 1
    return records_updated

def manage_single_asset(assets, asset_idx, all_historical_records, current_date):
    """
    Manage a single asset by index.
    
    Args:
        assets: List of all assets
        asset_idx: Index of the asset to manage
        all_historical_records: All historical records
        current_date: Current date string
        
    Returns:
        bool: True if changes were made, False otherwise
    """
    asset = assets[asset_idx]
    changes_made = False
    
    # Display the selected asset details
    console.print(f"\n[bold]Managing Asset: [/bold]{asset['name']}")
    console.print(f"Balance: [{'green' if asset['balance'] >= 0 else 'red'}]£{asset['balance']:,.2f}[/{'green' if asset['balance'] >= 0 else 'red'}]")
    console.print(f"Category: {asset.get('category', 'Other')}")
    console.print(f"Liquid: [{'green' if asset['liquid'] else 'red'}]{('Yes' if asset['liquid'] else 'No')}[/{'green' if asset['liquid'] else 'red'}]")
    
    # Show options for this asset
    console.print("\n[bold]Options:[/bold]")
    console.print(" 1. Update balance")
    console.print(" 2. Change category")
    console.print(" 3. Toggle liquidity status")
    console.print(" 4. Delete asset")
    console.print(" 5. View balance history")
    console.print(" 6. Return to asset list")
    
    option = console.input("\nSelect option (1-6): ").strip()
    
    if option == '1':
        # Update balance
        while True:
            balance_input = console.input(f"Enter new balance for [bold]'{asset['name']}'[/bold] (current: £{asset['balance']:,.2f}): ").strip()
            if not balance_input:
                console.print("[yellow]No input. Keeping current balance.[/yellow]")
                break
            try:
                new_balance = float(balance_input)
                asset['balance'] = new_balance
                console.print(f"Balance updated to [{'green' if new_balance >= 0 else 'red'}]£{new_balance:,.2f}[/{'green' if new_balance >= 0 else 'red'}]")
                changes_made = True
                save_historical_data(all_historical_records, current_date, assets)
                break
            except ValueError:
                console.print("[red]Invalid input. Please enter a numeric value.[/red]")
    
    elif option == '2':
        # Change category
        set_asset_category(asset, console)
        changes_made = True
        save_historical_data(all_historical_records, current_date, assets)
    
    elif option == '3':
        # Toggle liquidity status
        new_liquid_status = not asset['liquid']
        if Confirm.ask(
            f"Change [bold]'{asset['name']}'[/bold] to [{'green' if new_liquid_status else 'red'}]{('liquid' if new_liquid_status else 'non-liquid')}[/{'green' if new_liquid_status else 'red'}] for all historical entries?",
            default=True
        ):
            records_updated = update_asset_in_history(all_historical_records, asset['name'], 'liquid', new_liquid_status)
            asset['liquid'] = new_liquid_status
            changes_made = True
            save_historical_data(all_historical_records, current_date, assets)
            console.print(f"[green]Updated liquidity status in {records_updated} historical records.[/green]")
        else:
            console.print("[yellow]Liquidity status change cancelled.[/yellow]")
    
    elif option == '4':
        # Delete asset
        if Confirm.ask(f"Are you sure you want to delete [bold]'{asset['name']}'[/bold]?", default=False):
            assets.pop(asset_idx)
            console.print(f"[yellow]Asset '{asset['name']}' deleted.[/yellow]")
            changes_made = True
            save_historical_data(all_historical_records, current_date, assets)
        else:
            console.print("[yellow]Deletion cancelled.[/yellow]")
    
    elif option == '5':
        # View balance history
        view_asset_history(asset['name'], all_historical_records)
    
    elif option == '6':
        # Return to asset list
        pass
    
    else:
        console.print("[red]Invalid option. Returning to asset list.[/red]")
    
    return changes_made

def view_asset_history(asset_name, all_historical_records):
    """
    View the balance history for a specific asset over time.
    
    Args:
        asset_name: Name of the asset to view history for
        all_historical_records: All historical records
    """
    # Create a list to store historical entries for this asset
    history_entries = []
    
    # Extract history from records
    for record in sorted(all_historical_records, key=lambda r: r.get('date', ''), reverse=False):
        record_date = record.get('date', '')
        for asset in record.get('assets', []):
            if asset.get('name', '').lower() == asset_name.lower():
                # Found a match for this asset
                formatted_date = datetime.strptime(record_date, "%Y-%m-%d").strftime("%d %B %Y")
                history_entries.append({
                    'date': formatted_date,
                    'raw_date': record_date,
                    'balance': asset.get('balance', 0.0),
                    'category': asset.get('category', 'Other'),
                    'liquid': asset.get('liquid', False)
                })
                break
    
    if not history_entries:
        console.print(f"[yellow]No historical data found for asset '{asset_name}'.[/yellow]")
        console.print("[dim]Press Enter to return...[/dim]")
        console.input()
        return
    
    # Create a table to display history
    table = Table(
        title=Text(f"Balance History for {asset_name}", style="bold"),
        show_header=True,
        header_style="bold",
        box=box.SIMPLE,
        padding=(0, 1)
    )
    
    table.add_column("Date", min_width=15)
    table.add_column("Balance", justify="right", min_width=15)
    table.add_column("Change", justify="right", min_width=15)
    table.add_column("Category", min_width=15, style="dim")
    table.add_column("Liquid", justify="center", min_width=8)
    
    previous_balance = None
    
    for entry in history_entries:
        # Format balance
        balance = entry['balance']
        balance_style = "green" if balance >= 0 else "red"
        balance_str = Text(f"£{balance:,.2f}", style=balance_style)
        
        # Calculate and format change
        if previous_balance is not None:
            change = balance - previous_balance
            change_style = "green" if change > 0 else "red" if change < 0 else "dim"
            change_symbol = "↑" if change > 0 else "↓" if change < 0 else "→"
            change_str = Text(f"{change_symbol} £{abs(change):,.2f}", style=change_style)
        else:
            change_str = Text("N/A", style="dim")
        
        # Format liquid status
        liquid_status = Text("Yes", style="green") if entry['liquid'] else Text("No", style="red")
        
        # Add row to table
        table.add_row(
            entry['date'],
            balance_str,
            change_str,
            entry['category'],
            liquid_status
        )
        
        previous_balance = balance
    
    # Display the table
    console.print(table)
    
    # Calculate and display statistics
    if len(history_entries) > 1:
        first_balance = history_entries[0]['balance']
        last_balance = history_entries[-1]['balance']
        total_change = last_balance - first_balance
        first_date = history_entries[0]['date']
        last_date = history_entries[-1]['date']
        
        percentage_change = (total_change / abs(first_balance)) * 100 if first_balance != 0 else 0
        
        console.print(f"\n[bold]Summary statistics:[/bold]")
        console.print(f"• Period: {first_date} to {last_date}")
        console.print(f"• Starting balance: [{'green' if first_balance >= 0 else 'red'}]£{first_balance:,.2f}[/{'green' if first_balance >= 0 else 'red'}]")
        console.print(f"• Current balance: [{'green' if last_balance >= 0 else 'red'}]£{last_balance:,.2f}[/{'green' if last_balance >= 0 else 'red'}]")
        console.print(f"• Overall change: [{'green' if total_change >= 0 else 'red'}]£{total_change:,.2f} ({percentage_change:.1f}%)[/{'green' if total_change >= 0 else 'red'}]")
    
    console.print("\n[dim]Press Enter to return...[/dim]")
    console.input()

def main():
    """Main application loop."""
    # Load custom categories and custom keywords for auto-categorization
    load_custom_keywords()
    
    # Load historical data and set up current assets
    global CURRENT_DATA_FILE
    all_historical_records = check_existing_data()
    
    # Set up current assets and date from most recent record, or empty if no history
    current_assets = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    if all_historical_records:
        most_recent_record = all_historical_records[0]  # Records are sorted newest first
        current_assets = most_recent_record.get('assets', []).copy()
        current_date = most_recent_record.get('date', current_date)
    
    # Define menu options (without shortcuts - they'll be added by show_menu)
    menu_options = [
        "View/Edit Assets",
        "Quick Balance Update",
        "Generate Charts", 
        "View Categories",
        "File Options",
        "Exit Application"
    ]
    
    while True:
        # Calculate summary statistics (inside loop to refresh on changes)
        stats = calculate_summary_stats(current_assets, all_historical_records)
        
        # Clear the console for a fresh display
        console.clear()
        
        # Create header
        header_text = Text()
        header_text.append("NET WORTH TRACKER", style="bold blue")
        console.print(header_text)
        console.print("━" * 60, style="blue")
        console.print()
        
        # Create the net worth panel with trend indicator
        net_worth_text = Text()
        net_worth_text.append(f"£{stats['net_worth']:,.2f}", style="bold green" if stats['net_worth'] >= 0 else "bold red")
        
        # Add trend indicator if we have previous data
        if stats['has_previous_data']:
            if stats['change_value'] > 0:
                trend_symbol = "↑"
                trend_style = "bold green"
            elif stats['change_value'] < 0:
                trend_symbol = "↓"
                trend_style = "bold red"
            else:
                trend_symbol = "→"
                trend_style = "bold yellow"
                
            net_worth_text.append(f" {trend_symbol} ", style=trend_style)
            net_worth_text.append(f"£{abs(stats['change_value']):,.2f}", 
                                  style="green" if stats['change_value'] >= 0 else "red")
            net_worth_text.append(f" ({abs(stats['change_percentage']):.1f}%)", 
                                  style="green" if stats['change_value'] >= 0 else "red")
        
        # Direct content for financial summary panel
        summary_content = []
        summary_content.append(f"[bold]Current Net Worth:[/bold] {net_worth_text}")
        summary_content.append(f"[bold]Last Updated:[/bold] {datetime.strptime(current_date, '%Y-%m-%d').strftime('%d %B %Y')}")
        summary_content.append("")
        summary_content.append(f"[bold]Assets:[/bold] {'£':>10}{stats['total_assets_value']:,.2f}")
        summary_content.append(f"[bold]Debts:[/bold] {'£':>11}{stats['total_debts_value']:,.2f}")
        summary_content.append("")
        summary_content.append(f"[bold]Liquid Assets:[/bold] {'£':>6}{stats['liquid_assets_value']:,.2f} ({stats['liquid_percentage']:.1f}%)")
        summary_content.append(f"[bold]Non-liquid Assets:[/bold] {'£':>2}{stats['non_liquid_assets_value']:,.2f}")
        summary_content.append("")
        summary_content.append(f"[bold]Total Assets:[/bold] {stats['asset_count']} across {stats['category_count']} categories")
        
        # Add top categories if available
        if stats['top_categories']:
            summary_content.append("")
            summary_content.append(f"[bold]Top Categories:[/bold]")
            for category, value in stats['top_categories']:
                summary_content.append(f"  [yellow]{category}:[/yellow] {'£':>10}{value:,.2f}")
        
        # Create the summary panel (simplified with just one border)
        summary_panel = Panel(
            renderable="\n".join(summary_content),
            title="Financial Summary",
            border_style="green",
            box=box.ROUNDED,
            title_align="left",
            padding=(1, 2)
        )
        
        # Display the financial summary
        console.print(summary_panel)
        console.print()
        
        # Show the menu and get selection
        menu_index, selected_option = show_menu(
            menu_options,
            title="Select an option (or press shortcut key):",
            return_shortcut=False
        )
        
        # Check for cancellation
        if menu_index is None:
            console.print("\n[yellow]Exiting application. Goodbye![/yellow]")
            sys.exit()
        
        # Flag to track if we need the "press any key" prompt
        skip_key_prompt = False
        
        # Handle menu selection
        if selected_option == "View/Edit Assets":
            # Call the asset management screen
            current_assets, all_historical_records, changes_made = asset_management_screen(
                all_historical_records, 
                current_assets, 
                current_date
            )
        elif selected_option == "Quick Balance Update":
            balance_result = get_asset_balances(current_assets)
            if balance_result:
                # Save changes
                save_historical_data(all_historical_records, current_date, current_assets)
                console.print("[green]Balances updated and saved successfully.[/green]")
        elif selected_option == "Generate Charts" and CHARTING_AVAILABLE:
            # Charts submenu
            chart_options = [
                "Summary chart: Assets over time",
                "Detailed chart: All individual assets",
                "Category chart: Assets by category",
                "Single asset chart: Track one asset over time",
                "Generate all three main chart types"
            ]
            
            menu_index, selected_chart = show_menu(
                chart_options,
                title="\nChart Options:"
            )
            
            # Handle ESC/q or return
            if menu_index is None:
                console.print("[yellow]Returning to dashboard...[/yellow]")
                skip_key_prompt = True
                continue
            
            if selected_chart == "Summary chart: Assets over time":
                console.print("\n[green]Generating summary net worth chart...[/green]")
                chart_utils.generate_charts(all_historical_records, "summary")
            elif selected_chart == "Detailed chart: All individual assets":
                console.print("\n[green]Generating detailed net worth chart (all assets)...[/green]")
                chart_utils.generate_charts(all_historical_records, "detailed")
            elif selected_chart == "Category chart: Assets by category":
                console.print("\n[green]Generating category-based net worth chart...[/green]")
                chart_utils.generate_charts(all_historical_records, "category")
            elif selected_chart == "Single asset chart: Track one asset over time":
                # Let the user select an asset to chart
                if not current_assets:
                    console.print("[yellow]No assets available to chart.[/yellow]")
                else:
                    # Loop to allow charting multiple assets in succession
                    while True:
                        # Create asset selection menu
                        asset_options = [asset['name'] for asset in current_assets]
                        
                        menu_index, selected_asset = show_menu(
                            asset_options,
                            title="\nSelect an asset to chart:",
                            shortcuts=False
                        )
                        
                        if menu_index is None:
                            break
                            
                        console.print(f"\n[green]Generating chart for {selected_asset}...[/green]")
                        chart_utils.generate_charts(all_historical_records, "asset", selected_asset)
                        
                        if not Confirm.ask("\nWould you like to chart another asset?", default=False):
                            break
            elif selected_chart == "Generate all three main chart types":
                console.print("\n[green]Generating all chart types...[/green]")
                chart_utils.generate_charts(all_historical_records, "all")
        elif selected_option == "View Categories":
            view_categories(console)
        elif selected_option == "File Options":
            # File options submenu
            file_options = [
                f"Current file: {CURRENT_DATA_FILE}",
                "Load different file",
                "Create new file",
                "Export data"
            ]
            
            menu_index, selected_file_option = show_menu(
                file_options,
                title="\nFile Options:"
            )
            
            # Handle file operations based on selection
            if selected_file_option == "Load different file":
                all_historical_records = check_existing_data()
            elif selected_file_option == "Create new file":
                # Implement new file creation logic
                console.print("\n[bold green]New file creation to be implemented[/bold green]")
            elif selected_file_option == "Export data":
                # Implement export data logic
                console.print("\n[bold green]Export data to be implemented[/bold green]")
        elif selected_option == "Exit Application":
            console.print("\n[yellow]Exiting application. Goodbye![/yellow]")
            sys.exit()
        
        # Press any key to continue - skip if coming back from a submenu with its own return flow
        if not skip_key_prompt:
            console.print("\n[dim]Press any key to return to dashboard...[/dim]")
            try:
                readchar.readkey()
            except Exception:
                pass
    
    return all_historical_records

if __name__ == "__main__":
    main() 

# To run this in terminal: python net_worth_tracker.py