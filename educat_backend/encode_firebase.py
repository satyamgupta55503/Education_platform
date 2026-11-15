"""
encode_firebase.py — Utility to base64-encode a Firebase service account JSON
for use as an environment variable (e.g. FIREBASE_CREDENTIALS_BASE64).

Usage:
  1. Download your Firebase Admin SDK JSON from Firebase Console.
  2. Place it locally (do NOT commit it).
  3. Run:  python encode_firebase.py /path/to/service-account.json
  4. Copy the printed base64 string into your .env file.

The JSON structure expected:
{
  "type": "service_account",
  "project_id": "YOUR_PROJECT_ID",
  "private_key_id": "YOUR_KEY_ID",
  "private_key": "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n",
  "client_email": "...",
  ...
}
"""

import base64
import json
import sys

def encode_service_account(json_path: str) -> str:
    with open(json_path, "r") as f:
        data = json.load(f)
    return base64.b64encode(json.dumps(data).encode()).decode()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python encode_firebase.py <path-to-service-account.json>")
        sys.exit(1)
    encoded = encode_service_account(sys.argv[1])
    print(encoded)
