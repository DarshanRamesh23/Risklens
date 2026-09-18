"""
End-to-end demo script: creates a vendor, ingests the sample policy + sample
vendor SOC2 excerpt, then runs the full scoring pipeline and prints the
resulting findings. Run this after `uvicorn app.main:app` is up.

    python demo_seed.py
"""
import httpx

BASE = "http://localhost:8000/api"


def main():
    with httpx.Client(timeout=60) as client:
        vendor = client.post(f"{BASE}/vendors", json={
            "name": "Acme Cloud Services",
            "industry": "saas",
            "geography": "us",
            "past_incidents": 2,
            "contract_value_usd": 250000,
        }).json()
        vendor_id = vendor["id"]
        print(f"Created vendor: {vendor}")

        with open("sample_data/internal_data_retention_policy.txt", "rb") as f:
            resp = client.post(
                f"{BASE}/ingest/policy",
                params={"policy_name": "Data Retention and Vendor Handling Policy v3"},
                files={"file": ("internal_data_retention_policy.txt", f, "text/plain")},
            )
            print("Policy ingest:", resp.json())

        with open("sample_data/vendor_acme_soc2_excerpt.txt", "rb") as f:
            resp = client.post(
                f"{BASE}/ingest/vendor/{vendor_id}",
                files={"file": ("vendor_acme_soc2_excerpt.txt", f, "text/plain")},
            )
            print("Vendor doc ingest:", resp.json())

        print("Running scoring pipeline (ML gate + RAG agent + verification)...")
        result = client.post(f"{BASE}/score/{vendor_id}").json()
        print(f"\nFinal risk score: {result['final_risk_score']} ({result['final_risk_tier']})")
        print(f"ML prior: {result['ml_prior_risk_prob']} (driver: {result['ml_main_driver']})\n")
        for f in result["findings"]:
            print(f"[{f['severity'].upper()}] grounded={f['grounded']}")
            print(f"  {f['summary']}")
            print(f"  vendor: \"{f['vendor_quote']}\"")
            print(f"  policy: \"{f['policy_quote']}\"\n")


if __name__ == "__main__":
    main()
