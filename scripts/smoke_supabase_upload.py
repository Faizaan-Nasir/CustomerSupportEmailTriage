from app.repositories.supabase_client import get_client
from pathlib import Path
from app.rag.parser import parse_file
from app.repositories.attachment_repo import create_attachment
import uuid
from app.repositories.ticket_repo import create_ticket

BUCKET = "attachments"
SAMPLE_PATH = Path("apps/backend/sample_attachment.txt").resolve()
OBJECT_PATH = "smoke-test/sample_attachment.txt"

if not SAMPLE_PATH.exists():
    raise SystemExit(f"Sample file not found: {SAMPLE_PATH}")

client = get_client()
print("Uploading to Supabase...")
try:
    client.storage.from_(BUCKET).remove([OBJECT_PATH])
except Exception:
    pass
res = client.storage.from_(BUCKET).upload(OBJECT_PATH, str(SAMPLE_PATH))
print("Upload response:", res)

print("Creating signed URL...")
signed = client.storage.from_(BUCKET).create_signed_url(OBJECT_PATH, 60)
print("Signed URL:", signed)

print("Parsing file for DB record...")
parsed = parse_file(str(SAMPLE_PATH))
file_url = f"supabase://{BUCKET}/{OBJECT_PATH}"
ticket = create_ticket({
    "customer_email": "smoke@example.com",
    "subject": "Smoke test ticket",
    "body": "Created for smoke test attachment",
})
record = create_attachment({
    "ticket_id": ticket["id"],
    "file_url": file_url,
    "parsed_text": parsed["text"],
})
print("Created attachment record:", record)
