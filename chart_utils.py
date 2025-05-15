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
from datetime import datetime

# Initialize console for output
console = Console()

def generate_charts(all_historical_records, chart_type="summary", specific_asset=None):
    """
    Generate charts based on historical data.
    
    Args:
        all_historical_records: List of historical net worth records
        chart_type: Type of chart to generate ("summary", "detailed", "category", "asset", or "all")
        specific_asset: Name of a specific asset to chart (only used when chart_type is "asset")
        
    Returns:
        List of generated chart filenames
    """
    if not all_historical_records or len(all_historical_records) < 1:
        console.print("[yellow]No historical data (or less than 1 record) available to generate a chart.[/yellow]")
        return []
    
    # Apply a style
    plt.style.use('seaborn-v0_8-whitegrid')
    
    # Prepare data for charting
    chart_data = _prepare_chart_data(all_historical_records)
    if not chart_data:
        console.print("[yellow]No chartable data found after processing records.[/yellow]")
        return []
        
    generated_charts = []
    
    if chart_type == "summary" or chart_type == "all":
        chart_filename = "net_worth_summary_chart.png"
        _generate_summary_chart(chart_data, chart_filename)
        generated_charts.append(chart_filename)
        
    if chart_type == "detailed" or chart_type == "all":
        chart_filename = "net_worth_detailed_chart.png"
        _generate_detailed_chart(chart_data, chart_filename)
        generated_charts.append(chart_filename)
        
    if chart_type == "category" or chart_type == "all":
        chart_filename = "net_worth_category_chart.png"
        _generate_category_chart(chart_data, chart_filename, all_historical_records)
        generated_charts.append(chart_filename)
        
    if chart_type == "asset" and specific_asset:
        # Generate a chart for a specific asset
        chart_filename = f"{specific_asset.replace(' ', '_').lower()}_history_chart.png"
        _generate_single_asset_chart(chart_data, chart_filename, specific_asset)
        generated_charts.append(chart_filename)
        
    return generated_charts

def _prepare_chart_data(all_historical_records):
    """
    Prepares data for charting from historical records.
    
    Args:
        all_historical_records: List of historical net worth records
        
    Returns:
        Dictionary with chart data or None if no data
    """
    data_for_df = []
    # Sort records by date chronologically for the chart
    sorted_records = sorted(all_historical_records, key=lambda x: x['date'])

    all_asset_names = set()
    all_debt_names = set()

    for record in sorted_records:
        entry = {'date': record['date']}
        net_worth_for_date = 0
        positive_assets_total = 0
        negative_assets_total = 0 # Sum of absolute values of debts

        for asset in record['assets']:
            name = asset['name']
            balance = asset.get('balance', 0.0)
            net_worth_for_date += balance
            if balance >= 0:
                all_asset_names.add(name)
                entry[name] = balance
                positive_assets_total += balance
            else:
                debt_name = f"{name}" # Keep original name, will be plotted as negative or handled
                all_debt_names.add(debt_name)
                entry[debt_name] = balance # Store actual negative balance
                negative_assets_total += balance # balance is already negative
        
        entry['_Net_Worth'] = net_worth_for_date
        entry['_Positive_Assets_Total'] = positive_assets_total
        entry['_Debts_Total_Negative'] = negative_assets_total # This will be a negative sum
        data_for_df.append(entry)

    if not data_for_df:
        return None
        
    df = pd.DataFrame(data_for_df)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    # Consistently fill NaN with 0 for all potential asset/debt columns
    all_involved_names = all_asset_names.union(all_debt_names)
    for name in all_involved_names:
        if name not in df.columns:
            df[name] = 0.0
    df = df.fillna(0.0)

    # Separate positive assets and debts for plotting
    positive_asset_cols = sorted([name for name in all_asset_names if name in df.columns and df[name].sum() >= 0])
    debt_cols = sorted([name for name in all_debt_names if name in df.columns and df[name].sum() < 0])
    
    return {
        'df': df,
        'positive_asset_cols': positive_asset_cols,
        'debt_cols': debt_cols
    }

def _generate_summary_chart(chart_data, chart_filename):
    """
    Generates a summary chart with consolidated assets and debts.
    
    Args:
        chart_data: Dictionary with chart data
        chart_filename: Filename to save the chart
    """
    df = chart_data['df']
    positive_asset_cols = chart_data['positive_asset_cols']
    debt_cols = chart_data['debt_cols']

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

def _generate_category_chart(chart_data, chart_filename, all_historical_records):
    """
    Generates a chart that groups assets by category.
    
    Args:
        chart_data: Dictionary with chart data
        chart_filename: Filename to save the chart
        all_historical_records: List of historical net worth records for category lookup
    """
    from asset_utils import guess_category, DEFAULT_CATEGORIES, get_all_categories
    
    df = chart_data['df']
    positive_asset_cols = chart_data['positive_asset_cols'] 
    debt_cols = chart_data['debt_cols']
    
    # We need to determine the category for each asset column
    asset_categories = {}
    
    # Get the latest record to extract categories
    latest_record = max(all_historical_records, key=lambda x: x['date']) if all_historical_records else None
    
    if latest_record and 'assets' in latest_record:
        for asset in latest_record['assets']:
            if 'name' in asset and 'category' in asset:
                asset_categories[asset['name']] = asset['category']
    
    # For any assets not found in the latest record, try to guess
    for col in positive_asset_cols + debt_cols:
        if col not in asset_categories:
            asset_categories[col] = guess_category(col)
    
    # Group columns by category
    categories_to_cols = {}
    for col in positive_asset_cols + debt_cols:
        category = asset_categories.get(col, "Other")
        if category not in categories_to_cols:
            categories_to_cols[category] = []
        categories_to_cols[category].append(col)
    
    fig, ax = plt.subplots(figsize=(14, 9))  # Taller to accommodate bottom legend
    
    # Get a color cycle for categories
    import matplotlib.cm as cm
    from itertools import cycle
    
    # Create a colormap for categories
    categories = sorted(categories_to_cols.keys())
    category_colors = {}
    
    # Use tab20 colormap for first 20 categories, then cycle
    color_cycle = cycle(plt.cm.tab20.colors + plt.cm.tab20b.colors + plt.cm.tab20c.colors)
    for category in categories:
        category_colors[category] = next(color_cycle)
    
    # For each category, create a series that's the sum of all assets in that category
    category_data = {}
    category_is_negative = {}  # Track if a category contains primarily negative values
    
    for category, cols in categories_to_cols.items():
        # Sum all columns for this category
        if cols:
            category_series = df[cols].sum(axis=1)
            
            # Check if this category is primarily debts
            is_negative = category_series.sum() < 0
            category_is_negative[category] = is_negative
            
            # For debts (negative values), we'll plot separately with a different color
            category_data[category] = category_series
    
    # Sort categories by initial value (largest positive first, then largest negative)
    pos_categories = []
    neg_categories = []
    
    for category in categories:
        if category in category_data:
            if category_is_negative.get(category, False):
                neg_categories.append(category)
            else:
                pos_categories.append(category)
    
    # Sort positive categories by initial value (largest first)
    pos_categories.sort(key=lambda c: category_data[c].iloc[0] if not category_data[c].empty else 0, reverse=True)
    
    # Sort negative categories by absolute initial value (largest first)
    neg_categories.sort(key=lambda c: abs(category_data[c].iloc[0]) if not category_data[c].empty else 0, reverse=True)
    
    # Plot positive categories
    pos_plot_data = []
    pos_plot_colors = []
    pos_plot_labels = []
    
    for category in pos_categories:
        series = category_data[category].copy()
        series[series < 0] = 0  # Ensure all values are non-negative for stacking
        if series.sum() > 0:
            pos_plot_data.append(series)
            pos_plot_colors.append(category_colors[category])
            pos_plot_labels.append(category)
    
    if pos_plot_data:
        ax.stackplot(df.index, pos_plot_data, labels=pos_plot_labels, colors=pos_plot_colors, alpha=0.7)
    
    # Plot negative categories
    neg_plot_data = []
    neg_plot_colors = []
    neg_plot_labels = []
    
    for category in neg_categories:
        series = category_data[category]
        if series.sum() < 0:
            neg_plot_data.append(series)
            neg_plot_colors.append(category_colors[category])
            neg_plot_labels.append(f"{category} (Debt)")
    
    if neg_plot_data:
        ax.stackplot(df.index, neg_plot_data, labels=neg_plot_labels, colors=neg_plot_colors, alpha=0.7)
    
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
    ax.set_title('Net Worth by Category', fontsize=16)
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
        console.print(f"[green]Category chart saved as [cyan]{chart_filename}[/cyan][/green]")
    except Exception as e:
        console.print(f"[bold red]An error occurred while saving the category chart: {e}[/bold red]")
    finally:
        plt.close(fig)  # Close the figure to free memory 

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