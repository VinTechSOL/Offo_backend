import boto3
import uuid
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import HTTPException, UploadFile

from app.core.config import settings


# -------------------------------------------------
# CREATE S3 CLIENT (LOCAL + AWS IAM ROLE SUPPORT)
# -------------------------------------------------

def get_s3_client():
    """
    Creates an S3 client that works in both:
    - Local development (.env credentials)
    - AWS production (IAM Role)
    """

    if (
        getattr(settings, "AWS_ACCESS_KEY_ID", None)
        and getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
    ):
        return boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

    return boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
    )


s3 = get_s3_client()
BUCKET_NAME = settings.S3_BUCKET


# -------------------------------------------------
# FILE VALIDATION CONFIG
# -------------------------------------------------

IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

DOCUMENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_IMAGE_SIZE = 5 * 1024 * 1024       # 5 MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024   # 10 MB


# -------------------------------------------------
# VALIDATE FILE
# -------------------------------------------------

def validate_upload(
    file: UploadFile,
    *,
    allowed_types: set[str],
    max_size: int,
):
    """
    Validate uploaded file type and size.
    """

    if not file:
        return

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}",
        )

    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)

    if size > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum allowed size is {max_size // (1024 * 1024)} MB.",
        )


# -------------------------------------------------
# GENERIC FILE UPLOAD
# -------------------------------------------------

def upload_file(
    *,
    file_obj,
    filename: str | None,
    content_type: str,
    folder: str,
) -> str | None:
    """
    Upload any file (image/pdf/etc.) to S3.

    Example:
        branches/images/
        branches/documents/fssai/
        menu/
    """

    try:

        if filename and "." in filename:
            ext = filename.rsplit(".", 1)[1]
        else:
            ext = "bin"

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

        return (
            f"https://{BUCKET_NAME}.s3."
            f"{settings.AWS_REGION}.amazonaws.com/{key}"
        )

    except NoCredentialsError:
        print("⚠️ AWS credentials not found. Skipping upload.")
        return None

    except ClientError as e:
        raise Exception(f"S3 Upload Failed: {str(e)}")


# -------------------------------------------------
# DELETE FILE
# -------------------------------------------------

def delete_file(file_url: str | None):
    """
    Delete file from S3 using its generated S3 URL.
    """

    if not file_url:
        return

    try:
        prefix = (
            f"https://{BUCKET_NAME}.s3."
            f"{settings.AWS_REGION}.amazonaws.com/"
        )

        if not file_url.startswith(prefix):
            print("Invalid S3 file URL. Skipping delete.")
            return

        key = file_url[len(prefix):]

        if not key:
            return

        s3.delete_object(
            Bucket=BUCKET_NAME,
            Key=key,
        )

    except ClientError as e:
        print(f"S3 Delete failed: {str(e)}")