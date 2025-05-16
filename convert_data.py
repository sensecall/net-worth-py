import json
from datetime import datetime

# Predefined category keywords (similar to your _DEFAULT_CATEGORY_DATA)
# You can expand this list for better keyword association.
PREDEFINED_CATEGORY_KEYWORDS = {
    "Property": ["house", "property", "flat", "apartment", "land"],
    "Pension": ["pension", "sipp", "retirement"],
    "ISA": ["isa", "ssisa", "stocks and shares isa", "cash isa"],
    "Savings": ["savings", "premium bonds", "saver", "saving", "cash savings"],
    "Current Account": ["current", "checking", "bank balance"],
    "Investment": ["shares", "stocks", "investment", "fund", "gia", "brokerage"],
    "Mortgage": ["mortgage", "property loan"],
    "Loan": ["loan", "car finance", "personal loan", "debt"],
    "Credit Card": ["credit", "cc", "credit card balance"],
    "Business": ["business", "company assets", "business value"],
    "Other": ["miscellaneous", "other assets"]
}

# Categories typically considered liabilities
LIABILITY_CATEGORIES = ["Mortgage", "Loan", "Credit Card"]

def generate_id(existing_ids_list, prefix):
    """Generates a new unique ID string like prefix_1, prefix_2, etc."""
    if not existing_ids_list:
        return f"{prefix}1"
    
    numeric_parts = []
    for id_str in existing_ids_list:
        if id_str.startswith(prefix):
            try:
                numeric_parts.append(int(id_str[len(prefix):]))
            except ValueError:
                pass # Should not happen if IDs are well-formed
    
    next_num = max(numeric_parts) + 1 if numeric_parts else 1
    return f"{prefix}{next_num}"

def convert_data(old_file_path="net_worth_data.json", new_file_path="net_worth_refactored_converted.json"):
    """
    Converts data from the old format to the new refactored format.
    """
    try:
        with open(old_file_path, 'r') as f:
            old_data_snapshots = json.load(f)
    except FileNotFoundError:
        print(f"Error: Old data file '{old_file_path}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{old_file_path}'. File might be corrupted.")
        return

    new_categories_list = []
    new_financial_items_list = []
    new_snapshots_list = []

    # --- Step 1: Discover all unique categories and financial items ---
    category_name_to_id_map = {}
    financial_item_name_to_id_map = {}
    
    unique_category_names = set()
    unique_financial_item_details = {} # Stores {name: {'category': name, 'liquid': bool}}

    for old_snapshot in old_data_snapshots:
        for asset_entry in old_snapshot.get("assets", []):
            item_name = asset_entry.get("name")
            category_name = asset_entry.get("category")
            is_liquid = asset_entry.get("liquid", False)

            if not item_name or not category_name:
                print(f"Warning: Skipping entry with missing name or category in snapshot for date {old_snapshot.get('date')}: {asset_entry}")
                continue

            unique_category_names.add(category_name)
            if item_name not in unique_financial_item_details:
                unique_financial_item_details[item_name] = {
                    'category_name': category_name, 
                    'liquid': is_liquid
                }

    # --- Step 2: Create new category objects with unique IDs ---
    existing_cat_ids = []
    for cat_name in sorted(list(unique_category_names)):
        cat_id = generate_id(existing_cat_ids, "cat_")
        existing_cat_ids.append(cat_id)
        category_name_to_id_map[cat_name] = cat_id
        
        new_categories_list.append({
            "id": cat_id,
            "name": cat_name,
            "keywords": PREDEFINED_CATEGORY_KEYWORDS.get(cat_name, [])
        })

    # --- Step 3: Create new financial item objects with unique IDs ---
    existing_item_ids = []
    for item_name in sorted(list(unique_financial_item_details.keys())):
        details = unique_financial_item_details[item_name]
        item_id = generate_id(existing_item_ids, "item_")
        existing_item_ids.append(item_id)
        financial_item_name_to_id_map[item_name] = item_id
        
        original_cat_name = details['category_name']
        category_id_for_item = category_name_to_id_map.get(original_cat_name)
        
        if not category_id_for_item:
            print(f"Error: Could not find mapped category ID for category name '{original_cat_name}' for item '{item_name}'. This should not happen.")
            continue
            
        item_type = "asset"
        if original_cat_name in LIABILITY_CATEGORIES:
            item_type = "liability"

        new_financial_items_list.append({
            "id": item_id,
            "name": item_name,
            "category_id": category_id_for_item,
            "liquid": details['liquid'],
            "type": item_type
        })
        
    # --- Step 4: Create new snapshot objects using the new item IDs ---
    for old_snapshot in old_data_snapshots:
        new_balances_for_snapshot = []
        snapshot_date = old_snapshot.get("date")
        if not snapshot_date:
            print(f"Warning: Skipping snapshot with no date: {old_snapshot}")
            continue
            
        for asset_entry in old_snapshot.get("assets", []):
            item_name = asset_entry.get("name")
            balance = asset_entry.get("balance")

            if item_name is None or balance is None:
                 print(f"Warning: Skipping asset entry with missing name or balance in snapshot for date {snapshot_date}: {asset_entry}")
                 continue

            item_id_for_balance = financial_item_name_to_id_map.get(item_name)
            
            if not item_id_for_balance:
                print(f"Error: Could not find mapped item ID for item name '{item_name}' in snapshot {snapshot_date}. This should not happen.")
                continue

            new_balances_for_snapshot.append({
                "item_id": item_id_for_balance,
                "balance": float(balance)
            })
        
        new_snapshots_list.append({
            "date": snapshot_date,
            "balances": new_balances_for_snapshot
        })

    # --- Step 5: Assemble the final refactored data object ---
    refactored_data = {
        "categories": new_categories_list,
        "financial_items": new_financial_items_list,
        "snapshots": sorted(new_snapshots_list, key=lambda s: s['date'], reverse=True)
    }

    # --- Step 6: Write to the new JSON file ---
    try:
        with open(new_file_path, 'w') as f:
            json.dump(refactored_data, f, indent=2)
        print(f"Successfully converted data to '{new_file_path}'")
    except IOError:
        print(f"Error: Could not write converted data to '{new_file_path}'.")
    except Exception as e:
        print(f"An unexpected error occurred while writing the new file: {e}")

if __name__ == "__main__":
    print("Starting data conversion...")
    convert_data(old_file_path="net_worth_data.json", new_file_path="net_worth_refactored_converted.json")
    print("Conversion process finished.")
    print("Please check 'net_worth_refactored_converted.json'.")
    print("If it looks correct, you can rename it to 'net_worth_refactored.json' to be used by the main application.") 