import os
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("visualizations", exist_ok=True)

orders = pd.read_csv("data/orders.csv")
customers = pd.read_csv("data/customers.csv")
products = pd.read_csv("data/products.csv")

orders["payment_method"] = orders["payment_method"].str.strip().str.upper()

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

duplicate_mask = orders.duplicated(subset=natural_key, keep="first")
orders_clean = orders.loc[~duplicate_mask].copy()

orders_clean["discount_pct"] = orders_clean["discount_pct"].fillna(0)

rating_median = orders_clean["rating"].median()
orders_clean["rating"] = orders_clean["rating"].fillna(rating_median)

orders_merged = orders_clean.merge(
    products[["product_id", "price"]],
    on="product_id",
    how="left"
).merge(
    customers[["customer_id", "city_tier"]],
    on="customer_id",
    how="left"
)

orders_merged["order_value"] = (
    orders_merged["quantity"]
    * orders_merged["price"]
    * (1 - orders_merged["discount_pct"] / 100)
)

q1 = orders_merged["quantity"].quantile(0.25)
q3 = orders_merged["quantity"].quantile(0.75)
iqr = q3 - q1

lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr

orders_merged["is_outlier"] = (
    (orders_merged["quantity"] < lower)
    | (orders_merged["quantity"] > upper)
)

return_rates = (
    orders_merged.groupby("payment_method")["returned"]
    .mean()
    .mul(100)
    .sort_values(ascending=False)
)

fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(return_rates.index, return_rates.values)

ax.bar_label(
    bars,
    labels=[f"{value:.1f}%" for value in return_rates.values],
    padding=4
)

highest_method = return_rates.index[0]
highest_rate = return_rates.iloc[0]
card_rate = return_rates.get("CARD", float("nan"))

if pd.notna(card_rate) and card_rate > 0:
    ratio = highest_rate / card_rate
    title = f"{highest_method} Returns at {highest_rate:.1f}% — {ratio:.1f}x Card"
else:
    title = f"{highest_method} Returns at {highest_rate:.1f}%"

ax.set_title(title)
ax.set_xlabel("Payment Method")
ax.set_ylabel("Return Rate (%)")
ax.set_ylim(0, max(return_rates.values) * 1.2)
ax.grid(axis="y", linestyle="--", alpha=0.3)

fig.tight_layout()
fig.savefig("visualizations/return_rate_by_payment.png", dpi=150, bbox_inches="tight")
plt.close(fig)

print("Saved: visualizations/return_rate_by_payment.png")

# Visualization 2: Outlier-corrected monthly revenue
orders_merged["order_date"] = pd.to_datetime(orders_merged["order_date"])
orders_merged["year_month"] = orders_merged["order_date"].dt.to_period("M").astype(str)

orders_without_outliers = orders_merged.loc[~orders_merged["is_outlier"]].copy()

monthly_revenue = (
    orders_without_outliers.groupby("year_month")["order_value"]
    .sum()
    .sort_index()
)

peak_month = monthly_revenue.idxmax()
peak_revenue = monthly_revenue.max()

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(monthly_revenue.index, monthly_revenue.values, marker="o", linewidth=2)

for month, revenue in monthly_revenue.items():
    ax.annotate(
        f"₹{revenue:,.2f}",
        (month, revenue),
        textcoords="offset points",
        xytext=(0, 8),
        ha="center",
        fontsize=8
    )

ax.set_title(f"Outlier-Corrected Monthly Revenue — Peak: {peak_month}")
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (₹)")
ax.tick_params(axis="x", rotation=45)
ax.grid(True, linestyle="--", alpha=0.3)

fig.tight_layout()
fig.savefig("visualizations/monthly_revenue_trend.png", dpi=150, bbox_inches="tight")
plt.close(fig)

print("Saved: visualizations/monthly_revenue_trend.png")
print(f"Corrected revenue peak: {peak_month} (₹{peak_revenue:.2f})")