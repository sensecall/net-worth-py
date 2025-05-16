from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static, Label # Added Label
from textual.containers import Vertical, Horizontal

class ConfirmDeleteScreen(ModalScreen[bool]): # Specify bool as return type for dismiss
    """A modal screen to confirm irreversible deletion."""

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    #confirm_delete_dialog {
        width: 60;
        height: auto;
        border: thick $primary-background-darken-2;
        background: $surface;
        padding: 1 2;
    }
    #confirm_delete_dialog Label {
        margin-bottom: 1;
        width: 100%;
    }
    #confirm_delete_dialog .warning_text {
        color: $error; /* Make warning text red */
        text-style: bold;
    }
    #confirm_delete_dialog #button_bar {
        margin-top: 1;
        align: right middle;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, item_name_to_delete: str):
        super().__init__()
        self.item_name_to_delete = item_name_to_delete

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_delete_dialog"):
            yield Static("[b]Confirm Permanent Deletion[/b]", classes="dialog_title")
            yield Label(f"Are you sure you want to permanently delete '{self.item_name_to_delete}'?")
            yield Label("This action is IRREVERSIBLE.", classes="warning_text")
            yield Label("All historical balance entries for this item will also be permanently removed.", classes="warning_text")
            with Horizontal(id="button_bar"):
                yield Button("Cancel", id="cancel_delete", variant="default")
                yield Button("DELETE PERMANENTLY", id="confirm_delete_button", variant="error")

    def on_mount(self) -> None:
        self.query_one("#cancel_delete", Button).focus() # Default focus to cancel

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm_delete_button":
            self.dismiss(True)
        elif event.button.id == "cancel_delete":
            self.dismiss(False) 