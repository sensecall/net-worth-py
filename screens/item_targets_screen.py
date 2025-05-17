from textual.app import App, ComposeResult
from textual.screen import Screen, ModalScreen
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Button, DataTable, Input, Label, Header, Footer, Static
from textual.validation import Number
from textual.widgets.data_table import RowDoesNotExist
from typing import Optional, List, Dict, Any, Union

class EditTargetModalScreen(ModalScreen[Union[Optional[float], object]]):
    """A modal screen to edit the target balance for a financial item."""
    CANCELLED_OPERATION = object() # Sentinel for cancellation

    DEFAULT_CSS = """
    EditTargetModalScreen {
        align: center middle;
    }
    #edit_target_dialog {
        width: 60;
        height: auto;
        background: $surface;
        padding: 1 2;
        border: thick $primary-background-lighten-2;
        border-title-color: $text;
        border-title-style: bold;
    }
    #edit_target_dialog > Vertical {
        padding: 1;
    }
    Input { margin-bottom: 1; }
    .button_row { padding-top: 1; align: center middle; }
    """

    def __init__(self, item_name: str, current_target: Optional[float]) -> None:
        super().__init__()
        self.item_name = item_name
        self.current_target = current_target
        self.dialog_title = f"Set Target for: {self.item_name}"

    def compose(self) -> ComposeResult:
        initial_value = str(self.current_target) if self.current_target is not None else ""
        with Vertical(id="edit_target_dialog"):
            yield Static(self.dialog_title, classes="panel_title")
            yield Label("Target Balance (£):")
            yield Input(
                value=initial_value,
                placeholder="e.g., 0 or 10000 (leave blank to clear)",
                id="target_input",
                validators=[Number()] # Removed allow_blank=True
            )
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save_target")
                yield Button("Cancel", variant="default", id="cancel_target")

    def on_mount(self) -> None:
        self.query_one("#edit_target_dialog", Vertical).border_title = self.dialog_title
        self.query_one("#target_input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_target":
            input_widget = self.query_one("#target_input", Input)
            if not input_widget.is_valid: # Validator handles number format
                self.app.notify("Invalid input. Please enter a valid number or leave blank.", title="Invalid Target", severity="error")
                input_widget.focus()
                return
            
            value_str = input_widget.value.strip()
            if not value_str: # Blank means clear target
                self.dismiss(None) 
            else:
                try:
                    self.dismiss(float(value_str))
                except ValueError: # Should be caught by validator, but as a fallback
                    self.app.notify("Invalid number format.", title="Error", severity="error")
                    input_widget.focus()
        
        elif event.button.id == "cancel_target":
            self.dismiss(self.CANCELLED_OPERATION) # Cancelled: dismiss with sentinel


class ItemTargetsScreen(Screen):
    """A screen to manage target balances for individual financial items."""

    BINDINGS = [("escape", "close_screen", "Close")]

    DEFAULT_CSS = """
    #item_targets_layout {
        height: 100%;
        padding: 1;
        /* display: grid; Removed */
        /* grid-template-rows: auto 1fr auto; Removed */
    }
    #table_container {
        height: 1fr; /* Allow this container to expand */
    }
    DataTable {
        margin-top: 1;
        margin-bottom: 1;
        height: 100%; /* Make DataTable fill its container */
    }
    .action_buttons {
        width: 100%;
        height: auto; /* Or fixed height like 3 or 5 */
        align: center middle;
        padding-top: 1;
    }
    .action_buttons Button {
        margin-left: 2;
        margin-right: 2;
    }
    """

    def __init__(self, app_instance: App, name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None) -> None:
        super().__init__(name, id, classes)
        self.app_instance = app_instance # Store a reference to the main app
        self.local_financial_items: List[Dict[str, Any]] = [item.copy() for item in self.app_instance.financial_items]
        self.items_map: Dict[str, Dict[str, Any]] = {item['id']: item for item in self.local_financial_items}
        self.current_balances_map: Dict[str, float] = {}
        for bal_entry in self.app_instance.current_snapshot_balances:
            item_id_for_balance = bal_entry.get('item_id') 
            if item_id_for_balance:
                self.current_balances_map[item_id_for_balance] = bal_entry.get('balance', 0.0)
        self.selected_row_key: Optional[str] = None # To store the key of the selected row

    def compose(self) -> ComposeResult:
        yield Header(name="Item Targets Management")
        with Vertical(id="item_targets_layout"):
            yield Static("Manage Item Financial Targets", classes="panel_title")
            # Container for the DataTable to allow it to expand
            with Vertical(id="table_container"):
                yield DataTable(id="item_targets_table")
            with Horizontal(classes="action_buttons"):
                yield Button("Edit Selected Target", id="edit_item_target", variant="primary")
                yield Button("Save All Changes", id="save_item_targets", variant="success")
                yield Button("Close (Esc)", id="close_item_targets_screen", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        # Removed "ID" from visible columns, will use it as row key only
        table.add_columns("Item Name", "Type", "Current Balance (£)", "Target Balance (£)")
        self.refresh_table_data()
        # table.show_column("ID", show=False) # Removed, ID is no longer a visible column

    def refresh_table_data(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for item_id, item_data in self.items_map.items():
            name = item_data.get("name", "N/A")
            item_type = item_data.get("type", "N/A").capitalize()
            current_balance = self.current_balances_map.get(item_id, 0.0)
            target_balance = item_data.get("target_balance")
            target_display = f"£{target_balance:,.2f}" if target_balance is not None else "Not Set"
            
            # item_id is passed as key, not as a cell value for a visible column
            table.add_row(name, item_type, f"£{current_balance:,.2f}", target_display, key=item_id)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the DataTable."""
        if event.row_key:
            self.selected_row_key = str(event.row_key.value) # Ensure it's a string
        else:
            self.selected_row_key = None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "edit_item_target":
            if not self.selected_row_key:
                self.app_instance.notify("Please select an item from the table first.", title="No Item Selected", severity="warning")
                return
            
            selected_item = self.items_map.get(self.selected_row_key)
            if selected_item:
                # Push screen with a callback instead of push_screen_wait
                self.app.push_screen(
                    EditTargetModalScreen(
                        item_name=selected_item.get("name", "Unknown Item"),
                        current_target=selected_item.get("target_balance")
                    ),
                    self._handle_edit_target_result # Specify callback method
                )
            else:
                self.app_instance.notify("Selected item not found. Please try again.", title="Error", severity="error")
                self.selected_row_key = None

        elif event.button.id == "save_item_targets":
            self.dismiss(self.local_financial_items)
        
        elif event.button.id == "close_item_targets_screen":
            self.dismiss()

    def _handle_edit_target_result(self, result: Any) -> None:
        """Callback to handle the result from EditTargetModalScreen."""
        if result is EditTargetModalScreen.CANCELLED_OPERATION:
            self.app_instance.notify("Edit target cancelled.", severity="information")
            return

        # result is now Optional[float] (None means clear, float means set)
        if not self.selected_row_key:
            self.app_instance.notify("Error: No item context for target edit result.", title="Error", severity="error")
            return

        selected_item_data = self.items_map.get(self.selected_row_key)
        if selected_item_data:
            selected_item_data["target_balance"] = result # result is Optional[float]
            self.refresh_table_data()
            table = self.query_one(DataTable)
            try:
                row_index = table.get_row_index(self.selected_row_key)
                table.move_cursor(row=row_index) # Use move_cursor instead of setting cursor_row
            except RowDoesNotExist: 
                 # This might happen if the table was cleared or key changed unexpectedly
                pass 
            self.app_instance.notify(f"Target for '{selected_item_data['name']}' updated locally. Save changes to persist.", severity="information")
        else:
            self.app_instance.notify("Error applying target edit: Original item not found.", title="Error", severity="error")

    def action_close_screen(self) -> None:
        self.dismiss() 