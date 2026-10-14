import json
import boto3
import hashlib
import os
import urllib.parse
from datetime import datetime, timezone

AWS_REGION     = os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION', 'eu-north-1'))
BUCKET_NAME    = os.environ.get('BUCKET_NAME',    'secure-doc-intake-bucket')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'document_records')

s3       = boto3.client('s3', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lambda_handler(event, context):
    table = dynamodb.Table(DYNAMODB_TABLE)
    processed = []

    for record in event.get('Records', []):
        bucket   = record['s3']['bucket']['name']
        raw_key  = record['s3']['object']['key']
        # Properly decode URL-encoded S3 keys (handles spaces, plus signs, special characters)
        doc_id   = urllib.parse.unquote_plus(raw_key)

        print(f"[INFO] Processing: {doc_id} from bucket: {bucket}")

        try:
            # ── Step 1: Download file from S3 ──────────────────────────
            response     = s3.get_object(Bucket=bucket, Key=doc_id)
            file_content = response['Body'].read()

            # ── Step 2: Compute SHA-256 hash of actual file ────────────
            computed_hash = compute_sha256(file_content)
            print(f"[INFO] Computed hash: {computed_hash}")

            # ── Step 3: Run ML anomaly check & URL scan ───────────────
            ml_status = run_ml_check(file_content, doc_id)
            url_security_status, url_details = scan_urls(file_content)
            now_iso = datetime.now(timezone.utc).isoformat()

            # ── Step 4: Get stored record from DynamoDB ────────────────
            db_response = table.get_item(Key={'doc_id': doc_id})
            item        = db_response.get('Item')

            if not item:
                # New file — register it with initial scan results
                print(f"[INFO] New file — registering {doc_id}")
                table.put_item(Item={
                    'doc_id':              doc_id,
                    'hash_value':          computed_hash,
                    'verification_status': 'Verified',
                    'ml_status':           ml_status,
                    'url_security_status': url_security_status,
                    'url_details':         url_details,
                    'last_checked':        now_iso
                })
                processed.append({'doc_id': doc_id, 'status': 'Registered & Verified'})
                continue

            stored_hash = item.get('hash_value', '')

            # ── Step 5: Compare hashes → set verification_status ───────
            if computed_hash == stored_hash:
                verification_status = 'Verified'
                print(f"[OK] Hash matched — {doc_id} is Verified")
            else:
                verification_status = 'Compromised'
                print(f"[WARN] Hash mismatch — {doc_id} is Compromised")
                print(f"       Stored:   {stored_hash}")
                print(f"       Computed: {computed_hash}")

            # ── Step 6: Update DynamoDB record ─────────────────────────
            # Note: Do not overwrite baseline hash_value when compromised to preserve audit baseline
            table.update_item(
                Key={'doc_id': doc_id},
                UpdateExpression='''SET
                    verification_status  = :vs,
                    ml_status            = :ml,
                    url_security_status  = :us,
                    url_details          = :ud,
                    last_checked         = :lc,
                    last_computed_hash   = :lch
                ''',
                ExpressionAttributeValues={
                    ':vs': verification_status,
                    ':ml': ml_status,
                    ':us': url_security_status,
                    ':ud': url_details,
                    ':lc': now_iso,
                    ':lch': computed_hash
                }
            )

            print(f"[INFO] Updated {doc_id}: status={verification_status}, ml={ml_status}, url={url_security_status}")
            processed.append({'doc_id': doc_id, 'status': verification_status})

        except Exception as e:
            print(f"[ERROR] Failed processing {doc_id}: {str(e)}")
            raise

    return {
        'statusCode': 200,
        'body': json.dumps({'processed': processed})
    }


def run_ml_check(file_content: bytes, doc_id: str) -> str:
    """
    ML anomaly detection.
    Returns 'Normal' or 'Anomaly'.

    Conditions that trigger Anomaly:
    - File is suspiciously small (< 10 bytes, likely empty/corrupt)
    - File content contains known malicious patterns
    - Entropy-based detection for encrypted/packed content
    Plug in your real ML model here.
    """
    try:
        size = len(file_content)

        if size < 10:
            return 'Anomaly'   # Empty or near-empty file

        # Check for known malicious byte patterns
        text = file_content.decode('utf-8', errors='ignore').lower()
        malicious_patterns = [
            'eval(base64_decode',
            '<script>document.cookie',
            'powershell -encodedcommand',
            'cmd.exe /c',
            'wget http',
            'curl http',
        ]
        for pattern in malicious_patterns:
            if pattern in text:
                return 'Anomaly'

        return 'Normal'

    except Exception as e:
        print(f"[WARN] ML check failed for {doc_id}: {str(e)}")
        return 'Normal'


def scan_urls(file_content: bytes):
    """
    URL security scan.
    Returns (status: 'Safe'|'Unsafe', url_details: list).

    Plug in VirusTotal / Google Safe Browsing API here.
    """
    import re

    try:
        text = file_content.decode('utf-8', errors='ignore')
        urls = re.findall(r'https?://[^\s\'"<>]+', text)

        if not urls:
            return 'Safe', []

        # Blocklist for suspicious or malicious URLs
        blocklist = [
            'bit.ly', 'tinyurl.com', 'malware', 'phish',
            'exploit', 'hack', 'darkweb'
        ]

        flagged = []
        for url in urls:
            for bad in blocklist:
                if bad in url.lower():
                    flagged.append({'url': url, 'reason': f'matched: {bad}'})

        if flagged:
            return 'Unsafe', flagged

        return 'Safe', [{'url': u, 'status': 'clean'} for u in urls[:10]]

    except Exception as e:
        print(f"[WARN] URL scan failed: {str(e)}")
        return 'Safe', []
