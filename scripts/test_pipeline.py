import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

# Add apps/backend to PYTHONPATH
root_dir = Path(__file__).resolve().parents[1]
backend_dir = root_dir / "apps" / "backend"
sys.path.append(str(backend_dir))

# Mock external services if needed, but for now we'll try to run it raw
# We might need to set some ENV vars if they are required at import time
os.environ["SUPABASE_URL"] = os.getenv("SUPABASE_URL", "https://dummy.supabase.co")
os.environ["SUPABASE_KEY"] = os.getenv("SUPABASE_KEY", "dummy-key")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "dummy-key")

try:
    from app.main import app
except ImportError as e:
    print(f"Error importing app: {e}")
    sys.exit(1)

client = TestClient(app)

def run_evaluation():
    samples_path = root_dir / "scripts" / "evaluation_samples.json"
    with open(samples_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    results = []
    print(f"Running evaluation on {len(samples)} samples...\n")

    for sample in samples:
        print(f"Processing {sample['id']}: {sample['subject']}")
        payload = {
            "email": sample["body"],
            "subject": sample["subject"],
            "customer_email": f"customer_{sample['id']}@example.com",
            "sender": "customer"
        }
        
        try:
            response = client.post("/ingest", json=payload)
            if response.status_code == 200:
                data = response.json()
                results.append({
                    "id": sample["id"],
                    "success": True,
                    "output": data,
                    "expected": sample["expected"]
                })
                print(f"  Result: Success (Ticket ID: {data['ticket_id']})")
                # print(f"  Response Body: {data.get('email_body')[:100]}...")
            else:
                results.append({
                    "id": sample["id"],
                    "success": False,
                    "error": f"Status code {response.status_code}: {response.text}"
                })
                print(f"  Result: FAILED ({response.status_code})")
        except Exception as e:
            results.append({
                "id": sample["id"],
                "success": False,
                "error": str(e)
            })
            print(f"  Result: ERROR ({e})")

    # Analysis
    print("\n--- Evaluation Summary ---")
    total = len(samples)
    successful = sum(1 for r in results if r.get("success"))
    print(f"Successfully processed: {successful}/{total}")
    
    # In a real scenario, we would compare the output with expected
    # But since the pipeline produces a complex response (email body), 
    # and the logic happens inside services, we might want to check the DB 
    # or look at the logs if we had them.
    # For now, let's just output the raw results for analysis.
    
    with open(root_dir / "scripts" / "evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to scripts/evaluation_results.json")

if __name__ == "__main__":
    run_evaluation()
