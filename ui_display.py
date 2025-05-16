from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box
import collections # For  collections.abc.Iterable which is what enumerate wants

# Note: datetime might be needed if print_final_summary or display_assets re-formats dates,
# but for now, they seem to receive them pre-formatted or just display as is.

def display_app_title(console: Console):
    """Displays a visually appealing application title."""
    title_text = Text("Net Worth Tracker", style="bold green")
    subtitle_text = Text("Track your financial journey", style="italic dim")
    
    console.print(title_text, justify="center")
    console.print(subtitle_text, justify="center")
    console.print() # Add a blank line for spacing

def display_assets(console: Console, snapshot_balances: collections.abc.Iterable, financial_items: collections.abc.Iterable, categories_list: collections.abc.Iterable, show_balances=True, show_categories=True, table_title="Current Financial Snapshot"):
    """Displays the current list of financial items and their balances in a Rich Table."""
    if not snapshot_balances:
        console.print("[yellow]No balances to display for the current snapshot.[/yellow]")
        return

    items_dict = {item['id']: item for item in financial_items}
    cats_dict = {cat['id']: cat for cat in categories_list}

    table = Table(
        title=Text(table_title, style="bold"),
        show_header=True,
        header_style="bold magenta",
        box=box.SIMPLE,
        padding=(0, 1)
    )
    
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Item Name", min_width=20, style="cyan")
    if show_balances:
        table.add_column("Balance", justify="right", min_width=15)
    if show_categories:
        table.add_column("Category", min_width=15, style="dim")
    table.add_column("Liquid", justify="center", min_width=8)

    total_balance_val = 0.0
    liquid_balance_val = 0.0
    non_liquid_balance_val = 0.0

    for idx, balance_entry in enumerate(snapshot_balances, 1):
        item_id = balance_entry.get("item_id")
        actual_balance = balance_entry.get("balance", 0.0)

        item_details = items_dict.get(item_id)

        if not item_details:
            item_name_str = f"Unknown Item (ID: {item_id})"
            category_name_str = "Unknown"
            is_liquid = False
        else:
            item_name_str = item_details.get("name", f"Unnamed Item (ID: {item_id})")
            category_id = item_details.get("category_id")
            category_details = cats_dict.get(category_id)
            category_name_str = category_details.get("name", "Uncategorized") if category_details else "Invalid Category ID"
            is_liquid = item_details.get("liquid", False)

        row_content = [str(idx), item_name_str]
        
        if show_balances:
            total_balance_val += actual_balance
            if is_liquid:
                 liquid_balance_val += actual_balance
            else:
                 non_liquid_balance_val += actual_balance
            
            balance_color_style = "green" if actual_balance >= 0 else "red"
            balance_text_str = Text(f"£{actual_balance:,.2f}", style=balance_color_style)
            row_content.append(balance_text_str)
        
        if show_categories:
            row_content.append(category_name_str)
        
        liquid_status_text = Text("Yes", style="green") if is_liquid else Text("No", style="red")
        row_content.append(liquid_status_text)
        
        table.add_row(*row_content)

    if show_balances and snapshot_balances:
        table.add_section()
        
        summary_row_content = ["", Text("TOTAL", style="bold")]
        total_balance_color_style = "green" if total_balance_val >= 0 else "red"
        summary_row_content.append(Text(f"£{total_balance_val:,.2f}", style=total_balance_color_style))
        if show_categories:
            summary_row_content.append("")
        summary_row_content.append("")
        table.add_row(*summary_row_content)
        
        if liquid_balance_val != 0:
            liquid_row_content = ["", Text("Sum of Liquid Items", style="dim")]
            liquid_balance_color_style = "green" if liquid_balance_val >= 0 else "red"
            liquid_row_content.append(Text(f"£{liquid_balance_val:,.2f}", style=liquid_balance_color_style))
            if show_categories:
                liquid_row_content.append("")
            liquid_row_content.append(Text("Overall Liquid", style="dim"))
            table.add_row(*liquid_row_content)
        
        if non_liquid_balance_val != 0:
            non_liquid_row_content = ["", Text("Sum of Non-Liquid Items", style="dim")]
            non_liquid_color_style = "green" if non_liquid_balance_val >= 0 else "red"
            non_liquid_row_content.append(Text(f"£{non_liquid_balance_val:,.2f}", style=non_liquid_color_style))
            if show_categories:
                non_liquid_row_content.append("")
            non_liquid_row_content.append(Text("Overall Non-Liquid", style="dim"))
            table.add_row(*non_liquid_row_content)

    console.print(table)

def print_final_summary(console: Console, entry_date: str, snapshot_balances: collections.abc.Iterable, financial_items: collections.abc.Iterable, categories_list: collections.abc.Iterable):
    """Prints a final summary including date, item balances, and total net worth."""
    console.print("\n[bold green]------------------------------------[/bold green]")
    console.print(f"[bold green]Net Worth Summary for [cyan]{entry_date}[/cyan][/bold green]")
    if not snapshot_balances:
        console.print("[yellow]No item balances were entered for this date.[/yellow]")
    else:
        console.print("[bold blue]Your final item balances are:[/bold blue]")
        display_assets(console, snapshot_balances, financial_items, categories_list, show_balances=True, show_categories=True, table_title=f"Summary for {entry_date}")
        
        total_net_worth = sum(balance_entry.get('balance', 0.0) for balance_entry in snapshot_balances)
        
        console.print("\n------------------------------------")
        console.print(f"[bold white on blue] Total Net Worth: £{total_net_worth:,.2f} [/bold white on blue]")
    console.print("[bold green]------------------------------------[/bold green]") 