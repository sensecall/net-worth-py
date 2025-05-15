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

## Data Structure

The application stores data in JSON format with the following structure:

```json
[
    {
        "date": "YYYY-MM-DD",
        "assets": [
            {
                "name": "Asset Name",
                "liquid": true/false,
                "balance": 1000.00,
                "category": "Category Name"
            }
        ]
    }
]
```

## License

MIT License 