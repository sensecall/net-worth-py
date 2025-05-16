from textual.app import ComposeResult, App
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Button, Input, Label, Select, RadioSet, Checkbox, Static
from textual.containers import VerticalScroll, Horizontal, Vertical
from datetime import datetime # For generating unique IDs
import uuid # For more robust unique IDs

class AssetFormScreen(ModalScreen):
    """A modal screen to add or edit a financial item."""

    DEFAULT_CSS = """
    AssetFormScreen {
        align: center middle;
    }
    #dialog {
        width: 80%;
        max-width: 70;
        height: auto;
        max-height: 90%;
        border: thick $primary-background-darken-2;
        background: $surface;
        padding: 1 2;
    }
    #dialog > VerticalScroll {
        padding: 0 1;
    }
    .field_label {
        margin-top: 1;
        width: 100%;
    }
    Input, Select {
        width: 100%;
        margin-bottom: 1;
    }
    RadioSet {
        margin-bottom: 1;
    }
    Checkbox {
        width: 100%;
        margin-bottom: 1;
    }
    #button_bar {
        margin-top: 2;
        align: right middle;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, app_instance: App, categories: list, item_to_edit: dict | None = None):
        super().__init__()
        self.app_instance = app_instance
        self.categories = categories
        self.item_to_edit = item_to_edit
        self.is_edit_mode = item_to_edit is not None
        self.screen_title = "Edit Financial Item" if self.is_edit_mode else "Add New Financial Item"

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static(self.screen_title, classes="dialog_title") # Using Static for title styling flexibility
            with VerticalScroll():
                yield Label("Item Name:", classes="field_label")
                yield Input(placeholder="e.g., 'Main Savings Account'", id="item_name_input")
                
                yield Label("Category:", classes="field_label")
                yield Select([], id="item_category_select", prompt="Select a category")

                yield Label("Item Type:", classes="field_label")
                yield RadioSet("Asset", "Liability", id="item_type_radioset")

                yield Label("Liquidity Status:", classes="field_label")
                yield RadioSet("Liquid", "Not Liquid", id="item_liquid_radioset")
            
            with Horizontal(id="button_bar"):
                yield Button("Cancel", id="cancel_button", variant="default")
                yield Button("Save Changes" if self.is_edit_mode else "Add Item", id="save_button", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#item_name_input", Input).focus()

        # Populate category select
        category_options = [(cat.get('name', 'Unnamed Category'), cat.get('id')) for cat in self.categories if cat.get('id')]
        category_select = self.query_one("#item_category_select", Select)
        category_select.set_options(category_options)

        if self.is_edit_mode and self.item_to_edit:
            self.query_one("#item_name_input", Input).value = self.item_to_edit.get('name', '')
            category_select.value = self.item_to_edit.get('category_id') # Select will find by value (ID)
            item_type = self.item_to_edit.get('type', 'asset')
            self.query_one("#item_type_radioset", RadioSet).pressed_button_label = item_type.capitalize()
            self.query_one("#item_liquid_radioset", RadioSet).pressed_button_label = "Liquid" if self.item_to_edit.get('liquid', False) else "Not Liquid"
        else:
            # Default for add mode
            self.query_one("#item_type_radioset", RadioSet).pressed_button_label = "Asset"
            self.query_one("#item_liquid_radioset", RadioSet).pressed_button_label = "Liquid"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_button":
            name_input = self.query_one("#item_name_input", Input)
            category_select = self.query_one("#item_category_select", Select)
            type_radioset = self.query_one("#item_type_radioset", RadioSet)
            liquid_radioset = self.query_one("#item_liquid_radioset", RadioSet)

            item_name = name_input.value.strip()
            if not item_name:
                self.app_instance.notify("Item name cannot be empty.", severity="error", title="Validation Error")
                name_input.focus()
                return
            
            if category_select.value == Select.BLANK:
                self.app_instance.notify("Please select a category.", severity="error", title="Validation Error")
                category_select.focus()
                return

            item_data = {
                "id": self.item_to_edit.get('id') if self.is_edit_mode else f"item_{uuid.uuid4().hex[:8]}",
                "name": item_name,
                "category_id": category_select.value,
                "type": type_radioset.pressed_button_label.lower() if type_radioset.pressed_button else 'asset',
                "liquid": liquid_radioset.pressed_button_label == "Liquid" if liquid_radioset.pressed_button else False
            }
            self.dismiss(item_data)

        elif event.button.id == "cancel_button":
            self.dismiss(None) 