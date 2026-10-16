"""SQS-triggered AWS Lambda image thumbnail processor.

Expected SQS body: an Amazon S3 ObjectCreated notification.
Set SOURCE_BUCKET and DEST_BUCKET environment variables.
Package Pillow for the Lambda runtime/architecture before deployment.
"""
import json
import os
import urllib.parse
import logging
from io import BytesIO

import boto3
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
SOURCE_BUCKET = os.environ.get("SOURCE_BUCKET", "")
DEST_BUCKET = os.environ.get("DEST_BUCKET", "")
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 25_000_000
THUMBNAIL_SIZE = (300, 300)


def is_allowed_source_key(key: str) -> bool:
    """Only process objects uploaded to the incoming/ prefix."""
    return key.startswith("incoming/") and not key.endswith("/")


def process_record(record: dict) -> dict:
    body = json.loads(record["body"])

    # S3 may send a test event when notification configuration is created.
    if body.get("Event") == "s3:TestEvent":
        return {"status": "ignored-test-event"}

    results = []
    for item in body.get("Records", []):
        if not item.get("eventName", "").startswith("ObjectCreated:"):
            continue

        source_bucket = item["s3"]["bucket"]["name"]
        source_key = urllib.parse.unquote_plus(item["s3"]["object"]["key"])

        if SOURCE_BUCKET and source_bucket != SOURCE_BUCKET:
            raise ValueError("Unexpected source bucket")
        if not is_allowed_source_key(source_key):
            logger.info("Ignoring key outside incoming/ prefix")
            continue

        obj = s3.get_object(Bucket=source_bucket, Key=source_key)
        if obj.get("ContentLength", 0) > MAX_INPUT_BYTES:
            raise ValueError("Input image exceeds 10 MiB limit")

        raw = obj["Body"].read()
        try:
            with Image.open(BytesIO(raw)) as image:
                if image.format not in ALLOWED_FORMATS:
                    raise ValueError("Unsupported image format")
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError("Image pixel count exceeds limit")
                image.thumbnail(THUMBNAIL_SIZE)
                if image.mode not in ("RGB", "L"):
                    image = image.convert("RGB")
                output = BytesIO()
                image.save(output, format="JPEG", quality=85, optimize=True)
        except UnidentifiedImageError as exc:
            raise ValueError("Uploaded file is not a valid supported image") from exc

        destination_key = "thumbnails/" + source_key[len("incoming/"):]
        if not destination_key.lower().endswith((".jpg", ".jpeg")):
            destination_key += ".jpg"

        s3.put_object(
            Bucket=DEST_BUCKET,
            Key=destination_key,
            Body=output.getvalue(),
            ContentType="image/jpeg",
            ServerSideEncryption="AES256",
        )
        results.append({
            "source": f"s3://{source_bucket}/{source_key}",
            "thumbnail": f"s3://{DEST_BUCKET}/{destination_key}",
        })

    logger.info("Processed %d image(s)", len(results))
    return {"processed": results}


def lambda_handler(event, context):
    if not DEST_BUCKET:
        raise RuntimeError("DEST_BUCKET environment variable is required")

    results = []
    for record in event.get("Records", []):
        # SQS-triggered Lambda records are handled one at a time. With batch size 1,
        # raising an exception allows SQS redrive/DLQ handling to work predictably.
        results.append(process_record(record))
    return {"batchItemFailures": [], "results": results}
