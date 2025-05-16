"""
Chart utilities for Net Worth Tracker.
This module handles all chart generation functionality.
"""
import json
import os
from rich.console import Console
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
from datetime import datetime, timedelta
from rich.style import Style
from rich.text import Text

# Initialize console for output
console = Console()

# from asset_utils import guess_category, DEFAULT_CATEGORIES, get_all_categories # get_all_categories and DEFAULT_CATEGORIES removed
from asset_utils import guess_category # Only guess_category might be relevant if chart_utils is updated

def generate_charts(snapshots: list, financial_items: list, categories: list, chart_type="summary", specific_asset_id=None):
    """
    Generate charts based on historical data.
    
    Args:
        snapshots: List of historical snapshots.
        financial_items: List of all financial item definitions.
        categories: List of all category definitions.
        chart_type: Type of chart to generate ("summary", "detailed", "category", "asset", or "all")
        specific_asset_id: ID of a specific financial item to chart (only used when chart_type is "asset")
        
    Returns:
        List of generated chart filenames
    """
    if not snapshots or len(snapshots) < 1:
        console.print("[yellow]No historical data (or less than 1 record) available to generate a chart.[/yellow]")
        return []
    
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Prepare data for charting using the new data structures
    chart_data_prepared = _prepare_chart_data(snapshots, financial_items)
    if not chart_data_prepared:
        console.print("[yellow]No chartable data found after processing records.[/yellow]")
        return []
        
    generated_charts_list = []
    df_for_charts = chart_data_prepared['df']
    # specific_asset_name will be derived if specific_asset_id is provided
    specific_asset_name = None
    if specific_asset_id:
        item = next((fi for fi in financial_items if fi['id'] == specific_asset_id), None)
        if item: specific_asset_name = item['name']
        else: console.print(f"[red]Asset ID {specific_asset_id} not found for charting.[/red]"); return []

    if chart_type == "summary" or chart_type == "all":
        filename = "net_worth_summary_chart.png"
        _generate_summary_chart(chart_data_prepared, filename) # Pass the whole dict
        generated_charts_list.append(filename)
        
    if chart_type == "detailed" or chart_type == "all":
        filename = "net_worth_detailed_chart.png"
        _generate_detailed_chart(chart_data_prepared, filename) # Pass the whole dict
        generated_charts_list.append(filename)
        
    if chart_type == "category" or chart_type == "all":
        filename = "net_worth_category_chart.png"
        _generate_category_chart(df_for_charts, filename, snapshots, financial_items, categories)
        generated_charts_list.append(filename)
        
    if chart_type == "asset" and specific_asset_name: # Check specific_asset_name now
        filename = f"{specific_asset_name.replace(' ', '_').lower()}_history_chart.png"
        _generate_single_asset_chart(chart_data_prepared, filename, specific_asset_name) # Pass name
        generated_charts_list.append(filename)
        
    return generated_charts_list

def _prepare_chart_data(snapshots: list, financial_items: list):
    """
    Prepares data for charting from new data structures.
    
    Args:
        snapshots: List of historical snapshots.
        financial_items: List of all financial item definitions.
        
    Returns:
        Dictionary with chart data or None if no data
    """
    data_for_df_creation = []
    # Sort snapshots by date chronologically for the chart
    # Snapshots from data_manager are already sorted most recent first, so reverse for charting
    sorted_snapshots_for_chart = sorted(snapshots, key=lambda x: x['date'], reverse=False)

    # Create a lookup for item_id to item_name and item_type
    item_details_lookup = {item['id']: {'name': item['name'], 'type': item['type']} for item in financial_items}
    
    all_item_names_in_data = set() # To keep track of all item names that appear in snapshots

    for snapshot_entry in sorted_snapshots_for_chart:
        row_dict = {'date': snapshot_entry['date']}
        net_worth_for_this_date = 0
        positive_assets_total_for_date = 0
        # Liabilities are typically stored as positive numbers and their sum is subtracted, 
        # or stored as negative. Here, we assume balances are already signed correctly.
        # Let's track assets (positive balance contribution) and liabilities (negative balance contribution)
        # based on their *actual balances* in the snapshot for now, similar to old logic.
        # The `type` field in financial_items can be used for more robust classification later.

        for balance_item in snapshot_entry['balances']:
            item_id = balance_item['item_id']
            balance = balance_item.get('balance', 0.0)
            
            item_info = item_details_lookup.get(item_id)
            if not item_info: continue # Skip if item_id not in financial_items (should not happen)
            
            item_name = item_info['name']
            all_item_names_in_data.add(item_name)
            row_dict[item_name] = balance
            net_worth_for_this_date += balance
            
            if balance >= 0: # Simplified: positive balance = asset contribution for summary
                positive_assets_total_for_date += balance
            # else: negative_assets_total_for_date += balance (if tracking sum of negative values)
        
        row_dict['_Net_Worth'] = net_worth_for_this_date
        row_dict['_Positive_Assets_Total'] = positive_assets_total_for_date
        # For summary chart, we might need sum of liabilities. Let's assume balances are signed.
        # So, _Debts_Total_Negative would be sum of items with balance < 0.
        row_dict['_Debts_Total_Negative'] = sum(b['balance'] for b in snapshot_entry['balances'] if b['balance'] < 0)
        data_for_df_creation.append(row_dict)

    if not data_for_df_creation:
        return None
        
    df = pd.DataFrame(data_for_df_creation)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Fill NaN with 0.0 for all item names that appeared in the data plus special columns
    # This ensures all columns exist for all dates, even if an item had no balance.
    all_columns_to_ensure = list(all_item_names_in_data) + ['_Net_Worth', '_Positive_Assets_Total', '_Debts_Total_Negative']
    for col_name in all_columns_to_ensure:
        if col_name not in df.columns:
            df[col_name] = 0.0 # Add column if it was completely missing (e.g. an item never had data)
    df = df.fillna(0.0)

    # Classify columns more directly for plotting if possible.
    # For now, derive positive_asset_cols and debt_cols based on financial_item types and their presence in df.
    # This is a placeholder; the plotting functions might need more specific column lists.
    positive_potential_cols = []
    debt_potential_cols = []
    for item in financial_items:
        item_name = item['name']
        if item_name not in df.columns: continue # Only consider items that ended up in the DF

        # Simplified classification based on type for now, actual plotting might use sums of balances
        if item['type'] == 'asset':
            positive_potential_cols.append(item_name)
        elif item['type'] == 'liability':
            # Assuming liabilities are represented by their actual (often negative) balances in the item_name column
            debt_potential_cols.append(item_name) 

    # The original code for _generate_summary_chart expects columns whose *sum* is positive for assets
    # and sum is negative for debts. Let's try to reproduce that for minimal changes to plotting functions.
    # However, this is not ideal if an item (e.g. bank account) can be both asset and liability.
    final_positive_asset_cols = [col for col in positive_potential_cols if df[col].sum() >= 0 and col in df.columns]
    # For debt_cols, we look for items that are typed as liability AND their sum in the df is < 0 OR any item whose sum is <0
    # This part is tricky to match exactly without knowing how plotting functions use these.
    # Let's use a simpler approach: if it's a liability type, it's a debt_col for categorization.
    # The actual plotting for summary chart used _Positive_Assets_Total and _Debts_Total_Negative directly.
    # For detailed chart, it iterates these lists.
    
    # For detailed chart, we need lists of item names that are generally assets vs liabilities.
    # Let type be the primary guide.
    asset_cols_for_detailed = sorted([item['name'] for item in financial_items if item['type'] == 'asset' and item['name'] in df.columns])
    liability_cols_for_detailed = sorted([item['name'] for item in financial_items if item['type'] == 'liability' and item['name'] in df.columns])

    return {
        'df': df,
        'positive_asset_cols': asset_cols_for_detailed, # Used by detailed chart for positive items
        'debt_cols': liability_cols_for_detailed      # Used by detailed chart for negative items (actual balances are plotted)
    }

def _generate_summary_chart(chart_data_prepared, chart_filename):
    """
    Generates a summary chart with consolidated assets and debts.
    
    Args:
        chart_data_prepared: Dictionary with chart data
        chart_filename: Filename to save the chart
    """
    df = chart_data_prepared['df']
    positive_asset_cols = chart_data_prepared['positive_asset_cols']
    debt_cols = chart_data_prepared['debt_cols']

    fig, ax = plt.subplots(figsize=(14, 8))

    # Define colors
    positive_asset_color = 'mediumseagreen'
    debt_color = 'lightcoral'
    net_worth_line_color = 'royalblue'

    # Prepare data for consolidated plotting
    # Positive Assets: sum of all columns deemed 'positive assets', ensuring values are non-negative
    if positive_asset_cols:
        df_positive_plot_data = df[positive_asset_cols].copy()
        df_positive_plot_data[df_positive_plot_data < 0] = 0 # Zero out any anomalous negative values in these columns
        series_positive_assets = df_positive_plot_data.sum(axis=1)
        if not series_positive_assets.empty and series_positive_assets.sum() > 0:
            ax.stackplot(df.index, series_positive_assets, labels=['Assets'], colors=[positive_asset_color], alpha=0.7)

    # Debts: sum of all columns deemed 'debt assets' (these values are negative)
    if debt_cols:
        series_debts = df[debt_cols].sum(axis=1)
        if not series_debts.empty and series_debts.sum() < 0: # Ensure there are debts to plot
            ax.stackplot(df.index, series_debts, labels=['Debts'], colors=[debt_color], alpha=0.7)

    # Plot Net Worth as a line
    if '_Net_Worth' in df.columns:
        # Plot the line first
        ax.plot(df.index, df['_Net_Worth'], label='Total Net Worth', 
                       color=net_worth_line_color, linewidth=2.5, marker='o', linestyle='--')
        
        # Add annotations for net worth values with smart positioning to avoid overlap
        net_worth_values = df['_Net_Worth'].values
        dates = df.index
        
        # Determine a sensible interval for annotations based on the number of data points
        total_points = len(net_worth_values)
        if total_points <= 12:
            # For few points, annotate all
            annotation_indices = range(total_points)
        else:
            # For many points, annotate some sensibly spaced ones
            interval = max(1, total_points // 10)  # At most ~10 annotations
            annotation_indices = range(0, total_points, interval)
            # Always include the first and last points
            if total_points - 1 not in annotation_indices:
                annotation_indices = list(annotation_indices) + [total_points - 1]
        
        # Keep track of previous annotation positions to avoid overlap
        prev_y_pos = None
        text_height = 15000  # Estimated text height in data coordinates
        
        for i in annotation_indices:
            value = net_worth_values[i]
            date = dates[i]
            
            # Format the value with commas
            value_text = f"{value:,.0f}"
            
            # Determine position for annotation - alternate above/below if close to previous
            if prev_y_pos is not None and abs(value - prev_y_pos) < text_height * 2:
                # If close to previous annotation, position on opposite side
                if i % 2 == 0:
                    xytext = (0, 20)  # above
                else:
                    xytext = (0, -20)  # below
            else:
                # Default positioning based on whether this is a positive or negative value
                xytext = (0, 20) if value >= 0 else (0, -20)
            
            ax.annotate(value_text, 
                       xy=(date, value), 
                       xytext=xytext,
                       textcoords='offset points',
                       ha='center', 
                       va='bottom' if xytext[1] > 0 else 'top',
                       fontsize=9,
                       bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                       arrowprops=dict(arrowstyle='->', color=net_worth_line_color))
            
            prev_y_pos = value

    ax.axhline(0, color='black', linewidth=0.8, linestyle='-') # Zero line for reference
    ax.set_title('Net Worth Summary', fontsize=16)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Value', fontsize=12)
    
    # Format dates on x-axis to "5 Jun '25" format
    date_format = mdates.DateFormatter("%-d %b '%y")  # Use %-d to remove leading zeros
    ax.xaxis.set_major_formatter(date_format)
    
    # Set tick location to show every month
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    
    # Make tick labels smaller
    plt.xticks(rotation=45, fontsize=8)
    
    # Format y-axis to show numbers with commas and no decimals
    formatter = FuncFormatter(lambda y, _: f'{y:,.0f}')
    ax.yaxis.set_major_formatter(formatter)

    # Adjust legend: gather all labels from stackplots and the line plot
    handles, labels = ax.get_legend_handles_labels()
    # Filter out duplicate labels if any
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc='upper center', bbox_to_anchor=(0.5, -0.15), fontsize=10, ncol=3)
    
    plt.tight_layout(rect=[0, 0.05, 1, 1])  # Adjust layout to make space for legend below
    
    try:
        plt.savefig(chart_filename)
        console.print(f"[green]Summary chart saved as [cyan]{chart_filename}[/cyan][/green]")
    except Exception as e:
        console.print(f"[bold red]An error occurred while saving the summary chart: {e}[/bold red]")
    finally:
        plt.close(fig) # Close the figure to free memory

def _generate_detailed_chart(chart_data, chart_filename):
    """
    Generates a detailed chart with individual assets and debts shown separately.
    
    Args:
        chart_data: Dictionary with chart data
        chart_filename: Filename to save the chart
    """
    df = chart_data['df']
    positive_asset_cols = chart_data['positive_asset_cols'] 
    debt_cols = chart_data['debt_cols']

    fig, ax = plt.subplots(figsize=(14, 9))  # Taller to accommodate bottom legend

    # Prepare colormaps for assets and debts
    import matplotlib.cm as cm
    from itertools import cycle
    
    # Use a colormap with distinct colors
    asset_colors = cycle(plt.cm.tab20.colors[:10] + plt.cm.tab20b.colors[:10] + plt.cm.tab20c.colors[:10])
    debt_colors = cycle(plt.cm.Set3.colors)
    
    # Sort positive assets by their initial values to determine stacking order
    asset_first_values = {}
    for col in positive_asset_cols:
        series = df[col].copy()
        series[series < 0] = 0  # Ensure non-negative
        if series.sum() > 0:
            # Get first non-zero value or first value
            for val in series:
                if val > 0:
                    asset_first_values[col] = val
                    break
            else:
                asset_first_values[col] = 0

    # Sort assets by first value (descending) so largest are plotted first (closest to zero line)
    sorted_positive_assets = sorted(asset_first_values.keys(), 
                                    key=lambda x: asset_first_values[x], 
                                    reverse=True)
    
    # Sort debts by their absolute initial values (largest absolute value first)
    debt_first_values = {}
    for col in debt_cols:
        series = df[col]
        if series.sum() < 0:
            # Get first non-zero value or first value
            for val in series:
                if val < 0:
                    debt_first_values[col] = abs(val)  # Use absolute value for sorting
                    break
            else:
                debt_first_values[col] = 0
    
    # Sort debts by first value (descending) so largest absolute values are plotted first
    sorted_debt_cols = sorted(debt_first_values.keys(),
                             key=lambda x: debt_first_values[x],
                             reverse=True)
    
    # Plot each positive asset separately, in order of size (largest first)
    if sorted_positive_assets:
        asset_data = []
        asset_colors_list = []
        asset_labels = []
        
        for col in sorted_positive_assets:
            series = df[col].copy()
            series[series < 0] = 0  # Ensure all values are non-negative
            if series.sum() > 0:  # Only include if there are positive values
                asset_data.append(series)
                asset_colors_list.append(next(asset_colors))
                asset_labels.append(col)
        
        if asset_data:  # Only proceed if we have data to plot
            ax.stackplot(df.index, asset_data, labels=asset_labels, colors=asset_colors_list, alpha=0.7)
    
    # Plot each debt separately, in order of absolute size (largest first)
    if sorted_debt_cols:
        debt_data = []
        debt_colors_list = []
        debt_labels = []
        
        for col in sorted_debt_cols:
            series = df[col]
            if series.sum() < 0:  # Only include if there are negative values
                debt_data.append(series)
                debt_colors_list.append(next(debt_colors))
                debt_labels.append(col)
        
        if debt_data:  # Only proceed if we have data to plot
            ax.stackplot(df.index, debt_data, labels=debt_labels, colors=debt_colors_list, alpha=0.7)
    
    # Plot Net Worth as a line
    if '_Net_Worth' in df.columns:
        # Plot the line first
        ax.plot(df.index, df['_Net_Worth'], label='Total Net Worth', 
                     color='black', linewidth=2.5, marker='o', linestyle='--')
        
        # Add annotations for net worth values with smart positioning to avoid overlap
        net_worth_values = df['_Net_Worth'].values
        dates = df.index
        
        # Determine a sensible interval for annotations based on the number of data points
        total_points = len(net_worth_values)
        if total_points <= 12:
            # For few points, annotate all
            annotation_indices = range(total_points)
        else:
            # For many points, annotate some sensibly spaced ones
            interval = max(1, total_points // 8)  # At most ~8 annotations to avoid clutter
            annotation_indices = range(0, total_points, interval)
            # Always include the first and last points
            if total_points - 1 not in annotation_indices:
                annotation_indices = list(annotation_indices) + [total_points - 1]
        
        # Keep track of previous annotation positions to avoid overlap
        prev_y_pos = None
        text_height = 15000  # Estimated text height in data coordinates
        
        for i in annotation_indices:
            value = net_worth_values[i]
            date = dates[i]
            
            # Format the value with commas
            value_text = f"{value:,.0f}"
            
            # Determine position for annotation - alternate above/below if close to previous
            if prev_y_pos is not None and abs(value - prev_y_pos) < text_height * 2:
                # If close to previous annotation, position on opposite side
                if i % 2 == 0:
                    xytext = (0, 20)  # above
                else:
                    xytext = (0, -20)  # below
            else:
                # Default positioning based on whether this is a positive or negative value
                xytext = (0, 20) if value >= 0 else (0, -20)
            
            ax.annotate(value_text, 
                       xy=(date, value), 
                       xytext=xytext,
                       textcoords='offset points',
                       ha='center', 
                       va='bottom' if xytext[1] > 0 else 'top',
                       fontsize=9,
                       bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                       arrowprops=dict(arrowstyle='->', color='black'))
            
            prev_y_pos = value

    ax.axhline(0, color='black', linewidth=0.8, linestyle='-')  # Zero line for reference
    ax.set_title('Detailed Net Worth by Asset', fontsize=16)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Value', fontsize=12)
    
    # Format dates on x-axis to "5 Jun '25" format
    date_format = mdates.DateFormatter("%-d %b '%y")  # Use %-d to remove leading zeros
    ax.xaxis.set_major_formatter(date_format)
    
    # Set tick location to show every month
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    
    # Make tick labels smaller
    plt.xticks(rotation=45, fontsize=8)
    
    # Format y-axis to show numbers with commas and no decimals
    formatter = FuncFormatter(lambda y, _: f'{y:,.0f}')
    ax.yaxis.set_major_formatter(formatter)

    # Create legend with proper sizing
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    
    # Place legend at the bottom of the chart
    # Calculate number of columns based on number of items
    total_items = len(by_label)
    ncols = min(5, total_items)  # Max 5 columns, fewer if fewer items
    
    ax.legend(by_label.values(), by_label.keys(), 
              loc='upper center', 
              bbox_to_anchor=(0.5, -0.15), 
              fontsize=9, 
              ncol=ncols)
    
    plt.tight_layout(rect=[0, 0.1, 1, 1])  # Adjust layout to make space for legend at bottom
    
    try:
        plt.savefig(chart_filename)
        console.print(f"[green]Detailed chart saved as [cyan]{chart_filename}[/cyan][/green]")
    except Exception as e:
        console.print(f"[bold red]An error occurred while saving the detailed chart: {e}[/bold red]")
    finally:
        plt.close(fig)  # Close the figure to free memory

def _generate_category_chart(df_for_charts: pd.DataFrame, chart_filename: str, snapshots: list, financial_items: list, categories_list: list):
    """
    Generates a chart that groups financial items by category using the new data structures.
    
    Args:
        df_for_charts: Pandas DataFrame with dates as index and financial item names as columns.
        chart_filename: Filename to save the chart.
        snapshots: List of historical snapshots (not directly used here if df is sufficient, but passed for context).
        financial_items: List of all financial item definitions.
        categories_list: List of all category definitions.
    """
    # Create a lookup for category_id to category_name
    category_id_to_name_lookup = {cat['id']: cat['name'] for cat in categories_list}

    # Group item names by their category name
    # item_names_grouped_by_category will map: {<category_name>: [<item_name1>, <item_name2>, ...]}
    item_names_grouped_by_category = {}
    for item in financial_items:
        item_name = item['name']
        category_id = item.get('category_id')
        category_name = category_id_to_name_lookup.get(category_id, "Uncategorized") # Default if cat_id is missing or invalid
        
        if item_name not in df_for_charts.columns: # Only consider items present in the DataFrame
            continue
            
        if category_name not in item_names_grouped_by_category:
            item_names_grouped_by_category[category_name] = []
        item_names_grouped_by_category[category_name].append(item_name)

    if not item_names_grouped_by_category:
        console.print("[yellow]No items could be grouped by category for charting.[/yellow]")
        return

    fig, ax = plt.subplots(figsize=(14, 9))
    
    # Color cycling for categories
    import matplotlib.cm as cm
    from itertools import cycle
    unique_category_names = sorted(item_names_grouped_by_category.keys())
    category_color_map = {}
    # Using a robust color cycle
    color_cycler = cycle(plt.cm.tab20.colors + plt.cm.tab20b.colors + plt.cm.tab20c.colors)
    for cat_name_iter in unique_category_names:
        category_color_map[cat_name_iter] = next(color_cycler)

    # Calculate sum of balances for each category over time
    category_summed_data = {}
    category_is_predominantly_negative = {} # To help with stacking order

    for category_name_iter, item_names_in_cat in item_names_grouped_by_category.items():
        # Filter item_names_in_cat to those actually in df_for_charts.columns (already done above)
        valid_item_names_for_sum = [name for name in item_names_in_cat if name in df_for_charts.columns]
        if valid_item_names_for_sum:
            category_series_sum = df_for_charts[valid_item_names_for_sum].sum(axis=1)
            category_summed_data[category_name_iter] = category_series_sum
            # Check if the sum of the series is predominantly negative
            category_is_predominantly_negative[category_name_iter] = category_series_sum.sum() < 0 
        else:
            # Create an empty series if no valid items (e.g. all items filtered out)
             category_summed_data[category_name_iter] = pd.Series(0.0, index=df_for_charts.index) 
             category_is_predominantly_negative[category_name_iter] = False

    # Sort categories for consistent plotting order: positive sums first, then negative sums
    positive_value_categories = []
    negative_value_categories = []
    for cat_name_iter in unique_category_names: # Use unique_category_names for sorting base
        if category_is_predominantly_negative.get(cat_name_iter, False):
            negative_value_categories.append(cat_name_iter)
        else:
            positive_value_categories.append(cat_name_iter)
    
    # Sort positive categories by their initial summed value (largest first)
    positive_value_categories.sort(key=lambda c: category_summed_data[c].iloc[0] if not category_summed_data[c].empty else 0, reverse=True)
    # Sort negative categories by the absolute of their initial summed value (largest absolute first)
    negative_value_categories.sort(key=lambda c: abs(category_summed_data[c].iloc[0]) if not category_summed_data[c].empty else 0, reverse=True)

    # --- Plotting Positive Categories ---
    positive_category_plot_data = []
    positive_category_plot_colors = []
    positive_category_plot_labels = []
    for cat_name_iter in positive_value_categories:
        series_to_plot = category_summed_data[cat_name_iter].copy()
        # For stack plot, ensure values are non-negative for this section
        # If a category sum is negative but it wasn't classified as predominantly_negative, it might appear here.
        # We plot actual sum; if negative, it will subtract from stack.
        # For clear positive stacking, one might zero out negatives: series_to_plot[series_to_plot < 0] = 0
        # However, let's plot the true sum for the category.
        if not series_to_plot.empty: # Check if series has data
            positive_category_plot_data.append(series_to_plot)
            positive_category_plot_colors.append(category_color_map[cat_name_iter])
            positive_category_plot_labels.append(cat_name_iter)
    
    if positive_category_plot_data:
        ax.stackplot(df_for_charts.index, positive_category_plot_data, labels=positive_category_plot_labels, colors=positive_category_plot_colors, alpha=0.7)

    # --- Plotting Negative Categories ---
    # These are categories whose sums are predominantly negative.
    # Stackplot handles negative values by plotting them downwards from the previous stack level or zero line.
    negative_category_plot_data = []
    negative_category_plot_colors = []
    negative_category_plot_labels = []
    for cat_name_iter in negative_value_categories:
        series_to_plot = category_summed_data[cat_name_iter]
        if not series_to_plot.empty: # Check if series has data
            negative_category_plot_data.append(series_to_plot) # Plot actual (negative) sums
            negative_category_plot_colors.append(category_color_map[cat_name_iter])
            negative_category_plot_labels.append(f"{cat_name_iter} (Liability/Debt)") # Clarify in legend

    if negative_category_plot_data:
        ax.stackplot(df_for_charts.index, negative_category_plot_data, labels=negative_category_plot_labels, colors=negative_category_plot_colors, alpha=0.7)
    
    # Plot Net Worth as a line (same as in other charts, can be refactored to a helper)
    if '_Net_Worth' in df_for_charts.columns:
        ax.plot(df_for_charts.index, df_for_charts['_Net_Worth'], label='Total Net Worth', 
                     color='black', linewidth=2.5, marker='o', linestyle='--')
        net_worth_values = df_for_charts['_Net_Worth'].values
        dates = df_for_charts.index
        total_points = len(net_worth_values)
        annotation_indices = range(total_points) if total_points <= 12 else list(range(0, total_points, max(1, total_points // 8))) + ([total_points - 1] if total_points -1 not in range(0, total_points, max(1, total_points // 8)) else [])
        annotation_indices = sorted(list(set(annotation_indices))) # Ensure unique and sorted

        prev_y_pos = None; text_height_est = (df_for_charts['_Net_Worth'].max() - df_for_charts['_Net_Worth'].min()) * 0.05 if not df_for_charts['_Net_Worth'].empty else 1000
        if text_height_est == 0: text_height_est = 1000 # Avoid zero text height if flat net worth

        for i in annotation_indices:
            value = net_worth_values[i]; date = dates[i]; value_text = f"{value:,.0f}"
            xytext_offset_y = 20
            if prev_y_pos is not None and abs(value - prev_y_pos) < text_height_est * 1.5 : # More sensitive overlap check
                xytext_offset_y = -20 if (i % 2 == 0 and value > prev_y_pos) or (i % 2 != 0 and value < prev_y_pos) else 20
            else:
                xytext_offset_y = 20 if value >= (df_for_charts['_Net_Worth'].median() if not df_for_charts['_Net_Worth'].empty else 0) else -20 
            ax.annotate(value_text, xy=(date, value), xytext=(0, xytext_offset_y), textcoords='offset points', ha='center', 
                        va='bottom' if xytext_offset_y > 0 else 'top', fontsize=9,
                        bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.7),
                        arrowprops=dict(arrowstyle='->', connectionstyle="arc3,rad=.2", color='black'))
            prev_y_pos = value

    ax.axhline(0, color='black', linewidth=0.8, linestyle='-')
    ax.set_title('Net Worth by Category', fontsize=16)
    ax.set_xlabel('Date', fontsize=12); ax.set_ylabel('Value', fontsize=12)
    date_format = mdates.DateFormatter("%-d %b '%y"); ax.xaxis.set_major_formatter(date_format)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.xticks(rotation=45, fontsize=8)
    formatter = FuncFormatter(lambda y, _: f'{y:,.0f}'); ax.yaxis.set_major_formatter(formatter)

    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    total_legend_items = len(by_label)
    ncols_legend = min(max(1, total_legend_items // 2 if total_legend_items > 10 else total_legend_items //1 ), 4) # Dynamic columns
    ax.legend(by_label.values(), by_label.keys(), loc='upper center', bbox_to_anchor=(0.5, -0.20), fontsize=8, ncol=ncols_legend)
    plt.tight_layout(rect=[0, 0.15, 1, 1]) # Adjust for bottom legend
    
    try:
        plt.savefig(chart_filename)
        console.print(f"[green]Category chart saved as [cyan]{chart_filename}[/cyan][/green]")
    except Exception as e:
        console.print(f"[bold red]An error occurred while saving the category chart: {e}[/bold red]")
    finally:
        plt.close(fig)

def _generate_single_asset_chart(chart_data, chart_filename, asset_name):
    """
    Generates a chart showing the balance history of a single specific asset.
    
    Args:
        chart_data: Dictionary with chart data
        chart_filename: Filename to save the chart
        asset_name: Name of the asset to chart
    """
    df = chart_data['df']
    
    # Check if the asset exists in the dataframe
    if asset_name not in df.columns:
        console.print(f"[yellow]Asset '{asset_name}' not found in historical data.[/yellow]")
        return
    
    # Extract the asset's balance history
    asset_series = df[asset_name]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Determine if asset is generally positive or negative (debt)
    is_mostly_positive = asset_series.mean() >= 0
    line_color = 'green' if is_mostly_positive else 'red'
    fill_color = 'mediumseagreen' if is_mostly_positive else 'lightcoral'
    
    # Plot the asset balance as a line
    ax.plot(df.index, asset_series, label=asset_name, 
            color=line_color, linewidth=2.5, marker='o')
    
    # Add fill below the line to emphasize the values
    ax.fill_between(df.index, asset_series, 0, 
                    color=fill_color, alpha=0.3)
    
    # Add annotations for values
    for date, value in zip(df.index, asset_series):
        value_text = f"£{value:,.0f}"
        ax.annotate(value_text, (date, value),
                   xytext=(0, 10 if value >= 0 else -20),
                   textcoords='offset points',
                   ha='center', va='center',
                   bbox=dict(boxstyle='round,pad=0.5', fc='white', alpha=0.7),
                   fontsize=9)
    
    # Configure axes
    ax.set_title(f'Balance History for {asset_name}', fontsize=16, pad=20)
    ax.set_xlabel('Date', fontsize=12, labelpad=10)
    ax.set_ylabel('Balance (£)', fontsize=12, labelpad=10)
    
    # Format y-axis as currency
    def gbp_formatter(x, pos):
        return f'£{x:,.0f}'
    
    ax.yaxis.set_major_formatter(FuncFormatter(gbp_formatter))
    
    # Configure x-axis date formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    plt.xticks(rotation=45)
    
    # Add horizontal line at zero
    ax.axhline(y=0, color='gray', linestyle='-', alpha=0.7)
    
    # Add grid
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the chart
    plt.savefig(chart_filename, dpi=100, bbox_inches='tight')
    plt.close()
    
    console.print(f"[green]Single asset chart created: [bold]{chart_filename}[/bold][/green]") 