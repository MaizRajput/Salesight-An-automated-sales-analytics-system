from __future__ import annotations
import re
from dataclasses import dataclass, field
import pandas as pd

COLUMN_KEYWORDS: dict[str, list[str]] = {

    "order_id": [
        "order_id", "orderid", "order_no", "orderno", "order_number",
        "invoice", "invoice_no", "invoice_number", "invoiceno",
        "transaction_id", "txn_id", "txn_no", "bill_no", "billno",
        "receipt_no", "sale_id", "saleid", "ord_id",
    ],
    "customer_id": [
        "customer_id", "cust_id", "customerid", "custid",
        "client_id", "clientid", "user_id", "userid",
        "member_id", "memberid", "buyer_id", "account_id",
    ],
    "customer_name": [
        "customer_name", "cust_name", "custname", "client_name",
        "buyer", "buyer_name", "name", "full_name", "fullname",
        "customer", "client", "member_name",
    ],

    "product": [
        "product", "product_name", "productname", "prod_name",
        "item", "item_name", "itemname", "item_desc",
        "product_desc", "product_description",
        "sku", "sku_name", "goods", "article", "prod",
        "merchandise", "product_title",
    ],
    "category": [
        "category", "cat", "category_name",
        "dept", "department",
        "segment", "product_segment",
        "type", "product_type",
        "product_category", "prod_category",
        "sub_category", "subcategory", "sub_cat",
        "product_group", "item_category", "item_type",
    ],

    "order_status": [
        "order_status", "status", "order_state", "fulfillment_status",
        "delivery_status", "shipment_status", "transaction_status",
        "sale_status",
    ],

    "region": [
        "region", "zone", "area", "territory", "division",
        "sales_region", "geo_region", "business_region",
    ],
    "state": [
        "state", "province", "prefecture", "state_name",
        "state_code", "region_state",
    ],
    "city": [
        "city", "town", "location", "place",
        "city_name", "store_city", "customer_city",
    ],
    "country": [
        "country", "nation", "market", "country_name",
        "country_code", "sales_country",
    ],

    "gender": [
        "gender", "sex", "gen",
        "customer_gender", "cust_gender", "buyer_gender",
    ],
    "age": [
        "age", "customer_age", "cust_age",
        "age_group", "age_band", "age_range",
        "buyer_age", "client_age",
    ],

    "quantity": [
        "quantity", "qty", "units", "unit_qty",
        "count", "no_of_items", "num_items",
        "items", "pieces", "pcs", "num",
        "order_qty", "sold_qty", "units_sold",
        "number_of_items",
    ],
    "unit_price": [
        "unit_price", "unitprice", "price", "price_per_unit",
        "rate", "mrp", "list_price",
        "selling_price", "sale_price",
        "cost", "cost_price", "item_price",
        "product_price", "avg_price",
    ],
    "discount": [
        "discount", "disc", "discount_amount",
        "promo", "promotion", "rebate",
        "offer", "coupon",
        "discount_pct", "discount_percent", "discount_rate",
        "discount_value",
    ],

    "revenue": [
        "revenue", "sales", "total", "total_sales",
        "total_amount", "amount",
        "gmv", "gross_merchandise_value",
        "net_sales", "gross_sales",
        "turnover", "income",
        "sale_amount", "sales_amount",
        "order_value", "order_total", "order_amount",
        "line_total", "subtotal", "sub_total",
        "extended_price", "ext_price",
        "transaction_amount", "txn_amount",
    ],

    "profit": [
        "profit", "margin", "gross_margin",
        "net", "net_profit", "net_income",
        "earnings", "gain",
        "profit_amount", "profit_value",
    ],

    "rating": [
        "rating", "score", "review_score",
        "stars", "star_rating",
        "customer_rating", "cust_rating",
        "feedback_score", "feedback",
        "review", "review_rating",
        "satisfaction", "satisfaction_score",
        "nps",
    ],

    "order_date": [
        "order_date", "orderdate",
        "date", "sale_date", "sales_date",
        "transaction_date", "txn_date",
        "invoice_date", "purchase_date",
        "created_at", "created_date",
        "order_time", "order_datetime",
        "booking_date",
    ],
    "ship_date": [
        "ship_date", "shipdate",
        "shipping_date", "shipped_date",
        "delivery_date", "delivered_date",
        "dispatch_date", "dispatched_date",
        "fulfilment_date", "fulfillment_date",
        "estimated_delivery",
    ],

    "product_id": [
        "product_id", "prod_id", "productid", "prodid",
        "item_id", "itemid", "item_code", "itemcode",
        "sku", "sku_id", "skuid", "sku_code",
        "article_id", "articleid", "article_no", "article_code",
        "goods_id", "goodsid",
        "pid", "p_id", "prod_code", "product_code",
        "upc", "barcode", "bar_code",
        "stock_code", "stockcode", "catalog_id", "catalogid",
        "listing_id", "variant_id", "ref_id", "ref_no",
        "product_ref", "prod_ref", "item_ref", "part_no", "part_number",
    ],

    "branch": [
        "branch", "branch_name", "branch_id", "branch_no", "branch_code",
        "store", "store_name", "store_id", "store_no", "store_code",
        "outlet", "outlet_name", "outlet_id", "outlet_no", "outlet_code",
        "shop", "shop_name", "shop_id",
        "location", "loc", "loc_id", "location_id", "location_name",
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
        "employee_no", "emp_no", "employee_code", "emp_code",
        "operator_id", "operatorid", "operator",
        "associate_id", "associateid", "associate",
        "agent_id", "agentid", "agent",
        "rep_id", "repid", "rep", "sales_rep",
        "attendant_id", "attendant",
        "seller_id", "sellerid", "seller",
        "clerk_id", "clerkid", "clerk",
        "user_code", "staff_member", "pos_operator",
        "assigned_to", "handled_by", "served_by",
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
        "returning_customer", "repeat_customer",
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
        "cancelled", "cancellation", "cancel_flag",
        "chargeback", "dispute",
        "return_reason", "refund_reason",
        "voided", "void_flag",
    ],

    "payment_method": [
        "payment", "payment_method", "paymentmethod",
        "payment_mode", "paymentmode", "pay_mode",
        "pay_type", "paytype",
        "mode", "mode_of_payment",
        "transaction_type", "txn_type",
        "payment_type",
    ],
}

DTYPE_HINTS: dict[str, str] = {
    "quantity":       "numeric",
    "unit_price":     "numeric",
    "revenue":        "numeric",
    "discount":       "numeric",
    "rating":         "numeric",
    "profit":         "numeric",
    "age":            "numeric",
    "order_date":     "datetime",
    "ship_date":      "datetime",
    "gender":         "category",
    "region":         "category",
    "state":          "category",
    "city":           "category",
    "country":        "category",
    "category":       "category",
    "product":        "category",
    "payment_method": "category",
    "order_status":   "category",
}


@dataclass
class MappingResult:
    mapped:     dict[str, str]
    unmapped:   list[str]
    confidence: dict[str, float]
    warnings:   list[str] = field(default_factory=list)


def _norm(name: str) -> str:
    # lowercase and drop everything that is not a letter or digit
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _score(col_norm: str, keywords: list[str]) -> float:
    # best match score between 0 and 1 for a cleaned column name against a keyword list
    best = 0.0
    for kw in keywords:
        kn = _norm(kw)
        if col_norm == kn:
            return 1.0                                  # exact
        if kn in col_norm or col_norm in kn:
            best = max(best, 0.75)                      # one contains the other
        parts = [p for p in re.split(r"[^a-z0-9]", kw.lower()) if len(p) > 2]
        if any(p in col_norm for p in parts):
            best = max(best, 0.5)                       # only a piece of the keyword matches
    return best


def _looks_like_order_id(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(20)
    pattern = re.compile(r"^(ord|inv|txn|bill|sale|order|so|po|rec)[-_]?\d+$", re.I)
    hits = sum(1 for v in sample if pattern.match(v.strip()))
    return hits >= len(sample) * 0.6


def _looks_like_customer_id(series: pd.Series) -> bool:
    sample = series.dropna().astype(str).head(50)
    numeric_hits = sum(1 for v in sample if re.match(r"^\d{3,8}$", v.strip()))
    return numeric_hits >= len(sample) * 0.7


def detect_columns(df: pd.DataFrame) -> MappingResult:
    cols     = list(df.columns)
    norm_map = {c: _norm(c) for c in cols}

    pairs: list[tuple[float, str, str]] = []
    for canonical, keywords in COLUMN_KEYWORDS.items():
        for orig in cols:
            s = _score(norm_map[orig], keywords)
            if s >= 0.4:
                pairs.append((s, canonical, orig))
    pairs.sort(reverse=True)

    mapped:    dict[str, str]   = {}
    confidence:dict[str, float] = {}
    used_orig: set[str]         = set()
    used_can:  set[str]         = set()

    for sc, canonical, orig in pairs:
        if canonical in used_can or orig in used_orig:
            continue
        mapped[canonical]     = orig
        confidence[canonical] = round(sc, 2)
        used_orig.add(orig)
        used_can.add(canonical)

    remaining = [c for c in cols if c not in used_orig]
    for orig in remaining:
        if "order_id" not in used_can and _looks_like_order_id(df[orig]):
            mapped["order_id"]        = orig
            confidence["order_id"]    = 0.6
            used_orig.add(orig)
            used_can.add("order_id")
        elif "customer_id" not in used_can and _looks_like_customer_id(df[orig]):
            mapped["customer_id"]     = orig
            confidence["customer_id"] = 0.6
            used_orig.add(orig)
            used_can.add("customer_id")

    unmapped = [c for c in cols if c not in used_orig]

    warnings: list[str] = []
    if "revenue" not in mapped and not ({"quantity", "unit_price"} <= set(mapped)):
        warnings.append(
            "No revenue column found and no quantity+price pair to derive it from."
        )
    if "order_date" not in mapped:
        warnings.append("No date column found, so time trends will not be available.")
    if "order_id" not in mapped:
        warnings.append("No order ID column detected.")
    if "customer_id" not in mapped:
        warnings.append("No customer ID column detected.")

    return MappingResult(
        mapped=mapped, unmapped=unmapped,
        confidence=confidence, warnings=warnings,
    )


def apply_mapping(df: pd.DataFrame, result: MappingResult) -> pd.DataFrame:
    rename = {orig: can for can, orig in result.mapped.items()}
    df = df.rename(columns=rename)
    # if two source columns end up with the same name (say discount and discount_pct
    # both becoming discount) pandas keeps both and df["discount"] breaks later,
    # so keep only the first one
    df = df.loc[:, ~df.columns.duplicated(keep="first")]

    for col, dtype in DTYPE_HINTS.items():
        if col not in df.columns:
            continue
        try:
            if dtype == "numeric":
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(r"[^\d.\-]", "", regex=True),
                    errors="coerce",
                )
            elif dtype == "datetime":
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
            elif dtype == "category":
                df[col] = df[col].astype(str).str.strip()
        except Exception:
            pass
    return df


def mapping_summary(result: MappingResult) -> dict:
    return {
        "detected": {
            can: {
                "original_column": orig,
                "confidence":      result.confidence.get(can, 0),
            }
            for can, orig in result.mapped.items()
        },
        "unrecognised_columns": result.unmapped,
        "warnings":             result.warnings,
        "total_mapped":         len(result.mapped),
        "total_unmapped":       len(result.unmapped),
    }