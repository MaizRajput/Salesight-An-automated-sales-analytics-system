from __future__ import annotations
import re
import pandas as pd
import numpy as np


def _norm_cat(s: str) -> str:
    s = re.sub(r'\s+', ' ', str(s).strip()).lower()
    return s.title()


def geo_col(df: pd.DataFrame) -> str | None:
    for c in ["city", "state", "region", "country"]:
        if c in df.columns: return c
    return None

def prod_col(df: pd.DataFrame) -> str | None:
    for c in ["product", "category", "product_name", "item_name",
              "item", "product_id", "sub_category", "sub-category"]:
        if c in df.columns: return c
    return None

def rev_col(df: pd.DataFrame) -> str | None:
    for c in ["revenue_after_discount", "revenue", "total_sales",
              "sales", "sale_amount", "net_sales", "gross_sales",
              "amount", "price", "total_amount", "total_revenue"]:
        if c in df.columns: return c
    return None

def date_col(df: pd.DataFrame) -> str | None:
    for c in ["order_date", "date", "transaction_date", "purchase_date",
              "sale_date", "invoice_date", "created_at", "ship_date"]:
        if c in df.columns: return c
    return None


def _ensure_date_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Derive order_year / order_month / order_quarter / order_week from
    whichever date column is present, if they are not already there."""
    if "order_year" in df.columns and "order_month" in df.columns:
        return df
    dc = date_col(df)
    if not dc:
        return df
    df = df.copy()
    try:
        parsed = pd.to_datetime(df[dc], errors="coerce")
        if "order_year"    not in df.columns: df["order_year"]    = parsed.dt.year
        if "order_month"   not in df.columns: df["order_month"]   = parsed.dt.month
        if "order_quarter" not in df.columns: df["order_quarter"] = parsed.dt.quarter
        if "order_week"    not in df.columns: df["order_week"]    = parsed.dt.isocalendar().week.astype(int)
        if "order_dow"     not in df.columns: df["order_dow"]     = parsed.dt.dayofweek
        if "order_day"     not in df.columns: df["order_day"]     = parsed.dt.day
    except Exception:
        pass
    return df


def _ensure_revenue_tier(df: pd.DataFrame) -> pd.DataFrame:
    """Derive revenue_tier from whatever revenue column is present,
    if cleaner has not already done so."""
    if "revenue_tier" in df.columns:
        return df
    rc = rev_col(df)
    if not rc:
        return df
    df = df.copy()
    try:
        q33 = df[rc].quantile(0.33)
        q66 = df[rc].quantile(0.66)
        df["revenue_tier"] = pd.cut(
            df[rc],
            bins=[-float("inf"), q33, q66, float("inf")],
            labels=["Low", "Medium", "High"],
        ).astype(str)
    except Exception:
        pass
    return df


def get_kpis(df: pd.DataFrame) -> dict:
    df = _ensure_date_cols(df)
    df = _ensure_revenue_tier(df)
    rc = rev_col(df); gc = geo_col(df); pc = prod_col(df)
    out = {"total_orders": len(df)}
    if rc:
        out["total_revenue"]   = round(float(df[rc].sum()), 2)
        out["avg_order_value"] = round(float(df[rc].mean()), 2)
        out["max_order_value"] = round(float(df[rc].max()), 2)
    if "profit" in df.columns and rc:
        out["total_profit"]      = round(float(df["profit"].sum()), 2)
        out["profit_margin_pct"] = round(float(df["profit"].sum() / max(df[rc].sum(), 1) * 100), 2)
    if "quantity"    in df.columns: out["total_units_sold"] = int(df["quantity"].sum())
    if "rating"      in df.columns: out["avg_rating"]       = round(float(df["rating"].mean()), 2)
    if "discount"    in df.columns: out["avg_discount"]     = round(float(df["discount"].mean()), 2)
    if "customer_id" in df.columns: out["unique_customers"] = int(df["customer_id"].nunique())
    if pc and rc: out[f"top_{pc}"] = str(df.groupby(pc)[rc].sum().idxmax())
    if gc and rc: out[f"top_{gc}"] = str(df.groupby(gc)[rc].sum().idxmax())
    return out


def get_revenue_trend(df: pd.DataFrame, group_by: str = "month") -> dict:
    df = _ensure_date_cols(df)
    rc = rev_col(df)
    if not rc:
        return {"error": "No revenue column found."}
    col_map = {
        "month":   "order_month",
        "year":    "order_year",
        "quarter": "order_quarter",
        "dow":     "order_dow",
        "week":    "order_week",
    }
    gc = col_map.get(group_by)
    if not gc or gc not in df.columns:
        available = [k for k, v in col_map.items() if v in df.columns]
        return {"error": f"'{group_by}' not available. Try: {available}"}
    trend = (df.groupby(gc)[rc]
               .agg(total_revenue="sum", avg_revenue="mean", orders="count")
               .reset_index().sort_values(gc))
    trend[["total_revenue", "avg_revenue"]] = trend[["total_revenue", "avg_revenue"]].round(2)
    return {"group_by": group_by, "data": trend.to_dict(orient="records")}


def get_top_categories(df: pd.DataFrame, top_n: int = 10) -> dict:
    rc = rev_col(df)
    if "category" not in df.columns:
        return {"error": "No category column found."}
    agg: dict = {"orders": ("category", "count")}
    if rc:                         agg["total_revenue"] = (rc,         "sum")
    if "quantity" in df.columns:   agg["total_units"]   = ("quantity", "sum")
    if "rating"   in df.columns:   agg["avg_rating"]    = ("rating",  "mean")
    if "profit"   in df.columns:   agg["total_profit"]  = ("profit",  "sum")
    result = (df.groupby("category").agg(**agg).reset_index()
                .sort_values("orders" if not rc else "total_revenue", ascending=False)
                .head(top_n))
    for c in ["total_revenue", "avg_rating", "total_profit"]:
        if c in result.columns: result[c] = result[c].round(2)
    return {"data": result.to_dict(orient="records")}


def get_top_products(df: pd.DataFrame, top_n: int = 15) -> dict:
    rc = rev_col(df); pc = prod_col(df)
    if not pc:
        return {"error": "No product or category column found."}
    agg: dict = {"orders": (pc, "count")}
    if rc:                       agg["total_revenue"] = (rc,         "sum")
    if "quantity" in df.columns: agg["total_units"]   = ("quantity", "sum")
    if "rating"   in df.columns: agg["avg_rating"]    = ("rating",  "mean")
    sort = "total_revenue" if rc else "orders"
    result = (df.groupby(pc).agg(**agg).reset_index()
                .sort_values(sort, ascending=False).head(top_n))
    for c in ["total_revenue", "avg_rating"]:
        if c in result.columns: result[c] = result[c].round(2)
    return {"product_column": pc, "data": result.to_dict(orient="records")}


def get_lowest_products(df: pd.DataFrame, bottom_n: int = 15) -> dict:
    rc = rev_col(df); pc = prod_col(df)
    if not pc:
        return {"error": "No product or category column found."}
    agg: dict = {"orders": (pc, "count")}
    if rc:                       agg["total_revenue"] = (rc,         "sum")
    if "quantity" in df.columns: agg["total_units"]   = ("quantity", "sum")
    if "rating"   in df.columns: agg["avg_rating"]    = ("rating",  "mean")
    sort = "total_revenue" if rc else "orders"
    result = (df.groupby(pc).agg(**agg).reset_index()
                .sort_values(sort, ascending=True).head(bottom_n))
    for c in ["total_revenue", "avg_rating"]:
        if c in result.columns: result[c] = result[c].round(2)
    return {"product_column": pc, "data": result.to_dict(orient="records")}


def get_highest_rated(df: pd.DataFrame, min_orders: int = 5, top_n: int = 15) -> dict:
    if "rating" not in df.columns:
        return {"error": "No rating column found."}
    pc = prod_col(df)
    if not pc:
        return {"error": "No product or category column found."}
    rc  = rev_col(df)
    agg: dict = {"avg_rating": ("rating", "mean"), "orders": (pc, "count")}
    if rc: agg["total_revenue"] = (rc, "sum")
    result = (df.groupby(pc).agg(**agg).reset_index()
                .query(f"orders >= {min_orders}")
                .sort_values("avg_rating", ascending=False).head(top_n))
    result["avg_rating"] = result["avg_rating"].round(2)
    if rc and "total_revenue" in result.columns:
        result["total_revenue"] = result["total_revenue"].round(2)
    return {"product_column": pc, "min_orders_filter": min_orders, "data": result.to_dict(orient="records")}


def get_lowest_rated(df: pd.DataFrame, min_orders: int = 5, bottom_n: int = 15) -> dict:
    if "rating" not in df.columns:
        return {"error": "No rating column found."}
    pc = prod_col(df)
    if not pc:
        return {"error": "No product or category column found."}
    rc  = rev_col(df)
    agg: dict = {"avg_rating": ("rating", "mean"), "orders": (pc, "count")}
    if rc: agg["total_revenue"] = (rc, "sum")
    result = (df.groupby(pc).agg(**agg).reset_index()
                .query(f"orders >= {min_orders}")
                .sort_values("avg_rating", ascending=True).head(bottom_n))
    result["avg_rating"] = result["avg_rating"].round(2)
    if rc and "total_revenue" in result.columns:
        result["total_revenue"] = result["total_revenue"].round(2)
    return {"product_column": pc, "min_orders_filter": min_orders, "data": result.to_dict(orient="records")}


def get_regional(df: pd.DataFrame) -> dict:
    rc = rev_col(df); gc = geo_col(df)
    if not gc:
        return {"error": "No region/city/state/country column found."}
    agg: dict = {"orders": (gc, "count")}
    if rc:                       agg["total_revenue"] = (rc,         "sum")
    if "quantity" in df.columns: agg["total_units"]   = ("quantity", "sum")
    if "rating"   in df.columns: agg["avg_rating"]    = ("rating",  "mean")
    if "profit"   in df.columns: agg["total_profit"]  = ("profit",  "sum")
    result = (df.groupby(gc).agg(**agg).reset_index()
                .sort_values("orders" if not rc else "total_revenue", ascending=False))
    for c in ["total_revenue", "avg_rating", "total_profit"]:
        if c in result.columns: result[c] = result[c].round(2)
    return {"geo_column": gc, "data": result.to_dict(orient="records")}


def get_gender_distribution(df: pd.DataFrame) -> dict:
    if "gender" not in df.columns:
        return {"error": "No gender column found."}
    rc  = rev_col(df)
    agg: dict = {"orders": ("gender", "count")}
    if rc:                       agg["total_revenue"] = (rc,         "sum")
    if "quantity" in df.columns: agg["total_units"]   = ("quantity", "sum")
    if "rating"   in df.columns: agg["avg_rating"]    = ("rating",  "mean")
    if "age"      in df.columns: agg["avg_age"]       = ("age",     "mean")
    result = df.groupby("gender").agg(**agg).reset_index()
    result["share_pct"] = (result["orders"] / result["orders"].sum() * 100).round(1)
    for c in ["total_revenue", "avg_rating", "avg_age"]:
        if c in result.columns: result[c] = result[c].round(2)
    return {"data": result.to_dict(orient="records")}


def get_categories_by_gender(df: pd.DataFrame, top_n: int = 8) -> dict:
    if "gender" not in df.columns or "category" not in df.columns:
        return {"error": "Need both gender and category columns."}
    rc = rev_col(df)
    if rc:
        result = (df.groupby(["gender", "category"])[rc].sum()
                    .reset_index().rename(columns={rc: "revenue"}))
    else:
        result = (df.groupby(["gender", "category"]).size()
                    .reset_index(name="orders"))
    # top N categories overall
    val_col = "revenue" if rc else "orders"
    top_cats = result.groupby("category")[val_col].sum().nlargest(top_n).index.tolist()
    result   = result[result["category"].isin(top_cats)]
    result[val_col] = result[val_col].round(2)
    return {"value_column": val_col, "data": result.to_dict(orient="records")}


def get_age_distribution(df: pd.DataFrame) -> dict:
    if "age" not in df.columns:
        return {"error": "No age column found."}
    rc = rev_col(df)
    band_col = "age_group" if "age_group" in df.columns else (
               "age_band"  if "age_band"  in df.columns else None)

    if band_col:
        agg: dict = {"orders": (band_col, "count")}
        if rc:                      agg["total_revenue"] = (rc,       "sum")
        if "rating" in df.columns: agg["avg_rating"]    = ("rating", "mean")
        band_result = df.groupby(band_col).agg(**agg).reset_index()
        band_result["share_pct"] = (band_result["orders"] / band_result["orders"].sum() * 100).round(1)
        for c in ["total_revenue", "avg_rating"]:
            if c in band_result.columns: band_result[c] = band_result[c].round(2)
        bands = band_result.to_dict(orient="records")
    else:
        bands = []

    stats = {
        "mean":   round(float(df["age"].mean()),   1),
        "median": float(df["age"].median()),
        "min":    int(df["age"].min()),
        "max":    int(df["age"].max()),
    }
    return {"age_stats": stats, "by_band": bands, "band_column": band_col}


def get_revenue_growth(df: pd.DataFrame) -> dict:
    df = _ensure_date_cols(df)
    rc = rev_col(df)
    if not rc:
        return {"error": "No revenue column found."}
    if "order_month" not in df.columns or "order_year" not in df.columns:
        return {"error": "Need order_year and order_month columns (derived from order_date)."}

    monthly = (df.groupby(["order_year", "order_month"])[rc]
                 .sum().reset_index().sort_values(["order_year", "order_month"]))
    monthly.rename(columns={rc: "revenue"}, inplace=True)
    monthly["revenue"]    = monthly["revenue"].round(2)
    monthly["mom_change"] = monthly["revenue"].pct_change().mul(100).round(2).fillna(0)
    monthly["label"]      = monthly["order_year"].astype(str) + "-" + monthly["order_month"].astype(str).str.zfill(2)
    return {"data": monthly.to_dict(orient="records")}


def get_quarterly_revenue(df: pd.DataFrame) -> dict:
    df = _ensure_date_cols(df)
    rc = rev_col(df)
    if not rc:
        return {"error": "No revenue column found."}
    if "order_quarter" not in df.columns:
        return {"error": "Need order_quarter column (derived from order_date)."}

    grp_cols = ["order_year", "order_quarter"] if "order_year" in df.columns else ["order_quarter"]
    quarterly = (df.groupby(grp_cols)[rc]
                   .agg(total_revenue="sum", avg_revenue="mean", orders="count")
                   .reset_index())
    quarterly[["total_revenue", "avg_revenue"]] = quarterly[["total_revenue", "avg_revenue"]].round(2)
    if "order_year" in quarterly.columns:
        quarterly["label"] = quarterly["order_year"].astype(str) + " Q" + quarterly["order_quarter"].astype(str)
    else:
        quarterly["label"] = "Q" + quarterly["order_quarter"].astype(str)
    return {"data": quarterly.to_dict(orient="records")}


def get_category_growth(df: pd.DataFrame, top_n: int = 6) -> dict:
    df = _ensure_date_cols(df)
    rc = rev_col(df)
    if not rc or "category" not in df.columns:
        return {"error": "Need both revenue and category columns."}
    if "order_month" not in df.columns or "order_year" not in df.columns:
        return {"error": "Need order_year and order_month columns."}

    # Only top N categories by total revenue to keep chart readable
    top_cats = df.groupby("category")[rc].sum().nlargest(top_n).index.tolist()
    sub      = df[df["category"].isin(top_cats)]

    monthly = (sub.groupby(["order_year", "order_month", "category"])[rc]
                  .sum().reset_index().sort_values(["order_year", "order_month"]))
    monthly.rename(columns={rc: "revenue"}, inplace=True)
    monthly["revenue"] = monthly["revenue"].round(2)
    monthly["label"]   = (monthly["order_year"].astype(str) + "-"
                          + monthly["order_month"].astype(str).str.zfill(2))

    pivot = monthly.pivot_table(index="label", columns="category", values="revenue", fill_value=0)
    pivot = pivot.reset_index()
    return {
        "categories": top_cats,
        "labels":     pivot["label"].tolist(),
        "series":     {cat: pivot[cat].tolist() for cat in top_cats if cat in pivot.columns},
    }


def get_region_category(df: pd.DataFrame, top_n: int = 8) -> dict:
    gc = geo_col(df)
    pc = "category" if "category" in df.columns else prod_col(df)
    if not gc or not pc:
        return {"error": "Need both a geo column and a category column."}
    rc = rev_col(df)
    if rc:
        pivot = df.groupby([gc, pc])[rc].sum().reset_index().rename(columns={rc: "value"})
    else:
        pivot = df.groupby([gc, pc]).size().reset_index(name="value")
    top_regions = df[gc].value_counts().head(top_n).index.tolist()
    top_cats    = df[pc].value_counts().head(top_n).index.tolist()
    filtered    = pivot[pivot[gc].isin(top_regions) & pivot[pc].isin(top_cats)]
    return {"geo_column": gc, "category_column": pc,
            "top_regions": top_regions, "top_categories": top_cats,
            "data": filtered.round(2).to_dict(orient="records")}


def get_payment_methods(df: pd.DataFrame) -> dict:
    if "payment_method" not in df.columns:
        return {"error": "No payment_method column found."}
    rc  = rev_col(df)
    agg: dict = {"orders": ("payment_method", "count")}
    if rc: agg["total_revenue"] = (rc, "sum")
    result = df.groupby("payment_method").agg(**agg).reset_index()
    result["share_pct"] = (result["orders"] / result["orders"].sum() * 100).round(1)
    if "total_revenue" in result.columns: result["total_revenue"] = result["total_revenue"].round(2)
    return {"data": result.to_dict(orient="records")}


def get_anomalies(df: pd.DataFrame) -> dict:
    import json
    check_cols = [c for c in ["revenue", "revenue_after_discount", "total_sales",
                               "quantity", "unit_price", "profit"] if c in df.columns]
    if not check_cols:
        return {"error": "No numeric columns to check for anomalies."}
    mask = pd.Series(False, index=df.index)
    for col in check_cols:
        std = df[col].std()
        if std > 0:
            z = (df[col] - df[col].mean()) / std
            mask |= z.abs() > 3
    rows = json.loads(
        df[mask].head(200).fillna("").to_json(orient="records", date_format="iso", default_handler=str)
    )
    return {"total_anomalies": int(mask.sum()), "checked": check_cols, "rows": rows}


def get_revenue_tiers(df: pd.DataFrame) -> dict:
    df = _ensure_revenue_tier(df)
    if "revenue_tier" not in df.columns:
        return {"error": "No revenue_tier column — make sure cleaner ran successfully."}
    rc = rev_col(df)
    agg: dict = {"orders": ("revenue_tier", "count")}
    if rc: agg["total_revenue"] = (rc, "sum")
    result = df.groupby("revenue_tier").agg(**agg).reset_index()
    result["share_pct"] = (result["orders"] / result["orders"].sum() * 100).round(1)
    if "total_revenue" in result.columns: result["total_revenue"] = result["total_revenue"].round(2)
    return {"data": result.to_dict(orient="records")}


def get_summary(df: pd.DataFrame) -> dict:
    df = _ensure_date_cols(df)
    df = _ensure_revenue_tier(df)
    if "category" in df.columns:
        df = df.copy()
        df["category"] = df["category"].map(_norm_cat)

    rc = rev_col(df); gc = geo_col(df); pc = prod_col(df)
    out: dict = {"total_orders": len(df)}

    if rc:
        out["total_revenue"]   = round(float(df[rc].sum()), 2)
        out["avg_order_value"] = round(float(df[rc].mean()), 2)
    if "rating"   in df.columns: out["avg_rating"]       = round(float(df["rating"].mean()), 2)
    if "quantity" in df.columns: out["total_units_sold"]  = int(df["quantity"].sum())
    if "profit"   in df.columns: out["total_profit"]      = round(float(df["profit"].sum()), 2)

    if "category" in df.columns and rc:
        out["top_categories"] = (
            df.groupby("category")[rc].sum().sort_values(ascending=False)
              .head(10).round(2).reset_index().rename(columns={rc: "revenue"})
              .to_dict(orient="records"))
    if gc and rc:
        out["regional"] = (
            df.groupby(gc)[rc].sum().sort_values(ascending=False)
              .round(2).reset_index().rename(columns={rc: "revenue"})
              .to_dict(orient="records"))
    if "gender" in df.columns:
        vc = df["gender"].value_counts().reset_index()
        vc.columns = ["gender", "count"]
        out["gender"] = vc.to_dict(orient="records")

    age_band_col = ("age_group" if "age_group" in df.columns
                    else "age_band" if "age_band" in df.columns else None)
    if age_band_col:
        vc = df[age_band_col].value_counts().reset_index()
        vc.columns = ["age_group", "count"]
        out["age_bands"] = vc.to_dict(orient="records")

    if "revenue_tier" in df.columns:
        vc = df["revenue_tier"].value_counts().reset_index()
        vc.columns = ["revenue_tier", "count"]
        out["revenue_tiers"] = vc.to_dict(orient="records")

    # monthly trend for growth chart
    if rc and "order_month" in df.columns and "order_year" in df.columns:
        monthly = (df.groupby(["order_year", "order_month"])[rc]
                     .sum().reset_index().sort_values(["order_year", "order_month"]))
        monthly.rename(columns={rc: "revenue"}, inplace=True)
        monthly["revenue"]    = monthly["revenue"].round(2)
        monthly["mom_change"] = monthly["revenue"].pct_change().mul(100).round(2).fillna(0)
        monthly["label"]      = (monthly["order_year"].astype(str) + "-"
                                 + monthly["order_month"].astype(str).str.zfill(2))
        out["monthly_trend"] = monthly.to_dict(orient="records")

    # quarterly
    if rc and "order_quarter" in df.columns:
        grp = ["order_year", "order_quarter"] if "order_year" in df.columns else ["order_quarter"]
        q = df.groupby(grp)[rc].sum().reset_index()
        q.rename(columns={rc: "revenue"}, inplace=True)
        q["revenue"] = q["revenue"].round(2)
        if "order_year" in q.columns:
            q["label"] = q["order_year"].astype(str) + " Q" + q["order_quarter"].astype(str)
        else:
            q["label"] = "Q" + q["order_quarter"].astype(str)
        out["quarterly_trend"] = q.to_dict(orient="records")

    # category growth series
    if rc and "category" in df.columns and "order_month" in df.columns and "order_year" in df.columns:
        out["category_growth"] = get_category_growth(df, top_n=6)

    if "gender" in df.columns and "category" in df.columns:
        out["categories_by_gender"] = get_categories_by_gender(df)

    if prod_col(df):
        out["top_products"]    = get_top_products(df, top_n=10)
        out["lowest_products"] = get_lowest_products(df, bottom_n=10)

    if "rating" in df.columns and prod_col(df):
        out["highest_rated"] = get_highest_rated(df, top_n=10)
        out["lowest_rated"]  = get_lowest_rated(df, bottom_n=10)


    out["sales_velocity"] = get_sales_velocity(df)

    if "customer_id" in df.columns:
        out["repeat_customers"] = get_repeat_customers(df)

    # Which months were unusually strong (peaks) or weak (slumps) by z-score
    out["sales_phases"] = get_sales_phases(df)

    if "discount" in df.columns and "category" in df.columns:
        out["discount_vs_baseline"] = get_discount_vs_baseline(df)

    out["product_combos"] = get_product_combos(df)

    if "category" in df.columns:
        out["monthly_category_distribution"] = get_monthly_category_distribution(df)

    if "customer_id" in df.columns:
        out["post_purchase_return"] = get_post_purchase_return(df)

    return out


def get_sales_velocity(df: pd.DataFrame) -> dict:
    """
    Returns monthly sales velocity (revenue per period) broken down by:
      - category (all categories)
      - product (only products that appeared in >= 2 distinct months = 'repeat sellers')
    Suitable for an XY line chart showing rises/drops over time.
    """
    df = _ensure_date_cols(df)
    rc = rev_col(df)
    if not rc:
        return {"error": "No revenue column found."}
    if "order_year" not in df.columns or "order_month" not in df.columns:
        return {"error": "Need order_year and order_month columns derived from order_date."}

    def _label(row):
        return f"{int(row['order_year'])}-{str(int(row['order_month'])).zfill(2)}"

    category_series: dict = {}
    if "category" in df.columns:
        cat_monthly = (df.groupby(["order_year", "order_month", "category"])[rc]
                         .sum().reset_index()
                         .sort_values(["order_year", "order_month"]))
        cat_monthly["label"] = cat_monthly.apply(_label, axis=1)
        for cat, grp in cat_monthly.groupby("category"):
            grp = grp.sort_values(["order_year", "order_month"])
            prev = grp[rc].shift(1)
            grp = grp.copy()
            grp["mom_change_pct"] = ((grp[rc] - prev) / prev.replace(0, np.nan) * 100).round(2).fillna(0)
            category_series[str(cat)] = grp[["label", rc, "mom_change_pct"]].rename(
                columns={rc: "revenue"}).to_dict(orient="records")

    product_series: dict = {}
    pc = "product" if "product" in df.columns else None
    if pc:
        prod_month_counts = (df.groupby([pc, "order_year", "order_month"])
                               .size().reset_index(name="_cnt")
                               .groupby(pc)[["order_year", "order_month"]]
                               .apply(lambda x: len(x)).reset_index(name="month_count"))
        repeat_products = prod_month_counts[prod_month_counts["month_count"] >= 2][pc].tolist()

        if repeat_products:
            sub = df[df[pc].isin(repeat_products)]
            prod_monthly = (sub.groupby(["order_year", "order_month", pc])[rc]
                               .sum().reset_index()
                               .sort_values(["order_year", "order_month"]))
            prod_monthly["label"] = prod_monthly.apply(_label, axis=1)
            for prod, grp in prod_monthly.groupby(pc):
                grp = grp.sort_values(["order_year", "order_month"])
                prev = grp[rc].shift(1)
                grp = grp.copy()
                grp["mom_change_pct"] = ((grp[rc] - prev) / prev.replace(0, np.nan) * 100).round(2).fillna(0)
                product_series[str(prod)] = grp[["label", rc, "mom_change_pct"]].rename(
                    columns={rc: "revenue"}).to_dict(orient="records")

    overall = (df.groupby(["order_year", "order_month"])[rc]
                 .sum().reset_index().sort_values(["order_year", "order_month"]))
    overall["label"] = overall.apply(_label, axis=1)
    all_labels = overall["label"].tolist()

    return {
        "all_labels":      all_labels,
        "category_series": category_series,
        "product_series":  product_series,
        "revenue_col":     rc,
        "repeat_product_count": len(product_series),
    }


def get_repeat_customers(df: pd.DataFrame) -> dict:
    """
    Returns:
      - repeat_customer_pct  : % of customers who ordered more than once
      - top_repeat_products  : products with most repeat orders, with order frequency
      - order_frequency_dist : distribution of how many orders customers place
    Requires customer_id column.
    """
    if "customer_id" not in df.columns:
        return {"error": "No customer_id column found."}

    rc = rev_col(df)
    cust_orders = df.groupby("customer_id").size().reset_index(name="order_count")
    total_customers  = len(cust_orders)
    repeat_customers = int((cust_orders["order_count"] > 1).sum())
    repeat_pct       = round(repeat_customers / max(total_customers, 1) * 100, 2)

    _vc = cust_orders["order_count"].value_counts().reset_index()
    if "count" in _vc.columns:  # pandas >= 2.0
        _vc = _vc.rename(columns={"order_count": "orders_placed", "count": "customer_count"})
    else:
        _vc = _vc.rename(columns={"index": "orders_placed", "order_count": "customer_count"})
    freq_dist = _vc.sort_values("orders_placed")

    top_repeat_products: list = []
    pc = "product" if "product" in df.columns else ("category" if "category" in df.columns else None)
    if pc:
        # Only customers who bought more than once
        repeat_ids = cust_orders[cust_orders["order_count"] > 1]["customer_id"].tolist()
        sub = df[df["customer_id"].isin(repeat_ids)]
        agg: dict = {"repeat_orders": (pc, "count")}
        if rc: agg["total_revenue"] = (rc, "sum")
        prod_repeat = (sub.groupby(pc).agg(**agg).reset_index()
                          .sort_values("repeat_orders", ascending=False).head(15))
        cust_prod_freq = (sub.groupby(["customer_id", pc]).size()
                             .reset_index(name="freq")
                             .groupby(pc)["freq"].mean().round(2)
                             .reset_index(name="avg_orders_per_customer"))
        prod_repeat = prod_repeat.merge(cust_prod_freq, on=pc, how="left")
        if rc and "total_revenue" in prod_repeat.columns:
            prod_repeat["total_revenue"] = prod_repeat["total_revenue"].round(2)
        top_repeat_products = prod_repeat.to_dict(orient="records")

    return {
        "total_customers":         total_customers,
        "repeat_customers":        repeat_customers,
        "repeat_customer_pct":     repeat_pct,
        "order_frequency_distribution": freq_dist.to_dict(orient="records"),
        "top_repeat_products":     top_repeat_products,
        "product_column":          pc,
    }


def get_sales_phases(df: pd.DataFrame, z_threshold: float = 1.0) -> dict:
    """
    Identifies time phases where sales were significantly high (peaks) or
    significantly low (slumps) using z-score against monthly average.
    Returns:
      - monthly_data    : full monthly series with z-scores
      - peaks           : months where z > +z_threshold
      - slumps          : months where z < -z_threshold
      - peak_month      : single best month
      - slump_month     : single worst month
    """
    df = _ensure_date_cols(df)
    rc = rev_col(df)
    if not rc:
        return {"error": "No revenue column found."}
    if "order_year" not in df.columns or "order_month" not in df.columns:
        return {"error": "Need order_year and order_month columns derived from order_date."}

    monthly = (df.groupby(["order_year", "order_month"])[rc]
                 .agg(revenue="sum", orders="count")
                 .reset_index().sort_values(["order_year", "order_month"]))
    monthly["label"] = (monthly["order_year"].astype(str) + "-"
                        + monthly["order_month"].astype(str).str.zfill(2))
    monthly["revenue"] = monthly["revenue"].round(2)

    mean_rev = monthly["revenue"].mean()
    std_rev  = monthly["revenue"].std()
    monthly["z_score"]      = ((monthly["revenue"] - mean_rev) / max(std_rev, 1e-9)).round(3)
    monthly["mom_change"]   = monthly["revenue"].pct_change().mul(100).round(2).fillna(0)
    monthly["phase"]        = np.where(monthly["z_score"] > z_threshold,  "peak",
                              np.where(monthly["z_score"] < -z_threshold, "slump", "normal"))

    peaks  = monthly[monthly["phase"] == "peak" ][["label", "revenue", "z_score", "orders"]].to_dict(orient="records")
    slumps = monthly[monthly["phase"] == "slump"][["label", "revenue", "z_score", "orders"]].to_dict(orient="records")

    peak_row  = monthly.loc[monthly["revenue"].idxmax()]
    slump_row = monthly.loc[monthly["revenue"].idxmin()]

    return {
        "monthly_data": monthly[["label", "revenue", "orders", "z_score", "mom_change", "phase"]].to_dict(orient="records"),
        "peaks":        peaks,
        "slumps":       slumps,
        "peak_month":   {"label": peak_row["label"],  "revenue": round(float(peak_row["revenue"]),  2)},
        "slump_month":  {"label": slump_row["label"], "revenue": round(float(slump_row["revenue"]), 2)},
        "mean_monthly_revenue": round(float(mean_rev), 2),
        "z_threshold_used":     z_threshold,
    }


def get_discount_vs_baseline(df: pd.DataFrame) -> dict:
    """
    Compares category sales performance WITH discount applied vs WITHOUT (baseline).
    Returns per-category:
      - baseline_revenue   : avg revenue per order when no discount
      - discounted_revenue : avg revenue per order when discount > 0
      - baseline_orders    : count of non-discounted orders
      - discounted_orders  : count of discounted orders
      - revenue_lift_pct   : % change (discounted vs baseline avg order value)
    Also returns overall monthly series split by discounted / non-discounted.
    """
    df = _ensure_date_cols(df)
    rc = rev_col(df)
    if not rc:
        return {"error": "No revenue column found."}
    if "discount" not in df.columns:
        return {"error": "No discount column found."}
    if "category" not in df.columns:
        return {"error": "No category column found."}

    df = df.copy()
    df["_is_discounted"] = df["discount"] > 0

    rows = []
    for cat, grp in df.groupby("category"):
        base = grp[~grp["_is_discounted"]]
        disc = grp[grp["_is_discounted"]]
        base_rev  = round(float(base[rc].mean()),  2) if len(base) else None
        disc_rev  = round(float(disc[rc].mean()),  2) if len(disc) else None
        lift = None
        if base_rev and disc_rev and base_rev != 0:
            lift = round((disc_rev - base_rev) / base_rev * 100, 2)
        base_total = round(float(base[rc].sum()), 2) if len(base) else 0
        disc_total = round(float(disc[rc].sum()), 2) if len(disc) else 0
        rows.append({
            "category":            str(cat),
            "baseline_avg_order":  base_rev,
            "discounted_avg_order": disc_rev,
            "baseline_total_rev":  base_total,
            "discounted_total_rev": disc_total,
            "baseline_orders":     len(base),
            "discounted_orders":   len(disc),
            "revenue_lift_pct":    lift,
        })
    rows.sort(key=lambda x: (x["discounted_total_rev"] or 0), reverse=True)

    monthly_series: list = []
    if "order_year" in df.columns and "order_month" in df.columns:
        for flag, label in [(False, "baseline"), (True, "discounted")]:
            sub = df[df["_is_discounted"] == flag]
            if sub.empty:
                continue
            monthly = (sub.groupby(["order_year", "order_month"])[rc]
                          .agg(revenue="sum", orders="count")
                          .reset_index().sort_values(["order_year", "order_month"]))
            monthly["label"] = (monthly["order_year"].astype(str) + "-"
                                 + monthly["order_month"].astype(str).str.zfill(2))
            monthly["type"] = label
            monthly["revenue"] = monthly["revenue"].round(2)
            monthly_series.append(monthly[["label", "revenue", "orders", "type"]].to_dict(orient="records"))

    return {
        "category_comparison": rows,
        "monthly_series":      monthly_series,  # list of two lists: [baseline_records, discounted_records]
    }


def get_product_combos(df: pd.DataFrame, top_n: int = 7, min_support: int = 2) -> dict:
    """
    Finds the top N product pairs bought together in the same order.
    Requires order_id + a product column.
    Returns pairs with co-occurrence count and support %.
    """
    from itertools import combinations

    oid = next((c for c in ["order_id", "transaction_id", "invoice_id"] if c in df.columns), None)
    pc  = "product" if "product" in df.columns else ("category" if "category" in df.columns else None)
    if not oid:
        return {"error": "No order_id / transaction_id column found for basket analysis."}
    if not pc:
        return {"error": "No product or category column found."}

    basket = df.groupby(oid)[pc].apply(lambda x: sorted(set(x.astype(str)))).reset_index()
    basket.columns = [oid, "items"]
    # Only orders with 2+ distinct items
    basket = basket[basket["items"].apply(len) >= 2]
    if basket.empty:
        return {"error": "No orders with 2+ distinct products found — cannot compute combos."}

    pair_counts: dict = {}
    for items in basket["items"]:
        for pair in combinations(items, 2):
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    total_orders = len(basket)
    combo_rows = [
        {
            "product_a":    p[0],
            "product_b":    p[1],
            "co_orders":    cnt,
            "support_pct":  round(cnt / total_orders * 100, 2),
        }
        for p, cnt in pair_counts.items() if cnt >= min_support
    ]
    combo_rows.sort(key=lambda x: x["co_orders"], reverse=True)

    return {
        "total_orders_with_2plus_items": total_orders,
        "combos": combo_rows[:top_n],
        "product_column": pc,
        "order_id_column": oid,
    }


def get_monthly_category_distribution(df: pd.DataFrame) -> dict:
    """
    Returns the revenue (or order count) share of each category, per month.
    Suitable for a stacked bar or area chart.
    Returns:
      - labels          : sorted list of month labels (YYYY-MM)
      - categories      : list of all categories
      - series          : { category: [share_pct per month] }
      - absolute_series : { category: [revenue per month] }
    """
    df = _ensure_date_cols(df)
    if "category" not in df.columns:
        return {"error": "No category column found."}
    if "order_year" not in df.columns or "order_month" not in df.columns:
        return {"error": "Need order_year and order_month columns derived from order_date."}

    rc = rev_col(df)
    if rc:
        monthly = (df.groupby(["order_year", "order_month", "category"])[rc]
                     .sum().reset_index().rename(columns={rc: "value"}))
    else:
        monthly = (df.groupby(["order_year", "order_month", "category"])
                     .size().reset_index(name="value"))

    monthly["label"] = (monthly["order_year"].astype(str) + "-"
                        + monthly["order_month"].astype(str).str.zfill(2))
    monthly = monthly.sort_values(["order_year", "order_month"])

    # Month totals for share calculation
    month_totals = monthly.groupby("label")["value"].sum().to_dict()
    monthly["share_pct"] = monthly.apply(
        lambda r: round(r["value"] / max(month_totals.get(r["label"], 1), 1e-9) * 100, 2), axis=1)

    labels     = sorted(monthly["label"].unique().tolist())
    categories = sorted(monthly["category"].unique().tolist())

    pivot_abs   = monthly.pivot_table(index="label", columns="category", values="value",    fill_value=0)
    pivot_share = monthly.pivot_table(index="label", columns="category", values="share_pct", fill_value=0)

    absolute_series = {}
    share_series    = {}
    for cat in categories:
        if cat in pivot_abs.columns:
            absolute_series[str(cat)] = [round(float(v), 2) for v in pivot_abs.reindex(labels, fill_value=0)[cat].tolist()]
            share_series[str(cat)]    = [round(float(v), 2) for v in pivot_share.reindex(labels, fill_value=0)[cat].tolist()]

    return {
        "labels":           labels,
        "categories":       categories,
        "share_series":     share_series,         "absolute_series":  absolute_series,  # raw revenue/orders per category
        "value_type":       "revenue" if rc else "orders",
    }


def get_post_purchase_return(df: pd.DataFrame, top_n: int = 5) -> dict:
    """
    Determines:
      - Top N products that BROUGHT CUSTOMERS BACK (customer made another purchase after buying this)
      - Products sold only ONCE per customer and NEVER returned, filtered to those with avg rating < 3
        (potential churn-inducing products)
    Requires customer_id + order_date + a product column.
    """
    if "customer_id" not in df.columns:
        return {"error": "No customer_id column found."}

    dc = date_col(df)
    if not dc:
        return {"error": "No date column found (order_date / date / transaction_date)."}

    pc = "product" if "product" in df.columns else ("category" if "category" in df.columns else None)
    if not pc:
        return {"error": "No product or category column found."}

    df = df.copy()
    df[dc] = pd.to_datetime(df[dc], errors="coerce")
    df = df.dropna(subset=[dc])
    df = df.sort_values(["customer_id", dc])

    # For each customer, flag their orders chronologically
    df["_order_rank"] = df.groupby("customer_id")[dc].rank(method="first").astype(int)
    cust_max_orders   = df.groupby("customer_id")["_order_rank"].max().to_dict()

    rc = rev_col(df)
    come_back_rows = []
    no_return_rows = []

    for prod, grp in df.groupby(pc):
        cust_ids = grp["customer_id"].unique()
        returned  = 0
        not_returned = 0
        for cid in cust_ids:
            max_rank = cust_max_orders.get(cid, 1)
            first_prod_rank = grp[grp["customer_id"] == cid]["_order_rank"].min()
            if max_rank > first_prod_rank:
                returned += 1
            else:
                not_returned += 1
        total = returned + not_returned
        return_rate = round(returned / max(total, 1) * 100, 2)
        avg_rating  = round(float(grp["rating"].mean()), 2) if "rating" in df.columns else None
        row = {
            pc:              str(prod),
            "unique_customers": total,
            "customers_returned": returned,
            "customers_not_returned": not_returned,
            "return_rate_pct": return_rate,
            "avg_rating":    avg_rating,
        }
        if rc:
            row["total_revenue"] = round(float(grp[rc].sum()), 2)
        come_back_rows.append(row)
        # Candidate for churn list: purchased once per customer on average, low rating
        avg_orders_per_cust = round(len(grp) / max(total, 1), 2)
        if avg_orders_per_cust <= 1.1 and (avg_rating is None or avg_rating < 3):
            no_return_rows.append({**row, "avg_orders_per_customer": avg_orders_per_cust})

    come_back_rows.sort(key=lambda x: x["return_rate_pct"], reverse=True)
    no_return_rows.sort(key=lambda x: (x.get("return_rate_pct", 100)))

    return {
        "top_return_drivers":    come_back_rows[:top_n],          # products that brought customers back
        "churn_risk_products":   no_return_rows[:top_n],          # bought once, low rating, rarely returned
        "product_column":        pc,
        "all_products_analyzed": len(come_back_rows),
    }