"""
Asset utilities for Net Worth Tracker.
This module handles asset-related functionality like categorization.

Data Schema:
-----------
The application stores data in the following JSON format:
[
    {
        "date": "YYYY-MM-DD",
        "assets": [
            {
                "name": "Asset Name",
                "liquid": true/false,
                "balance": 1000.00,
                "category": "Category Name"
            },
            ...more assets
        ]
    },
    ...more dated records
]

Each asset MUST have a name, liquid status, and balance.
Each asset SHOULD have a category that matches one of the standard categories
or a custom category defined by the user.
"""

from rich.text import Text
from rich.prompt import Confirm # For confirming save before exit
from simple_term_menu import TerminalMenu
from rich.table import Table
from rich.panel import Panel
from rich import box
from menu_utils import show_menu

# UK-specific asset categories
DEFAULT_CATEGORIES = [
    "Property",
    "Pension",
    "ISA",
    "Savings",
    "Current Account",
    "Investment",
    "Mortgage",
    "Loan",
    "Credit Card",
    "Business",
    "Other"
]

# Rules for auto-categorizing assets based on names
AUTO_CATEGORIZE_RULES = {
    "Property": ["house", "property", "flat", "apartment", "land"],
    "Pension": ["pension", "sipp", "retirement"],
    "ISA": ["isa", "ssisa"],
    "Savings": ["savings", "premium bonds", "saver", "saving"],
    "Current Account": ["current", "checking"],
    "Investment": ["shares", "stocks", "investment", "fund", "gia"],
    "Mortgage": ["mortgage"],
    "Loan": ["loan", "car finance", "personal loan"],
    "Credit Card": ["credit", "cc"],
    "Business": ["business"]
}

# Store custom categories that users have added during the session
CUSTOM_CATEGORIES = set()

# Store custom keywords added by users (persisted between sessions)
CUSTOM_KEYWORDS = {}

def save_custom_keywords(filename="custom_keywords.json"):
    """
    Save custom keywords to a file.
    
    Args:
        filename: File to save custom keywords to
    """
    import json
    try:
        with open(filename, 'w') as f:
            json.dump(CUSTOM_KEYWORDS, f, indent=4)
    except Exception as e:
        print(f"Error saving custom keywords: {e}")

def load_custom_keywords(filename="custom_keywords.json"):
    """
    Load custom keywords from a file.
    
    Args:
        filename: File to load custom keywords from
    """
    import json
    import os
    global CUSTOM_KEYWORDS
    
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                CUSTOM_KEYWORDS.update(json.load(f))
        except Exception as e:
            print(f"Error loading custom keywords: {e}")

def add_custom_category(category_name):
    """
    Adds a new custom category to the session.
    
    Args:
        category_name (str): The name of the new category
    """
    global CUSTOM_CATEGORIES
    CUSTOM_CATEGORIES.add(category_name)
    # Initialize custom keywords for this category if it doesn't exist
    if category_name not in CUSTOM_KEYWORDS:
        CUSTOM_KEYWORDS[category_name] = []

def get_all_categories():
    """
    Returns all available categories (default + custom).
    
    Returns:
        list: Combined list of default and custom categories
    """
    return DEFAULT_CATEGORIES + sorted(list(CUSTOM_CATEGORIES - set(DEFAULT_CATEGORIES)))

def guess_category(asset_name):
    """
    Attempts to guess the category of an asset based on its name.
    
    Args:
        asset_name (str): The name of the asset to categorize
        
    Returns:
        str: Guessed category name
    """
    asset_name_lower = asset_name.lower()
    
    # Check built-in rules first
    for category, keywords in AUTO_CATEGORIZE_RULES.items():
        for keyword in keywords:
            if keyword.lower() in asset_name_lower:
                return category
    
    # Then check custom rules
    for category, keywords in CUSTOM_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in asset_name_lower:
                return category
    
    return "Other"  # Default category if no match is found

def set_asset_category_interactive(asset_name, console):
    """
    Interactively selects a category for an asset.
    
    Args:
        asset_name (str): The name of the asset to categorize
        console: Rich console object for output
        
    Returns:
        str: Selected category name
    """
    guessed_category = guess_category(asset_name)
    
    console.print(f"\nSelect a category for [cyan]'{asset_name}'[/cyan]")
    console.print(f"Suggested category: [green]{guessed_category}[/green]")
    
    all_categories = get_all_categories()
    for idx, category in enumerate(all_categories, 1):
        console.print(f"  {idx}. {category}")
    
    console.print(f"  C. Custom category")
    console.print(f"  Enter. Accept suggested [{guessed_category}]")
    
    user_input = console.input("Your choice: ").strip()
    
    if not user_input:
        return guessed_category
    elif user_input.lower() == 'c':
        custom_category = console.input("Enter custom category name: ").strip()
        if custom_category:
            add_custom_category(custom_category)
            return custom_category
        else:
            return guessed_category
    else:
        try:
            idx = int(user_input)
            if 1 <= idx <= len(all_categories):
                return all_categories[idx-1]
            else:
                console.print("[red]Invalid choice. Using suggested category.[/red]")
                return guessed_category
        except ValueError:
            console.print("[red]Invalid input. Using suggested category.[/red]")
            return guessed_category

def set_asset_category(asset, console):
    """
    Set the category for an asset using a menu interface.
    
    Args:
        asset: Asset dictionary to update
        console: Rich console object for output
    """
    console.print(f"\n[bold]Setting category for:[/bold] [cyan]{asset['name']}[/cyan]")
    if 'category' in asset:
        console.print(f"[bold]Current category:[/bold] [yellow]{asset['category']}[/yellow]")
    
    # Get all available categories
    all_categories = sorted(get_all_categories())
    
    # Add current category first if it exists and isn't in all_categories
    if 'category' in asset and asset['category'] not in all_categories:
        all_categories.insert(0, asset['category'])
    
    menu_index, selected_category = show_menu(
        all_categories,
        title="\nSelect a category:",
        shortcuts=False
    )
    
    if menu_index is not None:
        asset['category'] = selected_category
        console.print(f"[green]Set category to: [cyan]{selected_category}[/cyan][/green]")
    else:
        console.print("[yellow]Category change cancelled.[/yellow]")

def load_custom_categories_from_data(all_historical_records):
    """
    Extracts and loads custom categories from existing user data.
    
    Args:
        all_historical_records (list): List of historical net worth records
    """
    global CUSTOM_CATEGORIES
    
    if not all_historical_records:
        return
    
    for record in all_historical_records:
        if 'assets' in record:
            for asset in record['assets']:
                if 'category' in asset and asset['category'] not in DEFAULT_CATEGORIES:
                    CUSTOM_CATEGORIES.add(asset['category'])

def view_categories(console):
    """
    Displays all available categories (default and custom) with clean, simple formatting.
    Also allows adding new custom categories.
    
    Args:
        console: Rich console object for output
    """
    while True: # Loop to allow adding multiple categories
        # Create header
        console.print("\n[bold]AVAILABLE CATEGORIES[/bold]")
        console.print("─" * 50)
        
        # Create table for default categories with simpler styling
        default_table = Table(
            title="Default Categories",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold",
            padding=(0, 2)
        )
        
        default_table.add_column("Category")
        default_table.add_column("Auto-categorization Keywords", style="dim")
        
        # Add rows for default categories
        for category in DEFAULT_CATEGORIES:
            keywords = ", ".join(AUTO_CATEGORIZE_RULES.get(category, [])) or "None"
            default_table.add_row(category, keywords)
        
        # Display the default categories table
        console.print(default_table)
        
        # Create table for custom categories
        custom_categories = sorted(list(CUSTOM_CATEGORIES - set(DEFAULT_CATEGORIES)))
        
        if custom_categories:
            custom_table = Table(
                title="Custom Categories",
                box=box.SIMPLE,
                show_header=True,
                header_style="bold",
                padding=(0, 2)
            )
            
            custom_table.add_column("Category")
            
            # Add rows for custom categories
            for category in custom_categories:
                custom_table.add_row(category)
            
            # Display the custom categories table
            console.print("\n")
            console.print(custom_table)
        else:
            console.print("\n[dim]No custom categories defined yet.[/dim]")
        
        # Display options
        options = [
            "Add New Custom Category",
            "Manage Category Keywords"
        ]
        
        menu_index, selected_option = show_menu(
            options,
            title="\nSelect an option:"
        )
        
        if menu_index is None:
            console.print("[yellow]Returning to previous menu.[/yellow]")
            break
            
        if selected_option == "Add New Custom Category":
            new_category = console.input("\n[b magenta]Enter new category name: [/b magenta]").strip()
            if new_category:
                if new_category in DEFAULT_CATEGORIES:
                    console.print(f"[red]'{new_category}' is already a default category.[/red]")
                elif new_category in CUSTOM_CATEGORIES:
                    console.print(f"[red]'{new_category}' is already a custom category.[/red]")
                else:
                    CUSTOM_CATEGORIES.add(new_category)
                    save_custom_keywords()
                    console.print(f"[green]Added new category: [cyan]{new_category}[/cyan][/green]")
            else:
                console.print("[yellow]No category name provided.[/yellow]")
        elif selected_option == "Manage Category Keywords":
            manage_category_keywords(console)

def manage_category_keywords(console):
    """
    UI for managing custom keywords for categories.
    
    Args:
        console: Rich console object for output
    """
    # Load existing custom keywords
    load_custom_keywords()
    
    while True:
        console.print("\n[bold]CATEGORY KEYWORD MANAGEMENT[/bold]")
        console.print("─" * 50)
        
        # Create a table to show all categories and their keywords
        table = Table(
            title="Categories and Keywords",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold",
            padding=(0, 2)
        )
        
        table.add_column("Category")
        table.add_column("Default Keywords", style="dim")
        table.add_column("Custom Keywords", style="green")
        
        # Add rows for each category
        all_categories = get_all_categories()
        for category in all_categories:
            default_keywords = ", ".join(AUTO_CATEGORIZE_RULES.get(category, [])) or "None"
            custom_keywords = ", ".join(CUSTOM_KEYWORDS.get(category, [])) or "None"
            table.add_row(category, default_keywords, custom_keywords)
        
        console.print(table)
        
        # Options
        options = []
        
        # Add category options
        for category in all_categories:
            options.append(f"Add keywords to: {category}")
        
        # Add utility options
        options.append("Save changes")
        
        menu_index, selected_option = show_menu(
            options,
            title="\nSelect an option:"
        )
        
        # Handle ESC/q
        if menu_index is None:
            if Confirm.ask("Save changes before exiting?", default=True, console=console):
                save_custom_keywords()
                console.print("[green]Custom keywords saved.[/green]")
            console.print("[yellow]Returning to previous menu.[/yellow]")
            return
        
        if selected_option == "Save changes":
            save_custom_keywords()
            console.print("[green]Custom keywords saved.[/green]")
            if Confirm.ask("Return to previous menu?", default=False, console=console):
                return
        else:
            # Adding keywords to a category
            category = selected_option.replace("Add keywords to: ", "")
            add_keywords_to_category(category, console)

def add_keywords_to_category(category, console):
    """
    Add custom keywords to a category.
    
    Args:
        category: Category to add keywords to
        console: Rich console object for output
    """
    while True:
        console.print(f"\n[bold]Adding Keywords to Category: [cyan]{category}[/cyan][/bold]")
        console.print("─" * 50)
        
        # Show current keywords
        default_keywords = ", ".join(AUTO_CATEGORIZE_RULES.get(category, [])) or "None"
        custom_keywords = ", ".join(CUSTOM_KEYWORDS.get(category, [])) or "None"
        
        console.print(f"[bold]Default Keywords:[/bold] {default_keywords}")
        console.print(f"[bold]Custom Keywords:[/bold] [green]{custom_keywords}[/green]")
        
        # Options for keyword management
        options = [
            "Add a new keyword",
            "Remove a keyword",
            "Clear all custom keywords"
        ]
        
        menu_index, selected_option = show_menu(
            options,
            title="\nSelect an option:"
        )
        
        if menu_index is None:
            break
            
        if selected_option == "Add a new keyword":
            new_keyword = console.input("\n[b magenta]Enter new keyword: [/b magenta]").strip().lower()
            if new_keyword:
                if category not in CUSTOM_KEYWORDS:
                    CUSTOM_KEYWORDS[category] = []
                if new_keyword in CUSTOM_KEYWORDS[category]:
                    console.print(f"[yellow]Keyword '{new_keyword}' already exists for this category.[/yellow]")
                else:
                    CUSTOM_KEYWORDS[category].append(new_keyword)
                    console.print(f"[green]Added keyword: [cyan]{new_keyword}[/cyan][/green]")
            else:
                console.print("[yellow]No keyword provided.[/yellow]")
        elif selected_option == "Remove a keyword":
            if category not in CUSTOM_KEYWORDS or not CUSTOM_KEYWORDS[category]:
                console.print("[yellow]No custom keywords to remove.[/yellow]")
                continue
                
            # Create menu of keywords to remove
            keyword_options = CUSTOM_KEYWORDS[category].copy()
            
            menu_index, selected_keyword = show_menu(
                keyword_options,
                title="\nSelect a keyword to remove:",
                shortcuts=False
            )
            
            if menu_index is None:
                continue
                
            CUSTOM_KEYWORDS[category].remove(selected_keyword)
            console.print(f"[yellow]Removed keyword: [cyan]{selected_keyword}[/cyan][/yellow]")
            
            # Clean up empty lists
            if not CUSTOM_KEYWORDS[category]:
                del CUSTOM_KEYWORDS[category]
        elif selected_option == "Clear all custom keywords":
            if category in CUSTOM_KEYWORDS and CUSTOM_KEYWORDS[category]:
                if Confirm.ask(f"Are you sure you want to clear all custom keywords for {category}?", default=False, console=console):
                    del CUSTOM_KEYWORDS[category]
                    console.print(f"[yellow]Cleared all custom keywords for [cyan]{category}[/cyan].[/yellow]")
            else:
                console.print("[yellow]No custom keywords to clear.[/yellow]")

def auto_categorize_with_confirmation(assets, console):
    """
    Auto-categorizes assets with user confirmation for each suggestion.
    
    Args:
        assets: List of assets to categorize
        console: Rich console object for output
    """
    for asset in assets:
        if 'category' not in asset or asset.get('category') == 'Other':
            suggested_category = guess_category(asset['name'])
            
            console.print(f"\n[bold]Asset:[/bold] [cyan]{asset['name']}[/cyan]")
            console.print(f"[bold]Suggested Category:[/bold] [yellow]{suggested_category}[/yellow]")
            
            # Show all available categories for selection
            all_categories = sorted(get_all_categories())
            
            # Add the suggested category first if it's not already in all_categories
            if suggested_category not in all_categories:
                all_categories.insert(0, suggested_category)
            
            menu_index, selected_category = show_menu(
                all_categories,
                title="\nSelect a category (or press ESC to skip):",
                shortcuts=False
            )
            
            if menu_index is not None:
                asset['category'] = selected_category
                console.print(f"[green]Set category to: [cyan]{selected_category}[/cyan][/green]")
            else:
                console.print("[yellow]Skipped categorization.[/yellow]")

def categorize_assets(assets, console):
    """
    Allows categorizing multiple assets in sequence.
    
    Args:
        assets (list): List of asset dictionaries to categorize
        console: Rich console object for output
        
    Returns:
        bool: True if changes were saved, False if cancelled
    """
    from simple_term_menu import TerminalMenu
    from rich.prompt import Confirm
    
    if not assets:
        console.print("[yellow]No assets to categorize.[/yellow]")
        return True
    
    # Load custom keywords
    load_custom_keywords()
    
    console.print("\n[bold]ASSET CATEGORIZATION[/bold]")
    console.print("─" * 50)
    
    from net_worth_tracker import display_assets
    
    while True:
        display_assets(assets, show_balances=False, show_categories=True)
        
        # Build menu options
        options = []
        
        # Add asset options
        for idx, asset in enumerate(assets, 1):
            category = asset.get('category', 'Other')
            options.append(f"Set category for: {asset['name']} (currently: {category})")
        
        # Add utility options
        options.append("Auto-categorize all assets with confirmation")
        options.append("Auto-categorize all assets without confirmation")
        options.append("Manage category keywords")
        options.append("View all available categories")
        options.append("Done with categorization")
        options.append("Back to previous menu without saving changes")
        
        terminal_menu = TerminalMenu(
            options,
            title="\nSelect an option:",
            menu_cursor="► ",
            menu_cursor_style=("fg_black", "bold"),
            menu_highlight_style=("bg_gray", "fg_black"),
        )
        
        menu_entry_index = terminal_menu.show()
        
        # Handle ESC/q
        if menu_entry_index is None:
            console.print("[yellow]Returning to previous menu without applying category changes.[/yellow]")
            return False
            
        # Check which option was selected
        num_assets = len(assets)
        if menu_entry_index < num_assets:  # Selected an asset
            asset_idx = menu_entry_index
            set_asset_category(assets[asset_idx], console)
        elif options[menu_entry_index] == "Auto-categorize all assets with confirmation":
            auto_categorize_with_confirmation(assets, console)
        elif options[menu_entry_index] == "Auto-categorize all assets without confirmation":
            for asset in assets:
                if 'category' not in asset or asset.get('category') == 'Other':
                    asset['category'] = guess_category(asset['name'])
            console.print("[green]All assets have been auto-categorized.[/green]")
        elif options[menu_entry_index] == "Manage category keywords":
            manage_category_keywords(console)
        elif options[menu_entry_index] == "View all available categories":
            view_categories(console)
            # Wait for a key press to continue
            console.print("\n[cyan]Press Enter to continue[/cyan]")
            console.input()
        elif options[menu_entry_index] == "Done with categorization":
            return True
        elif options[menu_entry_index] == "Back to previous menu without saving changes":
            console.print("[yellow]Returning to previous menu without applying category changes.[/yellow]")
            return False
    
    return True 