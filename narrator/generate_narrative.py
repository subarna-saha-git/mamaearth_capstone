
import json
import os
from pathlib import Path

from google import genai
from google.genai import types


def generate_scr_narrative_offline(findings: dict) -> dict:
    returns = findings["return_rate_by_payment"]
    risk = findings["highest_risk_segment"]
    peak = findings["true_peak_month"]
    inflated = findings["outlier_inflated_month"]

    narrative = f"""Situation

Mamaearth's cleaned order data shows total revenue of ₹{findings["cleaned_total_revenue_inr"]:,.2f}, compared with raw revenue of ₹{findings["raw_total_revenue_inr"]:,.2f}. After cleaning, {peak["month"]} was the strongest month, with revenue of ₹{peak["revenue_inr"]:,.2f}.

Complication

Cash on Delivery (COD) had a return rate of {returns["COD"]:.1f}%, compared with {returns["CARD"]:.1f}% for CARD and {returns["UPI"]:.1f}% for UPI. The highest-risk segment was COD in Tier-{risk["city_tier"]}, with a return rate of {risk["return_rate_pct"]:.1f}%. The raw-to-cleaned revenue difference was ₹{findings["duplicate_reconciliation_delta_inr"]:,.2f}, caused by duplicate orders. January {inflated["month"]} revenue appeared to be ₹{inflated["apparent_revenue_inr"]:,.2f}, but was ₹{inflated["corrected_revenue_inr"]:,.2f} after excluding flagged quantity outliers.

Resolution

The team should review COD orders in Tier-{risk["city_tier"]} first and investigate why their return rate is higher. Reporting should use the cleaned revenue figures and remove the influence of flagged quantity outliers when assessing monthly trends. March remains the true peak month, at ₹{peak["revenue_inr"]:,.2f}. The ₹{findings["duplicate_reconciliation_delta_inr"]:,.2f} reconciliation difference should be tracked as a duplicate-order issue.
"""

    return {
        "status": "success",
        "narrative": narrative,
        "tokens": 0
    }


def generate_scr_narrative(findings: dict) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return generate_scr_narrative_offline(findings)

    system_instruction = (
    "You are a senior data analyst writing for Mamaearth's regional ops "
    "and finance heads. Write exactly three labeled sections: Situation, "
    "Complication, and Resolution. Keep the entire report under 200 words. "
    "Use only the supplied findings. Every number must come from the findings "
    "and retain its exact value. Do not invent statistics."
)

    prompt = (
        "Write a business narrative using the Situation–Complication–Resolution "
        "structure. Explain what the findings mean for Mamaearth's regional "
        "operations and finance teams. Use the supplied figures accurately. "
        "Do not introduce any numbers that are not present in the findings.\n\n"
        "Verified findings:\n"
        + json.dumps(findings, indent=2)
    )

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=30000)
        )

        response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.0,
        max_output_tokens=500,
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
)

        narrative = response.text or ""
        if not narrative.strip():
            raise ValueError("Gemini returned an empty narrative.")

        usage = getattr(response, "usage_metadata", None)
        tokens = getattr(usage, "total_token_count", 0) if usage else 0

        return {
            "status": "success",
            "narrative": narrative,
            "tokens": tokens
        }

    except Exception as err:
        return {
            "status": "error",
            "narrative": None,
            "message": str(err)
        }


def check_narrative(narrative: str) -> bool:
    normalized = narrative.replace(",", "").lower()

    checks = [
        ("Cleaned revenue: 97358.30", ["97358.30", "97358.3"]),
        ("COD return rate: 44.4", ["44.4"]),
        ("COD Tier-2 return rate: 54.5", ["54.5"]),
        ("Duplicate reconciliation delta: 2501.90", ["2501.90", "2501.9"]),
        ("March peak revenue: March and 20318.90",
         ["march", "20318.90", "20318.9"])
    ]

    all_passed = True

    for label, required in checks:
        if label.startswith("March"):
            passed = "march" in normalized and (
                "20318.90" in normalized or "20318.9" in normalized
            )
        else:
            passed = any(value in normalized for value in required)

        print(f"{'PASS' if passed else 'FAIL'}: {label}")
        if not passed:
            all_passed = False

    return all_passed


def main():
    findings_path = Path("narrator/findings.json")
    sample_path = Path("narrator/sample_output.txt")

    with open(findings_path, "r", encoding="utf-8") as file:
        findings = json.load(file)

    result = generate_scr_narrative(findings)

    if result["status"] == "error":
        print("Gemini failed; using the offline narrative.")
        print(result["message"])
        result = generate_scr_narrative_offline(findings)

    print("\n" + result["narrative"])

    with open(sample_path, "w", encoding="utf-8") as file:
        file.write(result["narrative"])

    print(f"\nSaved narrative to {sample_path}")
    print("\nNumeric accuracy check:")
    check_narrative(result["narrative"])

    print(f"\nStatus: {result['status']}")
    print(f"Tokens: {result['tokens']}")


if __name__ == "__main__":
    main()
