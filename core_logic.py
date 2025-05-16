# No specific imports like datetime seem needed for these functions based on current structure
# from datetime import datetime # Only if calculate_summary_stats were to parse dates internally

from datetime import datetime
import uuid

def generate_unique_id(id_strings_list: list, prefix: str = "id_") -> str:
    """Generates a unique ID string (e.g., 'cat_3', 'item_10')
    based on a list of existing ID strings with the same prefix.
    """
    if not id_strings_list:
        return f"{prefix}1" # Start with 1 if list is empty
    
    numeric_parts = []
    for id_str in id_strings_list:
        if isinstance(id_str, str) and id_str.startswith(prefix):
            try:
                numeric_parts.append(int(id_str[len(prefix):]))
            except ValueError:
                # Ignore IDs that don't have a valid number after prefix
                pass 

    if not numeric_parts:
        # This case means no existing IDs with the specified prefix were found or parseable,
        # so we start this prefix from 1.
        max_val = 0
    else:
        max_val = max(numeric_parts)
        
    return f"{prefix}{max_val + 1}"

def calculate_summary_stats(current_snapshot_balances, financial_items, all_snapshots, categories_list):
    """
    Calculate summary statistics from the current snapshot balances and historical data.
    
    Args:
        current_snapshot_balances: List of balance entries for the current view.
        financial_items: Global list of financial item definitions.
        all_snapshots: Global list of all historical snapshots.
        categories_list: Global list of category definitions.
        
    Returns:
        Dictionary with summary statistics.
    """
    items_dict = {item['id']: item for item in financial_items}
    cats_dict = {cat['id']: cat for cat in categories_list}

    total_assets_value = 0.0
    total_debts_value = 0.0
    liquid_assets_value = 0.0
    non_liquid_assets_value = 0.0

    categories_used = set()
    category_totals = {}

    for balance_entry in current_snapshot_balances:
        item_id = balance_entry.get("item_id")
        balance = balance_entry.get("balance", 0.0)
        item_details = items_dict.get(item_id)

        if not item_details:
            continue

        if balance > 0:
            total_assets_value += balance
            if item_details.get("liquid", False):
                liquid_assets_value += balance
            else:
                non_liquid_assets_value += balance
        elif balance < 0:
            total_debts_value += balance
        
        category_id = item_details.get("category_id")
        category_details = cats_dict.get(category_id)
        category_name = category_details.get("name", "Uncategorized") if category_details else "Invalid Category"
        
        categories_used.add(category_name)
        if category_name not in category_totals:
            category_totals[category_name] = 0
        category_totals[category_name] += balance

    net_worth = total_assets_value + total_debts_value
    
    top_categories = sorted(
        [(cat, value) for cat, value in category_totals.items() if value > 0],
        key=lambda x: x[1],
        reverse=True
    )[:3]
    
    if total_assets_value > 0:
        liquid_percentage = (liquid_assets_value / total_assets_value) * 100 if total_assets_value else 0
    else:
        liquid_percentage = 0
        
    change_value = 0
    change_percentage = 0
    previous_net_worth = None
    has_previous_data = False

    if all_snapshots and len(all_snapshots) > 1:
        previous_snapshot = all_snapshots[1]
        prev_snapshot_balances = previous_snapshot.get('balances', [])
        
        prev_total_assets = 0.0
        prev_total_debts = 0.0
        for prev_balance_entry in prev_snapshot_balances:
            prev_balance = prev_balance_entry.get("balance", 0.0)
            if prev_balance > 0:
                prev_total_assets += prev_balance
            elif prev_balance < 0:
                prev_total_debts += prev_balance
        
        previous_net_worth = prev_total_assets + prev_total_debts
        has_previous_data = True
                
        if previous_net_worth is not None:
            change_value = net_worth - previous_net_worth
            if previous_net_worth != 0:
                change_percentage = (change_value / abs(previous_net_worth)) * 100
            elif net_worth != 0:
                change_percentage = float('inf') * (1 if net_worth > 0 else -1)

    return {
        "net_worth": net_worth,
        "total_assets_value": total_assets_value,
        "total_debts_value": total_debts_value,
        "liquid_assets_value": liquid_assets_value,
        "non_liquid_assets_value": non_liquid_assets_value,
        "liquid_percentage": liquid_percentage,
        "asset_count": len(current_snapshot_balances),
        "category_count": len(categories_used),
        "top_categories": top_categories,
        "change_value": change_value,
        "change_percentage": change_percentage,
        "has_previous_data": has_previous_data
    } 