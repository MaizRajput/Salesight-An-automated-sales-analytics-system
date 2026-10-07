# Salesight: An Automated Sales Analytics System

This project takes messy retail sales data in any format, with any column names and any encoding, and turns it into clean data plus 30+ business insights through a REST API.

I built it as my B.Tech Computer Science capstone. The idea was to stop renaming columns by hand and stop writing a new cleaning script for every dataset. You upload a file and get a dashboard that is ready to use.

## Why it is different

Most sales dashboard projects assume the data is already clean and well labelled. This one does not.

- You can upload almost any sales CSV or Excel file, even if the columns are called `cust_nm`, `Amt_Rs`, `ord_dt_ddmmyyyy` or whatever the source system decided to use.
- A fuzzy column mapper matches the messy columns to standard fields on its own. It cleans up the column names and scores them against 400+ keyword variants across 25 field types (order ID, customer ID, product, category, region, revenue, profit, rating, dates, payment method, loyalty status, return flags and more). If the name gives no clue, it falls back to pattern matching, so a value like `INV-00234` is still recognised as an order ID.
- A 15 step cleaning pipeline handles type fixes, missing values, outliers and business rules. It has one hard rule: it can never drop more than 15% of the original rows. If a rule would remove too many, the data gets capped or corrected instead of deleted.
- On my test datasets it reached 96.3% column mapping accuracy and kept 94.3% of rows after cleaning.

## Main features

**Column mapping**
Exact, fuzzy, substring and word part scoring across 25 standard field types. Each detected field gets a confidence score, and anything the mapper could not place is listed separately. If something important like revenue, date, order ID or customer ID is missing and cannot be derived, a warning is raised.

**Data cleaning (15 steps)**
Files can be loaded with different encodings and delimiters. The pipeline fixes column names, merges duplicate columns, removes duplicate rows, handles infinite values, converts strings to numbers where it makes sense and parses dates in different formats. Missing values are filled with a different strategy for each field instead of one rule for everything. It also filters quantity ranges, normalises gender values, caps ratings, applies rules for cancelled orders, caps outliers using IQR and checks domain bounds. New columns are created automatically: `revenue`, `revenue_after_discount`, `age_group`, `revenue_tier` and a full date breakdown (year, month, quarter, week, day of week, weekend flag).

**30+ analytics endpoints**

| Category | What it covers |
|---|---|
| Core KPIs and summary | Revenue, orders, average order value, overall health |
| Revenue trends | Monthly and quarterly trend, growth rate, growth by category |
| Product performance | Top and lowest sellers, highest and lowest rated (with a minimum order count to avoid noise) |
| Customer segments | Gender split, age split, categories by gender |
| Geography | Regional breakdown, region by category |
| Behaviour | Repeat customer rate, sales velocity, sales phases (z score based spikes and dips) |
| Pricing and promotions | Discount vs baseline, revenue tiers, payment method mix |
| Advanced | Products bought together, monthly category split, post purchase returns, anomaly detection |

**REST API (FastAPI)**
One `/upload` call runs everything: cleaning, mapping, KPIs and saving to the database. Each upload gets a session ID, so you can come back later and use `/preview`, `/schema`, `/mapping`, `/report` or any `/insights/*` route without uploading again. You can also download the cleaned CSV and the full JSON cleaning report, and the interactive docs are generated at `/docs`.

**Storage**
SQLAlchemy with a swappable backend. SQLite for local work, Postgres or SQL Server for production, switched with a single environment variable (`DATABASE_URL`) and no code changes. Metadata for every session (row counts, retention percentage, warnings) is saved so there is a record of each upload.

**Frontend**
A single page dashboard (`ui.html`) that uses every API endpoint, from upload and preview to schema and all the insight views. It needs no build step.

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Data processing | Pandas, NumPy |
| Storage | SQLAlchemy (SQLite, Postgres, SQL Server) |
| File support | openpyxl, xlrd |
| Frontend | HTML, CSS and JS in a single file, no framework |
| Visualisation | Power BI (as a companion analytics layer) |

## API overview

```
POST   /upload                          run the full pipeline on a new file
GET    /sessions                        list all past upload sessions
GET    /preview                         row preview
GET    /schema                          dtype, nulls, uniques and samples per column
GET    /mapping                         column mapping confidence report
GET    /report                          full cleaning report for a session

GET    /insights/kpis
GET    /insights/revenue-trend
GET    /insights/revenue-growth
GET    /insights/quarterly-revenue
GET    /insights/category-growth
GET    /insights/top-categories
GET    /insights/top-products
GET    /insights/lowest-products
GET    /insights/highest-rated
GET    /insights/lowest-rated
GET    /insights/regional
GET    /insights/region-category
GET    /insights/gender-distribution
GET    /insights/categories-by-gender
GET    /insights/age-distribution
GET    /insights/payment-methods
GET    /insights/anomalies
GET    /insights/revenue-tiers
GET    /insights/sales-velocity
GET    /insights/repeat-customers
GET    /insights/sales-phases
GET    /insights/discount-vs-baseline
GET    /insights/product-combos
GET    /insights/monthly-category-distribution
GET    /insights/post-purchase-return
GET    /insights/summary

GET    /download/cleaned                cleaned CSV
GET    /download/report                 JSON cleaning report
```

The full interactive docs are at `/docs` once the app is running.

## Quickstart

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://localhost:8000` for the dashboard or `http://localhost:8000/docs` for the API explorer.

For deployment steps, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Project structure

```
main.py              FastAPI app, routes, session handling
cleaner.py           15 step cleaning pipeline
column_mapper.py     column detection and mapping to standard fields
insights.py          30+ analytics functions
db.py                SQLAlchemy models and session saving
static/ui.html       frontend dashboard
requirements.txt
```

## Background

This was my final year B.Tech (Computer Science and Engineering) capstone project. The problem it tackles is that real sales data almost never comes labelled the way tutorials expect. The system is built to cope with that: random column names, mixed encodings and dirty values, without someone mapping fields by hand before every analysis.
