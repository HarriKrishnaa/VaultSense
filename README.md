# VaultSense — Cloud Document Security Dashboard

A cloud-native document integrity and security monitoring dashboard built on AWS.

## Live at
https://harrikrishnaa.github.io/VaultSense/

## Architecture

```
Browser (GitHub Pages / S3)
        │
        │  POST { file, fileName } base64
        ▼
API Gateway → Lambda (upload handler)
        │
        │  PutObject
        ▼
S3 Bucket (secure-doc-intake-bucket)
        │
        │  S3 trigger (on ObjectCreated)
        ▼
Lambda (integrity_check_handler)
        │
        ├── SHA-256 hash computation
        ├── DynamoDB hash lookup & comparison
        ├── URL security scan
        └── ML anomaly detection
        │
        │  UpdateItem
        ▼
DynamoDB (document_records table)
        │
        │  GET /records
        ▼
API Gateway → Lambda (records handler)
        │
        ▼
Dashboard (reads & renders all records)
```

## Project Structure

```
vaultsense/
├── frontend/
│   └── index.html              # Single-page dashboard (VaultSense UI)
├── backend/
│   ├── lambda_function.py      # Upload handler Lambda
│   ├── integrity_check.py      # integrity_check_handler Lambda
│   └── requirements.txt        # Python dependencies
├── infrastructure/
│   ├── s3-cors.json            # S3 bucket CORS config
│   ├── s3-bucket-policy.json   # S3 bucket policy
│   └── iam-lambda-policy.json  # IAM role policy for Lambda
├── docs/
│   └── SETUP.md                # Full AWS setup guide
└── README.md
```

## AWS Resources Required

| Resource | Name |
|---|---|
| S3 Bucket | `secure-doc-intake-bucket` (eu-north-1) |
| DynamoDB Table | `document_records` |
| Lambda | `integrity_check_handler` |
| Lambda | upload handler |
| API Gateway | `tcgf31pbj3` (eu-north-1) |
| IAM Role | `document_verification_lambda-role-1objl7dm` |

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/production/records` | Fetch all document records |
| `POST` | `/production/upload` | Upload document to S3 |

## Record Schema (DynamoDB)

```json
{
  "doc_id": "filename.txt",
  "hash_value": "sha256...",
  "verification_status": "Registered | Verified | Compromised",
  "ml_status": "Normal | Anomaly",
  "url_security_status": "Safe | Unsafe",
  "url_details": [],
  "last_checked": "2026-03-21 06:48:30"
}
```

## Status Conditions

### verification_status
| Value | Meaning |
|---|---|
| `Registered` | File uploaded, hash stored, awaiting verification |
| `Verified` | Hash recomputed and matched — file is intact |
| `Compromised` | Hash mismatch — file has been tampered |

### ml_status
| Value | Meaning |
|---|---|
| `Normal` | ML model found no suspicious behaviour |
| `Anomaly` | ML model detected deviation — potential threat |

### url_security_status
| Value | Meaning |
|---|---|
| `Safe` | No malicious URLs found in document |
| `Unsafe` | Suspicious or malicious URLs detected |

## Hosting on GitHub Pages

1. Push this repo to GitHub
2. Go to **Settings → Pages**
3. Set source to `main` branch → `/frontend` folder (or via GitHub Actions workflow)
4. Dashboard will be live at `https://harrikrishnaa.github.io/VaultSense/`

> The frontend calls your AWS API Gateway directly — no server needed for hosting.

## Quick Deploy

```bash
git clone https://github.com/HarriKrishnaa/VaultSense.git
cd VaultSense
# Open frontend/index.html locally or view on GitHub Pages
```
