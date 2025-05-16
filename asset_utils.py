"""
Asset utilities for Net Worth Tracker.
This module handles category and financial item related utilities.

New Data Schema:
-----------------
The application stores data in a single JSON object with three top-level keys:
*   `categories`: List of category objects (`id` (str), `name` (str), `keywords` (list of str)).
*   `financial_items`: List of unique asset/liability definitions (`id` (str), `name` (str), 
                     `category_id` (str), `liquid` (bool), `type` (str: "asset" or "liability")).
*   `snapshots`: List of dated entries (`date` (str: "YYYY-MM-DD"), `balances` (list of objects: 
                 `item_id` (str), `balance` (float))).
"""

from rich.text import Text
from rich.prompt import Confirm, Prompt # For confirming save before exit and for Prompt
from simple_term_menu import TerminalMenu
from rich.table import Table
from rich.panel import Panel
from rich import box
from menu_utils import show_menu
from core_logic import generate_unique_id # Added import
import readchar # Ensure this import is present

# UK-specific asset categories (Initial source for default categories)
_DEFAULT_CATEGORY_DATA = {
    "Property": ["house", "property", "flat", "apartment", "land"],
    "Pension": ["pension", "sipp", "retirement"],
    "ISA": ["isa", "ssisa"],
    "Savings": ["savings", "premium bonds", "saver", "saving"],
    "Current Account": ["current", "checking"],
    "Investment": ["shares", "stocks", "investment", "fund", "gia"],
    "Mortgage": ["mortgage"], # Typically a liability
    "Loan": ["loan", "car finance", "personal loan"], # Typically a liability
    "Credit Card": ["credit", "cc"], # Typically a liability
    "Business": ["business"],
    "Other": [] # Default, no specific keywords
}

# Store custom keywords added by users (persisted between sessions)
# CUSTOM_KEYWORDS = {} # Removed

# def save_custom_keywords(filename="custom_keywords.json"):
#     """
#     Save custom keywords to a file.
#     
#     Args:
#         filename: File to save custom keywords to
#     """
#     import json
#     try:
#         with open(filename, 'w') as f:
#             json.dump(CUSTOM_KEYWORDS, f, indent=4)
#     except Exception as e:
#         print(f"Error saving custom keywords: {e}")

# def load_custom_keywords(filename="custom_keywords.json"):
#     """
#     Load custom keywords from a file.
#     
#     Args:
#         filename: File to load custom keywords from
#     """
#     import json
#     import os
#     global CUSTOM_KEYWORDS
#     
#     if os.path.exists(filename):
#         try:
#             with open(filename, 'r') as f:
#                 CUSTOM_KEYWORDS.update(json.load(f))
#         except Exception as e:
#             print(f"Error loading custom keywords: {e}")

def get_default_categories():
    """
    Generates a list of default category objects.
    Each category will have a unique ID and associated keywords.
    This is used to populate categories if starting with no data file.

    Returns:
        list: A list of default category dictionaries, e.g.,
              [{'id': 'cat_...', 'name': 'Property', 'keywords': ['house', ...]}, ...]
    """
    default_categories_list = []
    existing_ids_for_generation = [] # This will store full ID strings like ["cat_1", "cat_2"]

    for name, keywords in _DEFAULT_CATEGORY_DATA.items():
        # Pass the list of already generated full ID strings and the correct prefix
        cat_id_str = generate_unique_id(existing_ids_for_generation, prefix="cat_")
        
        default_categories_list.append({
            "id": cat_id_str,
            "name": name,
            "keywords": keywords
        })
        existing_ids_for_generation.append(cat_id_str) # Add the new string ID to the list
    return default_categories_list

def guess_category(item_name: str, categories_list: list) -> str | None:
    """
    Attempts to guess the category ID of an item based on its name by checking keywords.
    
    Args:
        item_name (str): The name of the item to categorize.
        categories_list (list): A list of category objects 
                                (e.g., [{'id': '...', 'name': '...', 'keywords': [...]}]).
        
    Returns:
        str | None: The ID of the guessed category, or None if no match is found.
    """
    item_name_lower = item_name.lower()
    
    for category in categories_list:
        for keyword in category.get('keywords', []):
            if keyword.lower() in item_name_lower:
                return category['id']
    
    # Optional: Could try to find and return a default "Other" category ID if no keyword match
    # For now, just returning None.
    return None

def view_categories(categories_list: list, console):
    """
    Displays all available categories with their IDs and keywords.
    
    Args:
        categories_list (list): A list of category objects 
                                  (e.g., [{'id': '...', 'name': '...', 'keywords': [...]}]).
        console: Rich console object for output
    """
    if not categories_list:
        console.print("[yellow]No categories defined yet.[/yellow]")
        return

    table = Table(title="Available Categories", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("ID", style="dim cyan", no_wrap=True)
    table.add_column("Name", style="bold magenta")
    table.add_column("Keywords", style="green")

    sorted_categories = sorted(categories_list, key=lambda c: c['name'])
    
    for idx, category in enumerate(sorted_categories, 1):
        keywords_str = ", ".join(category.get('keywords', [])) or "-"
        table.add_row(str(idx), category['id'], category['name'], keywords_str)
    
    console.print(table)

def manage_categories_interactive(categories_list: list, financial_items_list: list, console) -> list:
    """
    Provides a UI for managing categories: viewing, adding, editing, deleting.

    Args:
        categories_list (list): The current list of category objects.
        financial_items_list (list): The list of financial item objects (for checking dependencies).
        console: Rich console object for output.

    Returns:
        list: The potentially modified list of category objects.
    """
    changes_made = False # This tracks if any modification occurs during the session
    while True:
        console.clear()
        console.print(Panel("[bold cyan]Category Management[/bold cyan]", expand=False))
        
        view_categories(categories_list, console)
        console.print()

        console.print("[bold]Actions:[/bold]")
        console.print("  [cyan]a[/cyan] Add New Category")
        console.print("  [cyan]e[/cyan] Edit Existing Category (select by number from table)")
        console.print("  [cyan]d[/cyan] Delete Category (select by number from table)")
        console.print("  [cyan]q[/cyan] Back to Main Menu")
        console.print()
        
        console.print("Enter action: ", end="") # Prompt for action
        action_key_pressed = readchar.readkey()
        console.print(action_key_pressed) # Echo the key
        console.print() # Newline after echo

        action_key = action_key_pressed.lower()

        if action_key == 'a': # Add New Category
            console.print(Panel("[bold green]Add New Category[/bold green]", expand=False))
            new_name = Prompt.ask("Enter category name", console=console).strip()
            if not new_name:
                console.print("[yellow]Category name cannot be empty.[/yellow]")
                console.input("Press Enter to continue...") # Pause for user to read
                continue
            
            if any(cat['name'].lower() == new_name.lower() for cat in categories_list):
                console.print(f"[yellow]A category named '{new_name}' already exists.[/yellow]")
                console.input("Press Enter to continue...") # Pause
                continue

            keywords_str = Prompt.ask("Enter keywords (comma-separated, e.g., work, company, salary)", default="", console=console)
            new_keywords = sorted(list(set(k.strip().lower() for k in keywords_str.split(',') if k.strip())))
            
            new_id = generate_unique_id([cat['id'] for cat in categories_list])
            
            new_category = {
                "id": new_id,
                "name": new_name,
                "keywords": new_keywords
            }
            categories_list.append(new_category)
            console.print(f"[green]Category '{new_name}' added with ID '{new_id}'.[/green]")
            changes_made = True
            # No generic pause here, screen will redraw

        elif action_key == 'e': # Edit Existing Category
            if not categories_list:
                console.print("[yellow]No categories exist to edit.[/yellow]")
                console.input("Press Enter to continue...") # Pause
            else:
                console.print(Panel("[bold yellow]Edit Existing Category[/bold yellow]", expand=False))
                view_categories(categories_list, console)
                
                sorted_categories_for_selection = sorted(categories_list, key=lambda c: c['name'])
                
                cat_num_str = Prompt.ask("Enter the number of the category to edit (as shown in the table above, e.g., 1, 2, etc.), or type 'cancel'", console=console).strip()

                if cat_num_str.lower() == 'cancel':
                    continue
                
                category_to_edit = None
                try:
                    cat_idx_one_based = int(cat_num_str)
                    if 1 <= cat_idx_one_based <= len(sorted_categories_for_selection):
                        category_to_edit = sorted_categories_for_selection[cat_idx_one_based - 1]
                    else:
                        console.print(f"[red]Invalid number. Please enter a number between 1 and {len(sorted_categories_for_selection)}.[/red]")
                        console.input("Press Enter to continue...") # Pause
                        continue # Added continue after pause
                except ValueError:
                    console.print(f"[red]Invalid input. Please enter a number or 'cancel'. You entered: '{cat_num_str}'[/red]")
                    console.input("Press Enter to continue...") # Pause
                    continue # Added continue after pause

                if not category_to_edit:
                    # This case should be covered by the continues above if error messages are shown
                    continue
                else:
                    # Original editing logic for the found category_to_edit proceeds here
                    # This sub-logic sets its own `changes_made = True` if modifications occur
                    # and handles its own "Press Enter to continue..." within its sub-loops.
                    while True: 
                        console.print(f"\nEditing Category: [bold magenta]'{category_to_edit['name']}'[/bold magenta] (ID: {category_to_edit['id']})")
                        edit_options = ["Edit Name", "Edit Keywords", "Done Editing This Category"]
                        edit_idx, edit_choice_str = show_menu(edit_options, "Select an aspect to edit:")

                        if edit_idx is None: # Handles Esc, q, or selecting '[r] Return to previous menu'
                            break # Exit category editing options loop

                        if edit_choice_str == "Edit Name":
                            new_name = Prompt.ask(f"Enter new name for '{category_to_edit['name']}'", default=category_to_edit['name'], console=console).strip()
                            if not new_name:
                                console.print("[yellow]Name cannot be empty.[/yellow]")
                            elif any(cat['name'].lower() == new_name.lower() and cat['id'] != category_to_edit['id'] for cat in categories_list):
                                console.print(f"[yellow]Another category with the name '{new_name}' already exists.[/yellow]")
                            else:
                                if category_to_edit['name'] != new_name:
                                    category_to_edit['name'] = new_name
                                    console.print(f"[green]Category name updated to '{new_name}'.[/green]")
                                    changes_made = True
                                    Prompt.ask("\nPress Enter to continue...", default="", show_default=False, console=console) # Pause after successful action
                                else:
                                    console.print("[yellow]Name is unchanged.[/yellow]")
                                    # No pause if unchanged, menu will redraw.
                        
                        elif edit_choice_str == "Edit Keywords":
                            while True: # Loop for keyword editing
                                current_kws = category_to_edit.get('keywords', [])
                                console.print(f"Current keywords: [green]{', '.join(current_kws) if current_kws else 'None'}[/green]")
                                kw_options = ["Replace all keywords", "Add keyword(s)", "Remove keyword(s)", "Clear all keywords", "Back to category edit options"]
                                kw_idx, kw_choice_str = show_menu(kw_options, "Keyword action:")

                                if kw_idx is None: # Handles Esc, q, or selecting '[r] Return to previous menu'
                                    break # Exit keyword editing loop, NO prompt here

                                if kw_choice_str == "Replace all keywords":
                                    kws_str = Prompt.ask("Enter new keywords (comma-separated)", console=console)
                                    new_kws = sorted(list(set(k.strip().lower() for k in kws_str.split(',') if k.strip())))
                                    if category_to_edit.get('keywords') != new_kws:
                                        category_to_edit['keywords'] = new_kws
                                        console.print(f"[green]Keywords replaced. New keywords: {', '.join(new_kws) if new_kws else 'None'}[/green]")
                                        changes_made = True
                                        Prompt.ask("\nPress Enter to continue...", default="", show_default=False, console=console)
                                    else:
                                        console.print("[yellow]Keywords are unchanged.[/yellow]")
                                elif kw_choice_str == "Add keyword(s)":
                                    kws_str = Prompt.ask("Enter keywords to add (comma-separated)", console=console)
                                    to_add_kws = set(k.strip().lower() for k in kws_str.split(',') if k.strip())
                                    original_kws_set = set(current_kws)
                                    added_count = 0
                                    for kw in to_add_kws:
                                        if kw not in original_kws_set:
                                            current_kws.append(kw)
                                            added_count +=1
                                    if added_count > 0:
                                        category_to_edit['keywords'] = sorted(list(set(current_kws))) # Ensure unique and sort
                                        console.print(f"[green]{added_count} new keyword(s) added. Current: {', '.join(category_to_edit['keywords']) if category_to_edit['keywords'] else 'None'}[/green]")
                                        changes_made = True
                                        Prompt.ask("\nPress Enter to continue...", default="", show_default=False, console=console)
                                    else:
                                        console.print("[yellow]No new keywords were added (either empty input or keywords already exist).[/yellow]")
                                elif kw_choice_str == "Remove keyword(s)":
                                    if not current_kws:
                                        console.print("[yellow]No keywords to remove.[/yellow]")
                                        continue
                                    kws_to_remove_options = [f"{idx+1}. {kw}" for idx, kw in enumerate(current_kws)]
                                    console.print("Select keyword(s) to remove by number (comma-separated, e.g., 1,3) or type 'all':")
                                    for opt in kws_to_remove_options: console.print(f"  {opt}")
                                    kws_remove_input = Prompt.ask("Numbers to remove (or 'all')", console=console).strip().lower()
                                    removed_any = False
                                    if kws_remove_input == 'all':
                                        if Confirm.ask(f"Are you sure you want to remove all {len(current_kws)} keywords?", console=console, default=False):
                                            category_to_edit['keywords'] = []
                                            console.print("[green]All keywords removed.[/green]")
                                            changes_made = True
                                            removed_any = True
                                    else:
                                        indices_to_remove = set()
                                        try:
                                            for num_str in kws_remove_input.split(','):
                                                idx = int(num_str.strip()) - 1
                                                if 0 <= idx < len(current_kws):
                                                    indices_to_remove.add(idx)
                                                else:
                                                    console.print(f"[red]Invalid number: {idx+1}. Ignoring.[/red]")
                                        except ValueError:
                                            console.print("[red]Invalid input for numbers. Please use comma-separated numbers.[/red]")
                                            continue
                                        
                                        if indices_to_remove:
                                            new_kws_list = [kw for i, kw in enumerate(current_kws) if i not in indices_to_remove]
                                            if len(new_kws_list) < len(current_kws):
                                                category_to_edit['keywords'] = sorted(new_kws_list)
                                                console.print(f"[green]Selected keywords removed. Current: {', '.join(category_to_edit['keywords']) if category_to_edit['keywords'] else 'None'}[/green]")
                                                changes_made = True
                                                removed_any = True
                                                Prompt.ask("\nPress Enter to continue...", default="", show_default=False, console=console)
                                            else:
                                                console.print("[yellow]No valid keywords selected for removal or selection issue.[/yellow]")
                                        else:
                                             console.print("[yellow]No keywords selected for removal.[/yellow]")
                                    if not removed_any and kws_remove_input:
                                        console.print("[yellow]No keywords were removed.[/yellow]")
                                elif kw_choice_str == "Clear all keywords":
                                    if not current_kws:
                                        console.print("[yellow]No keywords to clear.[/yellow]")
                                    elif Confirm.ask(f"Are you sure you want to clear all {len(current_kws)} keywords?", console=console, default=False):
                                        category_to_edit['keywords'] = []
                                        console.print("[green]All keywords cleared.[/green]")
                                        changes_made = True
                                        Prompt.ask("\nPress Enter to continue...", default="", show_default=False, console=console)
                                    else:
                                        console.print("[yellow]Clear keywords cancelled.[/yellow]")
                                elif kw_choice_str == "Back to category edit options": # Explicit option from list
                                    break # Exit keyword editing loop, NO prompt here
                        
                        elif edit_choice_str == "Done Editing This Category": # Explicit option from list
                            break # Exit category editing options loop, NO prompt here, return to main cat menu

        elif action_key == 'd': # Delete Category
            if not categories_list:
                console.print("[yellow]No categories exist to delete.[/yellow]")
                console.input("Press Enter to continue...") # Pause
            else:
                console.print(Panel("[bold red]Delete Category[/bold red]", expand=False))
                view_categories(categories_list, console)
                
                sorted_categories_for_selection = sorted(categories_list, key=lambda c: c['name'])
                
                cat_num_str = Prompt.ask("Enter the number of the category to delete (as shown in the table), or type 'cancel'", console=console).strip()

                if cat_num_str.lower() == 'cancel':
                    continue

                category_to_delete = None
                try:
                    cat_idx_one_based = int(cat_num_str)
                    if 1 <= cat_idx_one_based <= len(sorted_categories_for_selection):
                        category_to_delete = sorted_categories_for_selection[cat_idx_one_based - 1]
                    else:
                        console.print(f"[red]Invalid number. Please enter a number between 1 and {len(sorted_categories_for_selection)}.[/red]")
                        console.input("Press Enter to continue...") # Pause
                        continue # Added continue
                except ValueError:
                    console.print(f"[red]Invalid input. Please enter a number or 'cancel'. You entered: '{cat_num_str}'[/red]")
                    console.input("Press Enter to continue...") # Pause
                    continue # Added continue
                
                if not category_to_delete:
                    continue
                else:
                    # Original deletion logic for the found category_to_delete proceeds here
                    cat_id_to_delete = category_to_delete['id'] # Get the actual ID for logic below
                    items_using_category = [item['name'] for item in financial_items_list if item.get('category_id') == cat_id_to_delete]
                    if items_using_category:
                        console.print(f"[red]Cannot delete category '{category_to_delete['name']}'. It is currently used by the following financial item(s):[/red]")
                        for item_name in items_using_category:
                            console.print(f"  - {item_name}")
                        console.print("[yellow]Please re-assign these items to a different category before deleting this one.[/yellow]")
                    else:
                        if Confirm.ask(f"Are you sure you want to delete category '{category_to_delete['name']}' (ID: {cat_id_to_delete})? This cannot be undone.", console=console, default=False):
                            categories_list.remove(category_to_delete)
                            console.print(f"[green]Category '{category_to_delete['name']}' deleted.[/green]")
                            changes_made = True
                        else:
                            console.print("[yellow]Deletion cancelled.[/yellow]")

        elif action_key == 'q':
            break # Exit category management
        
        else: # Invalid key
            console.print(f"[red]Invalid option: '{action_key_pressed}'.[/red]")
            console.input("Press Enter to continue...") # Pause for invalid input

        # The generic "Prompt.ask..." if changes_made was true in this iteration is REMOVED.
        # Pauses are now specific to errors or handled within sub-actions.
    
    return categories_list

def auto_categorize_with_confirmation(assets, console):
    """
    Auto-categorizes assets with user confirmation for each suggestion.
    
    Args:
        assets: List of assets to categorize
        console: Rich console object for output
    """
    # COMMENTED OUT
    pass

def categorize_assets(assets, console):
    """
    Allows categorizing multiple assets in sequence.
    
    Args:
        assets (list): List of asset dictionaries to categorize
        console: Rich console object for output
        
    Returns:
        bool: True if changes were saved, False if cancelled
    """
    # COMMENTED OUT
    pass
    
    # if not assets:
    #     console.print("[yellow]No assets to categorize.[/yellow]")
    #     return True
    
    # # Load custom keywords
    # load_custom_keywords()
    
    # console.print("\n[bold]ASSET CATEGORIZATION[/bold]")
    # console.print("─" * 50)
    
    # from net_worth_tracker import display_assets
    
    # while True:
    #     display_assets(assets, show_balances=False, show_categories=True)
        
    #     # Build menu options
    #     options = []
        
    #     # Add asset options
    #     for idx, asset in enumerate(assets, 1):
    #         category = asset.get('category', 'Other')
    #         options.append(f"Set category for: {asset['name']} (currently: {category})")
        
    #     # Add utility options
    #     options.append("Auto-categorize all assets with confirmation")
    #     options.append("Auto-categorize all assets without confirmation")
    #     options.append("Manage category keywords")
    #     options.append("View all available categories")
    #     options.append("Done with categorization")
    #     options.append("Back to previous menu without saving changes")
        
    #     terminal_menu = TerminalMenu(
    #         options,
    #         title="\nSelect an option:",
    #         menu_cursor="► ",
    #         menu_cursor_style=(\"fg_black\", \"bold\"),
    #         menu_highlight_style=(\"bg_gray\", \"fg_black\"),
    #     )
        
    #     menu_entry_index = terminal_menu.show()
        
    #     if menu_entry_index is None:
    #         console.print("[yellow]Returning to previous menu without applying category changes.[/yellow]")
    #         return False
            
    #     num_assets = len(assets)
    #     if menu_entry_index < num_assets:
    #         asset_idx = menu_entry_index
    #         # set_asset_category(assets[asset_idx], console) # This function was removed
    #         console.print(f"[yellow]\'set_asset_category\' (called from categorize_assets) was removed. Action for {assets[asset_idx]['name']} skipped.[/yellow]")
    #     elif options[menu_entry_index] == "Auto-categorize all assets with confirmation":
    #         # auto_categorize_with_confirmation(assets, console) # This function is now commented out
    #         console.print("[yellow]\'auto_categorize_with_confirmation\' is commented out. Action skipped.[/yellow]")
    #     elif options[menu_entry_index] == "Auto-categorize all assets without confirmation":
    #         for asset in assets:
    #             if 'category' not in asset or asset.get('category') == 'Other':
    #                 asset['category'] = guess_category(asset['name'])
    #         console.print("[green]All assets have been auto-categorized (using basic guess_category).[/green]")
    #     elif options[menu_entry_index] == "Manage category keywords":
    #         manage_category_keywords(console)
    #     elif options[menu_entry_index] == "View all available categories":
    #         view_categories(console)
    #         console.print("\\n[cyan]Press Enter to continue[/cyan]")
    #         console.input()
    #     elif options[menu_entry_index] == "Done with categorization":
    #         return True
    #     elif options[menu_entry_index] == "Back to previous menu without saving changes":
    #         console.print("[yellow]Returning to previous menu without applying category changes.[/yellow]")
    #         return False
    
    # return True 