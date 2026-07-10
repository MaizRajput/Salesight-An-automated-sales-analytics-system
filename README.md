# Salesight: An Automated Sales Analytics System

An end-to-end pipeline that takes messy, real-world retail data — any format, any column naming convention, any encoding — and turns it into clean data plus 30+ business insights, through a REST API.

Built as a B.Tech Computer Science capstone project. No manual column renaming, no writing a fresh cleaning script for every new dataset — upload a file, get an analytics-ready dashboard.

## What makes this different

Most "sales dashboard" projects assume the data is already clean and well-labeled. This one doesn't assume that.

- Upload basically any sales CSV or Excel file, even if the columns are named `cust_nm`, `Amt_Rs`, `ord_dt_ddmmyyyy`, or whatever the source system happened to call them.
- A fuzzy column-mapping engine maps messy source columns to canonical fields automatically. It normalizes column names, scores them against 400+ keyword variants across 25 field types (order ID, customer ID, product, category, region, revenue, profit, rating, dates, payment method, loyalty status, return flags, and more), and falls back to regex pattern-matching — recognizing something like `INV-00234` as an order ID — when the column name itself gives no useful hint.
- A 15-step cleaning pipeline handles type coercion, missing-value imputation, outlier capping, and business-rule enforcement, all guarded by a hard rule that the pipeline can never drop more than 15% of the original rows. If a rule would remove too many rows, it caps or corrects the data instead of deleting it.
- On real test datasets, this hits 96.3% column-mapping accuracy and 94.3% row retention after cleaning.

## Core features

**Intelligent column mapping**
Fuzzy, exact, substring, and word-part scoring across 25 canonical field types, with a confidence score reported per detected field and a clear list of anything left unmapped. Warnings are generated automatically when critical fields like revenue, date, order ID, or customer ID can't be found or derived.

**Multi-pass data cleaning (15 steps)**
Multi-encoding, multi-delimiter file loading; column name normalization and duplicate-column collapsing; duplicate row removal; infinite-value and type-coercion fixes with auto string-to-numeric detection and robust date parsing; context-aware missing-value imputation that uses a different strategy per field rather than one blanket rule; quantity range filtering; gender normalization; rating capping; cancelled-order business rules; IQR-based outlier capping; domain bound checks; and automatic derived columns (`revenue`, `revenue_after_discount`, `age_group`, `revenue_tier`, plus a full date breakdown into year, month, quarter, week, day-of-week, and weekend flag).

**30+ analytics endpoints**

| Category | What it covers |
|---|---|
| Core KPIs and summary | Revenue, orders, average order value, top-line health |
| Revenue trends | Monthly and quarterly trend, growth rate, category-level growth |
| Product performance | Top and lowest sellers, highest and lowest rated (with a minimum-order threshold to avoid noise) |
| Customer segmentation | Gender distribution, age distribution, categories by gender |
| Geography | Regional breakdown, region-by-category cross analysis |
| Behavioral analytics | Repeat customer rate, sales velocity, sales-phase detection (z-score based spike/dip finder) |
| Pricing and promotions | Discount-vs-baseline impact, revenue tiering, payment method mix |
| Advanced / market basket | Frequently-bought-together product combos, monthly category distribution, post-purchase return analysis, anomaly detection |

**REST API (FastAPI)**
A single `/upload` endpoint runs the whole pipeline in one call — cleaning, mapping, KPI computation, SQL persistence. Every upload gets a session ID, so you can come back later and hit `/preview`, `/schema`, `/mapping`, `/report`, or any `/insights/*` route without re-uploading. There are also download endpoints for the cleaned CSV and the full JSON cleaning report, and interactive API docs auto-generated at `/docs`.

**Storage**
SQLAlchemy ORM with a swappable backend — SQLite for local dev, Postgres or SQL Server for production, switched with a single environment variable (`DATABASE_URL`) and no code changes. Every session's metadata (row counts, retention percentage, warnings) is tracked for auditability.

**Frontend**
A single-page dashboard (`ui.html`) that consumes every API endpoint — upload, preview, schema, and all 30+ insight views — with no build step required.

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI |
| Data processing | Pandas, NumPy |
| Persistence | SQLAlchemy (SQLite / Postgres / SQL Server) |
| File support | openpyxl, xlrd |
| Frontend | HTML/CSS/JS, single file, no framework |
| Visualization layer | Power BI (companion analytics layer) |

## API overview

```
POST   /upload                          run the full pipeline on a new file
GET    /sessions                        list all past upload sessions
GET    /preview                         paginated row preview
GET    /schema                          per-column dtype, nulls, uniques, samples
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

Full interactive docs are available at `/docs` once the app is running.

## Quickstart

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Visit `http://localhost:8000` for the dashboard, or `http://localhost:8000/docs` for the API explorer.

For live deployment steps, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Project structure

```
.
├── main.py             FastAPI app, routes, session management
├── cleaner.py           15-step multi-pass cleaning pipeline
├── column_mapper.py     Fuzzy column detection and canonical mapping
├── insights.py          30+ analytics functions
├── db.py                SQLAlchemy models and session persistence
├── static/ui.html        Frontend dashboard
└── requirements.txt
```

## Background

Built as a final-year B.Tech (Computer Science and Engineering) capstone project. The core problem it solves: real sales data in the wild never comes pre-labeled the way tutorials assume. This system is built to handle that reality — arbitrary column names, inconsistent encodings, dirty values — without a human manually mapping fields before every analysis run.
