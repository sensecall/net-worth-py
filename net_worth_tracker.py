import json
import csv # For CSV export
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

def display_app_title():
    """Displays a visually appealing application title."""
    title_text = Text("Net Worth Tracker", style="bold green")
    subtitle_text = Text("Track your financial journey", style="italic dim")
    
    console.print(title_text, justify="center")
    console.print(subtitle_text, justify="center")
    console.print() # Add a blank line for spacing

def check_existing_data():
    """Checks for existing data files and prompts user with options."""
    global CURRENT_DATA_FILE
    
    display_app_title() # Display the title first

    if os.path.exists(DATA_FILENAME):
        console.print(
            Panel(
                Text.assemble(
                    ("We spotted a JSON file (", "white"),
                    (DATA_FILENAME, "cyan bold"),
                    (") which looks like it contains your net worth history.", "white")
                ),
                title="[bold yellow]Existing Data Found[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            )
        )
        console.print() # Add a blank line for spacing
        
        options = [
            f"Load existing file ({DATA_FILENAME})",
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
            
        if selected_option == f"Load existing file ({DATA_FILENAME})":
            console.print(f"\n[green]Loading data from [cyan]{DATA_FILENAME}[/cyan]...[/green]")
            CURRENT_DATA_FILE = DATA_FILENAME
            return load_historical_data()
        elif selected_option == "Start fresh (creates a new file, won't overwrite existing data)":
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
    Displays the asset management screen for viewing and editing assets with direct key press actions.
    
    Args:
        all_historical_records: List of all historical records
        current_assets: List of current assets
        current_date: Current date string
        
    Returns:
        Tuple of (updated_assets, updated_historical_records, changes_made_overall)
    """
    changes_made_overall = False
    
    while True:
        console.clear()
        # Display header
        console.print("\n[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
        console.print("[bold blue]ASSET MANAGEMENT[/bold blue]")
        console.print("[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
        
        # Calculate net worth summary
        total_assets_val = sum(asset.get('balance', 0.0) for asset in current_assets if asset.get('balance', 0.0) > 0)
        total_debts_val = sum(asset.get('balance', 0.0) for asset in current_assets if asset.get('balance', 0.0) < 0)
        net_worth_val = total_assets_val + total_debts_val
        liquid_assets_val = sum(asset.get('balance', 0.0) for asset in current_assets 
                              if asset.get('balance', 0.0) > 0 and asset.get('liquid', False))
        
        console.print()
        console.print(f"[bold]Net Worth:[/bold] [{'green' if net_worth_val >= 0 else 'red'}]£{net_worth_val:,.2f}[/{'green' if net_worth_val >= 0 else 'red'}]")
        console.print(f"[bold]Total Assets:[/bold] [green]£{total_assets_val:,.2f}[/green]")
        console.print(f"[bold]Total Debts:[/bold] [red]£{total_debts_val:,.2f}[/red]")
        console.print(f"[bold]Liquid Assets:[/bold] [cyan]£{liquid_assets_val:,.2f}[/cyan]")
        console.print()
        
        if current_assets:
            table = Table(
                title=Text("Current Assets", style="bold"),
                show_header=True, header_style="bold", box=box.SIMPLE, padding=(0, 1)
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
                table.add_row(str(idx), asset["name"], balance_str, category, liquid_status)
            console.print(table)
            
            console.print("\n[bold]Options:[/bold]")
            console.print(" • Press [cyan]m[/cyan] then asset # to manage")
            console.print(" • Press [cyan]a[/cyan] to add new asset")
            console.print(" • Press [cyan]h[/cyan] to view all asset history")
            console.print(" • Press [cyan]q[/cyan] to return to dashboard")
        else:
            console.print("[yellow]No assets defined yet.[/yellow]")
            console.print("\n[bold]Options:[/bold]")
            console.print(" • Press [cyan]a[/cyan] to add new asset")
            console.print(" • Press [cyan]h[/cyan] to view history (if any)")
            console.print(" • Press [cyan]q[/cyan] to return to dashboard")

        console.print("\nEnter action: ", end="")
        try:
            key = readchar.readkey()
            console.print(key) # Echo the key
            console.print() # Newline after key echo

            if key.lower() == 'q':
                console.print("[yellow]Returning to dashboard...[/yellow]")
                return current_assets, all_historical_records, changes_made_overall
            
            elif key.lower() == 'a':
                new_asset_added = add_new_asset(current_assets) # add_new_asset should return True if asset added
                if new_asset_added:
                    changes_made_overall = True
                    save_historical_data(all_historical_records, current_date, current_assets)
                    console.print("[green]New asset added and saved successfully.[/green]")
                    # Loop continues, will refresh screen
                else:
                    console.print("[yellow]Add asset cancelled.[/yellow]")
                console.input("Press Enter to continue...") # Pause to see message
                continue

            elif key.lower() == 'h':
                if all_historical_records or current_assets: # Allow viewing even if only current assets exist for structure
                    view_all_asset_updates_table(all_historical_records if all_historical_records else [{"date": current_date, "assets": current_assets}])
                else:
                    console.print("[yellow]No data available to view.[/yellow]")
                    console.input("Press Enter to continue...")
                continue # Refreshes asset_management_screen
            
            elif key.lower() == 'm':
                if not current_assets:
                    console.print("[red]No assets to manage.[/red]")
                    console.input("Press Enter to continue...")
                    continue
                
                try:
                    asset_num_str = console.input("Enter asset number to manage: ").strip()
                    if not asset_num_str: # User pressed Enter without typing a number
                        console.print("[yellow]No asset number entered. Returning to options.[/yellow]")
                        console.input("Press Enter to continue...")
                        continue

                    asset_idx = int(asset_num_str) - 1
                    if 0 <= asset_idx < len(current_assets):
                        console.clear() # Clear before showing single asset management
                        changes_made_this_session = manage_single_asset(current_assets, asset_idx, all_historical_records, current_date)
                        if changes_made_this_session:
                            changes_made_overall = True
                            # Data is saved within manage_single_asset if changes occur
                        # Loop continues, will refresh screen
                    else:
                        console.print(f"[red]Invalid asset number. Please enter a number between 1 and {len(current_assets)}.[/red]")
                except ValueError:
                    console.print("[red]Invalid input. Please enter a valid number.[/red]")
                except Exception as e_manage: # Catch any other errors during manage input
                    console.print(f"[red]An error occurred: {e_manage}[/red]")
                console.input("Press Enter to continue...")
                continue
            else:
                console.print(f"[red]Invalid option: '{key}'.[/red]")
                console.input("Press Enter to continue...")
                continue
        
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in asset management: {e}[/bold red]")
            console.input("Press Enter to continue...")
            # Decide if to break or continue, for now continue to allow retry
            continue
    
    # This line might not be reached if always returning from loop, but good for structure
    return current_assets, all_historical_records, changes_made_overall

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

def rename_asset_in_history(all_historical_records, old_name, new_name):
    """Renames an asset across all historical records."""
    records_affected = 0
    for record in all_historical_records:
        asset_found_in_record = False
        for asset in record.get('assets', []):
            if asset.get('name') == old_name:
                asset['name'] = new_name
                asset_found_in_record = True
        if asset_found_in_record:
            records_affected += 1
    return records_affected

def manage_single_asset(assets, asset_idx, all_historical_records, current_date):
    """
    Manage a single asset by index using direct key presses.
    
    Args:
        assets: List of all assets (current snapshot)
        asset_idx: Index of the asset to manage in the 'assets' list
        all_historical_records: All historical records
        current_date: Current date string for saving purposes
        
    Returns:
        bool: True if changes were made that require saving, False otherwise
    """
    if not (0 <= asset_idx < len(assets)):
        console.print("[red]Invalid asset index for management.[/red]")
        return False
        
    original_asset_name = assets[asset_idx]["name"] # Store for potential rename history update
    changes_made_session = False

    while True:
        console.clear()
        asset = assets[asset_idx] # Re-fetch in case of rename
        
        console.print(f"\n[bold underline]Managing Asset: {asset['name']}[/bold underline]")
        console.print(f"Current Balance: [{'green' if asset['balance'] >= 0 else 'red'}]£{asset['balance']:,.2f}[/{'green' if asset['balance'] >= 0 else 'red'}]")
        console.print(f"Category: {asset.get('category', 'Other')}")
        console.print(f"Liquidity: [{'green' if asset['liquid'] else 'red'}]{('Yes' if asset['liquid'] else 'No')}[/{'green' if asset['liquid'] else 'red'}]")
        
        console.print("\n[bold]Actions:[/bold]")
        console.print(" [cyan]b[/cyan]: Update Balance")
        console.print(" [cyan]c[/cyan]: Change Category")
        console.print(" [cyan]t[/cyan]: Toggle Liquidity")
        console.print(" [cyan]r[/cyan]: Rename Asset")
        console.print(" [cyan]x[/cyan]: Delete Asset")
        console.print(" [cyan]h[/cyan]: View Balance History")
        console.print(" [cyan]q[/cyan]: Return to Asset List")
        
        console.print("\nSelect action: ", end="")
        key = readchar.readkey()
        console.print(key) # Echo key
        console.print() # Newline

        action_taken_this_iteration = False

        if key.lower() == 'q':
            break # Exit the management loop for this asset

        elif key.lower() == 'b':
            console.print("--- Update Balance ---")
            console.print(f"This updates the balance for [bold]'{asset['name']}'[/bold] in the record for [cyan]{current_date}[/cyan].") # CLARIFICATION ADDED HERE
            balance_input = console.input(f"Enter new balance for [bold]'{asset['name']}'[/bold] (current: £{asset['balance']:,.2f}): ").strip()
            if not balance_input:
                console.print("[yellow]No input. Keeping current balance.[/yellow]")
            else:
                try:
                    new_balance = float(balance_input)
                    asset['balance'] = new_balance
                    console.print(f"Balance updated to [{'green' if new_balance >= 0 else 'red'}]£{new_balance:,.2f}[/{'green' if new_balance >= 0 else 'red'}]")
                    changes_made_session = True
                    action_taken_this_iteration = True
                except ValueError:
                    console.print("[red]Invalid input. Please enter a numeric value.[/red]")
        
        elif key.lower() == 'c':
            console.print("--- Change Category ---")
            # set_asset_category updates the asset in-place and returns True if changed
            if set_asset_category(asset, console):
                 changes_made_session = True
                 action_taken_this_iteration = True
        
        elif key.lower() == 't':
            console.print("--- Toggle Liquidity ---")
            new_liquid_status = not asset['liquid']
            if Confirm.ask(
                f"Change [bold]'{asset['name']}'[/bold] to [{'green' if new_liquid_status else 'red'}]{('liquid' if new_liquid_status else 'non-liquid')}[/{'green' if new_liquid_status else 'red'}] for all historical entries?",
                default=True
            ):
                records_updated = update_asset_in_history(all_historical_records, asset['name'], 'liquid', new_liquid_status)
                asset['liquid'] = new_liquid_status # Update current asset view
                changes_made_session = True
                action_taken_this_iteration = True
                console.print(f"[green]Updated liquidity status in {records_updated} historical records.[/green]")
            else:
                console.print("[yellow]Liquidity status change cancelled.[/yellow]")

        elif key.lower() == 'r': # Rename Asset
            console.print("--- Rename Asset ---")
            console.print("[yellow]WARNING: This will rename the asset in the current record AND all historical entries if confirmed later.[/yellow]") # WARNING ADDED
            old_name_for_history = asset["name"] 
            new_name_input = console.input(f"Enter new name for [bold]'{asset['name']}'[/bold]: ").strip()
            
            if not new_name_input:
                console.print("[yellow]No new name entered. Rename cancelled.[/yellow]")
            elif new_name_input == asset["name"]:
                console.print("[yellow]New name is the same as the current name. No change.[/yellow]")
            # DUPLICATE CHECK ADDED HERE (checks against other assets in the current list)
            elif any(a['name'] == new_name_input for i, a in enumerate(assets) if i != asset_idx):
                console.print(f"[red]Error: An asset with the name '{new_name_input}' already exists in the current asset list. Please choose a unique name.[/red]")
            else:
                # Current asset name update and historical update confirmation will follow here
                asset["name"] = new_name_input
                console.print(f"Asset name updated to [bold]'{new_name_input}'[/bold] in the current working record.")
                if Confirm.ask(f"Rename this asset in all {len(all_historical_records)} historical records as well?", default=True):
                    renamed_in_history_count = rename_asset_in_history(all_historical_records, old_name_for_history, new_name_input)
                    console.print(f"[green]Renamed asset in {renamed_in_history_count} historical records.[/green]")
                changes_made_session = True
                action_taken_this_iteration = True

        elif key.lower() == 'x': # Delete Asset
            console.print("--- Delete Asset ---")
            if Confirm.ask(f"Are you sure you want to delete [bold]'{asset['name']}'[/bold]? This will remove it from the current record.", default=False):
                deleted_asset_name = assets.pop(asset_idx)["name"]
                console.print(f"[yellow]Asset '{deleted_asset_name}' deleted from current record.[/yellow]")
                # Note: This does not remove it from historical records by default.
                # That would be a more complex operation, maybe a separate utility.
                changes_made_session = True
                # After deletion, this asset_idx is no longer valid for the 'assets' list in this scope.
                # We must return to the caller (asset_management_screen) to re-evaluate.
                save_historical_data(all_historical_records, current_date, assets) # Save immediately after deletion
                console.input("Press Enter to return to asset list...")
                return changes_made_session # Exit function, asset_idx invalid
            else:
                console.print("[yellow]Deletion cancelled.[/yellow]")

        elif key.lower() == 'h':
            console.print("--- View Balance History ---")
            view_asset_history(asset['name'], all_historical_records)
            action_taken_this_iteration = True # Viewing history is an action, pause needed
        
        else:
            console.print(f"[red]Invalid option: '{key}'[/red]")
            action_taken_this_iteration = True # Show message, then pause

        if changes_made_session and action_taken_this_iteration:
            # Save if any change was made AND an action was taken that should pause
            save_historical_data(all_historical_records, current_date, assets)
            console.print("[green]Current changes saved.[/green]")

        if action_taken_this_iteration and key.lower() != 'q':
             # Pause to see the result of the action, unless it was quitting
             # or an action that forces immediate return (like delete)
            console.input("Press Enter to continue managing this asset...")
            
    return changes_made_session

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

def export_data_to_csv(data_for_csv, default_filename="asset_updates.csv"):
    """Exports the given data to a CSV file."""
    if not data_for_csv:
        console.print("[yellow]No data available to export.[/yellow]")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = default_filename.replace(".csv", f"_{timestamp}.csv")
    
    try:
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write headers (assuming the first row in data_for_csv can be used for headers or define them explicitly)
            headers = ["Date", "Asset Name", "Category", "Liquid", "Balance", "Change Since Last"]
            writer.writerow(headers)
            # Write data rows
            for row in data_for_csv:
                writer.writerow(row)
        console.print(f"[green]Data exported successfully to [cyan]{filename}[/cyan][/green]")
    except IOError:
        console.print(f"[bold red]Error: Could not write to file [cyan]{filename}[/cyan][/bold red]")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred during CSV export: {e}[/bold red]")

def view_all_asset_updates_table(all_historical_records):
    """
    Displays a pivot table with 'Date' fixed left. Other columns (assets, TNW, Change)
    have uniform width and scroll horizontally. Headers wrap to 3 lines & truncate.
    Args:
        all_historical_records: List of all historical records.
    """
    if not all_historical_records:
        console.print("[yellow]No historical data to display.[/yellow]")
        console.print("\n[dim]Press Enter to return...[/dim]")
        readchar.readkey()
        return

    date_col_name = "Date"
    tnw_col_name = "Total Net Worth"
    change_col_name = "Change" # Change in TNW
    asset_names_only = sorted(list(set(asset['name'] for record in all_historical_records for asset in record.get('assets', []))))

    if not asset_names_only:
        console.print("[yellow]No assets found in historical data to display.[/yellow]")
        console.print("\n[dim]Press Enter to return...[/dim]")
        readchar.readkey()
        return

    scrollable_column_names = asset_names_only + [tnw_col_name, change_col_name]
    cell_horizontal_padding = 1 # Standard Rich table cell padding on one side
    date_col_content_width = 12

    # --- 2. Prepare full data for display and CSV & Determine max_scrollable_content_width ---
    processed_rows = []
    csv_export_rows = []
    csv_headers = [date_col_name] + scrollable_column_names
    csv_export_rows.append(csv_headers)
    all_dates_sorted = sorted(list(set(record['date'] for record in all_historical_records)))
    previous_tnw_for_change_calc = None
    max_scrollable_content_len = 0

    for date_str in all_dates_sorted:
        row_display_data = {}
        row_csv_data = [date_str]
        try:
            row_display_data[date_col_name] = Text(datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y"), style="dim")
        except ValueError:
            row_display_data[date_col_name] = Text(date_str, style="dim")

        record_for_date = next((r for r in all_historical_records if r['date'] == date_str), None)
        balances_for_date = {asset['name']: asset['balance'] for asset in record_for_date.get('assets', [])} if record_for_date else {}
        current_tnw_for_this_date = 0

        for asset_name in asset_names_only:
            balance = balances_for_date.get(asset_name, 0.0)
            current_tnw_for_this_date += balance
            style = "green" if balance >= 0 else "red"
            text_val = Text(f"£{balance:,.2f}", style=style if balance != 0 else "dim")
            row_display_data[asset_name] = text_val
            max_scrollable_content_len = max(max_scrollable_content_len, len(str(text_val)))
            row_csv_data.append(f"{balance:.2f}")

        # Total Net Worth - now bold
        tnw_style = "green bold" if current_tnw_for_this_date >= 0 else "red bold"
        tnw_text_val = Text(f"£{current_tnw_for_this_date:,.2f}", style=tnw_style)
        row_display_data[tnw_col_name] = tnw_text_val
        max_scrollable_content_len = max(max_scrollable_content_len, len(str(tnw_text_val)))
        row_csv_data.append(f"{current_tnw_for_this_date:.2f}")

        # Change in Total Net Worth - as percentage, bold, max 2dp
        change_display_text = Text("N/A", style="dim bold") # Default to bold N/A
        change_csv_val = "N/A"
        if previous_tnw_for_change_calc is not None:
            diff = current_tnw_for_this_date - previous_tnw_for_change_calc
            if previous_tnw_for_change_calc == 0:
                if diff == 0:
                    percentage_change = 0.0
                    ch_style = "dim bold"
                    symbol = "→"
                    change_display_text = Text(f"{symbol} {percentage_change:.2f}%", style=ch_style)
                else:
                    # Percentage change is infinite or undefined, display N/A or specific symbol
                    ch_style = "dim bold"
                    change_display_text = Text("N/A", style=ch_style) 
                change_csv_val = "N/A" # Or appropriate representation for CSV
            else:
                percentage_change = (diff / abs(previous_tnw_for_change_calc)) * 100
                ch_style = "green bold" if diff > 0 else "red bold" if diff < 0 else "dim bold"
                symbol = "↑" if diff > 0 else "↓" if diff < 0 else "→"
                change_display_text = Text(f"{symbol} {percentage_change:.2f}%", style=ch_style)
                change_csv_val = f"{percentage_change:.2f}%"
        
        row_display_data[change_col_name] = change_display_text
        max_scrollable_content_len = max(max_scrollable_content_len, len(str(change_display_text)))
        row_csv_data.append(change_csv_val)
        
        previous_tnw_for_change_calc = current_tnw_for_this_date
        processed_rows.append(row_display_data)
        csv_export_rows.append(row_csv_data)
    
    # Ensure a minimum sensible width for scrollable columns if all values are tiny
    uniform_scrollable_content_width = max(max_scrollable_content_len, 8) # Min content width of 8 for scrollable

    # --- 3. Scrolling and Table Rendering Loop ---
    current_page_start_idx = 0

    while True:
        console.clear()

        padded_date_col_total_width = date_col_content_width + 2 * cell_horizontal_padding
        width_consumed_by_fixed_date_and_structure = padded_date_col_total_width + 3 # 1 left edge, 1 sep after Date, 1 right edge
        available_width_for_scrollable_section = console.width - width_consumed_by_fixed_date_and_structure
        
        cost_per_scrollable_col_and_its_separator = (uniform_scrollable_content_width + 2 * cell_horizontal_padding) + 1 # +1 for its separator

        num_scrollable_cols_on_page = 0
        if available_width_for_scrollable_section > (uniform_scrollable_content_width + 2 * cell_horizontal_padding): # Can at least one col fit?
            num_scrollable_cols_on_page = max(1, available_width_for_scrollable_section // cost_per_scrollable_col_and_its_separator)
        elif len(scrollable_column_names) > 0 : # If not, but we have cols, try to show one (it will likely be messy)
             num_scrollable_cols_on_page = 1
        
        page_end_idx = min(current_page_start_idx + num_scrollable_cols_on_page, len(scrollable_column_names))
        scrollable_cols_this_page = scrollable_column_names[current_page_start_idx:page_end_idx]

        table = Table(
            title=Text("Asset Balances (Date Fixed, Others Scroll, Uniform Width)", style="bold blue"),
            show_header=True, header_style="bold magenta", box=box.ROUNDED,
            width=console.width
        )

        table.add_column(date_col_name, min_width=date_col_content_width)

        for col_name in scrollable_cols_this_page:
            header_text_obj = Text(col_name)
            wrapped_header_lines = header_text_obj.wrap(console, uniform_scrollable_content_width)
            
            final_header_lines = []
            for i, line in enumerate(wrapped_header_lines):
                if i < 2: # First two lines
                    final_header_lines.append(line)
                elif i == 2: # Third line
                    if len(wrapped_header_lines) > 3:
                        # If there are more than 3 lines, truncate 3rd line and add ellipsis
                        # This requires converting Text to str, truncating, then back to Text
                        line_str = str(line)
                        if len(line_str) > uniform_scrollable_content_width - 3:
                             final_header_lines.append(Text(line_str[:uniform_scrollable_content_width-3] + "...", style=line.style))
                        else:
                             final_header_lines.append(Text(str(line) + "...", style=line.style))
                    else: # Exactly 3 lines or less
                        final_header_lines.append(line)
                    break # Stop after 3rd line processing
            
            actual_header = Text("\n").join(final_header_lines) if final_header_lines else Text(col_name) # Fallback to col_name if empty
            table.add_column(actual_header, justify="right", min_width=uniform_scrollable_content_width)
        
        for row_data_map in processed_rows:
            display_row_values = [row_data_map[date_col_name]]
            for col_name in scrollable_cols_this_page:
                display_row_values.append(row_data_map.get(col_name, Text("-", style="dim")))
            table.add_row(*display_row_values)
        
        console.print(table)

        scroll_indicator = ""
        if current_page_start_idx > 0:
            scroll_indicator += "[cyan]< Left[/cyan]  "
        if page_end_idx < len(scrollable_column_names):
            scroll_indicator += "[cyan]Right >[/cyan]"
        
        console.print(f"\n[bold]Options:[/bold] {scroll_indicator}  Press [cyan]c[/cyan] to export, [cyan]q[/cyan] to return.")

        try:
            key = readchar.readkey()
            if key.lower() == 'c':
                export_pivot_data_to_csv(csv_export_rows, default_filename="asset_pivot_view.csv")
            elif key.lower() == 'q':
                console.clear()
                break
            elif key == readchar.key.RIGHT:
                if page_end_idx < len(scrollable_column_names):
                    current_page_start_idx += num_scrollable_cols_on_page
            elif key == readchar.key.LEFT:
                if current_page_start_idx > 0:
                    # To go left, recalculate based on what *would* have been displayed
                    # This is tricky if the number of cols per page varies based on previous page start
                    # For uniform width, it is simpler: just jump back by the current num_scrollable_cols_on_page
                    current_page_start_idx = max(0, current_page_start_idx - num_scrollable_cols_on_page)
        except Exception as e:
            console.print(f"[red]An error occurred: {e}. Returning to asset management.[/red]")
            console.input("Press Enter to continue...") 
            console.clear()
            break

# The export_pivot_data_to_csv function should still work if csv_export_rows is correct
# ... existing code ...

def main():
    """Main application loop."""
    console.clear() # Clear the console at the start
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
            current_assets, all_historical_records, changes_made_overall = asset_management_screen(
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