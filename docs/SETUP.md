# AWS Setup Guide — VaultSense

## Step 1 — S3 Bucket

1. Create bucket: `secure-doc-intake-bucket` in `eu-north-1`
2. **Permissions → Block Public Access** → uncheck all 4 boxes → Save
3. **Permissions → Bucket Policy** → paste `infrastructure/s3-bucket-policy.json`
4. **Permissions → CORS** → paste `infrastructure/s3-cors.json`

## Step 2 — DynamoDB Table

1. Create table: `document_records`
2. Partition key: `doc_id` (String)
3. Default settings (on-demand capacity)

## Step 3 — Lambda: Upload Handler

1. Create function → Runtime: Python 3.11
2. Paste code from `backend/lambda_function.py`
3. Set env variable: `BUCKET_NAME = secure-doc-intake-bucket`
4. Attach IAM policy from `infrastructure/iam-lambda-policy.json`

## Step 4 — Lambda: integrity_check_handler

1. Create function → Runtime: Python 3.11
2. Paste code from `backend/integrity_check.py`
3. Add S3 trigger → bucket: `secure-doc-intake-bucket` → Event: `PUT`
4. Set env variables:
   - `DYNAMODB_TABLE = document_records`
   - `BUCKET_NAME = secure-doc-intake-bucket`

## Step 5 — API Gateway

1. Create HTTP API
2. Add routes:
   - `POST /production/upload` → upload handler Lambda
   - `GET /production/records` → records handler Lambda  
3. Enable CORS:
   - Allow Origin: `*`
   - Allow Headers: `Content-Type`
   - Allow Methods: `POST, GET, OPTIONS`
4. Deploy to stage: `production`

## Step 6 — GitHub Pages

1. Push repo to GitHub
2. Settings → Pages → Source: `main` / `frontend` folder
3. Access at: `https://harrikrishnaa.github.io/VaultSense/`
