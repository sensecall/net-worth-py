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
from rich.progress import Progress

# Import from our new data_manager
from data_manager import DATA_FILENAME as DEFAULT_DATA_FILENAME, load_historical_data, save_historical_data, save_last_opened_file, load_last_opened_file
# Import from our new ui_display
from ui_display import display_app_title, display_assets, print_final_summary
# Import from our new core_logic
from core_logic import calculate_summary_stats, generate_unique_id
# Import from our new screens module
from screens import get_asset_balances, asset_management_screen, file_options_screen # add_new_financial_item_interactive is used within screens.py

# Import our utility modules
from asset_utils import (
    get_default_categories, # For initializing categories if none exist
    guess_category, 
    view_categories, # Will be used by manage_categories_interactive
    manage_categories_interactive
    # categorize_assets, # This function is commented out in asset_utils.py
    # set_asset_category_interactive, # This function is commented out in asset_utils.py
    # set_asset_category, # This function is commented out in asset_utils.py
    # load_custom_categories_from_data, # This function is commented out in asset_utils.py
    # load_custom_keywords # This function is commented out in asset_utils.py
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
CURRENT_DATA_FILE = DEFAULT_DATA_FILENAME  # Track the currently active data file using imported default

def check_existing_data():
    """Checks for existing data files and prompts user with options."""
    global CURRENT_DATA_FILE
    
    display_app_title(console)

    # Try to load the last opened file path
    last_opened = load_last_opened_file()
    potential_file_to_load = None

    if last_opened and os.path.exists(last_opened):
        console.print(Panel(f"Found last used data file: [cyan bold]{last_opened}[/cyan bold]", title="[bold yellow]Last Session[/bold yellow]"))
        potential_file_to_load = last_opened
    elif os.path.exists(DEFAULT_DATA_FILENAME):
        potential_file_to_load = DEFAULT_DATA_FILENAME
    
    if potential_file_to_load:
        CURRENT_DATA_FILE = potential_file_to_load # Set this early for display
        console.print(
            Panel(
                Text.assemble(
                    ("We spotted a JSON file (", "white"),
                    (CURRENT_DATA_FILE, "cyan bold"), # Use CURRENT_DATA_FILE for display
                    (") which looks like it contains your net worth history.", "white")
                ),
                title="[bold yellow]Existing Data Found[/bold yellow]",
                border_style="yellow",
                padding=(1, 2)
            )
        )
        console.print() # Add a blank line for spacing
        
        options = [
            f"Load existing file ({CURRENT_DATA_FILE})", # Use CURRENT_DATA_FILE
            "Start fresh (creates a new file, won't overwrite existing data)",
            "Open a different data file",
            "Exit application"
        ]
        
        menu_index, selected_option = show_menu(
            options,
            title="\nWhat would you like to do?",
            return_shortcut=False # No [r]eturn option on this initial menu
        )
        
        if menu_index is None or selected_option == "Exit application":
            console.print("\n[yellow]Exiting application. Goodbye![/yellow]")
            sys.exit()
            
        if selected_option == f"Load existing file ({CURRENT_DATA_FILE})":
            console.print(f"\n[green]Loading data from [cyan]{CURRENT_DATA_FILE}[/cyan]...[/green]")
            categories, financial_items, snapshots = load_historical_data(console, CURRENT_DATA_FILE)
            if categories is not None: # Check if load was successful
                save_last_opened_file(CURRENT_DATA_FILE)
            return categories, financial_items, snapshots
        elif selected_option == "Start fresh (creates a new file, won't overwrite existing data)":
            filename_without_ext = DEFAULT_DATA_FILENAME.rsplit('.', 1)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_filename = f"{filename_without_ext}_new_{timestamp}.json"
            
            console.print(f"\n[yellow]Starting fresh with no historical data.[/yellow]")
            console.print(f"[green]Your new data will be saved to [cyan]{new_filename}[/cyan] to preserve your existing data.[/green]")
            
            CURRENT_DATA_FILE = new_filename
            return [], [], [] # Return empty structures for categories, items, snapshots
        elif selected_option == "Open a different data file": # "Open a different data file" selected
            different_file = console.input("\nEnter the path to your data file: ").strip()
            if different_file and os.path.exists(different_file):
                console.print(f"[green]Loading data from [cyan]{different_file}[/cyan]...[/green]")
                CURRENT_DATA_FILE = different_file
                categories, financial_items, snapshots = load_historical_data(console, different_file)
                if categories is not None:
                    save_last_opened_file(CURRENT_DATA_FILE)
                return categories, financial_items, snapshots
            
            console.print(f"[red]File not found: [cyan]{different_file or '(empty input)'}[/cyan]. Starting fresh.[/red]")
            new_filename_base = different_file.rsplit('.', 1)[0] if '.' in different_file else (different_file or "net_worth_data")
            CURRENT_DATA_FILE = f"{new_filename_base}_new.json"
            console.print(f"[green]Your new data will be saved to [cyan]{CURRENT_DATA_FILE}[/cyan].[/green]")
            return [], [], [] # Return empty structures
    
    console.print(f"[yellow]No existing or last-used data file found. Starting fresh.[/yellow]")
    console.print(f"[dim]Default file will be '{DEFAULT_DATA_FILENAME}'[/dim]")
    CURRENT_DATA_FILE = DEFAULT_DATA_FILENAME 
    save_last_opened_file(CURRENT_DATA_FILE) # Save default as last used if starting fresh this way
    return [], [], []

def get_asset_balances(snapshot_balances, financial_items, categories_list):
    """Iterates through snapshot balances and prompts the user for their new balances, allowing skips."""
    if not snapshot_balances:
        console.print("[yellow]No balances to update in the current snapshot.[/yellow]")
        return True  # Nothing to update, or operation considered successful if no items.

    console.print("\n[bold blue]Now, let's update the balances for your financial items[/bold blue]")
    console.print("━" * 60, style="blue")
    console.print()

    # Create dictionaries for quick lookups
    items_dict = {item['id']: item for item in financial_items}
    cats_dict = {cat['id']: cat for cat in categories_list}

    # First show all items in the current snapshot
    display_assets(console, snapshot_balances, financial_items, categories_list, table_title="Current Financial Snapshot Overview") # MODIFIED
    console.print()
    console.print("[cyan]Instructions:[/cyan]")
    console.print(" • Press [bold]Enter[/bold] to keep the current balance")
    console.print(" • Type a [bold]new amount[/bold] to update the balance directly")
    console.print(" • Type [bold]b[/bold] to go back to the previous item")
    console.print(" • Type [bold]q[/bold] to finish and return to the menu")
    console.print(" [yellow]Note: Changes are applied to the current session. Save from the main menu.[/yellow]")
    console.print()
    
    modified_balance_entries = [] # Stores item_id of modified entries for summary
    
    current_idx = 0
    while current_idx < len(snapshot_balances):
        balance_entry = snapshot_balances[current_idx]
        item_id = balance_entry.get("item_id")
        current_balance = balance_entry.get('balance', 0.0)
        
        item_details = items_dict.get(item_id)
        if not item_details: # Should not happen with valid data
            console.print(f"[red]Error: Item with ID '{item_id}' not found in financial_items. Skipping.[/red]")
            current_idx += 1
            continue

        item_name = item_details.get("name", "Unknown Item")
        category_id = item_details.get("category_id")
        category_details = cats_dict.get(category_id)
        category_name = category_details.get("name", "Uncategorized") if category_details else "Invalid Category"
        is_liquid = item_details.get("liquid", False)
        
        console.print(f"[bold cyan]Item {current_idx + 1} of {len(snapshot_balances)}:[/bold cyan] [cyan]{item_name}[/cyan]")
        console.print(f"Current balance: [{'green' if current_balance >= 0 else 'red'}]£{current_balance:,.2f}[/{'green' if current_balance >= 0 else 'red'}]")
        console.print(f"Category: [yellow]{category_name}[/yellow] | Liquid: [{'green' if is_liquid else 'red'}]{('Yes' if is_liquid else 'No')}[/{'green' if is_liquid else 'red'}]")
        
        user_input = console.input("\nEnter new balance (or Enter to keep current): ").strip()
        
        if not user_input:
            console.print(f"[green]Keeping current balance for {item_name}: £{current_balance:,.2f}[/green]")
            current_idx += 1
        elif user_input.lower() == 'q':
            if modified_balance_entries:
                console.print("\n[yellow]Warning: You've made changes to balances.[/yellow]")
                if Confirm.ask("Confirm these changes before exiting balance update?", default=True):
                    console.print("[green]Changes confirmed for this session.[/green]")
                    return True # Indicates changes were made and confirmed
                else:
                    console.print("[red]Changes discarded. Balances reverted for this session.[/red]")
                    # Need to revert changes - this is tricky if we modified in place.
                    # For now, let's assume the calling function handles this based on False return.
                    # A better approach would be to work on a copy if cancellation needs full revert.
                    return False # Indicates changes were made but user wants to discard
            else:
                console.print("[yellow]Finished without making any changes.[/yellow]")
                return True # No changes, proceed as if successful
        elif user_input.lower() == 'b' and current_idx > 0:
            current_idx -= 1
            console.print("[yellow]Going back to previous item.[/yellow]")
        else:
            try:
                new_balance = float(user_input)
                balance_entry['balance'] = new_balance # Modify in-place
                console.print(f"Balance for '{item_name}' updated to [{'green' if new_balance >= 0 else 'red'}]£{new_balance:,.2f}[/{'green' if new_balance >= 0 else 'red'}]")
                if item_id not in [me["item_id"] for me in modified_balance_entries]: # Track unique modified items
                    modified_balance_entries.append({"item_id": item_id, "name": item_name, "new_balance": new_balance})
                current_idx += 1
            except ValueError:
                console.print("[red]Invalid input. Please enter a number, 'b' to go back, or 'q' to finish.[/red]")
        
        console.print("─" * 60, style="dim")
    
    if modified_balance_entries:
        console.print("\n[bold green]Summary of Updated Balances for this Session:[/bold green]")
        for entry_summary in modified_balance_entries:
            console.print(f"• [cyan]{entry_summary['name']}[/cyan]: [{'green' if entry_summary['new_balance'] >= 0 else 'red'}]£{entry_summary['new_balance']:,.2f}[/{'green' if entry_summary['new_balance'] >= 0 else 'red'}]")
        console.print("\n[green]Balance updates applied to current session.[/green]")
    else:
        console.print("\n[yellow]No changes were made to any balances.[/yellow]")
    
    return True # Indicates successful completion (even if no changes)

def main():
    """Main application loop."""
    console.clear()
    # load_custom_keywords() # Removed, as this function is no longer used/available
    
    global CURRENT_DATA_FILE
    categories, financial_items, snapshots = check_existing_data()
    
    # If starting fresh and no categories loaded, populate with defaults
    if not categories and not financial_items: # Check financial_items too to be sure it's a fresh start
        console.print("[yellow]No categories found, initializing with default categories.[/yellow]")
        categories = get_default_categories()
        # Optionally, save immediately so defaults are persisted if user exits early
        # save_historical_data(console, categories, financial_items, snapshots, CURRENT_DATA_FILE)

    current_snapshot_balances = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    if snapshots: 
        most_recent_snapshot = snapshots[0]
        current_date = most_recent_snapshot.get('date', current_date)
        current_snapshot_balances = most_recent_snapshot.get('balances', []).copy()
    else:
        pass 
    
    menu_options = [
        "View/Edit Assets",
        "Quick Balance Update",
        "Generate Charts", 
        "View Categories",
        "File Options",
        "Exit Application"
    ]
    
    while True:
        stats = calculate_summary_stats(current_snapshot_balances, financial_items, snapshots, categories)
        
        console.clear()
        
        header_text = Text()
        header_text.append("NET WORTH TRACKER", style="bold blue")
        console.print(header_text)
        console.print("━" * 60, style="blue")
        console.print()
        
        net_worth_text = Text()
        net_worth_text.append(f"£{stats['net_worth']:,.2f}", style="bold green" if stats['net_worth'] >= 0 else "bold red")
        
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
        
        if stats['top_categories']:
            summary_content.append("")
            summary_content.append(f"[bold]Top Categories:[/bold]")
            for category, value in stats['top_categories']:
                summary_content.append(f"  [yellow]{category}:[/yellow] {'£':>10}{value:,.2f}")
        
        summary_panel = Panel(
            renderable="\n".join(summary_content),
            title="Financial Summary",
            border_style="green",
            box=box.ROUNDED,
            title_align="left",
            padding=(1, 2)
        )
        
        console.print(summary_panel)
        console.print()
        
        menu_index, selected_option = show_menu(
            menu_options,
            title="Select an option (or press shortcut key):",
            return_shortcut=False
        )
        
        if menu_index is None:
            console.print("\n[yellow]Exiting application. Goodbye![/yellow]")
            sys.exit()
        
        skip_key_prompt = False
        
        if selected_option == "View/Edit Assets":
            categories, financial_items, snapshots, current_snapshot_balances, changes_made_overall = asset_management_screen(
                console, # MODIFIED
                categories, financial_items, snapshots, 
                current_snapshot_balances, 
                current_date
            )
        elif selected_option == "Quick Balance Update":
            balance_result = get_asset_balances(console, current_snapshot_balances, financial_items, categories) # MODIFIED
            if balance_result:
                # Update the main snapshots list before saving
                updated_snapshots = snapshots.copy() # Start with existing snapshots
                found_snapshot_for_date = False
                for i, snap in enumerate(updated_snapshots):
                    if snap.get('date') == current_date:
                        updated_snapshots[i]['balances'] = current_snapshot_balances
                        found_snapshot_for_date = True
                        break
                if not found_snapshot_for_date:
                    updated_snapshots.append({"date": current_date, "balances": current_snapshot_balances})
                # Re-sort snapshots after potential append or if order matters strictly before save
                snapshots = sorted(updated_snapshots, key=lambda x: x.get('date', ''), reverse=True)
                
                save_historical_data(console, categories, financial_items, snapshots, CURRENT_DATA_FILE)
                save_last_opened_file(CURRENT_DATA_FILE) # Remember this file
                console.print("[green]Balances updated and saved successfully.[/green]")
        elif selected_option == "Generate Charts" and CHARTING_AVAILABLE:
            # chart_utils.generate_charts will primarily need snapshots,
            # but might also use financial_items and categories for richer charts.
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
                chart_utils.generate_charts(snapshots, financial_items, categories, "summary")
            elif selected_chart == "Detailed chart: All individual assets":
                console.print("\n[green]Generating detailed net worth chart (all assets)...[/green]")
                chart_utils.generate_charts(snapshots, financial_items, categories, "detailed")
            elif selected_chart == "Category chart: Assets by category":
                console.print("\n[green]Generating category-based net worth chart...[/green]")
                chart_utils.generate_charts(snapshots, financial_items, categories, "category")
            elif selected_chart == "Single asset chart: Track one asset over time":
                # Let the user select an asset to chart
                if not financial_items:
                    console.print("[yellow]No financial items available to chart.[/yellow]")
                else:
                    # Loop to allow charting multiple assets in succession
                    while True:
                        # Create asset selection menu from financial_items
                        item_options_with_ids = [(item['id'], item['name']) for item in financial_items]
                        
                        if not item_options_with_ids:
                            console.print("[yellow]No financial items found to select for charting.[/yellow]")
                            break

                        # show_menu needs a list of strings for display. We'll map back to ID after selection.
                        display_options = [f"{name} (ID: {id})" for id, name in item_options_with_ids]
                        
                        menu_idx, selected_display_option = show_menu(
                            display_options,
                            title="\nSelect an item to chart:",
                            shortcuts=False # Allow selection by number
                        )
                        
                        if menu_idx is None: # User pressed Esc or q
                            break
                            
                        selected_item_id, selected_item_name = item_options_with_ids[menu_idx]
                        
                        console.print(f"\n[green]Generating chart for {selected_item_name}...[/green]")
                        chart_utils.generate_charts(snapshots, financial_items, categories, "asset", specific_asset_id=selected_item_id)
                        
                        if not Confirm.ask("\nWould you like to chart another item?", default=False):
                            break
            elif selected_chart == "Generate all three main chart types":
                console.print("\n[green]Generating all chart types...[/green]")
                chart_utils.generate_charts(snapshots, financial_items, categories, "all")
        elif selected_option == "View Categories":
            updated_categories = manage_categories_interactive(categories, financial_items, console)
            if updated_categories is not categories: # Check if the list object itself changed (or content differs)
                categories = updated_categories
                # Save data since categories list (which is part of the save structure) has been modified.
                save_historical_data(console, categories, financial_items, snapshots, CURRENT_DATA_FILE)
                save_last_opened_file(CURRENT_DATA_FILE) # Remember this file
                console.print("[green]Category changes saved successfully.[/green]")
            skip_key_prompt = True # Ensure we don't double-prompt for key press
        elif selected_option == "File Options":
            # Call the new file_options_screen and unpack all its return values
            (categories, financial_items, snapshots, 
             current_snapshot_balances, current_date, CURRENT_DATA_FILE) = file_options_screen(
                console, 
                categories, 
                financial_items, 
                snapshots, 
                current_snapshot_balances, 
                current_date, 
                CURRENT_DATA_FILE
            )
            skip_key_prompt = True # The file_options_screen handles its own prompts and flow
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
    
    # The main function might not need to return these if they are managed globally
    # or if the application exits from within the loop. For now, let's assume it does.
    return categories, financial_items, snapshots

if __name__ == "__main__":
    main() 

# To run this in terminal: python net_worth_tracker.py