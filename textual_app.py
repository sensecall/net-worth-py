from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Input, Label, Checkbox
from textual.containers import VerticalScroll, Horizontal, Vertical, Container
from textual.screen import ModalScreen, Screen
from textual.binding import Binding
from datetime import datetime, date
import os # For os.path.exists
from typing import Optional, List, Dict, Tuple

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

# Import screens
from screens.file_open_screen import FileOpenScreen
from screens.file_save_as_screen import FileSaveAsScreen
from screens.file_new_screen import FileNewScreen
from screens.balance_update_screen import QuickBalanceUpdateScreen
from screens.asset_management_screen import AssetManagementScreen
from screens.historical_data_screen import HistoricalDataScreen

class NetWorthApp(App):
    """A Textual app to manage and track net worth."""

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ("ctrl+s", "save_data", "Save Data"),
                ("ctrl+o", "open_file_dialog", "Open File"),
                ("ctrl+a", "save_data_as_dialog", "Save As..."),
                ("ctrl+n", "new_file_dialog", "New File"),
                ("ctrl+b", "show_balance_update_screen", "Update Balances"),
                ("ctrl+m", "show_asset_management_screen", "View & Manage Assets"),
                ("ctrl+h", "show_historical_data_screen", "View Historical Data"),
                ("q", "quit", "Quit")]

    CSS = """
    /* General App Styles */
    Screen {
        /* overflow: hidden auto; */ /* Allow app-level scroll if content exceeds screen */
    }

    Header, Footer {
        background: $primary-background-darken-1;
        color: $text;
    }

    /* Dashboard Layout */
    #dashboard_layout {
        layout: horizontal; /* Main two-column layout */
        width: 100%;
        height: 100%;
        /* overflow: auto; */ /* Let columns handle their own overflow */
    }

    .column {
        width: 1fr; /* Distribute space equally */
        height: 100%;
        padding: 0 1;
        overflow: auto; /* Allow columns to scroll if content exceeds */
    }
    
    .left_column {
        /* border-right: tall $background-lighten-2; */ /* Optional separator */
    }

    /* Dashboard Panel Styling */
    .dashboard_panel {
        border: round $primary-background-lighten-2;
        background: $surface; /* Panel background */
        padding: 1;
        margin: 1;
        height: auto; /* Adjust height based on content */
    }

    .panel_title {
        text-style: bold underline;
        padding-bottom: 1;
        width: 100%;
        text-align: center; /* Center panel titles */
    }
    
    /* Specific Panel Content Styling */
    #net_worth_value {
        content-align: center middle;
        text-style: bold;
        padding: 1 0;
        height: auto;
    }
    #net_worth_trend {
         content-align: center middle;
         padding-bottom: 1;
         height: auto;
    }
    #last_updated {
        text-align: center;
        color: $text-muted;
        height: auto;
    }

    .data_row { /* For simple key-value pairs within panels */
        padding: 0 0;
        height: auto;
        width: 100%; /* Ensure data_row spans width for text-align to work */
    }
    
    #top_categories_display {
        padding-top: 1;
        height: auto;
    }

    #total_assets,
    #total_debts,
    #liquid_assets,
    #non_liquid_assets {
        text-align: right;
    }

    /* Navigation buttons within panels */
    .nav_button {
        width: 100%;
        margin-top: 1;
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
        self.unsaved_changes = False

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
        with Horizontal(id="dashboard_layout"):
            # Left Column
            with Vertical(classes="column left_column"):
                # Net Worth Summary Panel
                with Container(classes="dashboard_panel"):
                    yield Static("Net Worth Summary", classes="panel_title")
                    yield Static(id="net_worth_value")
                    yield Static(id="net_worth_trend")
                    yield Static(id="last_updated")
                    yield Button("Update Balances (Ctrl+B)", id="update_balances_button", classes="nav_button")

                # Asset & Debt Overview Panel
                with Container(classes="dashboard_panel"):
                    # Title will be updatable
                    yield Static(id="asset_debt_title", classes="panel_title") 
                    yield Static(id="total_assets", classes="data_row")
                    yield Static(id="total_debts", classes="data_row")
            
            # Right Column
            with Vertical(classes="column right_column"):
                # Liquidity Panel
                with Container(classes="dashboard_panel"):
                    yield Static("Liquidity", classes="panel_title")
                    yield Static(id="liquid_assets", classes="data_row")
                    yield Static(id="non_liquid_assets", classes="data_row")

                # Details & Insights Panel
                with Container(classes="dashboard_panel"):
                    yield Static("Details & Insights", classes="panel_title") 
                    yield Static(id="asset_counts", classes="data_row")
                    yield Static(id="top_categories_display") 
                    yield Button("View & Manage Assets (Ctrl+M)", id="manage_assets_button", classes="nav_button")
                    yield Button("View Historical Data (Ctrl+H)", id="historical_data_button", classes="nav_button")

        yield Footer()

    def on_mount(self) -> None:
        """Load data and update the dashboard when the app starts."""
        self._load_and_prepare_data()
        self.update_dashboard()

    def update_dashboard(self) -> None:
        """Fetch data and update dashboard widgets using app's data attributes."""
        # Now uses actual data loaded into self.categories, self.financial_items, etc.
        # And the actual calculate_summary_stats function

        # Determine if data is available for certain operations/displays
        has_items = bool(self.financial_items)
        has_snapshots = bool(self.snapshots)

        if not has_items and not has_snapshots:
            # Simplified empty state update
            self.query_one("#net_worth_value", Static).update("£0.00")
            self.query_one("#net_worth_trend", Static).update("Trend: N/A")
            self.query_one("#last_updated", Static).update("Last Updated: Never")
            self.query_one("#asset_debt_title", Static).update("Asset & Debt Overview (0 Assets / 0 Liabilities)")
            self.query_one("#total_assets", Static).update("Total Assets: £0.00")
            self.query_one("#total_debts", Static).update("Total Debts: £0.00")
            self.query_one("#liquid_assets", Static).update("Liquid Assets: £0.00 (0.0%)")
            self.query_one("#non_liquid_assets", Static).update("Non-liquid Assets: £0.00")
            self.query_one("#asset_counts", Static).update("Tracked Assets: 0 across 0 categories")
            self.query_one("#top_categories_display", Static).update("Top Categories:\n  [dim]No data available.[/dim]")
            
            self.query_one("#update_balances_button", Button).disabled = True
            self.query_one("#manage_assets_button", Button).disabled = False # Can always add new assets
            self.query_one("#historical_data_button", Button).disabled = True
            return

        # Proceed with stats calculation if there's some data
        stats = calculate_summary_stats(
            self.current_snapshot_balances, # This is a list of dicts {'item_id': ..., 'balance': ...}
            self.financial_items,           # This is a list of item dicts
            self.snapshots,                 # This is a list of snapshot dicts
            self.categories                 # This is a list of category dicts
        )

        self.query_one("#net_worth_value", Static).update(f"£{stats['net_worth']:,.2f}")

        trend_text = ""
        if stats['has_previous_data']:
            trend_symbol = "↑" if stats['change_value'] > 0 else "↓" if stats['change_value'] < 0 else "→"
            trend_style = "green" if stats['change_value'] > 0 else "red" if stats['change_value'] < 0 else "yellow"
            trend_text = f"[{trend_style}]{trend_symbol} £{abs(stats['change_value']):,.2f} ({abs(stats['change_percentage']):.1f}%)[/{trend_style}]"
        self.query_one("#net_worth_trend", Static).update(trend_text)
        
        # Update Asset & Debt Overview panel title with counts
        num_assets = sum(1 for item in self.financial_items if item.get('type') == 'asset')
        num_liabilities = sum(1 for item in self.financial_items if item.get('type') == 'liability')
        asset_debt_title_text = f"Asset & Debt Overview ({num_assets} Assets / {num_liabilities} Liabilities)"
        try:
            self.query_one("#asset_debt_title", Static).update(asset_debt_title_text)
        except Exception as e:
            # Failsafe if compose order changes or widget not found immediately
            # This is less likely if IDs are unique and present during update_dashboard call
            pass # Silently ignore if widget not ready, will be populated on next update or mount

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
            top_cat_lines.append("  [dim]No category data available.[/dim]") # Dim if no data
        self.query_one("#top_categories_display", Static).update("\n".join(top_cat_lines))

        # Update button states based on data
        self.query_one("#update_balances_button", Button).disabled = not has_items
        self.query_one("#manage_assets_button", Button).disabled = False # Can always add assets
        self.query_one("#historical_data_button", Button).disabled = not (has_items and has_snapshots)

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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for the main app screen (e.g., nav buttons)."""
        if event.button.id == "manage_assets_button":
            self.action_show_asset_management_screen()
        elif event.button.id == "update_balances_button":
            self.action_show_balance_update_screen()
        elif event.button.id == "historical_data_button":
            self.action_show_historical_data_screen()
        # Add other main screen button handlers here if needed in the future

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
        """Callback for QuickBalanceUpdateScreen. Always saves/updates for TODAY's date."""
        if updated_balances is None: 
            self.notify("Balance update cancelled or no changes made.", title="Balance Update", severity="warning")
            return
        # An empty list from QuickBalanceUpdateScreen now means "no changes were confirmed by user"
        # Or if they opened and immediately hit apply without changing anything.
        # We should proceed to save this (potentially unchanged from today, or changed from historical) as today's record.

        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # The updated_balances list is a direct list of {'item_id': id, 'balance': val}
        # This will become the new self.current_snapshot_balances for today
        new_balances_for_today = updated_balances # Already in the correct format

        snapshot_updated_in_list = False
        for i, snap in enumerate(self.snapshots):
            if snap.get('date') == today_str:
                snap['balances'] = [bal.copy() for bal in new_balances_for_today] 
                snapshot_updated_in_list = True
                break
        
        if not snapshot_updated_in_list:
            self.snapshots.append({
                "date": today_str,
                "balances": [bal.copy() for bal in new_balances_for_today]
            })
        
        self.snapshots.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Crucially, update the app's main current_date and current_snapshot_balances to reflect today
        self.current_date = today_str
        self.current_snapshot_balances = [bal.copy() for bal in new_balances_for_today]

        self.update_dashboard()
        self.notify(f"Balances for {today_str} updated. Saving data...", title="Balances Updated", severity="information")
        self.action_save_data() 

    def action_show_balance_update_screen(self) -> None:
        """Pushes the QuickBalanceUpdateScreen, targeting today's date."""
        if not self.financial_items:
            self.notify("No financial items exist to update balances for.", title="No Items", severity="warning")
            return
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        balances_for_today_screen = []

        # Try to find an existing snapshot for today
        todays_snapshot = next((snap for snap in self.snapshots if snap.get('date') == today_str), None)

        if todays_snapshot:
            balances_for_today_screen = todays_snapshot.get('balances', []).copy()
        elif self.snapshots: # If no snapshot for today, use the most recent historical one as a starting point
            balances_for_today_screen = self.snapshots[0].get('balances', []).copy()
        else: # No historical snapshots either, start with zeros for all items
            balances_for_today_screen = [{'item_id': item['id'], 'balance': 0.0} for item in self.financial_items]

        # Ensure all current financial_items are represented in the balances passed to the screen
        # The QuickBalanceUpdateScreen init already handles merging/defaulting, but this provides a good base.
        current_item_ids = {item['id'] for item in self.financial_items}
        screen_balances_map = {bal['item_id']: bal['balance'] for bal in balances_for_today_screen}
        final_balances_for_screen = []
        for item_id in current_item_ids:
            final_balances_for_screen.append({
                'item_id': item_id,
                'balance': screen_balances_map.get(item_id, 0.0) # Default to 0.0 if not in snapshot
            })
        
        self.push_screen(
            QuickBalanceUpdateScreen(self.financial_items, final_balances_for_screen, app_instance=self),
            self._handle_balance_update_result
        )

    def _handle_asset_management_result(self, updated_financial_items: list | None) -> None:
        """Callback for AssetManagementScreen."""
        if updated_financial_items is None:
            self.notify("Asset management cancelled or no changes made.", title="Asset Management", severity="warning")
            return
        
        # Check if actual changes were made to avoid unnecessary saves/updates
        # This simple check might need to be more sophisticated if item order can change
        # or if only attributes of existing items are modified without changing the count.
        # For now, we'll assume any non-None list means potential changes.
        if not updated_financial_items and not self.financial_items: # Both empty, no change
            pass
        elif updated_financial_items == self.financial_items: # Simple equality check
            self.notify("No changes detected in financial items.", title="Asset Management", severity="information")
            return

        self.financial_items = updated_financial_items
        
        # Important: If items were added/deleted, snapshots might become inconsistent
        # or need updating. For now, we're just updating the core list.
        # A more robust solution would be to:
        # 1. For deleted items: Remove their balance entries from all snapshots.
        # 2. For new items: Add a default balance (e.g., 0.0) to the current snapshot, or prompt.
        # This will be part of P4's detailed implementation.

        # For now, let's create/update the current_snapshot_balances for any new/existing items
        # This is a simplified approach. A new item won't have a history, but should appear in current balances.
        existing_balances_map = {b['item_id']: b['balance'] for b in self.current_snapshot_balances}
        new_current_snapshot_balances = []
        for item in self.financial_items:
            new_current_snapshot_balances.append({
                "item_id": item['id'],
                "balance": existing_balances_map.get(item['id'], 0.0) # Keep existing, or 0.0 for new
            })
        self.current_snapshot_balances = new_current_snapshot_balances
        
        # Update snapshots (simple removal of balances for deleted items for now)
        # And ensure new items have a balance entry in the current snapshot
        # This is still a simplification; a full reconciliation might be needed.
        current_financial_item_ids = {item['id'] for item in self.financial_items}
        for snapshot in self.snapshots:
            snapshot['balances'] = [bal for bal in snapshot.get('balances', []) if bal['item_id'] in current_financial_item_ids]
            # For the current date snapshot, ensure all current items are present
            if snapshot.get('date') == self.current_date:
                snapshot_item_ids = {bal['item_id'] for bal in snapshot['balances']}
                for item_id in current_financial_item_ids:
                    if item_id not in snapshot_item_ids:
                        snapshot['balances'].append({'item_id': item_id, 'balance': 0.0})

        self.update_dashboard()
        self.notify("Financial items updated. Saving data...", title="Asset Management", severity="information")
        self.action_save_data() # Auto-save after changes

    def action_show_asset_management_screen(self) -> None:
        """Pushes the AssetManagementScreen."""
        if not self.categories:
            self.notify("Cannot manage assets without categories defined first.", title="Error", severity="error")
            return
        self.push_screen(
            AssetManagementScreen(
                app_instance=self, 
                financial_items=self.financial_items, 
                categories=self.categories,
                current_snapshot_balances=self.current_snapshot_balances
            ),
            self._handle_asset_management_result
        )

    def action_show_historical_data_screen(self) -> None:
        """Shows the historical data screen."""
        if not self.financial_items:
            self.notify("No financial items to display. Please add assets first.", severity="warning", title="Historical Data")
            return
        if not self.snapshots:
            self.notify("No historical snapshot data available. Please update balances first.", severity="warning", title="Historical Data")
            return

        # HistoricalDataScreen expects financial_items (list of dicts) and snapshots (list of dicts)
        self.push_screen(HistoricalDataScreen(financial_items=self.financial_items, snapshots=self.snapshots))

if __name__ == "__main__":
    app = NetWorthApp()
    app.run() 