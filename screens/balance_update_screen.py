from textual.app import ComposeResult, App # App needed for self.app.notify
from textual.widgets import Header, Footer, Static, Button, Input # Removed Label, Checkbox
from textual.containers import Container, Horizontal # Removed VerticalScroll, Vertical
from textual.screen import Screen 
from textual.binding import Binding 
# Removed datetime, os - not directly used by this screen

class QuickBalanceUpdateScreen(Screen):
    """A screen to quickly update balances for financial items."""

    BINDINGS = [
        Binding("escape", "request_close", "Close", show=False, priority=True),
        Binding("ctrl+s", "apply_changes", "Apply Changes", show=True),
    ]

    CSS = """
    QuickBalanceUpdateScreen {
        align: center top; 
        padding: 2 4; 
    }
    #item_info_container {
        width: 80%;
        max-width: 80;
        height: auto;
        padding: 1 2;
        border: round $primary;
        margin-bottom: 1;
    }
    #item_name_label {
        text-style: bold;
        margin-bottom: 1;
    }
    #current_balance_label {
        margin-bottom: 1;
    }
    #new_balance_input {
        width: 100%;
        margin-bottom: 1;
    }
    #navigation_buttons Horizontal {
        align: center middle;
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    #action_buttons Horizontal {
        align: center middle;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, financial_items: list, current_balances: list, app_instance: App):
        super().__init__()
        self.app_instance = app_instance # Store a reference to the main app for notifications
        self.all_financial_items = {item['id']: item for item in financial_items}
        self.items_to_update = [] 
        balance_map = {b['item_id']: b['balance'] for b in current_balances}

        for item in financial_items:
            current_val = balance_map.get(item['id'], 0.0) 
            self.items_to_update.append({
                "item_id": item['id'],
                "name": item['name'],
                "current_balance": current_val,
                "new_balance": current_val 
            })
        
        self.current_item_idx = 0
        self.is_dirty = False 

    def compose(self) -> ComposeResult:
        yield Header(name="Quick Balance Update")
        if not self.items_to_update:
            yield Static("No financial items to update balances for.")
            with Horizontal(id="action_buttons"):
                 yield Button("Close", id="close_no_items_button", variant="primary")
            yield Footer()
            return

        with Container(id="item_info_container"):
            yield Static(id="item_name_label")
            yield Static(id="current_balance_label")
            yield Input(id="new_balance_input", type="number", placeholder="Enter new balance")
        
        with Horizontal(id="navigation_buttons"):
            yield Button("Previous Item", id="prev_item_button")
            yield Static("", id="item_counter_label")
            yield Button("Next Item", id="next_item_button")

        with Horizontal(id="action_buttons"):
            yield Button("Apply Changes & Close", variant="success", id="apply_button")
            yield Button("Discard & Close", variant="error", id="discard_button")
        yield Footer()

    def on_mount(self) -> None:
        if self.items_to_update:
            self._load_item_ui(self.current_item_idx)
            self.query_one("#new_balance_input", Input).focus()
        else:
            try:
                close_button = self.query_one("#close_no_items_button", Button)
                close_button.focus()
            except Exception:
                pass 

    def _load_item_ui(self, idx: int) -> None:
        if not self.items_to_update or not (0 <= idx < len(self.items_to_update)):
            return

        item_data = self.items_to_update[idx]
        self.query_one("#item_name_label", Static).update(f"Item: {item_data['name']}")
        self.query_one("#current_balance_label", Static).update(f"Current Balance: £{item_data['current_balance']:,.2f}")
        new_balance_input = self.query_one("#new_balance_input", Input)
        new_balance_input.value = str(item_data['new_balance'])
        new_balance_input.focus()

        self.query_one("#item_counter_label", Static).update(f"{idx + 1} / {len(self.items_to_update)}")

        self.query_one("#prev_item_button", Button).disabled = (idx == 0)
        self.query_one("#next_item_button", Button).disabled = (idx == len(self.items_to_update) - 1)

    def _save_current_input(self) -> bool:
        if not self.items_to_update:
            return False
        try:
            new_balance_str = self.query_one("#new_balance_input", Input).value
            new_balance = float(new_balance_str)
            if self.items_to_update[self.current_item_idx]['new_balance'] != new_balance:
                self.items_to_update[self.current_item_idx]['new_balance'] = new_balance
                self.is_dirty = True
            return True
        except ValueError:
            self.app_instance.notify("Invalid balance amount. Please enter a number.", severity="error", title="Input Error")
            self.query_one("#new_balance_input", Input).focus()
            return False
        except Exception as e:
            self.app_instance.notify(f"Error saving input: {e}", severity="error", title="Error")
            return False

    def action_apply_changes(self):
        if self._save_current_input(): 
            result_balances = [
                {"item_id": item_d["item_id"], "balance": item_d["new_balance"]}
                for item_d in self.items_to_update
            ]
            self.dismiss(result_balances if self.is_dirty else []) 

    def action_request_close(self):
        if self.is_dirty:
            self.app_instance.notify("Changes discarded.", title="Discarded", severity="warning")
        self.dismiss(None)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "prev_item_button":
            if self._save_current_input() and self.current_item_idx > 0:
                self.current_item_idx -= 1
                self._load_item_ui(self.current_item_idx)
        elif button_id == "next_item_button":
            if self._save_current_input() and self.current_item_idx < len(self.items_to_update) - 1:
                self.current_item_idx += 1
                self._load_item_ui(self.current_item_idx)
        elif button_id == "apply_button":
            self.action_apply_changes()
        elif button_id == "discard_button" or button_id == "close_no_items_button":
            self.action_request_close()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "new_balance_input":
            if self._save_current_input():
                if self.current_item_idx < len(self.items_to_update) - 1:
                    self.current_item_idx += 1
                    self._load_item_ui(self.current_item_idx)
                else:
                    self.action_apply_changes() 