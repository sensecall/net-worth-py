from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich.prompt import Confirm, Prompt
from rich import box
import readchar
import collections # For collections.abc.Iterable
from datetime import datetime
from rich.panel import Panel

# Functions from other new modules
from ui_display import display_assets
from core_logic import generate_unique_id
from asset_utils import guess_category, view_categories, manage_categories_interactive
from menu_utils import show_menu

def get_asset_balances(console: Console, snapshot_balances: collections.abc.Iterable, financial_items: collections.abc.Iterable, categories_list: collections.abc.Iterable):
    """Iterates through snapshot balances and prompts the user for their new balances, allowing skips."""
    if not snapshot_balances:
        console.print("[yellow]No balances to update in the current snapshot.[/yellow]")
        return True

    console.print("\n[bold blue]Now, let's update the balances for your financial items[/bold blue]")
    console.print("━" * 60, style="blue")
    console.print()

    items_dict = {item['id']: item for item in financial_items}
    cats_dict = {cat['id']: cat for cat in categories_list}

    display_assets(console, snapshot_balances, financial_items, categories_list, table_title="Current Financial Snapshot Overview")
    console.print()
    console.print("[cyan]Instructions:[/cyan]")
    console.print(" • Press [bold]Enter[/bold] to keep the current balance")
    console.print(" • Type a [bold]new amount[/bold] to update the balance directly")
    console.print(" • Type [bold]b[/bold] to go back to the previous item")
    console.print(" • Type [bold]q[/bold] to finish and return to the menu")
    console.print(" [yellow]Note: Changes are applied to the current session. Save from the main menu.[/yellow]")
    console.print()
    
    modified_balance_entries = []
    
    current_idx = 0
    # Ensure snapshot_balances is a list for indexing
    snapshot_balances_list = list(snapshot_balances) 

    while current_idx < len(snapshot_balances_list):
        balance_entry = snapshot_balances_list[current_idx]
        item_id = balance_entry.get("item_id")
        current_balance = balance_entry.get('balance', 0.0)
        
        item_details = items_dict.get(item_id)
        if not item_details:
            console.print(f"[red]Error: Item with ID '{item_id}' not found in financial_items. Skipping.[/red]")
            current_idx += 1
            continue

        item_name = item_details.get("name", "Unknown Item")
        category_id = item_details.get("category_id")
        category_details = cats_dict.get(category_id)
        category_name = category_details.get("name", "Uncategorized") if category_details else "Invalid Category"
        is_liquid = item_details.get("liquid", False)
        
        console.print(f"[bold cyan]Item {current_idx + 1} of {len(snapshot_balances_list)}:[/bold cyan] [cyan]{item_name}[/cyan]")
        console.print(f"Current balance: [{'green' if current_balance >= 0 else 'red'}]£{current_balance:,.2f}[/{'green' if current_balance >= 0 else 'red'}]")
        console.print(f"Category: [yellow]{category_name}[/yellow] | Liquid: [{'green' if is_liquid else 'red'}]{('Yes' if is_liquid else 'No')}[/{'green' if is_liquid else 'red'}]")
        
        user_input = console.input("\nEnter new balance (or Enter to keep current): ").strip()
        
        if not user_input:
            console.print(f"[green]Keeping current balance for {item_name}: £{current_balance:,.2f}[/green]")
            current_idx += 1
        elif user_input.lower() == 'q':
            if modified_balance_entries:
                console.print("\n[yellow]Warning: You've made changes to balances.[/yellow]")
                if Confirm.ask("Confirm these changes before exiting balance update?", console=console, default=True):
                    console.print("[green]Changes confirmed for this session.[/green]")
                    return True
                else:
                    console.print("[red]Changes discarded. Balances reverted for this session.[/red]")
                    return False 
            else:
                console.print("[yellow]Finished without making any changes.[/yellow]")
                return True
        elif user_input.lower() == 'b' and current_idx > 0:
            current_idx -= 1
            console.print("[yellow]Going back to previous item.[/yellow]")
        else:
            try:
                new_balance = float(user_input)
                balance_entry['balance'] = new_balance
                console.print(f"Balance for '{item_name}' updated to [{'green' if new_balance >= 0 else 'red'}]£{new_balance:,.2f}[/{'green' if new_balance >= 0 else 'red'}]")
                if item_id not in [me["item_id"] for me in modified_balance_entries]:
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
    
    return True

def add_new_financial_item_interactive(console_instance: Console, financial_items_list: list, categories_list: list, current_snapshot_balances: list, current_date: str) -> tuple[list, list, bool]:
    """
    Interactively adds a new financial item (asset or liability).
    Modifies financial_items_list, categories_list (if new category), and current_snapshot_balances.
    Returns tuple: (updated_categories_list, updated_financial_items_list, item_added_bool).
    """
    console_instance.print("\n[bold blue]Adding a New Financial Item[/bold blue]")

    while True:
        name = console_instance.input("Enter the name for the new financial item: ").strip()
        if not name:
            console_instance.print("[red]Item name cannot be empty.[/red]")
            continue
        if any(item.get('name', '').lower() == name.lower() for item in financial_items_list):
            console_instance.print(f"[red]An item with the name '{name}' already exists. Please use a unique name.[/red]")
        else:
            break

    while True:
        item_type_str = console_instance.input("Is this an 'asset' or a 'liability'? ").strip().lower()
        if item_type_str in ["asset", "liability"]:
            break
        console_instance.print("[red]Invalid type. Please enter 'asset' or 'liability'.[/red]")

    is_liquid = Confirm.ask("Is this item liquid (e.g., cash, easily convertible to cash)?", console=console_instance, default=True)

    console_instance.print("\n[bold]Select or Create a Category:[/bold]")
    
    guessed_category_id = guess_category(name, categories_list)
    guessed_cat_obj = None
    if guessed_category_id:
        guessed_cat_obj = next((cat for cat in categories_list if cat['id'] == guessed_category_id), None)
        if guessed_cat_obj:
            console_instance.print(f"Suggested category based on name: [green]'{guessed_cat_obj['name']}'[/green] (ID: {guessed_category_id})")
        else: 
            console_instance.print(f"[yellow]Suggested category ID {guessed_category_id} not found in list. This is an error.[/yellow]")
            guessed_category_id = None 
    else:
        console_instance.print("[yellow]Could not automatically suggest a category based on keywords.[/yellow]")

    view_categories(categories_list, console_instance) 

    chosen_category_id = None
    while True:
        prompt_text = "Enter existing category ID"
        if guessed_category_id and guessed_cat_obj:
            prompt_text += f" (or press Enter to accept suggestion: '{guessed_cat_obj['name']}')"
        prompt_text += ", or type a new category name: "
        
        cat_choice = Prompt.ask(prompt_text, console=console_instance).strip()

        if not cat_choice and guessed_category_id: 
            chosen_category_id = guessed_category_id
            selected_cat_name = guessed_cat_obj['name'] if guessed_cat_obj else "Unknown (Error)"
            console_instance.print(f"Accepted suggested category: '{selected_cat_name}' (ID: {chosen_category_id})")
            break
        
        if not cat_choice: # Handles both cases: no suggestion, or suggestion ignored and empty input
             console_instance.print("[red]Category choice cannot be empty if no suggestion is available/accepted.[/red]")
             continue

        selected_cat_by_id = next((cat for cat in categories_list if cat.get('id') == cat_choice), None)
        if selected_cat_by_id:
            chosen_category_id = selected_cat_by_id['id']
            console_instance.print(f"Selected category by ID: '{selected_cat_by_id['name']}'")
            break
        
        new_category_name_potential = cat_choice
        existing_cat_by_name = next((cat for cat in categories_list if cat.get('name','').lower() == new_category_name_potential.lower()), None)
        
        if existing_cat_by_name:
            if Confirm.ask(f"A category named '{existing_cat_by_name['name']}' (ID: {existing_cat_by_name['id']}) already exists. Use this one?", console=console_instance):
                chosen_category_id = existing_cat_by_name['id']
                console_instance.print(f"Selected existing category: '{existing_cat_by_name['name']}'")
                break
            else:
                console_instance.print("Please try a different name for your new category or select an existing ID.")
                view_categories(categories_list, console_instance) 
                continue 
        else: 
            if Confirm.ask(f"Create a new category named '{new_category_name_potential}'?", console=console_instance):
                keywords_str = Prompt.ask(f"Enter keywords for '{new_category_name_potential}' (comma-separated)", default="", console=console_instance)
                new_keywords = sorted(list(set(k.strip().lower() for k in keywords_str.split(',') if k.strip())))
                
                new_cat_id_val = generate_unique_id([cat['id'] for cat in categories_list])
                categories_list.append({'id': new_cat_id_val, 'name': new_category_name_potential, 'keywords': new_keywords})
                chosen_category_id = new_cat_id_val
                console_instance.print(f"New category '{new_category_name_potential}' created with ID {chosen_category_id} and keywords: {', '.join(new_keywords) or 'None'}.")
                break
            else:
                view_categories(categories_list, console_instance) 
                continue
    
    while True:
        try:
            balance_str = console_instance.input(f"Enter the initial balance for '{name}' on {current_date}: £").strip()
            initial_balance = float(balance_str)
            break
        except ValueError:
            console_instance.print("[red]Invalid balance. Please enter a numeric value.[/red]")

    new_item_id = generate_unique_id([item['id'] for item in financial_items_list])

    new_item = {
        'id': new_item_id,
        'name': name,
        'category_id': chosen_category_id,
        'liquid': is_liquid,
        'type': item_type_str 
    }
    financial_items_list.append(new_item)

    # Ensure current_snapshot_balances is a list before appending
    if not isinstance(current_snapshot_balances, list):
        current_snapshot_balances = list(current_snapshot_balances) # Convert if it's some other iterable

    current_snapshot_balances.append({
        'item_id': new_item_id,
        'balance': initial_balance
    })

    console_instance.print(f"\n[green]Financial item '{name}' added successfully with ID {new_item_id} and initial balance £{initial_balance:.2f}.[/green]")
    return categories_list, financial_items_list, True

def manage_financial_item_interactive(
    console: Console, 
    item_id_to_manage: str, 
    current_date: str, 
    financial_items: list, 
    categories: list, 
    snapshots: list, 
    current_snapshot_balances: list
) -> tuple[list, list, list, list, bool]:
    """
    Manages a single financial item's properties and its balance for the current date.
    Returns: Tuple of (financial_items, categories, snapshots, current_snapshot_balances, changes_made_bool)
    """
    changes_made = False

    item_idx = next((i for i, item in enumerate(financial_items) if item['id'] == item_id_to_manage), -1)
    if item_idx == -1:
        console.print(f"[red]Error: Financial item with ID '{item_id_to_manage}' not found.[/red]")
        return financial_items, categories, snapshots, current_snapshot_balances, False
    
    item_details = financial_items[item_idx] # This is a reference, direct modifications will update the list

    balance_entry_idx = next((i for i, entry in enumerate(current_snapshot_balances) if entry['item_id'] == item_id_to_manage), -1)
    balance_entry = current_snapshot_balances[balance_entry_idx] if balance_entry_idx != -1 else None

    if not balance_entry:
        # If no balance entry for this item on this date, create one to manage
        current_snapshot_balances.append({'item_id': item_id_to_manage, 'balance': 0.0})
        balance_entry_idx = len(current_snapshot_balances) - 1
        balance_entry = current_snapshot_balances[balance_entry_idx]
        console.print(f"[yellow]No balance entry found for '{item_details['name']}' on {current_date}. Initializing with £0.00.[/yellow]")
        changes_made = True # Adding a balance entry is a change

    while True:
        console.clear()
        # Refresh details in case of rename
        item_name_display = item_details['name']
        item_type_display = item_details['type']
        item_liquid_display = item_details['liquid']
        
        category_details = next((cat for cat in categories if cat['id'] == item_details['category_id']), None)
        category_name_display = category_details['name'] if category_details else "Uncategorized"
        
        current_balance_display = balance_entry['balance']

        console.print(f"\n[bold underline]Managing: {item_name_display}[/bold underline] (ID: {item_id_to_manage})")
        console.print(f"Type: [cyan]{item_type_display.capitalize()}[/cyan]")
        console.print(f"Balance for {current_date}: [{'green' if current_balance_display >= 0 else 'red'}]£{current_balance_display:,.2f}[/{'green' if current_balance_display >= 0 else 'red'}]")
        console.print(f"Category: [yellow]{category_name_display}[/yellow] (ID: {item_details['category_id']})")
        console.print(f"Liquidity: [{'green' if item_liquid_display else 'red'}]{('Yes' if item_liquid_display else 'No')}[/{'green' if item_liquid_display else 'red'}]")
        
        menu_options = [
            "Update Balance for Current Date",
            "Edit Item Name",
            "Change Category",
            "Toggle Liquidity",
            "Toggle Item Type (Asset/Liability)",
            "Delete Financial Item (Globally!)",
        ]
        item_action_idx, choice_str = show_menu(menu_options, "Select an action:")

        if item_action_idx is None: # Handles Esc, q, or selecting '[r] Return to previous menu'
            break

        if choice_str == "Update Balance for Current Date":
            new_balance_str = Prompt.ask(
                f"Enter new balance for '{item_name_display}' on {current_date}", 
                default=str(current_balance_display), 
                console=console
            ).strip()
            try:
                new_balance = float(new_balance_str)
                if balance_entry['balance'] != new_balance:
                    balance_entry['balance'] = new_balance
                    console.print(f"[green]Balance updated to £{new_balance:,.2f}[/green]")
                    changes_made = True
                else:
                    console.print("[yellow]Balance unchanged.[/yellow]")
            except ValueError:
                console.print("[red]Invalid balance. Please enter a numeric value.[/red]")

        elif choice_str == "Edit Item Name":
            new_name = Prompt.ask("Enter new name", default=item_details['name'], console=console).strip()
            if not new_name:
                console.print("[red]Name cannot be empty.[/red]")
            elif any(item['name'].lower() == new_name.lower() and item['id'] != item_id_to_manage for item in financial_items):
                console.print(f"[red]An item named '{new_name}' already exists.[/red]")
            elif item_details['name'] != new_name:
                item_details['name'] = new_name
                console.print(f"[green]Item name updated to '{new_name}'.[/green]")
                changes_made = True
            else:
                console.print("[yellow]Name unchanged.[/yellow]")

        elif choice_str == "Change Category":
            console.print("\n[bold]Changing Category[/bold]")
            view_categories(categories, console)
            
            current_category_id = item_details['category_id']
            current_category_details = next((cat for cat in categories if cat['id'] == current_category_id), None)
            current_category_name = current_category_details['name'] if current_category_details else "None"
            console.print(f"Current category for '{item_details['name']}': [yellow]{current_category_name}[/yellow] (ID: {current_category_id})")

            chosen_category_id = None
            while True:
                cat_choice = Prompt.ask(
                    "Enter existing category ID to switch to, or type a new category name to create one",
                    console=console
                ).strip()

                if not cat_choice:
                    console.print("[yellow]No change made. Category remains '{current_category_name}'.[/yellow]")
                    break 

                selected_cat_by_id = next((cat for cat in categories if cat.get('id') == cat_choice), None)
                if selected_cat_by_id:
                    if selected_cat_by_id['id'] == current_category_id:
                        console.print(f"[yellow]Item is already in category '{selected_cat_by_id['name']}'. No change made.[/yellow]")
                        chosen_category_id = None # Ensure no change is processed
                        break
                    
                    if Confirm.ask(f"Change category to '{selected_cat_by_id['name']}' (ID: {selected_cat_by_id['id']})?", console=console):
                        chosen_category_id = selected_cat_by_id['id']
                        item_details['category_id'] = chosen_category_id
                        changes_made = True
                        console.print(f"[green]Category changed to '{selected_cat_by_id['name']}'.[/green]")
                    else:
                        console.print("[yellow]Category change cancelled.[/yellow]")
                    break
                
                # If not an ID, treat as a new category name or existing name
                new_category_name_potential = cat_choice
                existing_cat_by_name = next((cat for cat in categories if cat.get('name','').lower() == new_category_name_potential.lower()), None)
                
                if existing_cat_by_name:
                    if existing_cat_by_name['id'] == current_category_id:
                         console.print(f"[yellow]Item is already in category '{existing_cat_by_name['name']}'. No change made.[/yellow]")
                         chosen_category_id = None
                         break
                    if Confirm.ask(f"A category named '{existing_cat_by_name['name']}' (ID: {existing_cat_by_name['id']}) already exists. Use this one?", console=console):
                        chosen_category_id = existing_cat_by_name['id']
                        item_details['category_id'] = chosen_category_id
                        changes_made = True
                        console.print(f"[green]Category changed to '{existing_cat_by_name['name']}'.[/green]")
                        break
                    else:
                        console.print("Please try a different name for your new category or select an existing ID.")
                        view_categories(categories, console)
                        continue
                else: 
                    if Confirm.ask(f"Create a new category named '{new_category_name_potential}'?", console=console):
                        keywords_str = Prompt.ask(f"Enter keywords for '{new_category_name_potential}' (comma-separated)", default="", console=console)
                        new_keywords = sorted(list(set(k.strip().lower() for k in keywords_str.split(',') if k.strip())))
                        
                        new_cat_id_val = generate_unique_id([cat['id'] for cat in categories])
                        categories.append({'id': new_cat_id_val, 'name': new_category_name_potential, 'keywords': new_keywords})
                        chosen_category_id = new_cat_id_val
                        item_details['category_id'] = chosen_category_id
                        changes_made = True
                        console.print(f"[green]New category '{new_category_name_potential}' created and item assigned to it.[/green]")
                        break
                    else:
                        console.print("[yellow]New category creation cancelled.[/yellow]")
                        view_categories(categories, console)
                        continue
            # End of while True for category choice

        elif choice_str == "Toggle Liquidity":
            item_details['liquid'] = not item_details['liquid']
            console.print(f"[green]Liquidity toggled to: {'Yes' if item_details['liquid'] else 'No'}[/green]")
            changes_made = True
        
        elif choice_str == "Toggle Item Type (Asset/Liability)":
            current_type = item_details['type']
            new_type = "liability" if current_type == "asset" else "asset"
            if Confirm.ask(f"Change item type from '{current_type}' to '{new_type}'?", console=console):
                item_details['type'] = new_type
                console.print(f"[green]Item type changed to '{new_type}'.[/green]")
                changes_made = True
            else:
                console.print("[yellow]Item type unchanged.[/yellow]")

        elif choice_str == "Delete Financial Item (Globally!)":
            item_name_to_delete = item_details['name'] # Get name before potential deletion
            if Confirm.ask(f"[bold red]Are you sure you want to permanently delete '{item_name_to_delete}'? This will remove it and all its historical balance entries. This action cannot be undone.[/bold red]", console=console, default=False):
                
                # 1. Remove from financial_items list
                # item_idx is already known and points to the correct item in financial_items
                deleted_item_id = financial_items.pop(item_idx)['id']

                # 2. Remove from current_snapshot_balances
                # balance_entry_idx might be for an older item if list was modified by adding before deleting, so re-find
                balance_entry_idx_current = next((i for i, entry in enumerate(current_snapshot_balances) if entry['item_id'] == deleted_item_id), -1)
                if balance_entry_idx_current != -1:
                    current_snapshot_balances.pop(balance_entry_idx_current)

                # 3. Remove from ALL snapshots in the main snapshots list
                for snapshot in snapshots:
                    snapshot['balances'] = [bal for bal in snapshot.get('balances', []) if bal.get('item_id') != deleted_item_id]
                
                changes_made = True
                console.print(f"[green]Financial item '{item_name_to_delete}' (ID: {deleted_item_id}) and all its associated data have been deleted.[/green]")
                # 4. Return immediately as item_id_to_manage is no longer valid.
                return financial_items, categories, snapshots, current_snapshot_balances, True
            else:
                console.print(f"[yellow]Deletion of '{item_name_to_delete}' cancelled.[/yellow]")
        
        # Use choice_str for the pause condition. If item_action_idx was None, choice_str is "", so this won't run.
        if choice_str and choice_str not in ["Change Category", "Delete Financial Item (Globally!)"]: 
            Prompt.ask("\nPress Enter to continue...", default="", show_default=False, console=console)

    return financial_items, categories, snapshots, current_snapshot_balances, changes_made

def view_historical_snapshots_table(console: Console, snapshots: list, financial_items: list, categories: list):
    """
    Displays a pivot table with 'Date' fixed left. Other columns (items, TNW, Change)
    have uniform width and scroll horizontally. Headers wrap & truncate.
    """
    if not snapshots:
        console.print("[yellow]No historical data to display.[/yellow]")
        console.print("\n[dim]Press Enter to return...[/dim]")
        readchar.readkey()
        return

    items_dict = {item['id']: item for item in financial_items}
    date_col_name = "Date"
    tnw_col_name = "Total Net Worth"
    change_col_name = "Change" # Change in TNW
    
    # Get all unique financial item names, sorted, to be used as columns
    # Ensure we only pick items that actually appear in snapshots to avoid empty columns,
    # or list all known financial_items. For now, list all known, sorted by name.
    item_names_as_cols = sorted(list(set(item['name'] for item in financial_items)))

    if not item_names_as_cols:
        console.print("[yellow]No financial items found to display as columns.[/yellow]")
        console.print("\n[dim]Press Enter to return...[/dim]")
        readchar.readkey()
        return

    scrollable_column_names = item_names_as_cols + [tnw_col_name, change_col_name]
    cell_horizontal_padding = 1 
    date_col_content_width = 12

    # --- Prepare full data for display ---
    processed_rows = []
    # csv_export_rows = [] # CSV export can be a separate step if needed
    # csv_headers = [date_col_name] + scrollable_column_names
    # csv_export_rows.append(csv_headers)

    # Ensure snapshots are sorted by date, oldest first for chronological display & change calculation
    sorted_snapshots = sorted(snapshots, key=lambda s: s.get('date', ''), reverse=False)
    
    previous_tnw_for_change_calc = None
    max_scrollable_content_len = 0

    for snapshot in sorted_snapshots:
        date_str = snapshot['date']
        row_display_data = {}
        # row_csv_data = [date_str]
        try:
            row_display_data[date_col_name] = Text(datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y"), style="dim")
        except ValueError: # Fallback if date format is unexpected
            row_display_data[date_col_name] = Text(date_str, style="dim")

        balances_for_current_snapshot = {bal['item_id']: bal['balance'] for bal in snapshot.get('balances', [])}
        current_tnw_for_this_date = 0

        for item_name_col in item_names_as_cols:
            # Find the item_id for this item_name_col
            item_id_for_col = next((item['id'] for item in financial_items if item['name'] == item_name_col), None)
            balance = 0.0 # Default to 0.0 if item not in this snapshot or item_id not found
            if item_id_for_col and item_id_for_col in balances_for_current_snapshot:
                balance = balances_for_current_snapshot[item_id_for_col]
            
            current_tnw_for_this_date += balance # Sum all balances for TNW
            
            style = "green" if balance >= 0 else "red"
            text_val = Text(f"£{balance:,.2f}", style=style if balance != 0.0 else "dim") # Dim for zero balances
            row_display_data[item_name_col] = text_val
            max_scrollable_content_len = max(max_scrollable_content_len, len(str(text_val)))
            # row_csv_data.append(f"{balance:.2f}")

        # Total Net Worth
        tnw_style = "green bold" if current_tnw_for_this_date >= 0 else "red bold"
        tnw_text_val = Text(f"£{current_tnw_for_this_date:,.2f}", style=tnw_style)
        row_display_data[tnw_col_name] = tnw_text_val
        max_scrollable_content_len = max(max_scrollable_content_len, len(str(tnw_text_val)))
        # row_csv_data.append(f"{current_tnw_for_this_date:.2f}")

        # Change in Total Net Worth
        change_display_text = Text("N/A", style="dim bold")
        # change_csv_val = "N/A"
        if previous_tnw_for_change_calc is not None:
            diff = current_tnw_for_this_date - previous_tnw_for_change_calc
            if previous_tnw_for_change_calc == 0: # Avoid division by zero
                if diff == 0:
                    percentage_change = 0.0
                    ch_style = "dim bold"
                    symbol = "→"
                else: # Infinite change
                    percentage_change = float('inf') if diff > 0 else float('-inf')
                    ch_style = "green bold" if diff > 0 else "red bold"
                    symbol = "↑" if diff > 0 else "↓"
                change_display_text = Text(f"{symbol} {percentage_change:.2f}%" if percentage_change != float('inf') and percentage_change != float('-inf') else f"{symbol} N/A", style=ch_style)
            else:
                percentage_change = (diff / abs(previous_tnw_for_change_calc)) * 100
                ch_style = "green bold" if diff > 0 else "red bold" if diff < 0 else "dim bold"
                symbol = "↑" if diff > 0 else "↓" if diff < 0 else "→"
                change_display_text = Text(f"{symbol} {percentage_change:.2f}%", style=ch_style)
            # change_csv_val = f"{percentage_change:.2f}%" if previous_tnw_for_change_calc != 0 else "N/A"
        
        row_display_data[change_col_name] = change_display_text
        max_scrollable_content_len = max(max_scrollable_content_len, len(str(change_display_text)))
        # row_csv_data.append(change_csv_val)
        
        previous_tnw_for_change_calc = current_tnw_for_this_date
        processed_rows.append(row_display_data)
        # csv_export_rows.append(row_csv_data)
    
    uniform_scrollable_content_width = max(max_scrollable_content_len, 10) # Min content width of 10

    # --- Scrolling and Table Rendering Loop ---
    current_page_start_idx = 0
    while True:
        console.clear()
        padded_date_col_total_width = date_col_content_width + 2 * cell_horizontal_padding
        width_consumed_by_fixed_date_and_structure = padded_date_col_total_width + 3 
        available_width_for_scrollable_section = console.width - width_consumed_by_fixed_date_and_structure
        
        cost_per_scrollable_col_and_its_separator = (uniform_scrollable_content_width + 2 * cell_horizontal_padding) + 1

        num_scrollable_cols_on_page = 0
        if available_width_for_scrollable_section > (uniform_scrollable_content_width + 2 * cell_horizontal_padding):
            num_scrollable_cols_on_page = max(1, available_width_for_scrollable_section // cost_per_scrollable_col_and_its_separator)
        elif len(scrollable_column_names) > 0 :
             num_scrollable_cols_on_page = 1
        
        page_end_idx = min(current_page_start_idx + num_scrollable_cols_on_page, len(scrollable_column_names))
        scrollable_cols_this_page = scrollable_column_names[current_page_start_idx:page_end_idx]

        table = Table(
            title=Text("Historical Snapshot Data (Scrollable)", style="bold blue"),
            show_header=True, header_style="bold magenta", box=box.ROUNDED,
            width=console.width # Make table use full console width
        )

        table.add_column(date_col_name, min_width=date_col_content_width, style="dim") # Date column style

        for col_name in scrollable_cols_this_page:
            header_text_obj = Text(col_name) # Convert to Text for wrapping
            # Rich's Text.wrap is for single lines. For multi-line truncation:
            wrapped_header_lines = []
            # Simple truncation for header if too long for uniform_scrollable_content_width
            # A more sophisticated approach might wrap then truncate.
            max_header_len = uniform_scrollable_content_width
            
            current_line = ""
            temp_lines = []
            for word in col_name.split():
                if console.measure(current_line + word).maximum < max_header_len:
                    current_line += word + " "
                else:
                    if current_line: temp_lines.append(current_line.strip())
                    current_line = word + " "
            if current_line: temp_lines.append(current_line.strip())

            for i, line_text in enumerate(temp_lines):
                if i < 2: # Max 2 lines for header
                    wrapped_header_lines.append(Text(line_text))
                elif i == 2: # Add ellipsis if more lines
                    if len(temp_lines) > 2:
                         wrapped_header_lines[-1] = Text(str(wrapped_header_lines[-1])[:max_header_len-3] + "...", overflow="ellipsis")
                    break
            
            actual_header = Text("\n").join(wrapped_header_lines) if wrapped_header_lines else Text(col_name, overflow="ellipsis", width=max_header_len)
            table.add_column(actual_header, justify="right", min_width=uniform_scrollable_content_width, width=uniform_scrollable_content_width)
        
        for row_data_map in processed_rows:
            display_row_values = [row_data_map[date_col_name]]
            for col_name in scrollable_cols_this_page:
                display_row_values.append(row_data_map.get(col_name, Text("-", style="dim")))
            table.add_row(*display_row_values)
        
        console.print(table)

        scroll_indicator = ""
        if current_page_start_idx > 0:
            scroll_indicator += "[cyan]< Left (l)[/cyan]  "
        if page_end_idx < len(scrollable_column_names):
            scroll_indicator += "[cyan]Right (r) >[/cyan]"
        
        # console.print(f"\n[bold]Options:[/bold] {scroll_indicator}  Press [cyan]c[/cyan] to export, [cyan]q[/cyan] to return.")
        # Temporarily removing CSV export from this view as export_pivot_data_to_csv is not defined here
        console.print(f"\n[bold]Options:[/bold] {scroll_indicator}  Press [cyan]q[/cyan] to return.")

        key = readchar.readkey() # Read the key press here
        try:
            # if key.lower() == 'c':
            #     console.print("[yellow]CSV export for this view to be re-implemented.[/yellow]")
            #     # export_pivot_data_to_csv(csv_export_rows, default_filename="historical_snapshot_view.csv")
            if key.lower() == 'q':
                console.clear()
                break
            elif key.lower() == 'r' or key == readchar.key.RIGHT:
                if page_end_idx < len(scrollable_column_names):
                    current_page_start_idx = min(page_end_idx, len(scrollable_column_names) - num_scrollable_cols_on_page) if num_scrollable_cols_on_page > 0 else page_end_idx
            elif key.lower() == 'l' or key == readchar.key.LEFT:
                if current_page_start_idx > 0:
                    current_page_start_idx = max(0, current_page_start_idx - num_scrollable_cols_on_page)
        except Exception as e:
            console.print(f"[red]An error occurred: {e}. Returning.[/red]")
            console.input("Press Enter to continue...") 
            console.clear()
            break
    # End of while True for scrolling

def asset_management_screen(console: Console, categories: list, financial_items: list, snapshots: list, current_snapshot_balances: list, current_date: str):
    """
    Displays the asset management screen for viewing and editing financial items and their balances.
    Returns: Tuple of (updated_categories, updated_financial_items, updated_snapshots, 
                  updated_current_snapshot_balances, changes_made_overall)
    """
    changes_made_overall = False
    
    items_dict = {item['id']: item for item in financial_items}
    cats_dict = {cat['id']: cat for cat in categories}

    while True:
        console.clear()
        console.print("\n[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
        console.print("[bold blue]FINANCIAL ITEM MANAGEMENT[/bold blue]")
        console.print(f"[bold blue]For Date: [cyan]{current_date}[/cyan][/bold blue]")
        console.print("[bold blue]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold blue]")
        
        current_total_assets_val = 0.0
        current_total_debts_val = 0.0
        current_liquid_assets_val = 0.0

        for balance_entry in current_snapshot_balances:
            item_id = balance_entry.get("item_id")
            balance = balance_entry.get("balance", 0.0)
            item_details = items_dict.get(item_id)
            if not item_details: continue
            if balance > 0:
                current_total_assets_val += balance
                if item_details.get("liquid", False):
                    current_liquid_assets_val += balance
            elif balance < 0:
                current_total_debts_val += balance
        
        current_net_worth_val = current_total_assets_val + current_total_debts_val
        
        console.print()
        console.print(f"[bold]Net Worth ({current_date}):[/bold] [{'green' if current_net_worth_val >= 0 else 'red'}]£{current_net_worth_val:,.2f}[/{'green' if current_net_worth_val >= 0 else 'red'}]")
        console.print(f"[bold]Total Assets:[/bold] [green]£{current_total_assets_val:,.2f}[/green]")
        console.print(f"[bold]Total Debts:[/bold] [red]£{current_total_debts_val:,.2f}[/red]")
        console.print(f"[bold]Sum of Positive Liquid Items:[/bold] [cyan]£{current_liquid_assets_val:,.2f}[/cyan]")
        console.print()
        
        if current_snapshot_balances:
            table = Table(
                title=Text(f"Items and Balances for {current_date}", style="bold"),
                show_header=True, header_style="bold", box=box.SIMPLE, padding=(0, 1)
            )
            table.add_column("#", style="dim", width=4, justify="right")
            table.add_column("Item Name", min_width=20)
            table.add_column("Balance", justify="right", min_width=15)
            table.add_column("Category", min_width=15, style="dim")
            table.add_column("Liquid", justify="center", min_width=8)
            
            for idx, balance_entry in enumerate(current_snapshot_balances, 1):
                item_id = balance_entry.get("item_id")
                balance = balance_entry.get("balance", 0.0)
                item_details = items_dict.get(item_id)
                if not item_details:
                    item_name_str = f"Unknown Item (ID: {item_id})"
                    category_name_str = "Unknown"
                    is_liquid_val = False
                else:
                    item_name_str = item_details.get("name", f"Unnamed Item (ID: {item_id})")
                    category_id = item_details.get("category_id")
                    cat_details = cats_dict.get(category_id)
                    category_name_str = cat_details.get("name", "Uncategorized") if cat_details else "Invalid Category ID"
                    is_liquid_val = item_details.get("liquid", False)
                
                liquid_status_text = Text("Yes", style="green") if is_liquid_val else Text("No", style="red")
                balance_color_style = "green" if balance >= 0 else "red"
                balance_text_str = Text(f"£{balance:,.2f}", style=balance_color_style)
                
                table.add_row(str(idx), item_name_str, balance_text_str, category_name_str, liquid_status_text)
            console.print(table)
            
            console.print("\n[bold]Options:[/bold]")
            console.print(" • Press [cyan]m[/cyan] then item # to manage its balance/properties for this date")
            console.print(" • Press [cyan]a[/cyan] to add a new financial item (globally) and set its balance for this date")
            console.print(" • Press [cyan]c[/cyan] to manage categories (add, edit, delete)")
            console.print(" • Press [cyan]h[/cyan] to view all snapshot history (table view)")
            console.print(" • Press [cyan]q[/cyan] to return to dashboard")
        else:
            console.print(f"[yellow]No items with balances defined for {current_date}.[/yellow]")
            console.print("\n[bold]Options:[/bold]")
            console.print(" • Press [cyan]a[/cyan] to add a new financial item (globally) and set its balance for this date")
            console.print(" • Press [cyan]c[/cyan] to manage categories (add, edit, delete)")
            console.print(" • Press [cyan]h[/cyan] to view all snapshot history (table view)")
            console.print(" • Press [cyan]q[/cyan] to return to dashboard")

        console.print("\nEnter action: ", end="")
        try:
            key = readchar.readkey()
            console.print(key)
            console.print()

            if key.lower() == 'q':
                console.print("[yellow]Returning to dashboard...[/yellow]")
                return categories, financial_items, snapshots, current_snapshot_balances, changes_made_overall
            
            elif key.lower() == 'a':
                item_added = add_new_financial_item_interactive(
                    console, # Passing console as console_instance
                    financial_items, 
                    categories, 
                    current_snapshot_balances, 
                    current_date 
                )
                if item_added:
                    changes_made_overall = True
                    items_dict = {item['id']: item for item in financial_items}
                    cats_dict = {cat['id']: cat for cat in categories}
                continue

            elif key.lower() == 'c':
                updated_categories_list = manage_categories_interactive(categories, financial_items, console)
                if updated_categories_list is not categories:
                    categories = updated_categories_list
                    cats_dict = {cat['id']: cat for cat in categories}
                    changes_made_overall = True
                continue

            elif key.lower() == 'h':
                view_historical_snapshots_table(console, snapshots, financial_items, categories)
                continue
            
            elif key.lower() == 'm':
                if not current_snapshot_balances:
                    console.print("[red]No items to manage for this date.[/red]")
                    console.input("Press Enter to continue...")
                    continue
                
                try:
                    item_num_str = console.input("Enter item # to manage: ").strip()
                    if not item_num_str:
                        console.print("[yellow]No item number entered. Returning to options.[/yellow]")
                        console.input("Press Enter to continue...")
                        continue

                    item_idx_display = int(item_num_str) - 1 # User sees 1-based index
                    if 0 <= item_idx_display < len(current_snapshot_balances):
                        item_id_to_manage_local = current_snapshot_balances[item_idx_display]['item_id']
                        
                        # Call the new function
                        (updated_financial_items, updated_categories, updated_snapshots,
                        updated_current_snapshot_balances, item_management_changes) = manage_financial_item_interactive(
                            console,
                            item_id_to_manage_local,
                            current_date,
                            financial_items,
                            categories,
                            snapshots,
                            current_snapshot_balances
                        )
                        
                        if item_management_changes:
                            financial_items = updated_financial_items
                            categories = updated_categories
                            snapshots = updated_snapshots
                            current_snapshot_balances = updated_current_snapshot_balances
                            changes_made_overall = True
                            # Rebuild dicts if they are used before next loop iteration for display
                            items_dict = {item['id']: item for item in financial_items}
                            cats_dict = {cat['id']: cat for cat in categories}
                        
                    else:
                        console.print(f"[red]Invalid item number. Please enter a number between 1 and {len(current_snapshot_balances)}.[/red]")
                        console.input("Press Enter to continue...")
                except ValueError:
                    console.print("[red]Invalid input. Please enter a valid number.[/red]")
                    console.input("Press Enter to continue...")
                except Exception as e_manage:
                    console.print(f"[red]An error occurred: {e_manage}[/red]")
                    console.input("Press Enter to continue...")
                # No need for a separate "Press Enter" here, manage_financial_item_interactive handles its own flow
                continue # Go back to asset_management_screen menu
            else:
                console.print(f"[red]Invalid option: '{key}'.[/red]")
                console.input("Press Enter to continue...")
                continue
        
        except Exception as e:
            console.print(f"[bold red]An unexpected error occurred in financial item management: {e}[/bold red]")
            console.input("Press Enter to continue...")
            continue
    
    return categories, financial_items, snapshots, current_snapshot_balances, changes_made_overall 

def file_options_screen(console: Console, categories: list, financial_items: list, snapshots: list, current_snapshot_balances: list, current_date: str, current_data_file: str):
    """
    Displays a menu for file operations like saving, loading, changing file name.
    Returns: Tuple of (categories, financial_items, snapshots, current_snapshot_balances, current_date, new_data_file_path)
    allowing the main application to update its state if a new file is loaded or current file path changes.
    """
    original_data_file = current_data_file

    while True:
        console.clear()
        console.print(Panel(f"[bold cyan]File Options[/bold cyan]\nCurrent Data File: [yellow]{current_data_file}[/yellow]", expand=False))
        
        menu_items = [
            "Save Current Data",
            "Load Data File",
            "Set As Current Data File Path (for next save/load)",
            # "Import Data from CSV (Placeholder)", # Future feature
            # "Export Data to CSV (Placeholder)", # Future feature
            "Back to Main Menu"
        ]
        
        selected_index, choice = show_menu(menu_items, "Select an action:")

        if choice == "Save Current Data":
            # Import save_historical_data here to avoid circular dependency if screens.py imports data_manager
            from data_manager import save_historical_data, save_last_opened_file
            save_historical_data(console, categories, financial_items, snapshots, current_data_file)
            save_last_opened_file(current_data_file) # Remember this saved file
            Prompt.ask("\nData saved. Press Enter to continue...", console=console, show_default=False)
            
        elif choice == "Load Data File":
            from data_manager import load_historical_data, save_last_opened_file # Import for loading and saving config
            import os # For os.path.exists

            console.print(f"\nCurrent data file is: [yellow]{current_data_file}[/yellow]")
            new_file_path = Prompt.ask("Enter the path to the data file to load (e.g., data.json)", console=console).strip()

            if not new_file_path:
                console.print("[yellow]Load cancelled. No file path entered.[/yellow]")
            elif not os.path.exists(new_file_path):
                console.print(f"[red]Error: File not found at '{new_file_path}'.[/red]")
            elif new_file_path == current_data_file:
                console.print(f"[yellow]The specified file '{new_file_path}' is already the current data file. No action taken.[/yellow]")
            else:
                if Confirm.ask(f"Are you sure you want to load data from '{new_file_path}'? Unsaved changes to the current data will be lost.", console=console, default=False):
                    console.print(f"[green]Loading data from [cyan]{new_file_path}[/cyan]...[/green]")
                    loaded_categories, loaded_financial_items, loaded_snapshots = load_historical_data(console, new_file_path)
                    
                    if loaded_categories is not None: # Check if loading was successful (load_historical_data returns None for major errors)
                        # Successfully loaded new data, so update everything and return
                        current_data_file = new_file_path
                        categories = loaded_categories
                        financial_items = loaded_financial_items
                        snapshots = loaded_snapshots # Snapshots are already sorted by load_historical_data

                        # Reset current_snapshot_balances and current_date based on newly loaded snapshots
                        if snapshots:
                            most_recent_snapshot = snapshots[0] # Already sorted newest first
                            current_date = most_recent_snapshot.get('date', datetime.now().strftime("%Y-%m-%d"))
                            current_snapshot_balances = most_recent_snapshot.get('balances', []).copy()
                        else: # No snapshots in the loaded file
                            current_date = datetime.now().strftime("%Y-%m-%d")
                            current_snapshot_balances = []
                        
                        console.print(f"[bold green]Successfully loaded data from '{new_file_path}'. Returning to main menu.[/bold green]")
                        Prompt.ask("Press Enter to continue...", console=console, show_default=False)
                        # Return all potentially modified data to the main application loop
                        # Also save the successfully loaded file path to config before returning
                        save_last_opened_file(current_data_file)
                        return categories, financial_items, snapshots, current_snapshot_balances, current_date, current_data_file
                    else:
                        # load_historical_data would have printed an error.
                        console.print(f"[red]Failed to load data from '{new_file_path}'. Check messages above. No changes made.[/red]")
                else:
                    console.print("[yellow]Load operation cancelled.[/yellow]")
            Prompt.ask("\nPress Enter to continue...", console=console, show_default=False)

        elif choice == "Set As Current Data File Path (for next save/load)":
            new_save_path = Prompt.ask("Enter the new file path to use for saving/loading (e.g., my_net_worth.json)", default=current_data_file, console=console).strip()
            if not new_save_path:
                console.print("[yellow]File path cannot be empty. No change made.[/yellow]")
            elif new_save_path != current_data_file:
                current_data_file = new_save_path
                from data_manager import save_last_opened_file # Ensure import
                save_last_opened_file(current_data_file) # Remember this new path preference
                console.print(f"[green]Current data file path set to: [cyan]{current_data_file}[/cyan].[/green]")
                console.print("[dim]Data will be saved to/loaded from this path next time.[/dim]")
            else:
                console.print("[yellow]File path is the same as the current one. No change made.[/yellow]")
            Prompt.ask("\nPress Enter to continue...", console=console, show_default=False)

        elif choice == "Back to Main Menu" or choice is None:
            # Return original or updated file path, but other data is unchanged unless loaded.
            return categories, financial_items, snapshots, current_snapshot_balances, current_date, current_data_file
        
        # Placeholders for future features
        # elif choice == "Import Data from CSV (Placeholder)":
        #     console.print("[yellow]Import from CSV is not yet implemented.[/yellow]")
        #     Prompt.ask("\nPress Enter to continue...", console=console, show_default=False)
        # elif choice == "Export Data to CSV (Placeholder)":
        #     console.print("[yellow]Export to CSV is not yet implemented.[/yellow]")
        #     Prompt.ask("\nPress Enter to continue...", console=console, show_default=False)

    return categories, financial_items, snapshots, current_snapshot_balances, current_date, current_data_file 