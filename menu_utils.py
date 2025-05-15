from simple_term_menu import TerminalMenu
from typing import List, Optional, Tuple, Union

def create_menu(
    options: List[str],
    title: str = "",
    shortcuts: bool = True,
    return_shortcut: bool = True,
    return_label: str = "Return to previous menu"
) -> Tuple[TerminalMenu, List[str]]:
    """
    Creates a standardised menu with consistent styling and optional shortcuts.
    
    Args:
        options: List of menu options (without shortcuts)
        title: Menu title text
        shortcuts: Whether to add letter shortcuts ([a], [b], etc.)
        return_shortcut: Whether to add a return option with [r]
        return_label: Custom label for the return option
        
    Returns:
        Tuple of (TerminalMenu object, list of clean option texts without shortcuts)
    """
    menu_options = []
    clean_options = []
    
    if shortcuts:
        # Add letter shortcuts
        for idx, option in enumerate(options):
            shortcut = chr(97 + idx)  # a, b, c, etc.
            menu_options.append(f"[{shortcut}] {option}")
            clean_options.append(option)
    else:
        menu_options = options.copy()
        clean_options = options.copy()
    
    # Add return option if requested
    if return_shortcut:
        menu_options.append(f"[r] {return_label}")
        clean_options.append(return_label)
    
    # Create menu with standard styling
    terminal_menu = TerminalMenu(
        menu_options,
        title=title,
        menu_cursor="► ",
        menu_cursor_style=("fg_green", "bold"),
        menu_highlight_style=("bg_blue", "bold"),
        shortcut_key_highlight_style=("fg_yellow", "bold"),
        shortcut_brackets_highlight_style=("fg_gray", "bold"),
        show_shortcut_hints=True
    )
    
    return terminal_menu, clean_options

def show_menu(
    options: List[str],
    title: str = "",
    shortcuts: bool = True,
    return_shortcut: bool = True,
    return_label: str = "Return to previous menu"
) -> Tuple[Optional[int], str]:
    """
    Shows a standardised menu and returns the selected index and clean option text.
    
    Args:
        options: List of menu options (without shortcuts)
        title: Menu title text
        shortcuts: Whether to add letter shortcuts ([a], [b], etc.)
        return_shortcut: Whether to add a return option with [r]
        return_label: Custom label for the return option
        
    Returns:
        Tuple of (selected index or None if cancelled, selected option text without shortcuts)
    """
    terminal_menu, clean_options = create_menu(
        options,
        title,
        shortcuts,
        return_shortcut,
        return_label
    )
    
    menu_entry_index = terminal_menu.show()
    
    # Handle ESC/q or return option
    if menu_entry_index is None or (return_shortcut and menu_entry_index == len(clean_options) - 1):
        return None, ""
        
    return menu_entry_index, clean_options[menu_entry_index] 