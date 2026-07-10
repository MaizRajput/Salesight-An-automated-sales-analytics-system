from __future__ import annotations
import json, uuid, traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from cleaner       import DataCleaner
from column_mapper import detect_columns, apply_mapping, mapping_summary
from db            import init_db, save_cleaned_df, load_session_df, list_sessions, get_session_meta
import insights

app = FastAPI(title="Sales Analytics System", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for d in ["data/raw", "data/cleaned", "logs", "static"]:
    Path(d).mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

SESSIONS: dict = {}
MAX_MB = 100


@app.on_event("startup")
def on_startup():
    init_db()


def get_session(session_id: str) -> dict:
    if session_id in SESSIONS:
        return SESSIONS[session_id]
    df = load_session_df(session_id)
    if df is None:
        raise HTTPException(404, "Session not found. Please upload a file first.")
    meta = get_session_meta(session_id) or {}
    SESSIONS[session_id] = {"df": df, "report": meta, "filename": meta.get("filename", ""), "mapping": None}
    return SESSIONS[session_id]


def read_any_file(path: Path) -> pd.DataFrame:
    errors = []
    for fn in [
        lambda: pd.read_csv(path, encoding="utf-8"),
        lambda: pd.read_csv(path, encoding="latin1"),
        lambda: pd.read_excel(path, engine="openpyxl"),
        lambda: pd.read_excel(path, engine="xlrd"),   # handles old .xls disguised as .xlsx
        lambda: pd.read_csv(path, sep="\t", encoding="utf-8"),
        lambda: pd.read_csv(path, sep="\t", encoding="latin1"),
    ]:
        try:
            df = fn()
            if df.shape[1] > 1:
                return df
        except Exception as e:
            errors.append(str(e))
    raise ValueError(
        f"Could not read this file. Ensure it is a valid CSV or Excel file. "
        f"Attempted {len(errors)} strategies. Last error: {errors[-1] if errors else 'unknown'}"
    )


def df_records(df: pd.DataFrame, limit: int = 500) -> list[dict]:
    tmp = df.head(limit).copy()
    for col in tmp.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        tmp[col] = tmp[col].dt.strftime("%Y-%m-%d").fillna("")
    return json.loads(
        tmp.fillna("").to_json(orient="records", date_format="iso", default_handler=str)
    )


@app.get("/")
async def root():
    for f in [Path("static/ui.html"), Path("static/index.html")]:
        if f.exists(): return FileResponse(f)
    return JSONResponse({"status": "running — open /docs"})

@app.get("/health")
async def health():
    return {"status": "ok", "sessions_cached": len(SESSIONS), "ts": datetime.utcnow().isoformat()}

@app.get("/sessions")
async def sessions_list():
    return {"sessions": list_sessions()}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {MAX_MB} MB limit.")

    ext = Path(file.filename).suffix.lower()
    if ext not in {".csv", ".tsv", ".txt", ".xlsx", ".xls"}:
        raise HTTPException(400, f"Unsupported type '{ext}'. Upload a CSV or Excel file.")

    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = Path("data/raw") / f"{ts}_{file.filename}"
    raw_path.write_bytes(content)

    try:
        df_raw = read_any_file(raw_path)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(422, f"Could not read file: {e}")

    if df_raw.empty:
        raise HTTPException(422, "File is empty — no data rows found.")

    try:
        cleaner            = DataCleaner(df_raw)
        cleaned_df, report = cleaner.run()
    except Exception as e:
        raise HTTPException(500, f"Cleaning pipeline error: {e}\n{traceback.format_exc()}")

    try:
        mapping_result = detect_columns(cleaned_df)
        mapped_df      = apply_mapping(cleaned_df, mapping_result)
    except Exception:
        mapped_df      = cleaned_df
        mapping_result = None

    sid        = str(uuid.uuid4())[:8]
    clean_path = Path("data/cleaned") / f"{sid}_cleaned.csv"
    rpt_path   = Path("data/cleaned") / f"{sid}_report.json"
    mapped_df.to_csv(clean_path, index=False)

    ms = mapping_summary(mapping_result) if mapping_result else {}
    report.update({"session_id": sid, "filename": file.filename,
                   "file_type": ext, "column_mapping": ms})
    rpt_path.write_text(json.dumps(report, indent=2, default=str))

    try:
        table_name = save_cleaned_df(mapped_df, sid, file.filename, report)
    except Exception:
        table_name = None

    SESSIONS[sid] = {"df": mapped_df, "report": report,
                     "filename": file.filename, "mapping": mapping_result}

    kpis = insights.get_kpis(mapped_df)

    return {
        "session_id":        sid,
        "filename":          file.filename,
        "file_type":         ext,
        "original_shape":    report["original_shape"],
        "cleaned_shape":     report["cleaned_shape"],
        "rows_retained":     f"{report['rows_retained_pct']}%",
        "rows_retained_pct": report["rows_retained_pct"],
        "columns_mapped":    ms.get("total_mapped", 0),
        "warnings":          report.get("warnings", []),
        "columns":           list(mapped_df.columns),
        "final_columns":     list(mapped_df.columns),
        "detected_fields":   list(mapping_result.mapped.keys()) if mapping_result else [],
        "sql_table":         table_name,
        "metrics":           report.get("metrics", {}),
        "kpis":              kpis,
        "preview":           df_records(mapped_df, 100),
        "mapping":           ms,
        "meta": {
            "session_id":    sid,
            "filename":      file.filename,
            "rows":          report["cleaned_shape"][0],
            "original_rows": report["original_shape"][0],
            "warnings":      report.get("warnings", []),
            "derived_columns": [
                c for c in mapped_df.columns
                if c not in cleaned_df.columns or c in [
                    "revenue", "revenue_after_discount", "age_group", "revenue_tier",
                    "order_year", "order_month", "order_month_name", "order_quarter",
                    "order_week", "order_dow", "order_day", "order_is_weekend",
                ]
            ],
        },
    }


@app.get("/preview")
async def preview(session_id: str = Query(...), rows: int = Query(100, le=1000)):
    df = get_session(session_id)["df"]
    return {"columns": list(df.columns), "total_rows": len(df), "rows": df_records(df, rows)}

@app.get("/schema")
async def schema(session_id: str = Query(...)):
    df = get_session(session_id)["df"]
    return {"schema": [
        {"column": c, "dtype": str(df[c].dtype), "null_count": int(df[c].isna().sum()),
         "unique": int(df[c].nunique()), "sample": [str(x) for x in df[c].dropna().head(4).tolist()]}
        for c in df.columns
    ]}

@app.get("/mapping")
async def mapping(session_id: str = Query(...)):
    s = get_session(session_id)
    if s.get("mapping"):
        return mapping_summary(s["mapping"])
    return s["report"].get("column_mapping", {})

@app.get("/report")
async def report_endpoint(session_id: str = Query(...)):
    return get_session(session_id)["report"]


def _call(fn, *args, **kwargs):
    result = fn(*args, **kwargs)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(422, result["error"])
    return result

@app.get("/insights/kpis")
async def kpis(session_id: str = Query(...)):
    return _call(insights.get_kpis, get_session(session_id)["df"])

@app.get("/insights/revenue-trend")
async def revenue_trend(session_id: str = Query(...), group_by: str = Query("month")):
    return _call(insights.get_revenue_trend, get_session(session_id)["df"], group_by)

@app.get("/insights/top-categories")
async def top_categories(session_id: str = Query(...), top_n: int = Query(10)):
    return _call(insights.get_top_categories, get_session(session_id)["df"], top_n)

@app.get("/insights/top-products")
async def top_products(session_id: str = Query(...), top_n: int = Query(15)):
    return _call(insights.get_top_products, get_session(session_id)["df"], top_n)

@app.get("/insights/lowest-products")
async def lowest_products(session_id: str = Query(...), bottom_n: int = Query(15)):
    return _call(insights.get_lowest_products, get_session(session_id)["df"], bottom_n)

@app.get("/insights/highest-rated")
async def highest_rated(session_id: str = Query(...), min_orders: int = Query(5), top_n: int = Query(15)):
    return _call(insights.get_highest_rated, get_session(session_id)["df"], min_orders, top_n)

@app.get("/insights/lowest-rated")
async def lowest_rated(session_id: str = Query(...), min_orders: int = Query(5), bottom_n: int = Query(15)):
    return _call(insights.get_lowest_rated, get_session(session_id)["df"], min_orders, bottom_n)

@app.get("/insights/regional")
async def regional(session_id: str = Query(...)):
    return _call(insights.get_regional, get_session(session_id)["df"])

@app.get("/insights/gender-distribution")
async def gender_dist(session_id: str = Query(...)):
    return _call(insights.get_gender_distribution, get_session(session_id)["df"])

@app.get("/insights/categories-by-gender")
async def categories_by_gender(session_id: str = Query(...), top_n: int = Query(8)):
    return _call(insights.get_categories_by_gender, get_session(session_id)["df"], top_n)

@app.get("/insights/age-distribution")
async def age_dist(session_id: str = Query(...)):
    return _call(insights.get_age_distribution, get_session(session_id)["df"])

@app.get("/insights/revenue-growth")
async def revenue_growth(session_id: str = Query(...)):
    return _call(insights.get_revenue_growth, get_session(session_id)["df"])

@app.get("/insights/quarterly-revenue")
async def quarterly_revenue(session_id: str = Query(...)):
    return _call(insights.get_quarterly_revenue, get_session(session_id)["df"])

@app.get("/insights/category-growth")
async def category_growth(session_id: str = Query(...), top_n: int = Query(6)):
    return _call(insights.get_category_growth, get_session(session_id)["df"], top_n)

@app.get("/insights/region-category")
async def region_category(session_id: str = Query(...), top_n: int = Query(8)):
    return _call(insights.get_region_category, get_session(session_id)["df"], top_n)

@app.get("/insights/payment-methods")
async def payment_methods(session_id: str = Query(...)):
    return _call(insights.get_payment_methods, get_session(session_id)["df"])

@app.get("/insights/anomalies")
async def anomalies(session_id: str = Query(...)):
    return _call(insights.get_anomalies, get_session(session_id)["df"])

@app.get("/insights/revenue-tiers")
async def revenue_tiers(session_id: str = Query(...)):
    return _call(insights.get_revenue_tiers, get_session(session_id)["df"])

@app.get("/insights/summary")
async def summary(session_id: str = Query(...)):
    return insights.get_summary(get_session(session_id)["df"])


@app.get("/insights/sales-velocity")
async def sales_velocity(session_id: str = Query(...)):
    return _call(insights.get_sales_velocity, get_session(session_id)["df"])


@app.get("/insights/repeat-customers")
async def repeat_customers(session_id: str = Query(...)):
    return _call(insights.get_repeat_customers, get_session(session_id)["df"])


@app.get("/insights/sales-phases")
async def sales_phases(
    session_id:  str   = Query(...),
    z_threshold: float = Query(1.0),
):
    return _call(insights.get_sales_phases, get_session(session_id)["df"], z_threshold)


@app.get("/insights/discount-vs-baseline")
async def discount_vs_baseline(session_id: str = Query(...)):
    return _call(insights.get_discount_vs_baseline, get_session(session_id)["df"])


@app.get("/insights/product-combos")
async def product_combos(
    session_id:  str = Query(...),
    top_n:       int = Query(7),
    min_support: int = Query(2),
):
    return _call(insights.get_product_combos, get_session(session_id)["df"], top_n, min_support)


@app.get("/insights/monthly-category-distribution")
async def monthly_category_distribution(session_id: str = Query(...)):
    return _call(insights.get_monthly_category_distribution, get_session(session_id)["df"])


@app.get("/insights/post-purchase-return")
async def post_purchase_return(
    session_id: str = Query(...),
    top_n:      int = Query(5),
):
    return _call(insights.get_post_purchase_return, get_session(session_id)["df"], top_n)


@app.get("/download/cleaned")
async def dl_cleaned(session_id: str = Query(...)):
    p = Path("data/cleaned") / f"{session_id}_cleaned.csv"
    if not p.exists(): raise HTTPException(404, "Cleaned file not found.")
    return FileResponse(p, media_type="text/csv", filename=f"{session_id}_cleaned.csv")

@app.get("/download/report")
async def dl_report(session_id: str = Query(...)):
    p = Path("data/cleaned") / f"{session_id}_report.json"
    if not p.exists(): raise HTTPException(404, "Report not found.")
    return FileResponse(p, media_type="application/json", filename=f"{session_id}_report.json")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)