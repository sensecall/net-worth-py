from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Input, Label, Checkbox
from textual.containers import VerticalScroll, Horizontal, Vertical, Container
from textual.screen import ModalScreen, Screen
from textual.binding import Binding
from datetime import datetime
import os # For os.path.exists

# Import from our project's modules
from data_manager import (
    DATA_FILENAME as DEFAULT_DATA_FILENAME,
    load_historical_data,
    save_historical_data,
    save_last_opened_file,
    load_last_opened_file
)
from core_logic import calculate_summary_stats
from asset_utils import get_default_categories

class FileOpenScreen(ModalScreen):
    """A modal screen to prompt the user for a file path to open."""

    CSS = """
    FileOpenScreen > VerticalScroll {
        align: center middle;
        background: $panel-lighten-2;
        padding: 0 1;
    }

    FileOpenScreen #dialog {
        width: 70;
        height: auto;
        padding: 1 2;
        border: thick $primary-background-darken-2;
        background: $primary-background;
    }

    FileOpenScreen Input {
        margin-bottom: 1;
        width: 100%;
    }

    FileOpenScreen Horizontal {
        align: right middle;
        height: auto;
        width: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            with Vertical(id="dialog"):
                yield Label("Enter the path to your net worth data file (.json):")
                yield Input(placeholder="/path/to/your/net_worth_data.json", id="file_path_input")
                with Horizontal():
                    yield Button("Open", variant="primary", id="open_button")
                    yield Button("Cancel", id="cancel_button")

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open_button":
            file_path_input = self.query_one("#file_path_input", Input)
            file_path = file_path_input.value.strip()
            if file_path:
                self.dismiss(file_path)
            else:
                self.notify("File path cannot be empty.", severity="error", title="Input Error")
                file_path_input.focus()
        elif event.button.id == "cancel_button":
            self.dismiss(None)

class FileSaveAsScreen(ModalScreen):
    """A modal screen to prompt for a file path to save data as."""

    CSS = """
    FileSaveAsScreen > VerticalScroll {
        align: center middle;
        background: $panel-lighten-2;
        padding: 0 1;
    }

    FileSaveAsScreen #dialog {
        width: 70;
        height: auto;
        padding: 1 2;
        border: thick $primary-background-darken-2;
        background: $primary-background;
    }

    FileSaveAsScreen Input {
        margin-bottom: 1;
        width: 100%;
    }

    FileSaveAsScreen Horizontal {
        align: right middle;
        height: auto;
        width: 100%;
    }

    FileSaveAsScreen #overwrite_warning {
        color: $warning;
        margin-top: 1;
        height: auto;
    }
    """

    def __init__(self, current_filename: str):
        super().__init__()
        self.current_filename_for_placeholder = current_filename
        self._file_exists_warning_shown = False

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            with Vertical(id="dialog"):
                yield Label("Enter path to save data as (.json):")
                yield Input(id="file_path_input", value=self.current_filename_for_placeholder)
                yield Label("Warning: File exists and will be overwritten!", id="overwrite_warning", classes="hidden")
                with Horizontal():
                    yield Button("Save As", variant="primary", id="save_as_button")
                    yield Button("Cancel", id="cancel_button")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self.query_one("#overwrite_warning", Label).display = False

    async def on_input_changed(self, event: Input.Changed) -> None:
        """Check if file exists when input changes."""
        file_path = event.value.strip()
        warning_label = self.query_one("#overwrite_warning", Label)
        if file_path and os.path.exists(file_path):
            warning_label.display = True
            self._file_exists_warning_shown = True
        else:
            warning_label.display = False
            self._file_exists_warning_shown = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_as_button":
            file_path_input = self.query_one("#file_path_input", Input)
            file_path = file_path_input.value.strip()
            if not file_path:
                self.notify("File path cannot be empty.", severity="error", title="Input Error")
                file_path_input.focus()
                return
            if not file_path.lower().endswith(".json"):
                self.notify("File name must end with .json", severity="error", title="Input Error")
                file_path_input.focus()
                return
            self.dismiss(file_path)

        elif event.button.id == "cancel_button":
            self.dismiss(None)

class FileNewScreen(ModalScreen):
    """A modal screen to prompt for a new file path and confirm overwrite."""
    CSS = """ /* Similar to FileSaveAsScreen */
    FileNewScreen > VerticalScroll {
        align: center middle;
        background: $panel-lighten-2;
        padding: 0 1;
    }
    FileNewScreen #dialog {
        width: 70;
        height: auto;
        padding: 1 2;
        border: thick $primary-background-darken-2;
        background: $primary-background;
    }
    FileNewScreen Input {
        margin-bottom: 1;
        width: 100%;
    }
    FileNewScreen Horizontal {
        align: right middle;
        height: auto;
        width: 100%;
    }
    FileNewScreen #overwrite_warning_new_file {
        color: $warning;
        margin-top: 1;
        height: auto; 
    }
    FileNewScreen #confirm_overwrite_checkbox {
        margin-top: 1;
        width: auto; /* Adjust width for checkbox */
    }
    """

    def __init__(self, default_filename: str = "new_net_worth.json"):
        super().__init__()
        self.default_filename = default_filename

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            with Vertical(id="dialog"):
                yield Label("Enter file path for new net worth data (.json):")
                yield Input(id="file_path_input", value=self.default_filename)
                yield Label("Warning: File exists! Existing data will be lost.", id="overwrite_warning_new_file", classes="hidden")
                yield Checkbox("Confirm: Overwrite if file exists and start fresh.", id="confirm_overwrite_checkbox", value=False)
                with Horizontal():
                    yield Button("Create & Start Fresh", variant="success", id="create_new_button") # Changed variant
                    yield Button("Cancel", id="cancel_button")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self.query_one("#overwrite_warning_new_file", Label).display = False
        self.query_one("#confirm_overwrite_checkbox", Checkbox).display = False # Hide checkbox initially

    async def on_input_changed(self, event: Input.Changed) -> None:
        file_path = event.value.strip()
        warning_label = self.query_one("#overwrite_warning_new_file", Label)
        overwrite_checkbox = self.query_one("#confirm_overwrite_checkbox", Checkbox)
        exists = bool(file_path and os.path.exists(file_path))
        warning_label.display = exists
        overwrite_checkbox.display = exists # Show checkbox only if file exists
        if not exists:
            overwrite_checkbox.value = False # Reset if file no longer exists or path is cleared

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create_new_button":
            file_path_input = self.query_one("#file_path_input", Input)
            file_path = file_path_input.value.strip()
            overwrite_checkbox = self.query_one("#confirm_overwrite_checkbox", Checkbox)

            if not file_path:
                self.notify("File path cannot be empty.", severity="error", title="Input Error")
                file_path_input.focus()
                return
            if not file_path.lower().endswith(".json"):
                self.notify("File name must end with .json", severity="error", title="Input Error")
                file_path_input.focus()
                return
            
            if os.path.exists(file_path) and not overwrite_checkbox.value:
                self.notify("File exists. Please confirm overwrite or choose a different name.", severity="warning", title="Confirmation Needed")
                overwrite_checkbox.focus()
                return
            
            self.dismiss(file_path) # Return the path to proceed with creation

        elif event.button.id == "cancel_button":
            self.dismiss(None)

class QuickBalanceUpdateScreen(Screen):
    """A screen to quickly update balances for financial items."""

    BINDINGS = [
        Binding("escape", "request_close", "Close", show=False, priority=True),
        Binding("ctrl+s", "apply_changes", "Apply Changes", show=True),
    ]

    CSS = """
    QuickBalanceUpdateScreen {
        align: center top; /* Center horizontally, align to top */
        padding: 2 4; /* Add some padding around the content */
    }
    #item_info_container {
        width: 80%;
        max-width: 700px; /* Max width for better readability on wide screens */
        height: auto;
        padding: 1 2;
        border: round $primary;
        margin-bottom: 1;
    }
    #item_name_label {
        text-style: bold;
        margin-bottom: 1;
    }
    #current_balance_label {
        margin-bottom: 1;
    }
    #new_balance_input {
        width: 100%;
        margin-bottom: 1;
    }
    #navigation_buttons Horizontal {
        align: center middle;
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    #action_buttons Horizontal {
        align: center middle;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, financial_items: list, current_balances: list):
        super().__init__()
        self.all_financial_items = {item['id']: item for item in financial_items}
        # Create a working copy of balances with item names for easier display
        self.items_to_update = [] 
        # Create a mapping from item_id to its current balance for quick lookup
        balance_map = {b['item_id']: b['balance'] for b in current_balances}

        for item in financial_items:
            current_val = balance_map.get(item['id'], 0.0) # Default to 0.0 if not in current snapshot
            self.items_to_update.append({
                "item_id": item['id'],
                "name": item['name'],
                "current_balance": current_val,
                "new_balance": current_val # Initialize new_balance with current_balance
            })
        
        self.current_item_idx = 0
        self.is_dirty = False # Track if any changes have been made

    def compose(self) -> ComposeResult:
        yield Header(name="Quick Balance Update")
        if not self.items_to_update:
            yield Static("No financial items to update balances for.")
            with Horizontal(id="action_buttons"):
                 yield Button("Close", id="close_no_items_button", variant="primary")
            yield Footer()
            return

        with Container(id="item_info_container"):
            yield Static(id="item_name_label")
            yield Static(id="current_balance_label")
            yield Input(id="new_balance_input", type="number", placeholder="Enter new balance")
        
        with Horizontal(id="navigation_buttons"):
            yield Button("Previous Item", id="prev_item_button")
            yield Static(id="item_counter_label", renderable="") # Will be updated in _load_item_ui
            yield Button("Next Item", id="next_item_button")

        with Horizontal(id="action_buttons"):
            yield Button("Apply Changes & Close", variant="success", id="apply_button")
            yield Button("Discard & Close", variant="error", id="discard_button")
        yield Footer()

    def on_mount(self) -> None:
        if self.items_to_update:
            self._load_item_ui(self.current_item_idx)
            self.query_one("#new_balance_input", Input).focus()
        else:
            # If no items, focus the close button if it exists
            try:
                close_button = self.query_one("#close_no_items_button", Button)
                close_button.focus()
            except Exception:
                pass # Should not happen, but safety first


    def _load_item_ui(self, idx: int) -> None:
        if not self.items_to_update or not (0 <= idx < len(self.items_to_update)):
            return

        item_data = self.items_to_update[idx]
        self.query_one("#item_name_label", Static).update(f"Item: {item_data['name']}")
        self.query_one("#current_balance_label", Static).update(f"Current Balance: £{item_data['current_balance']:,.2f}")
        new_balance_input = self.query_one("#new_balance_input", Input)
        new_balance_input.value = str(item_data['new_balance'])
        new_balance_input.focus()

        self.query_one("#item_counter_label", Static).update(f"{idx + 1} / {len(self.items_to_update)}")

        self.query_one("#prev_item_button", Button).disabled = (idx == 0)
        self.query_one("#next_item_button", Button).disabled = (idx == len(self.items_to_update) - 1)

    def _save_current_input(self) -> bool:
        if not self.items_to_update:
            return False
        try:
            new_balance_str = self.query_one("#new_balance_input", Input).value
            new_balance = float(new_balance_str)
            if self.items_to_update[self.current_item_idx]['new_balance'] != new_balance:
                self.items_to_update[self.current_item_idx]['new_balance'] = new_balance
                self.is_dirty = True
            return True
        except ValueError:
            self.app.notify("Invalid balance amount. Please enter a number.", severity="error", title="Input Error")
            self.query_one("#new_balance_input", Input).focus()
            return False
        except Exception as e:
            self.app.notify(f"Error saving input: {e}", severity="error", title="Error")
            return False

    def action_apply_changes(self):
        """Called by Ctrl+S binding or Apply button"""
        if self._save_current_input(): # Save the currently focused item's input first
            # We return a list of {'item_id': ..., 'balance': ...} dicts
            # which matches the structure of current_snapshot_balances in NetWorthApp
            result_balances = [
                {"item_id": item_d["item_id"], "balance": item_d["new_balance"]}
                for item_d in self.items_to_update
            ]
            self.dismiss(result_balances if self.is_dirty else []) # Return empty list if no changes
        # else: error already notified by _save_current_input

    def action_request_close(self):
        """Called by Escape binding or Discard button"""
        if self.is_dirty:
            # TODO: Implement a confirmation dialog here if changes are dirty
            # For now, just discard
            self.app.notify("Changes discarded.", title="Discarded", severity="warning")
        self.dismiss(None)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "prev_item_button":
            if self._save_current_input() and self.current_item_idx > 0:
                self.current_item_idx -= 1
                self._load_item_ui(self.current_item_idx)
        elif button_id == "next_item_button":
            if self._save_current_input() and self.current_item_idx < len(self.items_to_update) - 1:
                self.current_item_idx += 1
                self._load_item_ui(self.current_item_idx)
        elif button_id == "apply_button":
            self.action_apply_changes()
        elif button_id == "discard_button" or button_id == "close_no_items_button":
            self.action_request_close()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key on the input field to move to the next item or apply."""
        if event.input.id == "new_balance_input":
            if self._save_current_input():
                if self.current_item_idx < len(self.items_to_update) - 1:
                    self.current_item_idx += 1
                    self._load_item_ui(self.current_item_idx)
                else:
                    # At the last item, Enter could mean apply changes
                    self.action_apply_changes()

class NetWorthApp(App):
    """A Textual app to manage and track net worth."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ("ctrl+s", "save_data", "Save Data"),
                ("ctrl+o", "open_file_dialog", "Open File"),
                ("ctrl+a", "save_data_as_dialog", "Save As..."),
                ("ctrl+n", "new_file_dialog", "New File"),
                ("ctrl+b", "show_balance_update_screen", "Update Balances"),
                ("q", "quit", "Quit")]

    CSS = """
    VerticalScroll {
        padding: 1 2;
    }
    Static {
        padding: 1 0; 
    }
    .summary_section_title { /* Changed from ID to class */
        text-style: bold underline;
        padding: 2 0 1 0;
    }
    #net_worth_value {
        content-align: center middle;
        text-style: bold;
    }
    #net_worth_trend {
         content-align: center middle;
    }
    """

    def __init__(self):
        super().__init__()
        # Initialize app-specific data attributes
        self.categories = []
        self.financial_items = []
        self.snapshots = []
        self.current_snapshot_balances = []
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.current_data_file = DEFAULT_DATA_FILENAME
        # Note: Rich console is not directly used by Textual App, 
        # but underlying functions might print to stdout.
        # We'll pass None where a console object was expected if the function allows it,
        # or let it print to stdout for now.
        self._rich_console_for_utils = None # Or a mock/dummy if needed by utils

    def _load_and_prepare_data(self) -> None:
        """Loads data from file, prepares defaults if needed, and sets app attributes."""
        loaded_file_path = load_last_opened_file()

        if loaded_file_path and os.path.exists(loaded_file_path):
            self.current_data_file = loaded_file_path
            # Passing None as console, assuming load_historical_data handles it or prints to stdout
            cats, items, snaps = load_historical_data(self._rich_console_for_utils, self.current_data_file)
            if cats is not None: # Data loaded successfully
                self.categories = cats
                self.financial_items = items
                self.snapshots = snaps
                save_last_opened_file(self.current_data_file) # Confirm this file as last opened
            else: # Failed to load specific file, attempt default or start fresh
                loaded_file_path = None # Fall through to try default or start fresh
                self.notify("Failed to load last opened file. Trying default.", title="Data Load Warning", severity="warning")


        if not loaded_file_path and os.path.exists(DEFAULT_DATA_FILENAME):
            self.current_data_file = DEFAULT_DATA_FILENAME
            cats, items, snaps = load_historical_data(self._rich_console_for_utils, self.current_data_file)
            if cats is not None:
                self.categories = cats
                self.financial_items = items
                self.snapshots = snaps
                save_last_opened_file(self.current_data_file)
            else: # Failed to load default file
                 self.notify(f"Failed to load default file ({DEFAULT_DATA_FILENAME}). Starting with empty data.", title="Data Load Error", severity="error")
                 self.categories = get_default_categories()
                 # Ensure current_data_file is set to DEFAULT_DATA_FILENAME before trying to save_last_opened_file with it
                 self.current_data_file = DEFAULT_DATA_FILENAME 
                 save_last_opened_file(self.current_data_file) # Save even if starting fresh with default name

        elif not loaded_file_path: # No last file, no default file found, start fresh
            self.notify(f"No data file found. Starting fresh. Data will be saved to {self.current_data_file}.", title="New Setup", severity="information")
            self.categories = get_default_categories()
            # financial_items and snapshots remain empty
            self.current_data_file = DEFAULT_DATA_FILENAME # Ensure it's set for potential save
            save_last_opened_file(self.current_data_file) # Save this as the file to use

        # Determine current snapshot balances and date from loaded data
        if self.snapshots:
            # Snapshots are assumed to be sorted newest first by load_historical_data
            most_recent_snapshot = self.snapshots[0]
            self.current_date = most_recent_snapshot.get('date', self.current_date)
            self.current_snapshot_balances = most_recent_snapshot.get('balances', []).copy()
        else:
            # No snapshots, so no balances. current_date is already today.
            # If we have financial_items but no snapshot, create an initial empty balance set for them
            if self.financial_items and not self.current_snapshot_balances:
                self.current_snapshot_balances = [
                    {"item_id": item['id'], "balance": 0.0} for item in self.financial_items
                ]
                # Potentially create an initial snapshot for today if none exist?
                # For now, just ensuring current_snapshot_balances reflects items.


    def action_save_data(self) -> None:
        """Saves the current financial data to the file."""
        try:
            save_historical_data(
                self._rich_console_for_utils, 
                self.categories, 
                self.financial_items, 
                self.snapshots, 
                self.current_data_file
            )
            self.notify(f"Data saved successfully to {self.current_data_file}", title="Save Successful", severity="information")
        except Exception as e:
            self.notify(f"Error saving data: {e}", title="Save Error", severity="error")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with VerticalScroll(id="dashboard_content"):
            yield Static("Net Worth Summary", classes="summary_section_title")
            yield Static(id="net_worth_value")
            yield Static(id="net_worth_trend")
            yield Static(id="last_updated")
            
            yield Static("Asset & Debt Overview", classes="summary_section_title")
            yield Static(id="total_assets")
            yield Static(id="total_debts")
            
            yield Static("Liquidity", classes="summary_section_title")
            yield Static(id="liquid_assets")
            yield Static(id="non_liquid_assets")
            
            yield Static("Counts", classes="summary_section_title")
            yield Static(id="asset_counts")
            
            yield Static("Top Categories", classes="summary_section_title")
            yield Static(id="top_categories_display")
        yield Footer()

    def on_mount(self) -> None:
        """Load data and update the dashboard when the app starts."""
        self._load_and_prepare_data()
        self.update_dashboard()

    def update_dashboard(self) -> None:
        """Fetch data and update dashboard widgets using app's data attributes."""
        # Now uses actual data loaded into self.categories, self.financial_items, etc.
        # And the actual calculate_summary_stats function
        stats = calculate_summary_stats(
            self.current_snapshot_balances,
            self.financial_items,
            self.snapshots,
            self.categories
        )

        self.query_one("#net_worth_value", Static).update(f"£{stats['net_worth']:,.2f}")

        trend_text = ""
        if stats['has_previous_data']:
            trend_symbol = "↑" if stats['change_value'] > 0 else "↓" if stats['change_value'] < 0 else "→"
            trend_style = "green" if stats['change_value'] > 0 else "red" if stats['change_value'] < 0 else "yellow"
            trend_text = f"[{trend_style}]{trend_symbol} £{abs(stats['change_value']):,.2f} ({abs(stats['change_percentage']):.1f}%)[/{trend_style}]"
        self.query_one("#net_worth_trend", Static).update(trend_text)
        
        # Ensure current_date is valid before trying to parse it
        try:
            formatted_date = datetime.strptime(self.current_date, '%Y-%m-%d').strftime('%d %B %Y')
        except ValueError:
            formatted_date = "Unknown" # Fallback if date format is unexpected
            self.notify(f"Warning: Could not parse date '{self.current_date}'.", severity="warning")

        self.query_one("#last_updated", Static).update(f"Last Updated: {formatted_date}")
        self.query_one("#total_assets", Static).update(f"Total Assets: £{stats['total_assets_value']:,.2f}")
        self.query_one("#total_debts", Static).update(f"Total Debts: £{stats['total_debts_value']:,.2f}")
        self.query_one("#liquid_assets", Static).update(f"Liquid Assets: £{stats['liquid_assets_value']:,.2f} ({stats['liquid_percentage']:.1f}%)")
        self.query_one("#non_liquid_assets", Static).update(f"Non-liquid Assets: £{stats['non_liquid_assets_value']:,.2f}")
        self.query_one("#asset_counts", Static).update(f"Tracked Assets: {stats['asset_count']} across {stats['category_count']} categories")

        top_cat_lines = ["Top Categories:"]
        if stats['top_categories']:
            for category, value in stats['top_categories']:
                top_cat_lines.append(f"  - {category}: £{value:,.2f}")
        else:
            top_cat_lines.append("  No category data available.")
        self.query_one("#top_categories_display", Static).update("\n".join(top_cat_lines))

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def _handle_open_file_result(self, file_path: str | None) -> None:
        """Callback to handle the result from FileOpenScreen."""
        if file_path:
            if not os.path.exists(file_path):
                self.notify(f"Error: File not found at '{file_path}'.", title="File Open Error", severity="error")
                return
            if not file_path.lower().endswith(".json"):
                self.notify(f"Error: Invalid file type. Please select a .json file.", title="File Open Error", severity="error")
                return

            # Attempt to load data from the new path
            cats, items, snaps = load_historical_data(self._rich_console_for_utils, file_path)

            if cats is not None: # Data loaded successfully
                self.current_data_file = file_path
                self.categories = cats
                self.financial_items = items
                self.snapshots = snaps
                
                # Update current_date and current_snapshot_balances from newly loaded data
                if self.snapshots:
                    most_recent_snapshot = self.snapshots[0]
                    self.current_date = most_recent_snapshot.get('date', datetime.now().strftime("%Y-%m-%d"))
                    self.current_snapshot_balances = most_recent_snapshot.get('balances', []).copy()
                else:
                    self.current_date = datetime.now().strftime("%Y-%m-%d")
                    self.current_snapshot_balances = []
                    if self.financial_items: # If new file has items but no snapshots
                         self.current_snapshot_balances = [{'item_id': item['id'], 'balance': 0.0} for item in self.financial_items]

                save_last_opened_file(self.current_data_file)
                self.update_dashboard()
                self.notify(f"Successfully loaded data from {self.current_data_file}", title="File Opened", severity="information")
            else:
                self.notify(f"Failed to load data from '{file_path}'. It might be corrupted or not in the correct format.", title="File Open Error", severity="error")
        else:
            self.notify("File open cancelled.", title="Cancelled", severity="warning")

    def action_open_file_dialog(self) -> None:
        """Pushes the FileOpenScreen to get a file path from the user."""
        self.push_screen(FileOpenScreen(), self._handle_open_file_result)

    def _handle_save_data_as_result(self, file_path: str | None) -> None:
        """Callback to handle the result from FileSaveAsScreen."""
        if file_path:
            # Basic validation (already done in screen, but good for safety)
            if not file_path.lower().endswith(".json"):
                self.notify("Error: Invalid file type. Must be .json.", title="Save As Error", severity="error")
                return

            # The actual save operation
            try:
                # Check for existence again, in case it was created between dialog and now (less likely but possible)
                # For a truly robust overwrite confirmation, the dialog itself should handle a confirm step.
                # For now, we proceed if a path is given.
                
                self.current_data_file = file_path # Update current file to the new path
                save_historical_data(
                    self._rich_console_for_utils,
                    self.categories,
                    self.financial_items,
                    self.snapshots,
                    self.current_data_file
                )
                save_last_opened_file(self.current_data_file) # Remember this new file as the last one
                self.notify(f"Data successfully saved as {self.current_data_file}", title="Save As Successful", severity="information")
                # No dashboard refresh needed unless data changed, but file context has.
            except Exception as e:
                self.notify(f"Error saving data to '{file_path}': {e}", title="Save As Error", severity="error")
        else:
            self.notify("Save As operation cancelled.", title="Cancelled", severity="warning")

    def action_save_data_as_dialog(self) -> None:
        """Pushes the FileSaveAsScreen to get a new file path from the user."""
        self.push_screen(FileSaveAsScreen(current_filename=self.current_data_file), self._handle_save_data_as_result)

    def _handle_new_file_result(self, file_path: str | None) -> None:
        """Callback to handle the result from FileNewScreen."""
        if file_path:
            try:
                # Path validation already handled more comprehensively in the screen
                self.current_data_file = file_path
                self.categories = get_default_categories()
                self.financial_items = []
                self.snapshots = [] # Ensure snapshots are cleared for a new file
                self.current_snapshot_balances = []
                self.current_date = datetime.now().strftime("%Y-%m-%d")

                save_historical_data( # Save the new empty/default structure
                    self._rich_console_for_utils,
                    self.categories,
                    self.financial_items,
                    self.snapshots,
                    self.current_data_file
                )
                save_last_opened_file(self.current_data_file)
                self.update_dashboard() # Refresh dashboard with new empty state
                self.notify(f"New data file '{self.current_data_file}' created and loaded.", title="New File Created", severity="information")
            except Exception as e:
                self.notify(f"Error creating new file '{file_path}': {e}", title="New File Error", severity="error")
        else:
            self.notify("New file operation cancelled.", title="Cancelled", severity="warning")

    def action_new_file_dialog(self) -> None:
        """Pushes the FileNewScreen to get a file path for a new data set."""
        self.push_screen(FileNewScreen(default_filename=f"net_worth_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"), self._handle_new_file_result)

    def _handle_balance_update_result(self, updated_balances: list | None) -> None:
        """Callback for QuickBalanceUpdateScreen."""
        if updated_balances is None: # User cancelled or closed without applying
            self.notify("Balance update cancelled or no changes made.", title="Balance Update", severity="warning")
            return
        if not updated_balances: # Empty list returned if no actual changes were made
             self.notify("No changes were made to balances.", title="Balance Update", severity="information")
             return

        # Update self.current_snapshot_balances
        # The updated_balances list is a direct replacement for balance entries with matching item_ids
        new_balances_map = {b['item_id']: b['balance'] for b in updated_balances}
        updated_current_snapshot_balances = []
        found_ids_in_update = set()

        for current_b_entry in self.current_snapshot_balances:
            item_id = current_b_entry['item_id']
            if item_id in new_balances_map:
                updated_current_snapshot_balances.append({"item_id": item_id, "balance": new_balances_map[item_id]})
                found_ids_in_update.add(item_id)
            else:
                # This item was in current_snapshot_balances but not in the items_to_update list shown on screen.
                # This shouldn't happen if items_to_update is derived from all financial_items for the current snapshot.
                # However, to be safe, keep its old balance.
                updated_current_snapshot_balances.append(current_b_entry)
        
        # Add any new items that might have been in `updated_balances` but not `current_snapshot_balances`
        # (e.g., if `current_snapshot_balances` was empty or missing some items listed in `financial_items`)
        for ub_entry in updated_balances:
            if ub_entry['item_id'] not in found_ids_in_update:
                updated_current_snapshot_balances.append(ub_entry)
        
        self.current_snapshot_balances = updated_current_snapshot_balances

        # Update self.snapshots
        snapshot_updated_in_list = False
        for i, snap in enumerate(self.snapshots):
            if snap.get('date') == self.current_date:
                snap['balances'] = [bal.copy() for bal in self.current_snapshot_balances] # Store a copy
                snapshot_updated_in_list = True
                break
        
        if not snapshot_updated_in_list:
            # No snapshot for current_date, create a new one
            self.snapshots.append({
                "date": self.current_date,
                "balances": [bal.copy() for bal in self.current_snapshot_balances] # Store a copy
            })
            # Re-sort snapshots if a new one was added (newest first)
            self.snapshots.sort(key=lambda x: x.get('date', ''), reverse=True)

        self.update_dashboard()
        self.notify("Balances updated. Saving data...", title="Balances Updated", severity="information")
        self.action_save_data() # Auto-save after balance updates

    def action_show_balance_update_screen(self) -> None:
        """Pushes the QuickBalanceUpdateScreen."""
        if not self.financial_items:
            self.notify("No financial items exist to update balances for.", title="No Items", severity="warning")
            return
        
        # We need to ensure that current_snapshot_balances reflects all financial_items, 
        # even if they don't have an explicit balance entry for the current_date yet.
        # The QuickBalanceUpdateScreen's __init__ handles merging these.
        self.push_screen(
            QuickBalanceUpdateScreen(self.financial_items, self.current_snapshot_balances),
            self._handle_balance_update_result
        )

if __name__ == "__main__":
    app = NetWorthApp()
    app.run() 