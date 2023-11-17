import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from django.conf import settings
import os

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)


def create_presigned_post(object_name, file_type, bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                          expiration=3600):
    """
    Generate a presigned URL S3 POST request to upload a file

    :param bucket_name: String.
    :param object_name: String.
    :param fields: Dictionary of prefilled form fields.
    :param conditions: List of conditions to include in the policy.
    :param expiration: Time in seconds for the presigned URL to remain valid.
    :return: Dictionary with the URL and fields needed for the POST operation. If error, returns None.
    """
    fields = {
        "Content-Disposition": f"inline; filename=\"{object_name}\"",
        "Content-Type": file_type
    }
    conditions = [
        {"Content-Disposition": f"inline; filename=\"{object_name}\""},
        ["starts-with", "$Content-Type", file_type]
    ]
    try:
        response = s3_client.generate_presigned_post(bucket_name,
                                                     object_name,
                                                     Fields=fields,
                                                     Conditions=conditions,
                                                     ExpiresIn=expiration)
    except ClientError as e:
        raise

    return response


def delete_s3_object(object_key, bucket_name=settings.AWS_STORAGE_BUCKET_NAME):
    """
    Delete an object from an S3 bucket

    :param bucket_name: String. The name of the S3 bucket.
    :param object_key: String. The key of the object to delete.
    :return: Boolean. True if deletion was successful, False otherwise.
    """
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
    except ClientError as e:
        raise

    return True
