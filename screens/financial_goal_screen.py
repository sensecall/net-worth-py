from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Label, Static
from textual.containers import Vertical, Horizontal
from textual.validation import Number
from typing import Optional, Dict, Any

class FinancialGoalScreen(ModalScreen):
    """A modal screen to set or edit a financial goal (target net worth)."""

    DEFAULT_CSS = """
    FinancialGoalScreen {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        background: $surface;
        padding: 2 4;
        border: thick $primary-background-lighten-2;
        border-title-color: $text;
        border-title-style: bold;
        border-title-align: center;
    }

    #dialog > Vertical {
        padding: 1;
    }
    
    Input {
        margin-bottom: 1;
    }

    .button_row {
        padding-top: 1;
        align: center middle;
    }
    """
    
    def __init__(self, current_goal: Optional[Dict[str, Any]] = None, name: Optional[str] = None, id: Optional[str] = None, classes: Optional[str] = None) -> None:
        super().__init__(name, id, classes)
        self.current_goal = current_goal
        self.title = "Set Financial Goal"
        if self.current_goal and self.current_goal.get("target_net_worth") is not None:
            self.title = "Edit Financial Goal"

    def compose(self) -> ComposeResult:
        initial_value = ""
        if self.current_goal and self.current_goal.get("target_net_worth") is not None:
            initial_value = str(self.current_goal["target_net_worth"])

        with Vertical(id="dialog"):
            yield Static(self.title, classes="panel_title") # Using panel_title style from main app
            yield Label("Target Net Worth (£):")
            yield Input(
                value=initial_value,
                placeholder="e.g., 1000000",
                id="goal_input",
                validators=[Number()]
            )
            with Horizontal(classes="button_row"):
                yield Button("Save", variant="primary", id="save_goal")
                yield Button("Cancel", variant="default", id="cancel_goal")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_goal":
            input_widget = self.query_one("#goal_input", Input)
            if not input_widget.is_valid:
                self.app.notify("Invalid input. Please enter a valid number for the goal.", title="Invalid Input", severity="error")
                input_widget.focus()
                return
            
            value_str = input_widget.value.strip()
            if not value_str: # If empty, treat as clearing the goal
                self.dismiss(None) 
                return

            try:
                target_value = float(value_str)
                if target_value < 0: 
                    self.app.notify("Target net worth must be a positive number.", title="Invalid Input", severity="error")
                    input_widget.focus()
                    return
                self.dismiss({"target_net_worth": target_value})
            except ValueError:
                self.app.notify("Invalid input format. Please enter a valid number.", title="Invalid Input", severity="error")
                input_widget.focus()
        elif event.button.id == "cancel_goal":
            self.dismiss(None)

    def on_mount(self) -> None:
        self.query_one("#dialog", Vertical).border_title = self.title
        self.query_one("#goal_input", Input).focus() 