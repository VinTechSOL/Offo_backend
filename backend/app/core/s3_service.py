import boto3
import uuid
from botocore.exceptions import NoCredentialsError, ClientError
from app.core.config import settings


# -------------------------------------------------
# CREATE S3 CLIENT (LOCAL + AWS IAM ROLE SUPPORT)
# -------------------------------------------------

def get_s3_client():

    """
    Creates an S3 client that works in both:
    - Local development (using .env credentials)
    - AWS production (using IAM role)
    """

    if getattr(settings, "AWS_ACCESS_KEY_ID", None) and getattr(settings, "AWS_SECRET_ACCESS_KEY", None):

        # Local development using .env credentials
        return boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

    # Production (EC2 / ECS / Lambda IAM Role)
    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
    )


s3 = get_s3_client()
BUCKET_NAME = settings.S3_BUCKET


# -------------------------------------------------
# GENERIC IMAGE UPLOAD
# -------------------------------------------------

def upload_image(
    *,
    file_obj,
    filename: str | None,
    content_type: str,
    folder: str,
) -> str | None:

    """
    Upload file to S3 inside a folder.

    Example keys:
        cafe/uuid.jpg
        menu/uuid.png
    """

    try:

        # Extract extension
        if filename and "." in filename:
            ext = filename.split(".")[-1]
        else:
            ext = "jpg"

        unique_filename = f"{uuid.uuid4()}.{ext}"

        key = f"{folder}/{unique_filename}"

        s3.upload_fileobj(
            file_obj,
            BUCKET_NAME,
            key,
            ExtraArgs={
                "ContentType": content_type,
            },
        )

        return f"https://{BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"

    except NoCredentialsError:

        # Local dev safety fallback
        print("⚠️ AWS credentials not found. Skipping upload.")
        return None

    except ClientError as e:

        raise Exception(f"S3 Upload Failed: {str(e)}")


# -------------------------------------------------
# DELETE FILE FROM S3
# -------------------------------------------------

def delete_file(file_url: str):

    """
    Delete a file from S3 using its URL
    """

    try:

        if not file_url:
            return

        key = file_url.split(
            f"{BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/"
        )[1]

        s3.delete_object(
            Bucket=BUCKET_NAME,
            Key=key,
        )

    except Exception as e:
        print(f"S3 Delete failed: {str(e)}")