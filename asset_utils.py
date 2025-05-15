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
    "Savings": ["savings", "premium bonds"],
    "Current Account": ["current", "monzo current", "nationwide current"],
    "Investment": ["shares", "stocks", "investment", "fund"],
    "Mortgage": ["mortgage"],
    "Loan": ["loan"],
    "Credit Card": ["credit", "amex"],
    "Business": ["business"]
}

# Store custom categories that users have added during the session
CUSTOM_CATEGORIES = set()

def add_custom_category(category_name):
    """
    Adds a new custom category to the session.
    
    Args:
        category_name (str): The name of the new category
    """
    global CUSTOM_CATEGORIES
    CUSTOM_CATEGORIES.add(category_name)

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
    
    for category, keywords in AUTO_CATEGORIZE_RULES.items():
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
    Sets or changes the category for an existing asset.
    
    Args:
        asset (dict): The asset dictionary to modify
        console: Rich console object for output
    """
    current_category = asset.get('category', 'Other')
    console.print(f"\nCurrent category for [cyan]'{asset['name']}'[/cyan]: [green]{current_category}[/green]")
    
    all_categories = get_all_categories()
    for idx, category in enumerate(all_categories, 1):
        console.print(f"  {idx}. {category}")
    
    console.print(f"  C. Custom category")
    
    user_input = console.input("Your choice (or Enter to keep current): ").strip()
    
    if not user_input:
        return  # Keep current category
    elif user_input.lower() == 'c':
        custom_category = console.input("Enter custom category name: ").strip()
        if custom_category:
            add_custom_category(custom_category)
            asset['category'] = custom_category
            console.print(f"[green]Category set to '{custom_category}'.[/green]")
    else:
        try:
            idx = int(user_input)
            if 1 <= idx <= len(all_categories):
                asset['category'] = all_categories[idx-1]
                console.print(f"[green]Category set to '{all_categories[idx-1]}'.[/green]")
            else:
                console.print("[red]Invalid choice. Category not changed.[/red]")
        except ValueError:
            console.print("[red]Invalid input. Category not changed.[/red]")

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
    Displays all available categories (default and custom).
    
    Args:
        console: Rich console object for output
    """
    from simple_term_menu import TerminalMenu
    
    console.print("\n[bold blue]------------------------------------[/bold blue]")
    console.print("[bold blue]Available Categories[/bold blue]")
    console.print("[bold blue]------------------------------------[/bold blue]")
    
    console.print("[bold green]Default Categories:[/bold green]")
    for idx, category in enumerate(DEFAULT_CATEGORIES, 1):
        console.print(f"  {idx}. {category}")
    
    if CUSTOM_CATEGORIES:
        console.print("\n[bold magenta]Custom Categories:[/bold magenta]")
        for idx, category in enumerate(sorted(list(CUSTOM_CATEGORIES - set(DEFAULT_CATEGORIES))), 1):
            console.print(f"  {idx}. {category}")
    else:
        console.print("\n[dim]No custom categories defined.[/dim]")
    
    # Add a menu with a back option
    options = ["Return to previous menu"]
    
    back_menu = TerminalMenu(
        options,
        title="\nPress Enter to return",
        menu_cursor="► ",
        menu_cursor_style=("fg_green", "bold"),
        menu_highlight_style=("bg_blue", "bold"),
    )
    
    back_menu.show()

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
    
    if not assets:
        console.print("[yellow]No assets to categorize.[/yellow]")
        return True
    
    console.print("\n[bold blue]------------------------------------[/bold blue]")
    console.print("[bold blue]Asset Categorization[/bold blue]")
    console.print("[bold blue]------------------------------------[/bold blue]")
    
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
        options.append("Auto-categorize all assets")
        options.append("View all available categories")
        options.append("Done with categorization")
        options.append("Back to previous menu without saving changes")
        
        terminal_menu = TerminalMenu(
            options,
            title="\nSelect an option:",
            menu_cursor="► ",
            menu_cursor_style=("fg_green", "bold"),
            menu_highlight_style=("bg_blue", "bold"),
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
        elif options[menu_entry_index] == "Auto-categorize all assets":
            for asset in assets:
                if 'category' not in asset or asset.get('category') == 'Other':
                    asset['category'] = guess_category(asset['name'])
            console.print("[green]All assets have been auto-categorized.[/green]")
        elif options[menu_entry_index] == "View all available categories":
            view_categories(console)
            # Wait for a key press to continue
            console.print("\n[cyan]Press any key to continue[/cyan]")
            try:
                import readchar
                readchar.readkey()
            except Exception:
                console.input("Press Enter to continue")
        elif options[menu_entry_index] == "Done with categorization":
            return True
        elif options[menu_entry_index] == "Back to previous menu without saving changes":
            console.print("[yellow]Returning to previous menu without applying category changes.[/yellow]")
            return False
    
    return True 