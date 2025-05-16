from textual.app import ComposeResult, App
from textual.screen import Screen
from textual.widgets import Header, Footer, Button, DataTable # Removed Placeholder, added DataTable
from textual.containers import VerticalScroll, Container, Horizontal # Added Container, Horizontal
from textual.coordinate import Coordinate # Added for DataTable.update_cell_at
from rich.text import Text # Import Rich Text

from .asset_form_screen import AssetFormScreen # Import the new form screen
from .confirm_delete_screen import ConfirmDeleteScreen # Import ConfirmDeleteScreen

class AssetManagementScreen(Screen):
    """A screen for managing financial assets and liabilities."""

    BINDINGS = [("escape", "request_close", "Close")] # More specific close binding

    def __init__(self, app_instance: App, financial_items: list, categories: list, current_snapshot_balances: list):
        super().__init__()
        self.app_instance = app_instance
        # self.financial_items = financial_items # Original list, if needed for comparison
        self.categories = categories
        self.category_map = {cat['id']: cat['name'] for cat in self.categories} # For easy name lookup
        # We'll store a working copy of items for editing/adding/deleting
        self.working_financial_items = [item.copy() for item in financial_items]
        # Create a map for quick balance lookup
        self.balance_map = {balance_entry['item_id']: balance_entry['balance'] for balance_entry in current_snapshot_balances}
        self.is_dirty = False # Track if changes have been made
        self.selected_row_item_id: str | None = None # To store the ID of the selected row

    def compose(self) -> ComposeResult:
        yield Header(name="View & Manage Financial Items")
        with VerticalScroll(): # Main content area
            yield DataTable(id="asset_table", zebra_stripes=True) # Added zebra_stripes for better readability
            with Container(id="action_buttons_container"):
                with Horizontal():
                    yield Button("Add New Item", id="add_item_button", variant="success")
                    yield Button("Edit Selected", id="edit_item_button", variant="primary")
                    yield Button("Delete Selected", id="delete_item_button", variant="error")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Name", "Category", "Type", "Liquid", "Current Balance") # Added Current Balance column
        self._refresh_table_data() # Use helper to populate initially

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the DataTable."""
        if event.row_key:
            self.selected_row_item_id = str(event.row_key.value)
            # Enable edit/delete buttons now that a row is selected and we have its ID
            # (assuming they might have been disabled if no rows or no selection initially)
            edit_button = self.query_one("#edit_item_button", Button)
            delete_button = self.query_one("#delete_item_button", Button)
            if self.working_financial_items: # Only enable if there are items to act upon
                edit_button.disabled = False
                delete_button.disabled = False
        else:
            self.selected_row_item_id = None
            # Optionally disable edit/delete if no valid row is selected
            # self.query_one("#edit_item_button", Button).disabled = True
            # self.query_one("#delete_item_button", Button).disabled = True

    def action_request_close(self) -> None:
        """Called when escape is pressed."""
        if self.is_dirty:
            # Here we might want to show a confirmation dialog if there are unsaved changes.
            # For now, we'll just notify and dismiss, returning the changed items.
            self.app_instance.notify("Changes applied and screen closed.", title="Asset Management")
            self.dismiss(self.working_financial_items)
        else:
            self.app_instance.notify("No changes made.", title="Asset Management")
            self.dismiss(None) # No changes

    # Placeholder for button actions - to be implemented
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add_item_button":
            # self.app_instance.notify("Add item functionality to be implemented.", severity="warning")
            self.app_instance.push_screen(
                AssetFormScreen(app_instance=self.app_instance, categories=self.categories, item_to_edit=None),
                self._handle_add_item_result
            )
        elif event.button.id == "edit_item_button":
            if not self.selected_row_item_id:
                self.app_instance.notify("No item selected to edit. Please click on a row in the table first.", severity="error", title="Selection Error")
                return

            item_to_edit = next((item for item in self.working_financial_items if item['id'] == self.selected_row_item_id), None)

            if item_to_edit:
                self.app_instance.push_screen(
                    AssetFormScreen(app_instance=self.app_instance, categories=self.categories, item_to_edit=item_to_edit),
                    self._handle_edit_item_result
                )
            else:
                self.app_instance.notify(f"Item with ID '{self.selected_row_item_id}' not found. This might indicate a data inconsistency.", severity="error", title="Data Error")
                self.selected_row_item_id = None # Reset selection as it seems invalid

        elif event.button.id == "delete_item_button":
            if not self.selected_row_item_id:
                self.app_instance.notify("No item selected to delete. Please click on a row in the table first.", severity="error", title="Selection Error")
                return
            
            selected_item_name = "Unknown Item"
            item_to_delete = next((item for item in self.working_financial_items if item['id'] == self.selected_row_item_id), None)
            if item_to_delete:
                selected_item_name = item_to_delete.get('name', selected_item_name)
            
            self.app_instance.push_screen(
                ConfirmDeleteScreen(item_name_to_delete=selected_item_name),
                self._handle_delete_confirmation
            )

    def _handle_add_item_result(self, new_item: dict | None) -> None:
        """Callback for when the AssetFormScreen returns a new item."""
        if new_item:
            # Check for ID collision before adding (though UUIDs make this very unlikely)
            if any(item['id'] == new_item['id'] for item in self.working_financial_items):
                self.app_instance.notify(f"Error: Item with ID '{new_item['id']}' already exists.", title="Add Error", severity="error")
                return

            self.working_financial_items.append(new_item)
            # New items won't have a balance in the existing self.balance_map from __init__
            # We should add a default balance (0.0) for them in the map for immediate display
            # Or, ideally, the main app would update its current_snapshot_balances and pass the refreshed one.
            # For now, let's assume 0.0 for new items in this screen's local map if not found.
            if new_item['id'] not in self.balance_map:
                 self.balance_map[new_item['id']] = 0.0
            self.is_dirty = True
            self._refresh_table_data()
            self.app_instance.notify(f"Item '{new_item.get('name')}' added.", title="Item Added")
        else:
            self.app_instance.notify("Add item cancelled.", title="Cancelled")

    def _handle_edit_item_result(self, edited_item: dict | None) -> None:
        """Callback for when the AssetFormScreen returns an edited item."""
        if edited_item:
            item_id_to_update = edited_item.get('id')
            found_item_index = -1
            for i, item in enumerate(self.working_financial_items):
                if item.get('id') == item_id_to_update:
                    found_item_index = i
                    break
            
            if found_item_index != -1:
                self.working_financial_items[found_item_index] = edited_item
                # Balances are not edited on this screen, so self.balance_map remains valid
                self.is_dirty = True
                self._refresh_table_data() # Refresh the entire table
                self.app_instance.notify(f"Item '{edited_item.get('name')}' updated.", title="Item Updated")
            else:
                # This case should ideally not be reached if editing an existing item whose ID hasn't changed.
                self.app_instance.notify(f"Failed to find item with ID '{item_id_to_update}' to update after edit.", title="Update Error", severity="error")
        else:
            self.app_instance.notify("Edit item cancelled.", title="Cancelled")

    def _handle_delete_confirmation(self, confirmed: bool) -> None:
        """Callback for the ConfirmDeleteScreen."""
        if confirmed:
            if not self.selected_row_item_id: # Should still be set from button press
                self.app_instance.notify("Error: No item ID was selected for deletion.", title="Delete Error", severity="error")
                return

            item_to_remove = next((item for item in self.working_financial_items if item['id'] == self.selected_row_item_id), None)
            if item_to_remove:
                item_name = item_to_remove.get('name', self.selected_row_item_id) # Get name for notification
                self.working_financial_items.remove(item_to_remove)
                
                # Remove from balance_map as well
                if self.selected_row_item_id in self.balance_map:
                    del self.balance_map[self.selected_row_item_id]
                
                self.is_dirty = True
                self._refresh_table_data() # Refresh table to remove the row
                self.app_instance.notify(f"Item '{item_name}' and its historical data permanently deleted.", title="Item Deleted")
                self.selected_row_item_id = None # Clear selection as item is gone
            else:
                self.app_instance.notify(f"Error: Item with ID '{self.selected_row_item_id}' not found for deletion.", title="Delete Error", severity="error")
        else:
            self.app_instance.notify("Deletion cancelled.", title="Cancelled")

    def _refresh_table_data(self) -> None:
        """Helper to clear and reload all data into the DataTable."""
        table = self.query_one(DataTable)
        # Storing current cursor and scroll position to try and restore it
        # current_cursor_row = table.cursor_row # We can read it, but not set it directly
        current_scroll_y = self.query_one(VerticalScroll).scroll_y

        table.clear(columns=False) # Keep columns, just clear rows
        
        for item in self.working_financial_items:
            item_id = item.get('id')
            category_name = self.category_map.get(item.get('category_id', ''), 'N/A')
            
            item_type_raw = item.get('type', 'asset')
            item_type_display = f"[green]{item_type_raw.capitalize()}[/green]" if item_type_raw == 'asset' else f"[red]{item_type_raw.capitalize()}[/red]"
            
            is_liquid_raw = item.get('liquid', False)
            is_liquid_display = f"[b cyan]Yes[/b cyan]" if is_liquid_raw else f"[dim orange]No[/dim orange]"
            
            current_balance = self.balance_map.get(item_id, 0.0) 
            balance_text_str = f"£{current_balance:,.2f}"
            
            balance_style = ""
            if current_balance > 0:
                balance_style = "green"
            elif current_balance < 0:
                balance_style = "red"
            else:
                balance_style = "dim grey" # Or just "" for default terminal color

            balance_display = Text(balance_text_str, style=balance_style, justify="right")
            
            # ID is not added as a visible cell, only as key
            table.add_row(
                item.get('name', 'N/A'), 
                category_name, 
                item_type_display, 
                is_liquid_display,
                balance_display, # Added balance display
                key=item_id
            )
        if not self.working_financial_items:
            # Spanning the message across available columns for better appearance if table is empty
            col_count = len(table.columns)
            placeholder_row = ["[b]No financial items found. Click 'Add New Item' to start.[/b]"] + [""] * (col_count - 1)
            if col_count > 0: table.add_row(*placeholder_row) # Pass as multiple arguments
            else: table.add_row(placeholder_row[0]) # Failsafe if no columns somehow
            
            self.query_one("#edit_item_button", Button).disabled = True
            self.query_one("#delete_item_button", Button).disabled = True
        else:
            self.query_one("#edit_item_button", Button).disabled = True # Disable until a row is selected
            self.query_one("#delete_item_button", Button).disabled = True # Disable until a row is selected
        
        # Try to restore scroll position
        # if table.row_count > 0:
        #     if 0 <= current_cursor_row < table.row_count:
        #         # table.cursor_row = current_cursor_row # Cannot set cursor_row directly
        #         pass # Cursor will reset
        #     else:
        #         # table.cursor_row = 0 # Default to first row if old cursor is out of bounds
        #         pass # Cursor will reset
        self.query_one(VerticalScroll).scroll_y = current_scroll_y
        # table.refresh_rows() # Not strictly necessary after clear() and add_row() in a batch like this, but doesn't hurt.

    # We will need methods to handle:
    # - Showing a form to add/edit an item (perhaps a new ModalScreen)
    # - Handling add/edit/delete actions on self.working_financial_items
    # - Setting self.is_dirty = True when changes are made

    # Example of how to close and potentially return data:
    # def action_save_and_close(self) -> None:
    #     # Here you would prepare the data to return
    #     # For example, if changes were made:
    #     # updated_items = self.working_financial_items 
    #     # self.dismiss(updated_items) 
    #     # If no changes or user cancels:
    #     self.dismiss(None) # Or self.app_instance.pop_screen() if not returning data

    # def on_button_pressed(self, event: Button.Pressed) -> None:
    # if event.button.id == "some_button":
    # # Handle button action
    # pass 