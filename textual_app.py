from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Input, Label, Checkbox, ProgressBar
from textual.containers import VerticalScroll, Horizontal, Vertical, Container
from textual.screen import ModalScreen, Screen
from textual.binding import Binding
from datetime import datetime, date
import os # For os.path.exists
from typing import Optional, List, Dict, Tuple, Any

# Import from our project's modules
from data_manager import (
    DATA_FILENAME as DEFAULT_DATA_FILENAME,
    load_historical_data,
    save_historical_data,
    save_last_opened_file,
    load_last_opened_file
)
from core_logic import (
    calculate_summary_stats, 
    STANDARD_MILESTONES, 
    calculate_enhanced_trends,
    update_and_get_milestone_progress,
    calculate_goal_projection
)
from asset_utils import get_default_categories

# Import screens
from screens.file_open_screen import FileOpenScreen
from screens.file_save_as_screen import FileSaveAsScreen
from screens.file_new_screen import FileNewScreen
from screens.balance_update_screen import QuickBalanceUpdateScreen
from screens.asset_management_screen import AssetManagementScreen
from screens.historical_data_screen import HistoricalDataScreen
from screens.financial_goal_screen import FinancialGoalScreen
from screens.item_targets_screen import ItemTargetsScreen

class NetWorthApp(App):
    """A Textual app to manage and track net worth."""

    BINDINGS = [("ctrl+s", "save_data", "Save Data"),
                ("ctrl+o", "open_file_dialog", "Open File"),
                ("ctrl+a", "save_data_as_dialog", "Save As..."),
                ("ctrl+n", "new_file_dialog", "New File"),
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
        margin: 1 0; /* Tighter vertical spacing */
        background: $surface-darken-1; /* Slightly darker than panel for definition */
        color: $text; /* Ensure text is readable */
        text-style: bold; /* Make button text bold */
        height: auto; /* Allow height to be determined by content + padding */
        padding: 0 1; /* Add some horizontal padding inside the button */
    }

    .nav_button:hover {
        background: $surface-lighten-1; /* Lighter on hover for feedback */
        color: $text; /* Ensure text color remains consistent */
    }

    /* Styling for ProgressBars to make them stand out */
    .visual_progress_bar {
        border: round $primary-lighten-2;
        margin: 1 0;
        height: 1; /* Ensures the bar itself is visible with a border */
        /* bar-background: $primary-background-darken-2; */ /* This was the track, we'll adjust this next if needed */
    }

    .visual_progress_bar > .bar--bar {
        /* background: $primary-lighten-1; */ /* REMOVING THIS to use default bar color */
        /* color: $text; */ /* Text color for on-bar percentage (not currently used) */
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
        self.achieved_milestones: List[Any] = [] # Initialize achieved_milestones
        self.financial_goal: Optional[Dict[str, Any]] = None # Initialize financial_goal

    def _load_and_prepare_data(self) -> None:
        """Loads data from file, prepares defaults if needed, and sets app attributes."""
        loaded_file_path = load_last_opened_file()
        data_loaded_successfully = False

        if loaded_file_path and os.path.exists(loaded_file_path):
            self.current_data_file = loaded_file_path
            # Load data including achieved_milestones and financial_goal
            loaded_data = load_historical_data(self._rich_console_for_utils, self.current_data_file)
            if loaded_data and len(loaded_data) == 5: # Expect 5 elements now
                self.categories, self.financial_items, self.snapshots, self.achieved_milestones, self.financial_goal = loaded_data
                save_last_opened_file(self.current_data_file) # Confirm this file as last opened
                data_loaded_successfully = True
            else: # Failed to load specific file correctly, attempt default or start fresh
                loaded_file_path = None # Fall through to try default or start fresh
                self.notify("Failed to load last opened file or data was incomplete (expected goal data). Trying default.", title="Data Load Warning", severity="warning")
                self.achieved_milestones = [] # Reset if load failed
                self.financial_goal = None # Reset if load failed

        if not data_loaded_successfully and os.path.exists(DEFAULT_DATA_FILENAME):
            self.current_data_file = DEFAULT_DATA_FILENAME
            loaded_data = load_historical_data(self._rich_console_for_utils, self.current_data_file)
            if loaded_data and len(loaded_data) == 5: # Expect 5 elements
                self.categories, self.financial_items, self.snapshots, self.achieved_milestones, self.financial_goal = loaded_data
                save_last_opened_file(self.current_data_file)
                data_loaded_successfully = True
            else: # Failed to load default file
                 self.notify(f"Failed to load default file ({DEFAULT_DATA_FILENAME}) or data was incomplete (expected goal data). Starting with empty data.", title="Data Load Error", severity="error")
                 self.categories = get_default_categories()
                 self.financial_items = []
                 self.snapshots = []
                 self.achieved_milestones = [] # Reset for fresh start
                 self.financial_goal = None # Reset for fresh start
                 self.current_data_file = DEFAULT_DATA_FILENAME
                 save_last_opened_file(self.current_data_file)

        elif not data_loaded_successfully: # No last file, no default file found, or loads failed; start fresh
            self.notify(f"No data file found or load failed. Starting fresh. Data will be saved to {self.current_data_file}.", title="New Setup", severity="information")
            self.categories = get_default_categories()
            self.financial_items = []
            self.snapshots = []
            self.achieved_milestones = [] # Reset for fresh start
            self.financial_goal = None # Reset for fresh start
            self.current_data_file = DEFAULT_DATA_FILENAME
            save_last_opened_file(self.current_data_file)

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
                self.achieved_milestones,
                self.financial_goal, # Pass financial_goal
                self.current_data_file
            )
            self.notify(f"Data saved successfully to {self.current_data_file}", title="Save Successful", severity="information")
            self.unsaved_changes = False # Reset unsaved changes flag
        except Exception as e:
            self.notify(f"Error saving data: {e}", title="Save Error", severity="error")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Horizontal(id="dashboard_layout"):
            # Left Column
            with Vertical(classes="column left_column"):
                # Net Worth Summary Panel (Now includes main navigation)
                with Container(classes="dashboard_panel"):
                    yield Static("Net Worth Summary", classes="panel_title")
                    yield Static(id="net_worth_value")
                    # yield Static(id="net_worth_trend") # Removed
                    yield Static(id="last_updated")
                    # Navigation buttons moved here
                    yield Button("Update Balances", id="update_balances_button", classes="nav_button")
                    yield Button("View & Manage Items", id="manage_assets_button", classes="nav_button")
                    yield Button("Manage Item Targets", id="manage_item_targets_button", classes="nav_button")
                    yield Button("View Historical Data", id="historical_data_button", classes="nav_button")
                    yield Button("Set/Edit Financial Goal", id="set_goal_button", classes="nav_button") # Moved from Progress & Goals

                # Financial Snapshot Panel (Stays in left column)
                with Container(classes="dashboard_panel", id="financial_snapshot_panel"):
                    yield Static("Financial Snapshot", classes="panel_title")
                    yield Static(id="total_assets_snapshot", classes="data_row")
                    yield Static(id="total_debts_snapshot", classes="data_row")
                    yield Static(id="liquid_assets_snapshot", classes="data_row")
                    yield Static(id="non_liquid_assets_snapshot", classes="data_row")
                    yield Static(id="asset_debt_count_summary", classes="data_row")
            
                # Progress & Goals Panel (No longer here, moved to right column)
                # with Container(classes="dashboard_panel", id="fire_insights_panel"):
                #    ...

            # Right Column
            with Vertical(classes="column right_column"):
                # Progress & Goals Panel (Moved here from left column)
                with Container(classes="dashboard_panel", id="fire_insights_panel"):
                    yield Static("Progress & Goals", classes="panel_title")
                    yield Static("Enhanced Trends:", classes="data_row sub_header") 
                    yield Static(id="avg_trend_3m_display", classes="data_row")
                    yield Static(id="avg_trend_6m_display", classes="data_row")
                    yield Static(id="avg_trend_12m_display", classes="data_row")
                    yield Static("Milestones:", classes="data_row sub_header") 
                    yield Static(id="next_milestone_display", classes="data_row")
                    yield ProgressBar(id="milestone_progress_bar", total=100, show_eta=False, classes="visual_progress_bar")
                    yield Static(id="milestone_progress_display", classes="data_row") 
                    yield Static("Financial Goal:", classes="data_row sub_header") 
                    yield Static(id="financial_goal_target_display", classes="data_row")
                    yield ProgressBar(id="financial_goal_progress_bar", total=100, show_eta=False, classes="visual_progress_bar")
                    yield Static(id="financial_goal_projection_display", classes="data_row")
                    # Button "Set/Edit Financial Goal" (id="set_goal_button") was here, but moved to Net Worth Summary

                # Explore & Act Panel (REMOVED)
                # with Container(classes="dashboard_panel", id="explore_act_panel"):
                #    ...

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
            self.query_one("#net_worth_value", Static).update(f"[bold green]£0.00[/bold green]")
            self.query_one("#last_updated", Static).update("Last Updated: Never")
            # Update new Financial Snapshot panel for empty state
            self.query_one("#total_assets_snapshot", Static).update(f"Total Assets: [bold green]£0.00[/bold green]")
            self.query_one("#total_debts_snapshot", Static).update(f"Total Debts: [bold red]£0.00[/bold red]")
            self.query_one("#liquid_assets_snapshot", Static).update(f"Liquid Assets: [bold green]£0.00[/bold green] ([bold #D3D3D3]0.0%[/bold #D3D3D3])")
            self.query_one("#non_liquid_assets_snapshot", Static).update(f"Non-liquid Assets: [bold green]£0.00[/bold green]")
            self.query_one("#asset_debt_count_summary", Static).update("(Summary based on 0 Assets / 0 Liabilities)")
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

        self.query_one("#net_worth_value", Static).update(f"[bold green]£{stats['net_worth']:,.2f}[/bold green]")

        # The old simple trend is now GONE.
        # self.query_one("#net_worth_trend", Static).update("") # Removed
        
        # Update Asset & Debt Overview panel title with counts (Now part of Financial Snapshot summary's asset_debt_count_summary)
        num_assets = sum(1 for item in self.financial_items if item.get('type') == 'asset')
        num_liabilities = sum(1 for item in self.financial_items if item.get('type') == 'liability')
        asset_debt_summary_text = f"(Summary based on {num_assets} Assets / {num_liabilities} Liabilities)"
        self.query_one("#asset_debt_count_summary", Static).update(asset_debt_summary_text)

        # Ensure current_date is valid before trying to parse it
        try:
            formatted_date = datetime.strptime(self.current_date, '%Y-%m-%d').strftime('%d %B %Y')
        except ValueError:
            formatted_date = "Unknown" # Fallback if date format is unexpected
            self.notify(f"Warning: Could not parse date '{self.current_date}'.", severity="warning")

        self.query_one("#last_updated", Static).update(f"Last Updated: {formatted_date}")
        # Update new Financial Snapshot panel widgets
        self.query_one("#total_assets_snapshot", Static).update(f"Total Assets: [bold green]£{stats['total_assets_value']:,.2f}[/bold green]")
        self.query_one("#total_debts_snapshot", Static).update(f"Total Debts: [bold red]£{stats['total_debts_value']:,.2f}[/bold red]")
        self.query_one("#liquid_assets_snapshot", Static).update(f"Liquid Assets: [bold green]£{stats['liquid_assets_value']:,.2f}[/bold green] ([bold #D3D3D3]{stats['liquid_percentage']:.1f}%[/bold #D3D3D3])")
        self.query_one("#non_liquid_assets_snapshot", Static).update(f"Non-liquid Assets: [bold green]£{stats['non_liquid_assets_value']:,.2f}[/bold green]")

        # Remove old widget updates for Explore & Act panel elements
        # self.query_one("#asset_counts", Static).update(f"Tracked Assets: {stats['asset_count']} across {stats['category_count']} categories") # Removed

        # top_cat_lines = ["Top Categories:"]
        # if stats['top_categories']:
        #     for category, value in stats['top_categories']:
        #         top_cat_lines.append(f"  - {category}: £{value:,.2f}")
        # else:
        #     top_cat_lines.append("  [dim]No category data available.[/dim]") 
        # self.query_one("#top_categories_display", Static).update("\n".join(top_cat_lines)) # Removed

        # Update button states based on data
        self.query_one("#update_balances_button", Button).disabled = not has_items
        self.query_one("#manage_assets_button", Button).disabled = False # Can always add assets
        self.query_one("#historical_data_button", Button).disabled = not (has_items and has_snapshots)

        # Calculate current net worth from current_snapshot_balances
        current_nw = 0.0
        if has_items: # Only calculate if there are items, otherwise it's 0 by default
            temp_total_assets = 0.0
            temp_total_debts = 0.0
            for balance_entry in self.current_snapshot_balances:
                balance = balance_entry.get("balance", 0.0)
                if balance > 0:
                    temp_total_assets += balance
                elif balance < 0:
                    temp_total_debts += balance
            current_nw = temp_total_assets + temp_total_debts
        
        # --- Initialize display data for FIRE panel --- 
        next_milestone_text = "Next Milestone: N/A"
        milestone_progress_text = "Progress: N/A"
        milestone_progress_value = 0.0 # For the ProgressBar
        avg_3m_text = "Avg. Trend (3M): N/A"
        avg_6m_text = "Avg. Trend (6M): N/A"
        avg_12m_text = "Avg. Trend (12M): N/A"

        if has_items and has_snapshots and len(self.snapshots) > 0:
            milestone_data = update_and_get_milestone_progress(
                current_net_worth=current_nw, 
                achieved_milestones_values=self.achieved_milestones, 
                standard_milestones_definition=STANDARD_MILESTONES
            )
            
            newly_achieved_in_this_update = []
            if milestone_data.get('newly_achieved_milestones'):
                all_newly_flagged = milestone_data['newly_achieved_milestones'] # Milestones flagged as new by core_logic
                
                for val in all_newly_flagged:
                    if val not in self.achieved_milestones:
                        self.achieved_milestones.append(val)
                        newly_achieved_in_this_update.append(val)
                
                if newly_achieved_in_this_update:
                    self.achieved_milestones.sort() # Sort all, including newly added
                    self.unsaved_changes = True

                    # Notify for the highest of the ones *actually added* in this cycle
                    highest_newly_achieved_val = max(newly_achieved_in_this_update)
                    highest_achieved_name = next(
                        (m['name'] for m in STANDARD_MILESTONES if m['value'] == highest_newly_achieved_val), 
                        str(highest_newly_achieved_val)
                    )
                    self.notify(
                        f"Congratulations! Milestone Achieved: {highest_achieved_name}", 
                        title="Milestone Reached!", 
                        timeout=10
                    )

            if milestone_data.get('all_milestones_achieved'):
                next_milestone_text = "All standard milestones achieved!"
                milestone_progress_text = "Congratulations!"
            else:
                next_milestone_text = f"Next Milestone: {milestone_data.get('next_milestone_name', 'N/A')}"
                milestone_progress_value = milestone_data.get('progress_percent', 0.0)
                milestone_progress_text = f"Progress: [bold #D3D3D3]{milestone_progress_value:.1f}%[/bold #D3D3D3]"

            enhanced_trends_data = calculate_enhanced_trends(self.snapshots, self.financial_items)
            avg_3m_raw = enhanced_trends_data.get('avg_3m_raw')
            avg_6m_raw = enhanced_trends_data.get('avg_6m_raw')
            avg_12m_raw = enhanced_trends_data.get('avg_12m_raw')

            avg_3m_display_val = enhanced_trends_data.get('avg_3m_display', 'N/A')
            if isinstance(avg_3m_raw, (int, float)) and avg_3m_raw > 0:
                avg_3m_text = f"Avg. Trend (3M): [bold green]{avg_3m_display_val}[/bold green]"
            elif isinstance(avg_3m_raw, (int, float)) and avg_3m_raw < 0:
                avg_3m_text = f"Avg. Trend (3M): [bold red]{avg_3m_display_val}[/bold red]"
            else:
                avg_3m_text = f"Avg. Trend (3M): {avg_3m_display_val}" # Default, no color for 0 or N/A
            
            avg_6m_display_val = enhanced_trends_data.get('avg_6m_display', 'N/A')
            if isinstance(avg_6m_raw, (int, float)) and avg_6m_raw > 0:
                 avg_6m_text = f"Avg. Trend (6M): [bold green]{avg_6m_display_val}[/bold green]"
            elif isinstance(avg_6m_raw, (int, float)) and avg_6m_raw < 0:
                 avg_6m_text = f"Avg. Trend (6M): [bold red]{avg_6m_display_val}[/bold red]"
            else:
                 avg_6m_text = f"Avg. Trend (6M): {avg_6m_display_val}"

            avg_12m_display_val = enhanced_trends_data.get('avg_12m_display', 'N/A')
            if isinstance(avg_12m_raw, (int, float)) and avg_12m_raw > 0:
                avg_12m_text = f"Avg. Trend (12M): [bold green]{avg_12m_display_val}[/bold green]"
            elif isinstance(avg_12m_raw, (int, float)) and avg_12m_raw < 0:
                avg_12m_text = f"Avg. Trend (12M): [bold red]{avg_12m_display_val}[/bold red]"
            else:
                avg_12m_text = f"Avg. Trend (12M): {avg_12m_display_val}"
        
        # --- Initialize display data for Goal Projection --- 
        goal_target_text = "Financial Goal: Not Set"
        goal_projection_text = "Projection: N/A"
        goal_progress_value = 0.0 # For the ProgressBar

        if has_items and has_snapshots and len(self.snapshots) > 0:
            # Calculate Goal Projection
            trends_for_goal_calc = {
                "avg_3m_raw": enhanced_trends_data.get('avg_3m_raw'),
                "avg_6m_raw": enhanced_trends_data.get('avg_6m_raw'),
                "avg_12m_raw": enhanced_trends_data.get('avg_12m_raw')
            }
            
            goal_projection_data = calculate_goal_projection(
                financial_goal=self.financial_goal,
                current_net_worth=current_nw,
                trends_raw=trends_for_goal_calc
            )
            
            # Calculate goal progress for the ProgressBar and for the text display
            if self.financial_goal and self.financial_goal.get('target_net_worth', 0) > 0:
                target_nw_goal = self.financial_goal['target_net_worth']
                goal_progress_value = min((current_nw / target_nw_goal) * 100, 100) if target_nw_goal > 0 else 0.0
                goal_target_text = f"Goal: [bold green]£{current_nw:,.0f}[/bold green] / [bold green]£{target_nw_goal:,.0f}[/bold green] ([bold #D3D3D3]{goal_progress_value:.1f}%[/bold #D3D3D3])"
            else:
                goal_progress_value = 0.0 # No goal set or target is 0
                goal_target_text = "Financial Goal: Not Set" # Keep this default if no goal

            if goal_projection_data.get("goal_already_reached"):
                goal_projection_text = goal_projection_data.get("overall_status_message")
            elif goal_projection_data.get("individual_projections"):
                projection_lines = []
                for proj in goal_projection_data["individual_projections"]:
                    # Color the time to goal string parts if possible, this is more complex due to 'Approx. X years and Y months'
                    # For now, let's not color the projection text parts to keep it simpler.
                    projection_lines.append(f"  - {proj['period_label']}: {proj['time_to_goal_str']}")
                if projection_lines:
                    goal_projection_text = "Time to Goal (based on trends):\n" + "\n".join(projection_lines)
                else: 
                    goal_projection_text = goal_projection_data.get("overall_status_message")
            else: 
                goal_projection_text = goal_projection_data.get("overall_status_message")

        # Update FIRE Insights Panel Widgets
        try:
            self.query_one("#next_milestone_display", Static).update(next_milestone_text)
            self.query_one("#milestone_progress_bar", ProgressBar).progress = milestone_progress_value
            self.query_one("#milestone_progress_display", Static).update(milestone_progress_text)
            self.query_one("#avg_trend_3m_display", Static).update(avg_3m_text)
            self.query_one("#avg_trend_6m_display", Static).update(avg_6m_text)
            self.query_one("#avg_trend_12m_display", Static).update(avg_12m_text)
            self.query_one("#financial_goal_target_display", Static).update(goal_target_text)
            self.query_one("#financial_goal_progress_bar", ProgressBar).progress = goal_progress_value
            self.query_one("#financial_goal_projection_display", Static).update(goal_projection_text)
        except Exception:
            pass # Silently ignore if widgets not found (e.g. during initial compose)

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
            loaded_data = load_historical_data(self._rich_console_for_utils, file_path)

            if loaded_data and len(loaded_data) == 5: # Data loaded successfully (all 5 components)
                self.current_data_file = file_path
                self.categories, self.financial_items, self.snapshots, self.achieved_milestones, self.financial_goal = loaded_data
                
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
        elif event.button.id == "set_goal_button":
            self.action_set_financial_goal()
        elif event.button.id == "manage_item_targets_button":
            self.action_show_item_targets_screen()
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
                self.current_data_file = file_path # Update current file to the new path
                save_historical_data(
                    self._rich_console_for_utils,
                    self.categories,
                    self.financial_items,
                    self.snapshots,
                    self.achieved_milestones,
                    self.financial_goal, # Pass financial_goal
                    self.current_data_file
                )
                save_last_opened_file(self.current_data_file) # Remember this new file as the last one
                self.notify(f"Data successfully saved as {self.current_data_file}", title="Save As Successful", severity="information")
                self.unsaved_changes = False # Reset unsaved changes flag
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
                self.achieved_milestones = [] # Ensure achieved_milestones are cleared for a new file
                self.financial_goal = None # Ensure financial_goal is cleared for a new file
                self.current_snapshot_balances = []
                self.current_date = datetime.now().strftime("%Y-%m-%d")

                save_historical_data( # Save the new empty/default structure
                    self._rich_console_for_utils,
                    self.categories,
                    self.financial_items,
                    self.snapshots,
                    self.achieved_milestones,
                    self.financial_goal, # Pass financial_goal
                    self.current_data_file
                )
                save_last_opened_file(self.current_data_file)
                self.update_dashboard() # Refresh dashboard with new empty state
                self.notify(f"New data file '{self.current_data_file}' created and loaded.", title="New File Created", severity="information")
                self.unsaved_changes = False # Reset unsaved changes flag
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

        self.update_dashboard() # This will now trigger FIRE calculations which might update achieved_milestones
        self.notify(f"Balances for {today_str} updated. Saving data...", title="Balances Updated", severity="information")
        self.action_save_data() # This now saves achieved_milestones
        self.unsaved_changes = True # Mark changes as unsaved until next explicit save

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

        self.update_dashboard() # This will now trigger FIRE calculations
        self.notify("Financial items updated. Saving data...", title="Asset Management", severity="information")
        self.action_save_data() # This now saves achieved_milestones
        self.unsaved_changes = True # Mark changes as unsaved until next explicit save

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

    def _handle_financial_goal_result(self, result: Optional[Dict[str, Any]]) -> None:
        """Callback to handle the result from FinancialGoalScreen."""
        if result is not None: # User saved a goal (could be a new value or cleared by saving empty)
            if result.get("target_net_worth") is not None:
                self.financial_goal = result
                self.notify(f"Financial goal set to: £{result['target_net_worth']:,.2f}", title="Goal Set", severity="information")
            else: # User cleared the goal by saving an empty input
                self.financial_goal = None
                self.notify("Financial goal cleared.", title="Goal Cleared", severity="information")
            
            self.unsaved_changes = True
            self.action_save_data() # Save immediately
            self.update_dashboard() # Refresh dashboard (for future display of goal)
        else: # User cancelled or FinancialGoalScreen dismissed with None for other reasons (e.g. empty input)
            # Check if the goal was actually cleared by FinancialGoalScreen sending None explicitly
            # versus user just hitting cancel. The screen sends None for empty save *and* cancel.
            # If self.financial_goal existed before and now result is None, it implies clearing.
            # However, the screen logic for empty string already sends None. So this branch is for "Cancel".
            self.notify("Financial goal setting cancelled.", title="Cancelled", severity="warning")


    def action_set_financial_goal(self) -> None:
        """Shows the screen for setting/editing the financial goal."""
        self.push_screen(
            FinancialGoalScreen(current_goal=self.financial_goal), 
            self._handle_financial_goal_result
        )

    def _handle_item_targets_result(self, updated_items: Optional[List[Dict[str, Any]]]) -> None:
        """Callback to handle the result from ItemTargetsScreen."""
        if updated_items is not None:
            # Potentially add a check here to see if actual changes were made 
            # if self.financial_items != updated_items:
            self.financial_items = updated_items
            self.unsaved_changes = True
            self.action_save_data()
            self.update_dashboard() # Refresh, though no direct display of item targets here yet
            self.notify("Item financial targets updated and saved.", title="Item Targets Saved", severity="information")
            # else:
            #     self.notify("No changes made to item targets.", title="Item Targets", severity="information")
        else:
            self.notify("Item target management cancelled or no changes to save.", title="Item Targets", severity="warning")

    def action_show_item_targets_screen(self) -> None:
        """Shows the screen for managing financial targets for individual items."""
        if not self.financial_items:
            self.notify("No financial items exist to set targets for. Please add assets first.", title="No Items", severity="warning")
            return
        self.push_screen(
            ItemTargetsScreen(app_instance=self),
            self._handle_item_targets_result
        )

if __name__ == "__main__":
    app = NetWorthApp()
    app.run() 