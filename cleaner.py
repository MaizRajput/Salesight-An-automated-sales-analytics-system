import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename="logs/cleaning.log",
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
_log = logging.getLogger(__name__)


def log(msg: str, level: str = "info") -> None:
    getattr(_log, level)(msg)
    prefix = {"info": "  ·", "warning": "  ⚠", "error": "  ✖"}.get(level, "  ")
    print(f"{prefix} {msg}")


# ── Column alias dictionary ───────────────────────────────────────────────────
COLUMN_ALIASES: dict[str, list[str]] = {
    "order_date": [
        "order_date", "date", "purchase_date", "transaction_date", "sale_date",
        "orderdate", "created_at", "timestamp", "order date", "purchase date",
        "transaction date", "sale date", "invoice_date", "invoice date",
    ],
    "quantity": [
        "quantity", "qty", "units", "count", "num_units", "order_qty",
        "quantity_ordered", "units_sold", "quantity sold", "no_of_units",
        "no of units", "items_sold",
    ],
    "unit_price": [
        "unit_price", "price", "unit price", "price_per_unit", "selling_price",
        "item_price", "rate", "unitprice", "unit cost", "mrp", "cost_price",
    ],
    "revenue": [
        "revenue", "total", "total_price", "total_amount", "sales", "sale_amount",
        "total_revenue", "net_revenue", "order_total", "gross_sales", "total sales",
        "amount", "sales_amount", "invoice_total", "line_total",
    ],
    "product": [
        "product", "product_name", "item", "item_name", "product_id",
        "productname", "item name", "product name", "goods",
    ],
    "category": [
        "category", "cat", "product_category", "type", "product_type",
        "department", "segment", "subcategory", "sub_category",
        "product category", "item category", "genre",
    ],
    "region": [
        "region", "state", "province", "territory", "area",
        "sales_region", "geo", "location", "sales region", "zone",
    ],
    "country":  ["country", "nation", "country_name", "country name"],
    "city":     ["city", "town", "municipality", "district"],
    "gender": [
        "gender", "sex", "customer_gender", "user_gender",
        "customer gender", "user gender",
    ],
    "age": [
        "age", "customer_age", "user_age", "buyer_age",
        "customer age", "age_years",
    ],
    "customer_id": [
        "customer_id", "cust_id", "client_id", "user_id", "customerid",
        "customer id", "client id", "buyer_id",
    ],
    "customer_name": [
        "customer_name", "name", "client_name", "buyer_name",
        "full_name", "customer name", "buyer",
    ],
    "rating": [
        "rating", "review_score", "score", "stars", "customer_rating",
        "feedback_score", "review rating", "product_rating",
        "review_rating", "ratings",
    ],
    "discount": [
        "discount", "discount_pct", "discount_rate", "disc",
        "promo", "promotion", "coupon", "discount percent", "discount_%",
    ],
    "payment_method": [
        "payment_method", "payment", "pay_method", "payment_type",
        "method_of_payment", "payment method", "mode_of_payment",
        "payment_mode", "pay_mode", "paymentmode",
    ],
    "order_id": [
        "order_id", "transaction_id", "invoice_id", "order_no",
        "orderid", "order id", "txn_id", "invoice no", "invoice_no",
    ],
    "order_status": [
        "order_status", "status", "order_state", "fulfillment_status",
        "delivery_status", "shipment_status",
    ],
    "profit": [
        "profit", "margin", "net_profit", "earnings", "net",
    ],
    "ship_date": [
        "ship_date", "shipping_date", "delivery_date", "dispatch_date",
        "shipped_date", "delivered_date",
    ],
    "product_id": [
        "product_id", "prod_id", "productid", "prodid",
        "item_id", "itemid", "item_code", "itemcode",
        "sku", "sku_id", "skuid", "sku_code",
        "article_id", "articleid", "article_no", "article_code",
        "pid", "prod_code", "product_code",
        "upc", "barcode", "bar_code", "stock_code",
        "catalog_id", "listing_id", "variant_id", "ref_id",
        "product_ref", "part_no", "part_number",
    ],
    "branch": [
        "branch", "branch_name", "branch_id", "branch_no", "branch_code",
        "store", "store_name", "store_id", "store_no", "store_code",
        "outlet", "outlet_name", "outlet_id", "outlet_code",
        "shop", "shop_name", "shop_id",
        "location", "loc", "location_id", "location_name",
        "site", "site_id", "site_name", "site_code",
        "unit", "unit_id", "unit_name",
        "franchise", "franchise_id", "franchise_name",
        "warehouse", "wh", "wh_id",
        "pos", "pos_id", "point_of_sale",
        "center", "centre", "hub", "kiosk",
    ],
    "cashier_id": [
        "cashier_id", "cashierid", "cashier",
        "teller_id", "tellerid", "teller",
        "staff_id", "staffid", "staff_no", "staff_code",
        "employee_id", "employeeid", "emp_id", "empid",
        "employee_no", "emp_no", "employee_code",
        "operator_id", "operatorid", "operator",
        "associate_id", "associateid", "associate",
        "agent_id", "agentid",
        "rep_id", "repid", "sales_rep",
        "attendant_id", "attendant",
        "seller_id", "sellerid",
        "clerk_id", "clerkid", "clerk",
        "served_by", "handled_by", "assigned_to",
    ],
    "loyalty_member": [
        "loyalty_member", "loyalty", "loyal",
        "is_member", "ismember", "member_flag", "membership",
        "loyalty_flag", "loyalty_status", "loyalty_program",
        "member", "member_status", "member_type", "membership_status",
        "membership_type", "membership_level",
        "vip", "vip_flag", "is_vip",
        "premium", "premium_member", "premium_flag",
        "club_member", "club_membership",
        "rewards_member", "rewards_program",
        "loyalty_card", "card_holder", "cardholder",
        "subscriber", "subscription", "subscribed",
        "enrolled", "enrolment", "enrollment",
        "points_member", "frequent_buyer", "frequent_customer",
        "registered", "registered_user", "registered_customer",
    ],
    "return_flag": [
        "return_flag", "returnflag", "is_return", "isreturn",
        "returned", "return", "return_status", "return_indicator",
        "is_returned", "return_ind",
        "refund", "refunded", "is_refund", "isrefund",
        "refund_flag", "refund_status", "refund_indicator",
        "reversed", "reversal", "is_reversed",
        "exchange", "exchanged", "is_exchange",
        "cancelled_item", "cancel_flag",
        "chargeback", "dispute",
        "voided", "void_flag",
    ],
}


def _normalise(name: str) -> str:
    return re.sub(r"[^\w]", "_", name.strip().lower())


def detect_column_mapping(df: pd.DataFrame) -> dict[str, str]:
    normed = {col: _normalise(col) for col in df.columns}
    mapping: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        alias_set = {a.lower().replace(" ", "_") for a in aliases}
        for col, norm in normed.items():
            if norm in alias_set:
                mapping[canonical] = col
                break
    return mapping


@dataclass
class CleanerConfig:
    numeric_fill:         str   = "median"
    string_fill:          str   = "Unknown"
    iqr_multiplier:       float = 1.5
    max_rows_drop_pct:    float = 15.0      # NEVER drop more than this % of rows total
    # Quantity range (from your CLEANORDERS.PY)
    quantity_min:         int   = 1
    quantity_max:         int   = 49
    # Rating range (from your CLEANORDERS.PY)
    rating_min:           float = 0.0      # 0 allowed for cancelled orders
    rating_max:           float = 5.0
    # Age range (from your CLEANORDERS.PY)
    age_min:              int   = 5
    age_max:              int   = 100
    # Discount range
    discount_min:         float = 0.0
    discount_max:         float = 100.0
    # Gender valid values (from your CLEANORDERS.PY)
    valid_genders:        list  = field(default_factory=lambda: ["M", "F", "OTHER"])
    unknown_gender:       str   = "Unmentioned"   # your exact label
    output_dir:           str   = "data/cleaned"


class DataCleaner:
    """
    Merged cleaning pipeline:
      Steps 1-4  : load, normalise columns, detect aliases, remove duplicates
      Step  5    : drop 'index' column if present  (your code)
      Steps 6-7  : fix infinite, fix types (dates → datetime, age → int)
      Step  8    : fill missing  (age→median, city→"Not Disclosed",
                                  discount→0, rating→mean)
      Step  9    : quantity filter 1-49  (your code, guarded by 15% rule)
      Step  10   : gender normalisation  (your code: Unmentioned for weird)
      Step  11   : order_status rules  (cancelled → rating=0, your code)
      Step  12   : rating cap at 5  (your code)
      Step  13   : IQR outlier capping
      Step  14   : domain bounds  (age, discount — guarded)
      Step  15   : derive columns (revenue, date parts, age_group, revenue_tier)
    """

    def __init__(
        self,
        source: "str | Path | pd.DataFrame",
        config: Optional[CleanerConfig] = None,
    ):
        self.config      = config or CleanerConfig()
        self._warnings:  list[str] = []
        self._metrics:   dict      = {}

        if isinstance(source, pd.DataFrame):
            self.df          = source.copy()
            self.source_name = "dataframe"
        else:
            self.source_name = Path(source).name
            self.df          = self._load(Path(source))

        self.original_shape = self.df.shape
        self._original_len  = len(self.df)   # used by 15% guard
        self.col_map: dict[str, str] = {}


    def _rows_remaining_pct(self) -> float:
        """How many % of original rows do we still have."""
        return len(self.df) / max(self._original_len, 1) * 100

    def _can_drop(self, n_to_drop: int) -> bool:
        """
        Return True only if dropping n_to_drop more rows keeps us
        above the 85% retention floor (i.e., loses at most 15%).
        """
        rows_after = len(self.df) - n_to_drop
        pct_after  = rows_after / max(self._original_len, 1) * 100
        return pct_after >= (100.0 - self.config.max_rows_drop_pct)

    def _load(self, path: Path) -> pd.DataFrame:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                sample = path.read_bytes()[:4096].decode(enc, errors="replace")
                delim  = "\t" if sample.count("\t") > sample.count(",") else ","
                df = pd.read_csv(path, encoding=enc, sep=delim)
                log(f"Loaded '{path.name}'  enc={enc}  shape={df.shape}")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        raise ValueError(f"Could not load '{path}'.")

    def _normalise_columns(self) -> None:
        before = list(self.df.columns)
        self.df.columns = pd.Index([
            re.sub(r"[^\w]+", "_", c.strip().lower()).strip("_")
            for c in self.df.columns
        ])
        renamed = {b: a for b, a in zip(before, self.df.columns) if b != a}
        if renamed:
            log(f"Columns normalised: {renamed}")
        self._metrics["columns_normalised"] = len(renamed)

    def _detect_and_alias(self) -> None:
        raw_map = detect_column_mapping(self.df)
        rename  = {actual: canon
                   for canon, actual in raw_map.items()
                   if actual != canon and canon not in self.df.columns}
        if rename:
            self.df.rename(columns=rename, inplace=True)
            log(f"Canonical rename: {rename}")
        self.col_map = {canon: canon for canon in COLUMN_ALIASES if canon in self.df.columns}
        self._metrics["detected_columns"] = list(self.col_map.keys())
        log(f"Detected columns → {list(self.col_map.keys())}")

    def _remove_duplicates(self) -> None:
        before = len(self.df)
        self.df.drop_duplicates(inplace=True)
        removed = before - len(self.df)
        log(f"Duplicates removed: {removed}")
        self._metrics["duplicates_removed"] = removed

    def _drop_index_column(self) -> None:
        for col in ["index", "unnamed:_0", "unnamed: 0", "unnamed_0"]:
            if col in self.df.columns:
                self.df.drop(columns=[col], inplace=True)
                log(f"Dropped artefact column '{col}'")

    def _fix_infinite(self) -> None:
        num_cols = self.df.select_dtypes(include=np.number).columns
        n = int(np.isinf(self.df[num_cols].to_numpy()).sum())
        if n:
            self.df[num_cols] = self.df[num_cols].replace([np.inf, -np.inf], np.nan)
            log(f"Infinite values replaced: {n}")
        self._metrics["infinite_replaced"] = n

    def _fix_types(self) -> None:
        for date_col in ["order_date", "ship_date", "date",
                         "purchase_date", "transaction_date"]:
            if date_col in self.df.columns:
                self.df[date_col] = pd.to_datetime(
                    self.df[date_col], errors="coerce", dayfirst=True
                )
                bad = int(self.df[date_col].isna().sum())
                if bad:
                    msg = f"'{date_col}': {bad} unparseable dates → NaT"
                    self._warnings.append(msg)
                    log(msg, "warning")
                else:
                    log(f"'{date_col}' parsed OK as datetime  dtype={self.df[date_col].dtype}")

        if "age" in self.df.columns:
            self.df["age"] = pd.to_numeric(self.df["age"], errors="coerce")
            med    = self.df["age"].median()
            filled = int(self.df["age"].isna().sum())
            self.df["age"] = self.df["age"].fillna(med).round().astype(int)
            log(f"'age' → int  (filled {filled} NaN with median {med:.0f})")

        for col in self.df.select_dtypes(include="object").columns:
            cleaned   = self.df[col].astype(str).str.replace(r"[$,\s]", "", regex=True)
            converted = pd.to_numeric(cleaned, errors="coerce")
            if converted.notna().mean() > 0.90:
                self.df[col] = converted
                log(f"'{col}' auto-converted string → numeric")

    def _fill_missing(self) -> None:
        stats: dict = {}
        strat = self.config.numeric_fill

        for col in self.df.columns:
            n_missing = int(self.df[col].isna().sum())
            if not n_missing:
                continue

            if col == "age":
                fill_val = self.df[col].median()
                self.df[col] = self.df[col].fillna(fill_val).round().astype(int)
                stats[col] = {"missing": n_missing, "fill": "median"}

            elif col == "city":
                self.df[col] = self.df[col].fillna("Not Disclosed")
                stats[col] = {"missing": n_missing, "fill": "Not Disclosed"}
                log(f"'city': filled {n_missing} NaN → 'Not Disclosed'")

            elif col == "discount":
                self.df[col] = self.df[col].fillna(0.0)
                stats[col] = {"missing": n_missing, "fill": 0.0}
                log(f"'discount': filled {n_missing} NaN → 0.0")

            elif col == "rating":
                fill_val = self.df[col].mean()
                self.df[col] = self.df[col].fillna(round(fill_val, 2))
                stats[col] = {"missing": n_missing, "fill": round(fill_val, 2)}
                log(f"'rating': filled {n_missing} NaN → mean ({fill_val:.2f})")

            elif self.df[col].dtype.kind in ("f", "i", "u"):
                if strat == "median":   fill_val = self.df[col].median()
                elif strat == "mean":   fill_val = self.df[col].mean()
                elif strat == "mode":   fill_val = self.df[col].mode()[0]
                else:                   fill_val = 0.0
                self.df[col] = self.df[col].fillna(fill_val)
                stats[col] = {"missing": n_missing, "strategy": strat,
                              "fill": round(float(fill_val), 4)}
                log(f"'{col}': filled {n_missing} NaN → {strat} ({fill_val:.4g})")

            else:
                self.df[col] = self.df[col].fillna(self.config.string_fill)
                stats[col] = {"missing": n_missing, "fill": self.config.string_fill}
                log(f"'{col}': filled {n_missing} NaN → '{self.config.string_fill}'")

        self._metrics["missing_filled"] = stats

    def _filter_quantity(self) -> None:
        if "quantity" not in self.df.columns:
            return

        qmin = self.config.quantity_min   # 1
        qmax = self.config.quantity_max   # 49

        mask_bad = (self.df["quantity"] < qmin) | (self.df["quantity"] > qmax)
        n_bad    = int(mask_bad.sum())

        if n_bad == 0:
            return

        if self._can_drop(n_bad):
            # safe to drop — your original approach
            self.df = self.df[~mask_bad]
            log(f"'quantity': dropped {n_bad} rows outside [{qmin}, {qmax}]")
            self._metrics["quantity_rows_dropped"] = n_bad
        else:
            # too many — cap instead of drop to protect 15% rule
            self.df["quantity"] = self.df["quantity"].clip(lower=qmin, upper=qmax)
            msg = (f"'quantity': {n_bad} rows outside [{qmin},{qmax}] — "
                   f"capped instead of dropped to preserve row count")
            self._warnings.append(msg)
            log(msg, "warning")
            self._metrics["quantity_rows_capped"] = n_bad

    def _clean_gender(self) -> None:
        if "gender" not in self.df.columns:
            return

        # Your exact mapping from CLEANORDERS.PY + extended
        _GENDER_MAP = {
            "m": "M", "male": "M", "man": "M", "boy": "M", "1": "M",
            "f": "F", "female": "F", "woman": "F", "girl": "F", "0": "F",
            "other": "OTHER", "non-binary": "OTHER", "nonbinary": "OTHER",
            "nb": "OTHER", "non_binary": "OTHER",
        }
        raw              = self.df["gender"].astype(str).str.strip().str.lower()
        self.df["gender"]= raw.map(_GENDER_MAP).fillna(self.config.unknown_gender)
        # Your label: "Unmentioned"
        invalid = int((self.df["gender"] == self.config.unknown_gender).sum())
        log(f"'gender' normalised  ({invalid} set to '{self.config.unknown_gender}')")
        self._metrics["gender_normalised"] = invalid

        # Strip whitespace from all string columns
        for col in self.df.select_dtypes(include="object").columns:
            self.df[col] = self.df[col].astype(str).str.strip()

    def _apply_status_rules(self) -> None:
        if "order_status" not in self.df.columns:
            return

        # Your rule: cancelled orders → rating = 0
        cancelled_mask = self.df["order_status"].str.strip().str.lower() == "cancelled"
        n_cancelled    = int(cancelled_mask.sum())
        if "rating" in self.df.columns and n_cancelled:
            self.df.loc[cancelled_mask, "rating"] = 0.0
            log(f"'order_status': set rating=0 for {n_cancelled} cancelled orders")
            self._metrics["cancelled_rating_zeroed"] = n_cancelled

    def _cap_rating(self) -> None:
        if "rating" not in self.df.columns:
            return
        over5  = int((self.df["rating"] > 5).sum())
        under0 = int((self.df["rating"] < 0).sum())
        if over5:
            self.df.loc[self.df["rating"] > 5, "rating"] = 5.0
            log(f"'rating': capped {over5} values > 5 → 5.0")
        if under0:
            self.df.loc[self.df["rating"] < 0, "rating"] = 0.0
            log(f"'rating': capped {under0} values < 0 → 0.0")
        self._metrics["rating_capped"] = {"over5": over5, "under0": under0}

    # ── Step 12a – product_id cleaning ────────────────────────────────────
    def _clean_product_id(self) -> None:
        """
        Guidelines
        ----------
        - Strip leading/trailing whitespace.
        - Uppercase the whole value so 'sku-001' and 'SKU-001' are identical.
        - Replace NaN / blank / 'nan' / 'none' with 'UNKNOWN_PRODUCT'.
        - Log how many values were null or non-conforming.

        No rows are dropped; all corrections are in-place fills/transforms.
        """
        if "product_id" not in self.df.columns:
            return

        col = self.df["product_id"].astype(str).str.strip().str.upper()
        _null_tokens = {"NAN", "NONE", "NULL", "NA", "", "N/A", "-"}
        n_null = int(col.isin(_null_tokens).sum())
        col = col.replace(dict.fromkeys(_null_tokens, "UNKNOWN_PRODUCT"))
        self.df["product_id"] = col
        log(f"'product_id': uppercased & stripped  ({n_null} nulls → 'UNKNOWN_PRODUCT')")
        self._metrics["product_id_nulls_filled"] = n_null

    # ── Step 12b – branch cleaning ─────────────────────────────────────────
    def _clean_branch(self) -> None:
        """
        Guidelines
        ----------
        - Strip whitespace, convert to Title Case for consistent display.
        - Collapse common abbreviations: 'BR', 'STR', 'STORE' etc.
          are left as-is because real names differ by dataset; only blank/null
          values are filled.
        - Replace NaN / blank / 'nan' / 'none' with 'Unknown Branch'.
        - Log count of nulls filled.
        """
        if "branch" not in self.df.columns:
            return

        col = self.df["branch"].astype(str).str.strip().str.title()
        _null_tokens = {"Nan", "None", "Null", "Na", "", "N/A", "-"}
        n_null = int(col.isin(_null_tokens).sum())
        col = col.replace(dict.fromkeys(_null_tokens, "Unknown Branch"))
        self.df["branch"] = col
        log(f"'branch': title-cased & stripped  ({n_null} nulls → 'Unknown Branch')")
        self._metrics["branch_nulls_filled"] = n_null

    # ── Step 12c – cashier_id cleaning ────────────────────────────────────
    def _clean_cashier_id(self) -> None:
        """
        Guidelines
        ----------
        - Strip whitespace, uppercase (IDs like 'emp-042' → 'EMP-042').
        - Replace NaN / blank / 'nan' / 'none' with 'UNKNOWN_CASHIER'.
        - Log count of nulls filled.

        No rows are dropped.
        """
        if "cashier_id" not in self.df.columns:
            return

        col = self.df["cashier_id"].astype(str).str.strip().str.upper()
        _null_tokens = {"NAN", "NONE", "NULL", "NA", "", "N/A", "-"}
        n_null = int(col.isin(_null_tokens).sum())
        col = col.replace(dict.fromkeys(_null_tokens, "UNKNOWN_CASHIER"))
        self.df["cashier_id"] = col
        log(f"'cashier_id': uppercased & stripped  ({n_null} nulls → 'UNKNOWN_CASHIER')")
        self._metrics["cashier_id_nulls_filled"] = n_null

    # ── Step 12d – loyalty_member normalisation ───────────────────────────
    def _clean_loyalty_member(self) -> None:
        """
        Guidelines
        ----------
        - Accepts a wide range of truthy / falsy representations:
            Truthy  → 1 : '1', 'yes', 'y', 'true', 't', 'member',
                          'enrolled', 'subscribed', 'vip', 'premium'
            Falsy   → 0 : '0', 'no', 'n', 'false', 'f',
                          'non-member', 'not enrolled', 'none'
        - Unknown / missing → NaN (kept as pd.NA in Int8).
        - Output dtype: pandas nullable Int8 (0 / 1 / <NA>).
        - Log counts of 1s, 0s, and unknowns.

        No rows are dropped.
        """
        if "loyalty_member" not in self.df.columns:
            return

        _TRUTHY  = {"1", "yes", "y", "true", "t", "member", "enrolled",
                    "subscribed", "vip", "premium", "active", "loyal"}
        _FALSY   = {"0", "no", "n", "false", "f", "non-member",
                    "not enrolled", "none", "inactive", "non_member"}

        raw = self.df["loyalty_member"].astype(str).str.strip().str.lower()

        def _map(v: str):
            if v in _TRUTHY:
                return 1
            if v in _FALSY:
                return 0
            return pd.NA

        mapped = raw.map(_map)
        self.df["loyalty_member"] = pd.array(mapped, dtype="Int8")

        n_yes     = int((self.df["loyalty_member"] == 1).sum())
        n_no      = int((self.df["loyalty_member"] == 0).sum())
        n_unknown = int(self.df["loyalty_member"].isna().sum())
        log(f"'loyalty_member' normalised → 1={n_yes}, 0={n_no}, unknown={n_unknown}")
        self._metrics["loyalty_member"] = {
            "members": n_yes, "non_members": n_no, "unknown": n_unknown,
        }

    # ── Step 12e – return_flag normalisation ──────────────────────────────
    def _clean_return_flag(self) -> None:
        """
        Guidelines
        ----------
        - Accepts a wide range of truthy / falsy representations:
            Truthy  → 1 : '1', 'yes', 'y', 'true', 't',
                          'returned', 'refunded', 'refund',
                          'reversed', 'exchanged', 'voided'
            Falsy   → 0 : '0', 'no', 'n', 'false', 'f',
                          'not returned', 'none', 'completed'
        - Unknown / missing → NaN (kept as pd.NA in Int8).
        - Output dtype: pandas nullable Int8 (0 / 1 / <NA>).
        - Log counts of returns, non-returns, and unknowns.
        - Also cross-checks: if order_status is 'cancelled' and return_flag
          is 0, flag a warning (possible data inconsistency) but does NOT
          override the value — business logic stays with the analyst.

        No rows are dropped.
        """
        if "return_flag" not in self.df.columns:
            return

        _TRUTHY = {"1", "yes", "y", "true", "t",
                   "returned", "refunded", "refund",
                   "reversed", "exchanged", "voided", "return"}
        _FALSY  = {"0", "no", "n", "false", "f",
                   "not returned", "none", "completed", "sold"}

        raw = self.df["return_flag"].astype(str).str.strip().str.lower()

        def _map(v: str):
            if v in _TRUTHY:
                return 1
            if v in _FALSY:
                return 0
            return pd.NA

        mapped = raw.map(_map)
        self.df["return_flag"] = pd.array(mapped, dtype="Int8")

        n_returned    = int((self.df["return_flag"] == 1).sum())
        n_not_returned= int((self.df["return_flag"] == 0).sum())
        n_unknown     = int(self.df["return_flag"].isna().sum())
        log(f"'return_flag' normalised → returned={n_returned}, "
            f"not_returned={n_not_returned}, unknown={n_unknown}")
        self._metrics["return_flag"] = {
            "returned": n_returned,
            "not_returned": n_not_returned,
            "unknown": n_unknown,
        }

        if "order_status" in self.df.columns:
            cancelled_mask = (
                self.df["order_status"].astype(str).str.strip().str.lower()
                == "cancelled"
            )
            inconsistent = int(
                (cancelled_mask & (self.df["return_flag"] == 0)).sum()
            )
            if inconsistent:
                msg = (f"'return_flag': {inconsistent} rows have order_status='cancelled' "
                       f"but return_flag=0 — verify data consistency.")
                self._warnings.append(msg)
                log(msg, "warning")

    def _cap_outliers(self) -> None:
        k     = self.config.iqr_multiplier
        stats = {}
        # Skip columns that have their own specific rules
        skip  = {"rating", "quantity", "age", "discount"}

        for col in self.df.select_dtypes(include=np.number).columns:
            if col in skip:
                continue
            q1, q3 = self.df[col].quantile([0.25, 0.75])
            iqr    = q3 - q1
            if iqr == 0:
                continue
            lo, hi = q1 - k * iqr, q3 + k * iqr
            n      = int(((self.df[col] < lo) | (self.df[col] > hi)).sum())
            if n:
                self.df[col] = self.df[col].clip(lower=lo, upper=hi)
                stats[col]   = {"capped": n, "lower": round(lo, 4), "upper": round(hi, 4)}
                log(f"'{col}': capped {n} outliers  [{lo:.3g}, {hi:.3g}]")
        self._metrics["outliers_capped"] = stats

    def _apply_domain_rules(self) -> None:
        rules = {
            "age":      (self.config.age_min,      self.config.age_max),
            "discount": (self.config.discount_min,  self.config.discount_max),
        }
        total = 0
        for col, (lo, hi) in rules.items():
            if col not in self.df.columns:
                continue
            mask_bad = ~self.df[col].between(lo, hi)
            n_bad    = int(mask_bad.sum())
            if not n_bad:
                continue
            if self._can_drop(n_bad):
                before     = len(self.df)
                self.df    = self.df[~mask_bad]
                dropped    = before - len(self.df)
                total     += dropped
                log(f"'{col}': dropped {dropped} rows outside [{lo}, {hi}]", "warning")
            else:
                self.df[col] = self.df[col].clip(lower=lo, upper=hi)
                msg = (f"'{col}': {n_bad} rows outside [{lo},{hi}] — "
                       f"capped to protect row count")
                self._warnings.append(msg)
                log(msg, "warning")
        self._metrics["rows_dropped_rules"] = total

    def _derive_columns(self) -> None:
        if "revenue" not in self.df.columns:
            if {"quantity", "unit_price"}.issubset(self.df.columns):
                self.df["revenue"] = (self.df["quantity"] * self.df["unit_price"]).round(2)
                log("Derived 'revenue' = quantity × unit_price")
            elif {"quantity", "price"}.issubset(self.df.columns):
                self.df["revenue"] = (self.df["quantity"] * self.df["price"]).round(2)
                log("Derived 'revenue' = quantity × price")

        if "revenue" in self.df.columns and "discount" in self.df.columns:
            self.df["revenue_after_discount"] = (
                self.df["revenue"] * (1 - self.df["discount"] / 100)
            ).round(2)
            log("Derived 'revenue_after_discount'")

        # Looks for order_date first, then ship_date
        for date_col in ["order_date", "ship_date", "date",
                         "purchase_date", "transaction_date"]:
            if date_col not in self.df.columns:
                continue
            if not pd.api.types.is_datetime64_any_dtype(self.df[date_col]):
                continue
            dt = self.df[date_col]
            prefix = "order" if date_col in ("order_date", "date",
                                              "purchase_date",
                                              "transaction_date") else "ship"

            self.df[f"{prefix}_year"]       = dt.dt.year.astype("Int64")
            self.df[f"{prefix}_month"]      = dt.dt.month.astype("Int64")
            self.df[f"{prefix}_month_name"] = dt.dt.strftime("%b")      # Jan, Feb …
            self.df[f"{prefix}_quarter"]    = dt.dt.quarter.map(lambda q: f"Q{q}")
            self.df[f"{prefix}_week"]       = dt.dt.isocalendar().week.astype("Int64")
            self.df[f"{prefix}_dow"]        = dt.dt.day_name()          # Monday …
            self.df[f"{prefix}_day"]        = dt.dt.day.astype("Int64")
            self.df[f"{prefix}_is_weekend"] = dt.dt.dayofweek >= 5

            log(f"Derived date parts from '{date_col}': "
                f"year, month, month_name, quarter, week, dow, day, is_weekend")

            # Only derive from the first valid date col
            if date_col in ("order_date", "date", "purchase_date", "transaction_date"):
                break

        if "age" in self.df.columns:
            bins   = [0,  17,  24,  34,  44,  54,  64, 200]
            labels = ["<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
            self.df["age_group"] = pd.cut(
                self.df["age"], bins=bins, labels=labels, right=True
            ).astype(str)
            log("Derived 'age_group'")

        rev_col = ("revenue_after_discount" if "revenue_after_discount" in self.df.columns
                   else "revenue" if "revenue" in self.df.columns else None)
        if rev_col:
            q33 = self.df[rev_col].quantile(0.33)
            q66 = self.df[rev_col].quantile(0.66)
            self.df["revenue_tier"] = pd.cut(
                self.df[rev_col],
                bins=[-np.inf, q33, q66, np.inf],
                labels=["Low", "Medium", "High"],
            ).astype(str)
            log("Derived 'revenue_tier'  (Low / Medium / High)")

    def _validate(self) -> None:
        if self.df.empty:
            raise ValueError("DataFrame is empty.")
        if self.df.shape[1] < 2:
            raise ValueError("Only 1 column — check file format.")
        for col in self.df.columns:
            pct = self.df[col].isna().mean()
            if pct > 0.80:
                msg = f"'{col}' is {pct:.0%} missing — consider dropping it."
                self._warnings.append(msg)
                log(msg, "warning")

    def _build_report(self) -> dict:
        rows_retained = round(len(self.df) / max(self._original_len, 1) * 100, 1)
        if rows_retained < (100.0 - self.config.max_rows_drop_pct):
            msg = (f"WARNING: only {rows_retained}% rows retained "
                   f"(threshold {100 - self.config.max_rows_drop_pct}%)")
            self._warnings.append(msg)
            log(msg, "warning")
        return {
            "source":            self.source_name,
            "timestamp":         datetime.now().isoformat(timespec="seconds"),
            "original_shape":    list(self.original_shape),
            "cleaned_shape":     list(self.df.shape),
            "rows_retained_pct": rows_retained,
            "detected_columns":  self._metrics.get("detected_columns", []),
            "final_columns":     list(self.df.columns),
            "warnings":          self._warnings,
            "metrics":           self._metrics,
        }

    def _print_summary(self, report: dict) -> None:
        sep = "─" * 52
        print(f"\n{sep}")
        print(f"  CLEANING SUMMARY")
        print(sep)
        print(f"  Source    : {report['source']}")
        print(f"  Original  : {report['original_shape'][0]:,} rows × "
              f"{report['original_shape'][1]} cols")
        print(f"  Cleaned   : {report['cleaned_shape'][0]:,} rows × "
              f"{report['cleaned_shape'][1]} cols")
        print(f"  Retained  : {report['rows_retained_pct']}%")
        if self._warnings:
            print(f"  Warnings  :")
            for w in self._warnings:
                print(f"    ⚠  {w}")
        print(sep + "\n")

    def _save(self, report: dict) -> tuple[Path, Path]:
        out_dir = Path(self.config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
        stem        = Path(self.source_name).stem or "data"
        csv_path    = out_dir / f"{stem}_cleaned_{ts}.csv"
        report_path = out_dir / f"{stem}_report_{ts}.json"
        self.df.to_csv(csv_path, index=False)
        report_path.write_text(json.dumps(report, indent=2, default=str))
        log(f"Saved → {csv_path}")
        log(f"Saved → {report_path}")
        return csv_path, report_path

    def run(self) -> tuple[pd.DataFrame, dict]:
        print("\n" + "═" * 52)
        print("  Starting DataCleaner pipeline")
        print("═" * 52)

        self._validate()
        self._normalise_columns()
        self._detect_and_alias()
        self._remove_duplicates()
        self._drop_index_column()
        self._fix_infinite()
        self._fix_types()
        self._detect_and_alias()
        self._fill_missing()
        self._filter_quantity()
        self._clean_gender()
        self._apply_status_rules()
        self._cap_rating()
        self._clean_product_id()
        self._clean_branch()
        self._clean_cashier_id()
        self._clean_loyalty_member()
        self._clean_return_flag()
        self._cap_outliers()
        self._apply_domain_rules()
        self._derive_columns()

        report = self._build_report()
        self._print_summary(report)
        csv_path, report_path = self._save(report)
        report["output_csv"]    = str(csv_path)
        report["output_report"] = str(report_path)
        return self.df, report