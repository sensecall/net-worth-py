import json
import readchar # For reading single key presses
import sys # For sys.exit()
import os # For os.path.exists()
from datetime import datetime # For today's date
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.prompt import Confirm

# Import our utility modules
from asset_utils import (
    DEFAULT_CATEGORIES, 
    AUTO_CATEGORIZE_RULES,
    guess_category, 
    set_asset_category_interactive, 
    set_asset_category, 
    categorize_assets,
    load_custom_categories_from_data,
    view_categories
)

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
        console.print("\nWhat would you like to do?")
        console.print("  [bold green]L[/bold green]. Load this existing file")
        console.print("  [bold blue]F[/bold blue]. Start fresh (creates a new file, won't overwrite existing data)")
        console.print("  [bold magenta]O[/bold magenta]. Open a different data file")
        console.print("Your choice: ", end="")
        
        try:
            choice = readchar.readkey().lower()
            console.print(choice)
            
            if choice == 'l':
                console.print(f"\n[green]Loading data from [cyan]{DATA_FILENAME}[/cyan]...[/green]")
                CURRENT_DATA_FILE = DATA_FILENAME
                return load_historical_data()
            elif choice == 'f':
                # Generate a new filename to avoid overwriting the existing file
                filename_without_ext = os.path.splitext(DATA_FILENAME)[0]
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_filename = f"{filename_without_ext}_new_{timestamp}.json"
                
                console.print(f"\n[yellow]Starting fresh with no historical data.[/yellow]")
                console.print(f"[green]Your new data will be saved to [cyan]{new_filename}[/cyan] to preserve your existing data.[/green]")
                
                CURRENT_DATA_FILE = new_filename
                return []
            elif choice == 'o':
                different_file = console.input("\nEnter the path to your data file: ").strip()
                if different_file and os.path.exists(different_file):
                    console.print(f"[green]Loading data from [cyan]{different_file}[/cyan]...[/green]")
                    CURRENT_DATA_FILE = different_file
                    return load_historical_data(different_file)
                else:
                    console.print(f"[red]File not found: [cyan]{different_file}[/cyan]. Starting fresh.[/red]")
                    # Generate a new filename since the specified file doesn't exist
                    filename_without_ext = os.path.splitext(different_file)[0] if '.' in different_file else different_file
                    CURRENT_DATA_FILE = f"{filename_without_ext}.json"
                    console.print(f"[green]Your data will be saved to [cyan]{CURRENT_DATA_FILE}[/cyan].[/green]")
                    return []
            else:
                console.print(" [red]Invalid choice. Loading default file.[/red]")
                CURRENT_DATA_FILE = DATA_FILENAME
                return load_historical_data()
        except Exception as e:
            console.print(f"\n[red]Error reading input: {e}. Loading default file.[/red]")
            CURRENT_DATA_FILE = DATA_FILENAME
            return load_historical_data()
    else:
        console.print("[yellow]No existing data file found. Starting fresh.[/yellow]")
        CURRENT_DATA_FILE = DATA_FILENAME
        return []

def welcome_message():
    """Displays a welcome message using Rich Console."""
    console.print("[bold green]------------------------------------[/bold green]")
    console.print("[bold green]Welcome to your Net Worth Tracker![/bold green]")
    console.print("[bold green]------------------------------------[/bold green]")
    console.print("You can load previous data, start fresh, or view historical charts.")
    console.print("Each session is saved with a date, allowing historical tracking.")
    console.print("Default date for new/updated records is always [cyan]today[/cyan].")
    console.print("Assets can be categorised for additional reporting.")
    console.print()
    console.print("[dim]Data is stored in JSON format with each record containing:[/dim]")
    console.print("[dim]- A date (YYYY-MM-DD)[/dim]")
    console.print("[dim]- A list of assets, each with:[/dim]")
    console.print("[dim]  * Name[/dim]")
    console.print("[dim]  * Liquid status (true/false)[/dim]")
    console.print("[dim]  * Balance (currency value)[/dim]")
    console.print("[dim]  * Category (aligns with standard or custom categories)[/dim]")
    console.print()

def display_assets(assets, show_balances=True, show_categories=True):
    """Displays the current list of assets in a Rich Table."""
    table = Table(title=Text("Current Assets", style="bold blue"), show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Asset Name", min_width=20)
    table.add_column("Liquid", justify="center", min_width=8)
    if show_categories:
        table.add_column("Category", min_width=15)
    if show_balances:
        table.add_column("Balance", justify="right", min_width=12)

    if not assets:
        console.print("[yellow]No assets defined yet.[/yellow]")
        return

    for idx, asset in enumerate(assets, 1):
        liquid_status = Text("Yes", style="green") if asset["liquid"] else Text("No", style="red")
        
        if show_categories and show_balances:
            category = asset.get("category", "Other")
            balance_str = f"{asset.get('balance', 0.0):,.2f}"
            table.add_row(str(idx), asset["name"], liquid_status, category, balance_str)
        elif show_categories:
            category = asset.get("category", "Other")
            table.add_row(str(idx), asset["name"], liquid_status, category)
        elif show_balances:
            balance_str = f"{asset.get('balance', 0.0):,.2f}"
            table.add_row(str(idx), asset["name"], liquid_status, balance_str)
        else:
            table.add_row(str(idx), asset["name"], liquid_status)
    
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
        return

    console.print("\n[bold blue]------------------------------------[/bold blue]")
    console.print("[bold blue]Now, let's enter the balances for your assets.[/bold blue]")
    console.print("([italic]Press Enter to keep current balance, 's' to skip an asset, or 'q' to quit.[/italic])")
    console.print("[bold blue]------------------------------------[/bold blue]")

    for asset in assets:
        current_balance = asset.get('balance', 0.0)
        display_assets([asset]) # Show only the current asset being queried
        
        while True:
            prompt_text = f"Enter balance for [cyan]'{asset['name']}'[/cyan] ([green]{current_balance:,.2f}[/green]), 's' to skip, or 'q' to quit: "
            user_input = console.input(prompt_text).strip().lower()

            if user_input == 'q':
                console.print("[yellow]Quitting balance update. Returning to previous menu.[/yellow]")
                return False
            elif user_input == 's':
                console.print(f"[yellow]Skipped '{asset['name']}'. Balance remains {current_balance:,.2f}.[/yellow]\n")
                break # Move to the next asset
            elif not user_input: # User pressed Enter (accept current balance)
                # No change needed, balance is already current_balance
                console.print(f"Balance for '{asset['name']}' kept as [green]{current_balance:,.2f}[/green].\n")
                break # Move to the next asset
            else:
                try:
                    new_balance = float(user_input)
                    asset['balance'] = new_balance
                    console.print(f"Balance for '{asset['name']}' set to [green]{new_balance:,.2f}[/green].\n")
                    break # Move to the next asset
                except ValueError:
                    console.print("[red]Invalid input. Please enter a number, 's' to skip, or 'q' to quit.[/red]")
    
    console.print("[green]Finished updating balances.[/green]")
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
    """Manages the process of defining/editing assets, balances, and date for a session."""
    current_assets = [dict(a) for a in initial_assets] # Deep copy for editing this session
    loaded_record_date_for_editing = initial_date_str
    action_choice = '' # To satisfy logic later if we jump past asset editing
    proceed_to_asset_editing = True # Default to allowing asset editing

    # If we have initial assets (i.e., loaded a record), ask if user wants to edit them or just update balances
    if current_assets:
        console.print(f"Data for the record ([cyan]{loaded_record_date_for_editing or 'New Record'}[/cyan]) with {len(current_assets)} asset(s) is ready for review/update.")
        while True:
            console.print("\nWhat would you like to do with this record?")
            console.print("  [bold yellow]E[/bold yellow]. Add/remove/rename assets or change their liquid status")
            console.print("  [bold cyan]U[/bold cyan]. Update the values/balances of your existing assets")
            console.print("  [bold magenta]C[/bold magenta]. Set categories for your assets (e.g., Pension, ISA, Property)")
            # No 'S'tart fresh here, that's handled by main menu choice 'N'
            console.print("Your choice (e, u, or c): ", end="")
            try:
                action_choice = readchar.readkey().lower()
                console.print(action_choice)
                if action_choice == 'e':
                    proceed_to_asset_editing = True
                    break
                elif action_choice == 'u':
                    proceed_to_asset_editing = False
                    break
                elif action_choice == 'c':
                    category_result = categorize_assets(current_assets, console)
                    if category_result is False:
                        # User wants to go back without saving category changes
                        console.print("[yellow]Returning to main menu without saving category changes.[/yellow]")
                        return all_historical_records
                    continue  # Show the menu again after categorizing
                else:
                    console.print(" [red]Invalid choice. Please press E, U, or C.[/red]")
            except Exception as e_sub:
                console.print(f"\n[red]Error reading input: {e_sub}. Please try again.[/red]")
        
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
            console.print("\n[b]Options:[/b]")
            console.print("• Type an asset name to add a new asset")
            console.print("• Type [cyan]'remove 1'[/cyan] to delete asset number 1")
            console.print("• Type [cyan]'undo'[/cyan] to remove the last added asset")
            console.print("• Type [cyan]'category 2'[/cyan] to set the category for asset number 2")
            console.print("• Type [cyan]'done'[/cyan] when you've finished editing assets")
            console.print("• Type [cyan]'back'[/cyan] or [cyan]'cancel'[/cyan] to return to the previous menu")
            user_input = console.input("[b magenta]Enter command or asset name:[/b magenta] ").strip()
            command = user_input.lower()
            console.print() 

            if command == "done":
                if not current_assets:
                    console.print("[yellow]No assets defined.[/yellow]")
                else:
                    console.print("[green]Finished defining/editing assets.[/green]")
                break
            elif command in ["back", "cancel"]:
                console.print("[yellow]Returning to previous menu without saving changes.[/yellow]")
                return all_historical_records  # Return without making changes
            elif command == "undo":
                if current_assets:
                    removed_asset = current_assets.pop()
                    console.print(f"[yellow]Undid adding '{removed_asset['name']}'.[/yellow]\n")
                else:
                    console.print("[red]No assets to undo.[/red]\n")
            elif command.startswith("remove "):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 2 and parts[0].lower() == "remove":
                    try:
                        index_to_remove = int(parts[1])
                        if 1 <= index_to_remove <= len(current_assets):
                            removed_asset = current_assets.pop(index_to_remove - 1)
                            console.print(f"[yellow]Removed '{removed_asset['name']}'.[/yellow]\n")
                        else:
                            console.print(f"[red]Invalid index.[/red]\n")
                    except ValueError:
                        console.print(f"[red]Invalid index number.[/red]\n")
                else:
                    console.print("[red]Invalid remove command.[/red]\n")
            elif command.startswith("category "):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 2 and parts[0].lower() == "category":
                    try:
                        index_to_categorize = int(parts[1])
                        if 1 <= index_to_categorize <= len(current_assets):
                            set_asset_category(current_assets[index_to_categorize - 1], console)
                        else:
                            console.print(f"[red]Invalid index.[/red]\n")
                    except ValueError:
                        console.print(f"[red]Invalid index number.[/red]\n")
                else:
                    console.print("[red]Invalid category command.[/red]\n")
            elif user_input:
                asset_name = user_input
                while True:
                    console.print(f"Is [cyan]'{asset_name}'[/cyan] a liquid asset? (y/n): ", end="", highlight=False)
                    try:
                        is_liquid_input = readchar.readkey().lower()
                        console.print(is_liquid_input)
                        if is_liquid_input in ['y', 'n']:
                            is_liquid = is_liquid_input == 'y'
                            break
                        else: console.print(" [red]Invalid input.[/red]")
                    except Exception:
                        fallback_input = console.input(" (y/n fallback): ").strip().lower()
                        if fallback_input in ['y', 'n']:
                            is_liquid = fallback_input == 'y'
                            break
                        else: console.print(" [red]Invalid input.[/red]")
                
                # Ask for category
                category = set_asset_category_interactive(asset_name, console)
                
                current_assets.append({"name": asset_name, "liquid": is_liquid, "balance": 0.0, "category": category})
                console.print(f"[green]Asset '{asset_name}' defined with category '{category}'.[/green]\n")
            else: 
                console.print("[yellow]No input.[/yellow]\n")
            if command not in ["done"]: console.print("[dim]----------------[/dim]")

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

        console.print("Enter a date in YYYY-MM-DD format, or press Enter for today's date.")
        console.print("You can also type 'cancel' to return to the main menu without saving.")
        date_prompt = f"Date for this record ([cyan]{todays_date_str}[/cyan]): "
        user_date_input = console.input(date_prompt).strip()
        
        if user_date_input.lower() == 'cancel':
            console.print("[yellow]Cancelled. Returning to main menu without saving.[/yellow]")
            return all_historical_records
        elif user_date_input:
            try:
                datetime.strptime(user_date_input, "%Y-%m-%d")
                final_entry_date = user_date_input
                console.print(f"[green]Date for record set to [cyan]{final_entry_date}[/cyan].[/green]")
            except ValueError:
                console.print(f"[red]Invalid date format for '{user_date_input}'. Using default: [cyan]{todays_date_str}[/cyan].[/red]")
        else:
            console.print(f"[green]Using default date: [cyan]{final_entry_date}[/cyan].[/green]")
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

def main():
    welcome_message()
    all_historical_records = check_existing_data()
    
    while True: # Main menu loop
        console.print("\n[bold underline]Main Menu[/bold underline]")
        console.print("  [bold green]U[/bold green]. Update your net worth record")
        console.print("  [bold cyan]V[/bold cyan]. View available asset categories")
        
        if CHARTING_AVAILABLE:
            console.print("  [bold yellow]C[/bold yellow]. Generate chart: Overview of assets vs debts")
            console.print("  [bold magenta]D[/bold magenta]. Generate chart: Detailed view of all your assets")
            console.print("  [bold cyan]G[/bold cyan]. Generate chart: Assets grouped by category")
            console.print("  [bold white]A[/bold white]. Generate all three chart types at once")
        else:
            console.print("  [dim]Charts not available - matplotlib/pandas missing[/dim]")
            
        console.print("  [bold red]Q[/bold red]. Quit the application")
        console.print("Your choice: ", end="")
        
        try:
            menu_choice = readchar.readkey().lower()
            console.print(menu_choice)
        except Exception as e:
            console.print(f"\n[red]Error reading input: {e}. Please try again.[/red]")
            continue

        if menu_choice == 'u':
            if not all_historical_records:
                console.print("\n[yellow]No historical data found. Starting a new fresh record.[/yellow]")
                all_historical_records = manage_record_session([], None, all_historical_records)
            else:
                latest_record = all_historical_records[0] # Assumes sorted
                # Pass a copy of assets and the date of the latest record
                all_historical_records = manage_record_session(
                    latest_record.get('assets', []), 
                    latest_record.get('date'), 
                    all_historical_records
                )
        elif menu_choice == 'v':
            console.print("\n[green]Viewing categories...[/green]")
            view_categories(console)
            
            # Additional options for when viewing categories
            console.print("\n[bold]Options:[/bold]")
            console.print("  [cyan]Press any key to return to main menu[/cyan]")
            try:
                readchar.readkey()
            except Exception:
                pass
        elif CHARTING_AVAILABLE and menu_choice == 'c':
            console.print("\n[green]Generating summary net worth chart...[/green]")
            chart_utils.generate_charts(all_historical_records, "summary")
        elif CHARTING_AVAILABLE and menu_choice == 'd':
            console.print("\n[green]Generating detailed net worth chart (all assets)...[/green]")
            chart_utils.generate_charts(all_historical_records, "detailed")
        elif CHARTING_AVAILABLE and menu_choice == 'g':
            console.print("\n[green]Generating category-based net worth chart...[/green]")
            chart_utils.generate_charts(all_historical_records, "category")
        elif CHARTING_AVAILABLE and menu_choice == 'a':
            console.print("\n[green]Generating all chart types...[/green]")
            chart_utils.generate_charts(all_historical_records, "all")
        elif menu_choice == 'q':
            console.print("\n[yellow]Exiting application. Goodbye![/yellow]")
            sys.exit()
        else:
            console.print(" [red]Invalid choice. Please select from the menu.[/red]")
        
        console.print("\n[dim]Returning to main menu...[/dim]")

if __name__ == "__main__":
    main() 

# To run this in terminal: python net_worth_tracker.py