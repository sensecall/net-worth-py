import os
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.app import ComposeResult

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
        file_path = event.value.strip()
        warning_label = self.query_one("#overwrite_warning", Label)
        warning_label.display = bool(file_path and os.path.exists(file_path))

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