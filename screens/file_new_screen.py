import os
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Checkbox
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual.app import ComposeResult

class FileNewScreen(ModalScreen):
    """A modal screen to prompt for a new file path and confirm overwrite."""
    CSS = """
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
        width: auto; 
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
                    yield Button("Create & Start Fresh", variant="success", id="create_new_button") 
                    yield Button("Cancel", id="cancel_button")

    def on_mount(self) -> None:
        self.query_one(Input).focus()
        self.query_one("#overwrite_warning_new_file", Label).display = False
        self.query_one("#confirm_overwrite_checkbox", Checkbox).display = False 

    async def on_input_changed(self, event: Input.Changed) -> None:
        file_path = event.value.strip()
        warning_label = self.query_one("#overwrite_warning_new_file", Label)
        overwrite_checkbox = self.query_one("#confirm_overwrite_checkbox", Checkbox)
        exists = bool(file_path and os.path.exists(file_path))
        warning_label.display = exists
        overwrite_checkbox.display = exists 
        if not exists:
            overwrite_checkbox.value = False 

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
            
            self.dismiss(file_path) 

        elif event.button.id == "cancel_button":
            self.dismiss(None) 