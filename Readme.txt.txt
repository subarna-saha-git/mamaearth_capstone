# Mamaearth Data Analytics and AI Capstone

## Project Overview

This project uses SQL and Python to analyze Mamaearth sales data. It also creates charts and uses Gemini AI to write a business report.

## 1. Run SQL Files

Open MySQL Workbench and run these files in order:

1. `sql/schema.sql`
2. `sql/seed_data.sql`
3. `sql/reports.sql`

## 2. Run Python Analysis

Install the required libraries:

```bash
python -m pip install pandas matplotlib
```

Run these commands from the project folder:

```bash
python analysis/clean_and_eda.py
python analysis/visualize.py
```

The first script cleans the data and creates `narrator/findings.json`. The second script creates charts and saves them in the `visualizations/` folder.

## 3. Generate the AI Report

Install the Gemini library:

```bash
python -m pip install google-genai
```

To use Gemini, get a free-tier API key from [Google AI Studio](https://aistudio.google.com/apikey).

In Windows Command Prompt, set your key:

```cmd
set GEMINI_API_KEY=your_api_key_here
```

Then run:

```cmd
python narrator\generate_narrative.py
```

The report is saved in `narrator/sample_output.txt`.

To run without a key, use:

```cmd
set GEMINI_API_KEY=
python narrator\generate_narrative.py
```

The script will use the offline version instead. No API key or internet connection is needed.

## 4. Output Files

- `narrator/findings.json` — analysis results
- `narrator/sample_output.txt` — business report
- `visualizations/return_rate_by_payment.png` — return-rate chart
- `visualizations/monthly_revenue_trend.png` — monthly revenue chart

Run all three Python scripts in order to complete the project.
