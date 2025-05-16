import os
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.app import ComposeResult

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
                # It's good practice for screens to handle their own notifications if possible
                # or communicate back to the app to show them.
                self.notify("File path cannot be empty.", severity="error", title="Input Error")
                file_path_input.focus()
        elif event.button.id == "cancel_button":
            self.dismiss(None) 