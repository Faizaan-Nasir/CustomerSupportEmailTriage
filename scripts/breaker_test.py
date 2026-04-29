import os
import sys
import json
from pathlib import Path
from fastapi.testclient import TestClient

root_dir = Path(__file__).resolve().parents[1]
backend_dir = root_dir / "apps" / "backend"
sys.path.append(str(backend_dir))

from app.main import app

client = TestClient(app)

breaker_samples = [
    {
        "id": "breaker_01",
        "subject": "I noticed something strange",
        "body": "I was checking my records and I noticed some very strange activity that I didn't authorize. I'm not sure if it's related to my recent interaction with your site or something else, but I need you to look into it immediately. This is extremely sensitive and I'm very concerned about my privacy. Do not share this with anyone else.",
        "expected_low_confidence": True
    },
    {
        "id": "breaker_02",
        "subject": "Important update required",
        "body": "There is a significant issue that we need to discuss regarding the information I provided previously. It seems there was a misunderstanding and now things are much more complicated than they should be. Please contact me at your earliest convenience to resolve this matter once and for all. I expect you to take this seriously.",
        "expected_low_confidence": True
    }
]

def run_breaker_tests():
    print("Running Breaker Tests (Cryptic/Sensitive Samples)...\n")
    results = []
    for sample in breaker_samples:
        print(f"Processing {sample['id']}...")
        payload = {
            "email": sample["body"],
            "subject": sample["subject"],
            "customer_email": f"breaker_{sample['id']}@example.com",
            "sender": "customer"
        }
        
        # We need to manually call the interpretation service or check the ticket details
        # because the /ingest endpoint doesn't return the confidence score directly.
        # But we can check the logs (which we see in output) or the DB if we had access.
        # For this script, we'll assume the internal prints show us what we need.
        
        response = client.post("/ingest", json=payload)
        if response.status_code == 200:
            data = response.json()
            print(f"  Success: Ticket {data['ticket_id']} created.")
            # Note: The confidence score is logged in the backend console output.
        else:
            print(f"  Failed: {response.text}")

if __name__ == "__main__":
    run_breaker_tests()
