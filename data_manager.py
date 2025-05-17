import json
import os # For os.path.exists, etc.

# Default data file name
DATA_FILENAME = "net_worth_refactored.json"
APP_CONFIG_FILENAME = "app_config.json" # Configuration file

def load_historical_data(console, filename=None):
    """Loads all data (categories, financial_items, snapshots, achieved_milestones, financial_goal) from the JSON file."""
    if filename is None:
        filename = DATA_FILENAME
    
    default_return = [], [], [], [], None # Added None for financial_goal

    try:
        with open(filename, 'r') as f:
            data = json.load(f)

        # Validate the basic structure
        if not isinstance(data, dict) or \
           'categories' not in data or \
           'financial_items' not in data or \
           'snapshots' not in data: # achieved_milestones & financial_goal are optional for backward compatibility
            if console:
                console.print(f"[red]Error: Data file [cyan]{filename}[/cyan] is not in the expected new format.[/red]")
                console.print("[yellow]Expected format: {'categories': ..., 'financial_items': ..., 'snapshots': ..., 'achieved_milestones': ... (opt), 'financial_goal': ... (opt)}[/yellow]")
            return default_return

        categories = data.get('categories', [])
        financial_items = data.get('financial_items', [])
        snapshots = data.get('snapshots', [])
        achieved_milestones = data.get('achieved_milestones', []) 
        financial_goal = data.get('financial_goal', None) # Load financial_goal, default to None

        # Ensure each financial item has a 'target_balance' key, defaulting to None for backward compatibility
        for item in financial_items:
            if 'target_balance' not in item:
                item['target_balance'] = None

        # Sort snapshots by date, most recent first
        snapshots = sorted(snapshots, key=lambda x: x.get('date', ''), reverse=True)
        
        if console:
            console.print(f"[green]Successfully loaded data from [cyan]{filename}[/cyan].[/green]")
        return categories, financial_items, snapshots, achieved_milestones, financial_goal

    except FileNotFoundError:
        if console:
            console.print(f"[yellow]Data file [cyan]{filename}[/cyan] not found. Starting with empty data.[/yellow]")
        return default_return
    except json.JSONDecodeError:
        if console:
            console.print(f"[red]Error: Could not decode JSON from [cyan]{filename}[/cyan]. File might be corrupted.[/red]")
        return default_return
    except Exception as e:
        if console:
            console.print(f"[red]An unexpected error occurred while loading data from {filename}: {e}[/red]")
        return default_return

def save_historical_data(console, categories, financial_items, snapshots, achieved_milestones, financial_goal, filename=None):
    """Saves all data (categories, financial_items, snapshots, achieved_milestones, financial_goal) to the JSON file."""
    if filename is None:
        filename = DATA_FILENAME

    # Ensure snapshots are sorted by date, most recent first, for consistent file structure
    snapshots_sorted = sorted(snapshots, key=lambda x: x.get('date', ''), reverse=True)

    data_to_save = {
        "categories": categories,
        "financial_items": financial_items,
        "snapshots": snapshots_sorted,
        "achieved_milestones": achieved_milestones,
        "financial_goal": financial_goal # Add financial_goal to save data
    }

    try:
        with open(filename, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        if console:
            console.print(f"\n[green]All data saved to [cyan]{filename}[/cyan][/green]")
    except IOError:
        if console:
            console.print(f"\n[bold red]Error: Could not save data to [cyan]{filename}[/cyan][/bold red]")
    except Exception as e:
        if console:
            console.print(f"\n[bold red]An unexpected error occurred while saving data to {filename}: {e}[/bold red]")

# --- Functions for remembering the last opened file ---

def save_last_opened_file(filepath: str):
    """Saves the path of the last opened/used data file."""
    try:
        with open(APP_CONFIG_FILENAME, 'w') as f:
            json.dump({"last_opened_file": filepath}, f, indent=4)
        # print(f"[dim]Last opened file path '{filepath}' saved to config.[/dim]") # Optional debug print
    except IOError:
        # Non-critical, so we might not want to bother the user too much
        # print(f"[yellow dim]Warning: Could not save last opened file path to {APP_CONFIG_FILENAME}.[/yellow dim]")
        pass
    except Exception as e:
        # print(f"[yellow dim]Warning: An unexpected error occurred while saving last opened file path: {e}[/yellow dim]")
        pass

def load_last_opened_file() -> str | None:
    """Loads the path of the last opened data file from the config.
       Returns the path as a string, or None if not found or error.
    """
    if not os.path.exists(APP_CONFIG_FILENAME):
        return None
    try:
        with open(APP_CONFIG_FILENAME, 'r') as f:
            config_data = json.load(f)
            return config_data.get("last_opened_file")
    except (IOError, json.JSONDecodeError):
        # If file is corrupted or unreadable, act as if no config exists
        return None
    except Exception:
        # Catch any other unexpected error during load
        return None 