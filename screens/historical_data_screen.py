from textual.app import ComposeResult, App
from textual.screen import Screen
from textual.widgets import Header, Footer, DataTable
from textual.containers import ScrollableContainer # For horizontal and vertical scrolling if needed
from rich.text import Text # For styling cells

class HistoricalDataScreen(Screen):
    """A screen to display historical snapshot data in a pivot-table like view."""

    BINDINGS = [("escape", "app.pop_screen", "Close")]

    def __init__(self, financial_items: list, snapshots: list):
        super().__init__()
        self.financial_items = sorted(financial_items, key=lambda x: x.get('name', '').lower()) # Sort items by name for consistent column order
        self.snapshots = sorted(snapshots, key=lambda x: x.get('date', ''), reverse=True) # Ensure snapshots are newest first
        self.item_id_to_name = {item['id']: item['name'] for item in self.financial_items}

    def compose(self) -> ComposeResult:
        yield Header(name="Historical Snapshot Data")
        # Using ScrollableContainer to ensure DataTable can scroll in both directions if content is too large
        with ScrollableContainer(id="historical_table_container"):
            yield DataTable(id="historical_data_table", zebra_stripes=True, fixed_columns=1) # Fix the Date column
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#historical_data_table", DataTable)
        
        # --- Setup Columns ---
        columns = ["Date"] 
        for item in self.financial_items:
            columns.append(Text(item.get('name', 'Unnamed Item'), style="bold")) # Item names as column headers
        table.add_columns(*columns)

        # --- Populate Rows ---
        if not self.snapshots:
            table.add_row("No snapshot data available.")
            return

        for snapshot in self.snapshots:
            row_data = [snapshot.get('date', 'N/A')]
            snapshot_balances_map = {bal_entry['item_id']: bal_entry['balance'] for bal_entry in snapshot.get('balances', [])}
            
            for item in self.financial_items: # Iterate in the defined column order
                balance = snapshot_balances_map.get(item['id'])
                if balance is not None:
                    balance_str = f"£{balance:,.2f}"
                    style = "green" if balance > 0 else "red" if balance < 0 else "dim grey"
                    row_data.append(Text(balance_str, style=style, justify="right"))
                else:
                    row_data.append(Text("-", style="dim", justify="center")) # Placeholder if no balance for this item in this snapshot
            
            table.add_row(*row_data) 