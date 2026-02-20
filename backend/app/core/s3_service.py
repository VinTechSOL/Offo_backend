import boto3
import uuid
from botocore.exceptions import NoCredentialsError, ClientError
from app.core.config import settings


# -------------------------------------------------
# S3 CLIENT
# -------------------------------------------------

s3 = boto3.client(
    "s3",
    region_name=settings.AWS_REGION,
)

BUCKET_NAME = settings.S3_BUCKET


# -------------------------------------------------
# GENERIC UPLOAD FUNCTION
# -------------------------------------------------

def upload_image(
    *,
    file_obj,
    filename: str | None,
    content_type: str,
    folder: str,
) -> str:
    """
    Upload file to S3 inside a specific folder.

    Example:
        folder="menu"  -> menu/uuid.jpg
        folder="cafe"  -> cafe/uuid.jpg
    """

    try:
        # If filename not provided, generate one
        if not filename:
            filename = str(uuid.uuid4())

        key = f"{folder}/{filename}"

        s3.upload_fileobj(
            file_obj,
            BUCKET_NAME,
            key,
            ExtraArgs={
                "ContentType": content_type,
            },
        )

        file_url = f"https://{BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

        return file_url

    except NoCredentialsError:
        raise Exception("AWS credentials not configured properly")

    except ClientError as e:
        raise Exception(f"S3 Upload Failed: {str(e)}")


# -------------------------------------------------
# OPTIONAL: DELETE FILE (Good for future)
# -------------------------------------------------

def delete_file(file_url: str):
    """
    Deletes a file from S3 using its full URL.
    """
    try:
        # Extract key from URL
        key = file_url.split(f"{BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/")[1]

        s3.delete_object(
            Bucket=BUCKET_NAME,
            Key=key,
        )

    except Exception:
        pass