# Net Worth Tracker

A Python-based terminal application for tracking personal net worth over time.

## Features

- Add, edit, and categorise assets and liabilities
- Track assets by liquidity status and category
- Historical tracking of net worth with dated records
- Generate visualisations of your financial data:
  - Summary chart showing assets vs debts
  - Detailed chart breaking down individual assets
  - Category-based chart grouping assets by type
- UK-specific asset categorisation (Pension, ISA, Property, etc.)
- Data preserved in JSON format for portability

## Getting Started

### Requirements

- Python 3.x
- Optional: matplotlib and pandas for chart generation

### Installation

1. Clone this repository
2. (Optional) Set up a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate
   ```
   or if you're on an ARM Mac:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
   or if you're on Windows:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install rich readchar simple-term-menu
   pip install matplotlib pandas  # Optional, for charts
   ```

   Alternatively, you can install all dependencies using the requirements file:
   ```
   pip install -r requirements.txt
   ```

### Usage

Run the application from your terminal:

```
python net_worth_tracker.py
```

## Data Structure (`net_worth_refactored.json`)

The `net_worth_refactored.json` file stores the net worth data in a structured format. It consists of three main sections: `categories`, `financial_items`, and `snapshots`.

### 1. `categories`
A list of all financial categories. Each category object has:
- `id` (string): A unique identifier for the category (e.g., "cat_1").
- `name` (string): The display name of the category (e.g., "Mortgage").
- `keywords` (list of strings): Keywords for potential auto-categorisation or search (e.g., ["mortgage", "property loan"]).

### 2. `financial_items`
A list of all unique assets and liabilities. Each item object has:
- `id` (string): A unique identifier for the financial item (e.g., "item_1").
- `name` (string): The display name of the item (e.g., "Mortgage").
- `category_id` (string): The ID of the category this item belongs to (links to `categories`).
- `liquid` (boolean): Indicates if the item is considered liquid.
- `type` (string): Specifies if the item is an "asset" or a "liability".

### 3. `snapshots`
A time-series list of net worth snapshots. Each snapshot object has:
- `date` (string): The date of the snapshot in "YYYY-MM-DD" format.
- `balances` (list of objects): A list of balances for various financial items on that date. Each balance object contains:
    - `item_id` (string): The ID of the financial item (links to `financial_items`).
    - `balance` (float): The monetary balance of the item on that date.

## License

MIT License 