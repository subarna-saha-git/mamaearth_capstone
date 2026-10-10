import pandas as pd

orders = pd.read_csv("data/orders.csv")
customers = pd.read_csv("data/customers.csv")
products = pd.read_csv("data/products.csv")

print("Orders shape:", orders.shape)

print(orders["payment_method"].unique())

orders["payment_method"] = (
    orders["payment_method"].str.strip().str.upper()
)

print(orders["payment_method"].unique())

natural_key = [
    "customer_id",
    "product_id",
    "order_date",
    "quantity",
    "discount_pct",
    "payment_method",
    "rating",
    "returned"
]
duplicate_mask = orders.duplicated(
    subset=natural_key,
    keep="first"
)
dropped_order_ids = orders.loc[duplicate_mask, "order_id"]

print(dropped_order_ids.to_list())
orders_clean = orders.loc[~duplicate_mask].copy()
print(orders_clean.shape)


null_value=orders_clean[["discount_pct", "rating"]].isnull().sum()
print(null_value)
orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)
rating_median = orders_clean["rating"].median()
orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)
print(orders_clean[["discount_pct", "rating"]].isnull().sum())


orders_merged = orders_clean.merge(
    products[["product_id", "price"]],
    on="product_id",
    how="left"
)
orders_merged = orders_merged.merge(
    customers[["customer_id", "city_tier"]],
    on="customer_id",
    how="left"
)

orders_merged["order_value"] = (
    orders_merged["quantity"]
    * orders_merged["price"]
    * (1 - orders_merged["discount_pct"] / 100)
)

cleaned_total = orders_merged["order_value"].sum()

print("Cleaned merged row count:", len(orders_merged))
print(f"Cleaned order value total: ₹{cleaned_total:.2f}")

dropped_orders = orders.loc[duplicate_mask].copy()

dropped_orders = dropped_orders.merge(
    products[["product_id", "price"]],
    on="product_id",
    how="left"
)

dropped_orders["discount_pct"] = dropped_orders["discount_pct"].fillna(0)

dropped_orders["order_value"] = (
    dropped_orders["quantity"]
    * dropped_orders["price"]
    * (1 - dropped_orders["discount_pct"] / 100)
)

dropped_total = dropped_orders["order_value"].sum()

print(dropped_orders["order_id"].to_list())
print(f"Combined value of dropped duplicate rows: ₹{dropped_total:.2f}")

part1_raw_total = 99860.20
difference = part1_raw_total - cleaned_total

print(f"\nPart 1 raw total: ₹{part1_raw_total:.2f}")
print(f"Difference (Part 1 - cleaned total): ₹{difference:.2f}")

print(
    "\nReconciliation note: Part 1 Report (a) shows a raw order-value "
    f"total of ₹{part1_raw_total:.2f}, while the cleaned dataset has "
    f"175 rows with a total of ₹{cleaned_total:.2f}. The difference "
    f"is ₹{difference:.2f}, attributable to the five duplicate orders "
    f"removed in Task 3 ({', '.join(dropped_orders['order_id'].astype(str))}), "
    f"whose independently calculated combined order value is "
    f"₹{dropped_total:.2f}. Discount and rating imputation did not "
    "change the order-value total: missing discounts were treated as "
    "0%, and rating values are not used in the order-value formula."
)


Q1 = orders_merged["quantity"].quantile(0.25)
Q3 = orders_merged["quantity"].quantile(0.75)
IQR = Q3 - Q1

lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

print(f"Q1: {Q1}")
print(f"Q3: {Q3}")
print(f"IQR: {IQR}")
print(f"Lower bound: {lower}")
print(f"Upper bound: {upper}")

orders_merged["is_outlier"] = (
    (orders_merged["quantity"] < lower)
    | (orders_merged["quantity"] > upper)
)

outliers = orders_merged.loc[
    orders_merged["is_outlier"],
    ["order_id", "quantity"]
]

print(outliers.to_string(index=False))
print("Number of outliers:", len(outliers))
print("Rows retained in merged dataset:", len(orders_merged))

print(
    "Hypothesis: COD orders have a higher return rate "
    "than CARD and UPI orders."
)

return_summary = orders_merged.groupby(
    "payment_method"
)["returned"].agg(["count", "mean"])

return_summary["return_rate_pct"] = return_summary["mean"] * 100

print(return_summary.round(3).to_string())

for method, row in return_summary.iterrows():
    print(f"{method}: {row['return_rate_pct']:.1f}%")

cod_rate = return_summary.loc["COD", "mean"]
other_rates = return_summary.loc[["CARD", "UPI"], "mean"]

if (cod_rate > other_rates).all():
    print("Hypothesis result: Confirmed")
else:
    print("Hypothesis result: Not confirmed")

segment_summary = orders_merged.groupby(
    ["payment_method", "city_tier"]
)["returned"].agg(["count", "mean"])

segment_summary["return_rate_pct"] = segment_summary["mean"] * 100

print(segment_summary.round(3).to_string())

highest_risk = segment_summary["return_rate_pct"].idxmax()
highest_rate = segment_summary["return_rate_pct"].max()

print(
    f"Highest-risk segment: {highest_risk[0]} + {highest_risk[1]} "
    f"cities at {highest_rate:.1f}% return rate"
)

cod_segments = segment_summary.loc["COD"]


for tier, row in cod_segments.iterrows():
    print(
        f"{tier}: {int(row['count'])} orders, "
        f"{row['return_rate_pct']:.1f}% returns"
    )

correlation_columns = [
    "rating",
    "returned",
    "discount_pct",
    "quantity"
]

correlation_matrix = orders_merged[
    correlation_columns
].corr()

print(correlation_matrix.round(3).to_string())

def correlation_strength(r):
    absolute_r = abs(r)

    if absolute_r < 0.2:
        return "negligible"
    elif absolute_r < 0.4:
        return "weak"
    elif absolute_r < 0.7:
        return "moderate"
    else:
        return "strong"

pairs = [
    ("rating", "returned"),
    ("rating", "discount_pct"),
    ("rating", "quantity"),
    ("returned", "discount_pct"),
    ("returned", "quantity"),
    ("discount_pct", "quantity")
]

for col1, col2 in pairs:
    r = correlation_matrix.loc[col1, col2]
    strength = correlation_strength(r)

    print(
        f"{col1} vs {col2}: "
        f"r = {r:.3f}, strength = {strength}"
    )

discount_return_corr = correlation_matrix.loc[
    "discount_pct", "returned"
]

print(
    "\nHypothesis: Higher discounts reduce returns."
)
print(
    f"Correlation between discount_pct and returned: "
    f"{discount_return_corr:.3f}"
)

if abs(discount_return_corr) < 0.2:
    print(
        "Hypothesis result: Busted — the correlation is negligible "
        "and does not provide meaningful evidence of a linear "
        "relationship between discount percentage and returns."
    )
else:
    print(
        "Hypothesis result: Review the correlation strength "
        "and direction before drawing a conclusion."
    )

orders_merged["order_date"] = pd.to_datetime(orders_merged["order_date"])


orders_merged["year_month"] = (orders_merged["order_date"].dt.to_period("M").astype(str))


monthly_revenue_all = (
    orders_merged.groupby("year_month")["order_value"].sum().sort_index()
)


for month, revenue in monthly_revenue_all.items():
    print(f"{month}: {revenue:.2f}")


orders_without_outliers = orders_merged.loc[
    ~orders_merged["is_outlier"]
].copy()

monthly_revenue_corrected = (
    orders_without_outliers.groupby("year_month")["order_value"]
    .sum()
    .sort_index()
)


for month, revenue in monthly_revenue_corrected.items():
    print(f"{month}: {revenue:.2f}")


peak_month_all = monthly_revenue_all.idxmax()
peak_month_corrected = monthly_revenue_corrected.idxmax()

print(
    f"\nPeak month including outliers: {peak_month_all} "
    f"(₹{monthly_revenue_all.max():.2f})"
)
print(
    f"Peak month excluding outliers: {peak_month_corrected} "
    f"(₹{monthly_revenue_corrected.max():.2f})"
)

print(
    "\nInterpretation: January's apparent revenue lead is an artifact "
    "of two bulk orders landing in January: O0011 on 2026-01-28 "
    "and O0098 on 2026-01-10. After excluding these two flagged "
    "orders, March 2026 is the genuine peak month."
)
orders_merged["order_date"] = pd.to_datetime(orders_merged["order_date"])
orders_merged["year_month"] = orders_merged["order_date"].dt.to_period("M").astype(str)

monthly_all = orders_merged.groupby("year_month")["order_value"].sum().sort_index()

orders_without_outliers = orders_merged[~orders_merged["is_outlier"]].copy()

monthly_clean = orders_without_outliers.groupby("year_month")["order_value"].sum().sort_index()



import json
from pathlib import Path

raw_orders_for_total = orders.copy()
raw_orders_for_total["discount_pct"] = raw_orders_for_total["discount_pct"].fillna(0)
raw_orders_for_total = raw_orders_for_total.merge(
    products[["product_id", "price"]],
    on="product_id",
    how="left"
)
raw_orders_for_total["order_value"] = (
    raw_orders_for_total["quantity"]
    * raw_orders_for_total["price"]
    * (1 - raw_orders_for_total["discount_pct"] / 100)
)
raw_total_revenue = raw_orders_for_total["order_value"].sum()

return_rates = {
    payment: round(float(rate * 100), 1)
    for payment, rate in return_summary["mean"].items()
}

highest_risk = segment_summary["return_rate_pct"].idxmax()
highest_risk_rate = segment_summary.loc[highest_risk, "return_rate_pct"]

true_peak_month = monthly_clean.idxmax()
outlier_month = monthly_all.idxmax()

findings = {
    "cleaned_total_revenue_inr": round(float(cleaned_total), 2),
    "raw_total_revenue_inr": round(float(raw_total_revenue), 2),
    "duplicate_reconciliation_delta_inr": round(
        float(raw_total_revenue - cleaned_total), 2
    ),
    "return_rate_by_payment": return_rates,
    "highest_risk_segment": {
        "payment_method": str(highest_risk[0]),
        "city_tier": int(highest_risk[1]),
        "return_rate_pct": round(float(highest_risk_rate), 1)
    },
    "true_peak_month": {
        "month": str(true_peak_month),
        "revenue_inr": round(float(monthly_clean.loc[true_peak_month]), 2)
    },
    "outlier_inflated_month": {
        "month": str(outlier_month),
        "apparent_revenue_inr": round(float(monthly_all.loc[outlier_month]), 2),
        "corrected_revenue_inr": round(float(monthly_clean.loc[outlier_month]), 2)
    }
}
Path("narrator").mkdir(exist_ok=True)

with open("narrator/findings.json", "w", encoding="utf-8") as file:
    json.dump(findings, file, indent=4)

print("Saved findings to narrator/findings.json")