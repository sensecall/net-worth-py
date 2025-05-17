# No specific imports like datetime seem needed for these functions based on current structure
# from datetime import datetime # Only if calculate_summary_stats were to parse dates internally

from datetime import datetime
import uuid
from typing import Optional, Dict, Any

STANDARD_MILESTONES = [
    {"value": 0, "name": "Debt Free"},  # Represents Net Worth >= 0
    {"value": 1000, "name": "£1k"},
    {"value": 10000, "name": "£10k"},
    {"value": 25000, "name": "£25k"},
    {"value": 50000, "name": "£50k"},
    {"value": 100000, "name": "£100k"},
    {"value": 250000, "name": "£250k"},
    {"value": 500000, "name": "£500k"},
    {"value": 750000, "name": "£750k"},
    {"value": 1000000, "name": "£1M"}
]

def get_net_worth_for_snapshot(snapshot_balances: list, financial_items: list) -> float:
    """Calculates the total net worth for a given single snapshot's balances and financial items list."""
    # This function assumes financial_items contains the definitions needed to interpret balances.
    # For simplicity, we are assuming balance entries directly contribute to net worth.
    # A more complex version might use item_type from financial_items if snapshot_balances
    # only contains positive values and item_type distinguishes assets from liabilities.
    # However, the current structure seems to store balances with their sign (+ for assets, - for debts).
    net_worth = 0.0
    for balance_entry in snapshot_balances:
        net_worth += balance_entry.get("balance", 0.0)
    return net_worth

def calculate_enhanced_trends(snapshots: list, financial_items: list) -> dict:
    """Calculates average monthly net worth changes over 3, 6, and 12 months."""
    trends = {
        'avg_3m_raw': None, 'avg_6m_raw': None, 'avg_12m_raw': None,
        'avg_3m_display': "N/A", 'avg_6m_display': "N/A", 'avg_12m_display': "N/A",
        'current_month_net_worth': None,
        'oldest_available_net_worth_12m': None # For context
    }

    if not snapshots or not financial_items:
        return trends

    # Snapshots are assumed to be sorted: most recent first.
    # We need to parse dates to determine month boundaries and calculate net worth for each snapshot.
    monthly_net_worths = {}
    for snapshot in snapshots:
        try:
            snap_date_str = snapshot.get('date')
            if not snap_date_str: continue
            snap_datetime = datetime.strptime(snap_date_str, '%Y-%m-%d')
            month_year_key = snap_datetime.strftime('%Y-%m') # Use YYYY-MM as a key for monthly data
            
            # If multiple snapshots in a month, use the latest one (first one we encounter due to sorting)
            if month_year_key not in monthly_net_worths:
                monthly_net_worths[month_year_key] = get_net_worth_for_snapshot(snapshot.get('balances', []), financial_items)
        except ValueError:
            continue # Skip snapshots with invalid dates
    
    if not monthly_net_worths:
        return trends

    sorted_months = sorted(monthly_net_worths.keys(), reverse=True) # Most recent month first
    
    trends['current_month_net_worth'] = monthly_net_worths[sorted_months[0]]

    # Helper to calculate average change
    def _calculate_average_monthly_change(num_months):
        if len(sorted_months) < num_months + 1: # Need at least N+1 months of data to compare N periods
            return None
        
        # Net worth at the start of the period (N months ago from current month's start)
        # sorted_months[0] is current month, sorted_months[num_months] is N months ago.
        current_period_end_nw = monthly_net_worths[sorted_months[0]]
        period_start_nw = monthly_net_worths[sorted_months[num_months]]
        
        total_change = current_period_end_nw - period_start_nw
        average_change = total_change / num_months
        return average_change

    periods = [(3, '3m'), (6, '6m'), (12, '12m')]
    for num_months, key_suffix in periods:
        avg_change = _calculate_average_monthly_change(num_months)
        if avg_change is not None:
            trends[f'avg_{key_suffix}_raw'] = avg_change
            sign = "+" if avg_change >= 0 else "-"
            trends[f'avg_{key_suffix}_display'] = f"{sign}£{abs(avg_change):,.2f}/month"
        if key_suffix == '12m' and len(sorted_months) >= 12 +1:
             trends['oldest_available_net_worth_12m'] = monthly_net_worths[sorted_months[12]]
    
    return trends

def update_and_get_milestone_progress(current_net_worth: float, 
                                      achieved_milestones_values: list, 
                                      standard_milestones_definition: list) -> dict:
    """Checks for newly achieved milestones, updates the list, and determines progress to the next one."""
    result = {
        'next_milestone_name': "N/A",
        'next_milestone_value': None,
        'progress_percent': 0.0,
        'newly_achieved_milestones': [], # List of values of newly achieved milestones
        'all_milestones_achieved': False
    }

    # Sort standard milestones by value to ensure correct processing
    sorted_standard_milestones = sorted(standard_milestones_definition, key=lambda m: m['value'])

    # Check for newly achieved milestones
    for milestone in sorted_standard_milestones:
        milestone_val = milestone['value']
        if current_net_worth >= milestone_val and milestone_val not in achieved_milestones_values:
            result['newly_achieved_milestones'].append(milestone_val)
    
    # Find the next unachieved milestone
    next_milestone_found = False
    for milestone in sorted_standard_milestones:
        milestone_val = milestone['value']
        # A milestone is a candidate for "next" if its value is greater than current net worth,
        # OR if it's one of the newly achieved ones (meaning we just passed it, 
        # but it wasn't in the *original* achieved_milestones_values list yet for progress calculation)
        # OR if it has not been achieved yet from the original list.
        # Simplified: find first standard milestone whose value hasn't been confirmed as achieved *before this function call*.
        if milestone_val not in achieved_milestones_values and milestone_val not in result['newly_achieved_milestones']:
            # This milestone is not yet in the persistently achieved list.
            # Is it the next one we are aiming for?
            if current_net_worth < milestone_val:
                result['next_milestone_name'] = milestone['name']
                result['next_milestone_value'] = milestone_val
                next_milestone_found = True
                break # Found the immediate next one we are working towards
    
    if not next_milestone_found and result['newly_achieved_milestones']:
        # We might have achieved some, and need to find the one AFTER the highest newly achieved
        # OR if all standard milestones that are >= current_net_worth are now achieved.
        # Let's re-evaluate after adding newly_achieved to a temporary full list
        temp_all_achieved = achieved_milestones_values + result['newly_achieved_milestones']
        for milestone in sorted_standard_milestones:
            if milestone['value'] not in temp_all_achieved and current_net_worth < milestone['value']:
                result['next_milestone_name'] = milestone['name']
                result['next_milestone_value'] = milestone_val
                next_milestone_found = True
                break

    if not next_milestone_found:
        # Check if all defined milestones are achieved or surpassed
        highest_defined_milestone = sorted_standard_milestones[-1]['value'] if sorted_standard_milestones else 0
        if current_net_worth >= highest_defined_milestone and \
           all(m['value'] in achieved_milestones_values or m['value'] in result['newly_achieved_milestones'] for m in sorted_standard_milestones if m['value'] <= current_net_worth):
            result['all_milestones_achieved'] = True
            result['next_milestone_name'] = "All Defined Milestones Achieved!"

    # Calculate progress to the found next milestone
    if result['next_milestone_value'] is not None and not result['all_milestones_achieved']:
        # Determine the correct previous milestone for percentage calculation
        # This is the highest achieved milestone that is less than the next_milestone_value.
        # If no such milestone exists (e.g., next milestone is £1k and £0/Debt Free was just passed or is the base),
        # then the previous milestone value is effectively 0 for calculation if current_net_worth is positive.
        # If current_net_worth is negative and target is £0 (Debt Free), special handling is needed.

        previous_milestone_for_progress = 0 # Default starting point for progress calculation
        
        # Combine originally achieved and newly achieved for finding the immediate prior milestone
        all_currently_achieved_values = sorted(list(set(achieved_milestones_values + result['newly_achieved_milestones'])), reverse=True)
        
        for achieved_val in all_currently_achieved_values:
            if achieved_val < result['next_milestone_value']:
                previous_milestone_for_progress = achieved_val
                break
        
        # Specific handling for the "Debt Free" (£0) milestone as the target
        if result['next_milestone_value'] == 0:
            if current_net_worth >= 0:
                result['progress_percent'] = 100.0
            else:
                # If current net worth is negative, and the "previous" milestone for progress is also negative (which is unlikely with current definitions)
                # or if previous_milestone_for_progress is 0 (meaning we are coming from debt towards 0).
                # Let's assume the "start" of the journey to £0 is the lowest recorded net worth or a conceptual deep debt.
                # For simplicity here, if current_net_worth is < 0, and target is 0, progress towards 0 is hard to represent as a simple percentage from a previous positive milestone.
                # We will show 0% until >= 0 for the £0 milestone.
                # A more nuanced display might show "Remaining debt: £X" instead of percentage here.
                result['progress_percent'] = 0.0 
        else: # For all other positive milestones
            # Progress is from the 'previous_milestone_for_progress' towards 'result['next_milestone_value']'
            target_value = result['next_milestone_value']
            base_value = previous_milestone_for_progress

            # Ensure base_value is not greater than current_net_worth if current_net_worth is below base_value but targeting higher.
            # This can happen if user falls back below an achieved milestone.
            # The progress should be from the highest achieved milestone *below* the target that is also less than or equal to current net worth, or 0.
            # Effectively, the `previous_milestone_for_progress` logic already tries to find the right base.

            current_progress_value = current_net_worth - base_value
            total_progress_needed = target_value - base_value

            if total_progress_needed > 0:
                percentage = (current_progress_value / total_progress_needed) * 100
                result['progress_percent'] = max(0, min(100, percentage)) # Clamp between 0 and 100
            elif current_net_worth >= target_value: # Should have been caught as newly achieved, but for safety
                result['progress_percent'] = 100.0
            else: # target_range is 0 or negative (e.g. target is same as base, or an error in logic/data)
                result['progress_percent'] = 0.0 

    elif result['all_milestones_achieved']:
        result['progress_percent'] = 100.0

    return result

def calculate_goal_projection(financial_goal: Optional[Dict[str, Any]], 
                              current_net_worth: float, 
                              trends_raw: Dict[str, Optional[float]]) -> Dict[str, Any]:
    """Calculates the projected time to reach a financial goal based on multiple trend periods."""
    
    base_result = {
        "target_net_worth_display": "N/A",
        "goal_already_reached": False,
        "individual_projections": [],
        "overall_status_message": "Financial goal not set."
    }

    if not financial_goal or financial_goal.get("target_net_worth") is None:
        return base_result

    target_nw = financial_goal["target_net_worth"]
    base_result["target_net_worth_display"] = f"£{target_nw:,.2f}"

    if current_net_worth >= target_nw:
        base_result["goal_already_reached"] = True
        base_result["overall_status_message"] = "Goal already reached!"
        return base_result

    valid_projections_found = False
    for period_key, avg_monthly_change in trends_raw.items():
        period_label = "Unknown Trend"
        if period_key == "avg_3m_raw": period_label = "3M Avg"
        elif period_key == "avg_6m_raw": period_label = "6M Avg"
        elif period_key == "avg_12m_raw": period_label = "12M Avg"
        # Add more specific labels if other keys are used in trends_raw

        if avg_monthly_change is not None and avg_monthly_change > 0:
            months_to_goal_float = (target_nw - current_net_worth) / avg_monthly_change
            
            years = int(months_to_goal_float // 12)
            remaining_months = int(months_to_goal_float % 12)

            time_parts = []
            if years > 0:
                time_parts.append(f"{years} year{'s' if years > 1 else ''}")
            if remaining_months > 0:
                time_parts.append(f"{remaining_months} month{'s' if remaining_months > 1 else ''}")
            
            current_time_str = ""
            if not time_parts:
                current_time_str = "<1 month"
            else:
                current_time_str = f"Approx. {' and '.join(time_parts)}"

            base_result["individual_projections"].append({
                "period_label": period_label,
                "time_to_goal_str": current_time_str,
                "raw_months": round(months_to_goal_float, 1) # Store raw months for potential sorting/min-max
            })
            valid_projections_found = True
    
    if valid_projections_found:
        # Sort by raw_months to have a somewhat consistent order if needed, shortest first
        base_result["individual_projections"].sort(key=lambda p: p["raw_months"])
        base_result["overall_status_message"] = "See individual trend projections."
    elif not trends_raw or all(val is None for val in trends_raw.values()):
        base_result["overall_status_message"] = "Projection N/A (insufficient trend data)."
    else: # Some trends exist, but none are positive
        base_result["overall_status_message"] = "Projection N/A (trends are zero or negative)."
        
    return base_result

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