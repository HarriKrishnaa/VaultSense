import json
import boto3
import base64
import uuid
import mimetypes

s3 = boto3.client('s3')

BUCKET_NAME = "secure-doc-intake-bucket"   # eu-north-1 ✓

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS'
}


def lambda_handler(event, context):

    # ── Handle CORS preflight ──────────────────────────────────────
    http_method = (
        event.get('httpMethod')                                   # REST API
        or event.get('requestContext', {})
               .get('http', {})
               .get('method', '')                                 # HTTP API v2
    )

    if http_method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }

    # ── Parse body ────────────────────────────────────────────────
    try:
        raw_body = event.get('body', '{}')

        # API Gateway can base64-encode the body itself
        if event.get('isBase64Encoded', False):
            raw_body = base64.b64decode(raw_body).decode('utf-8')

        body = json.loads(raw_body)

    except Exception as e:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({"error": f"Invalid request body: {str(e)}"})
        }

    # ── Validate payload ──────────────────────────────────────────
    if 'file' not in body:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({"error": "Missing 'file' field (base64 encoded content)"})
        }

    # ── Decode file content ───────────────────────────────────────
    try:
        file_content = base64.b64decode(body['file'])
    except Exception as e:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({"error": f"Failed to decode base64 file: {str(e)}"})
        }

    # ── Determine file name and content type ──────────────────────
    file_name    = body.get('fileName', str(uuid.uuid4()))
    content_type = body.get('contentType', None)

    # Auto-detect content type from file extension if not provided
    if not content_type:
        guessed, _ = mimetypes.guess_type(file_name)
        content_type = guessed or 'application/octet-stream'

    # ── Upload to S3 ──────────────────────────────────────────────
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,                    # saved as-is in the bucket root
            Body=file_content,
            ContentType=content_type,
            Metadata={
                'uploaded-by': 'vaultsense-dashboard',
                'original-name': file_name
            }
        )

        # Build the S3 URI for confirmation
        s3_uri = f"s3://{BUCKET_NAME}/{file_name}"

        print(f"[OK] Uploaded '{file_name}' ({len(file_content)} bytes) -> {s3_uri}")

        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                "message": "File uploaded successfully",
                "file": file_name,
                "s3_uri": s3_uri,
                "bucket": BUCKET_NAME,
                "size_bytes": len(file_content),
                "content_type": content_type
            })
        }

    except s3.exceptions.NoSuchBucket:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({"error": f"Bucket '{BUCKET_NAME}' does not exist"})
        }

    except Exception as e:
        print(f"[ERROR] S3 upload failed: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({"error": str(e)})
        }
