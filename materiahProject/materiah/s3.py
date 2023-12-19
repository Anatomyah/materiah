import boto3
from botocore.exceptions import ClientError
from django.conf import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_S3_REGION_NAME
)


def create_presigned_post(object_name, file_type, bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                          expiration=3600):
    """
    :param object_name: (str) The name of the object to be uploaded.
    :param file_type: (str) The type of the file to be uploaded.
    :param bucket_name: (str) The name of the bucket where the object will be uploaded. Defaults to the value set in the AWS_STORAGE_BUCKET_NAME setting.
    :param expiration: (int) The time in seconds until the presigned URL expires. Defaults to 3600 seconds (1 hour).
    :return: (dict) A dictionary containing the presigned URL and the form fields required for the upload.

    This method generates a presigned URL and form fields for uploading a file to Amazon S3.

    The `object_name` parameter specifies the name of the object (file) to be uploaded.
    The `file_type` parameter specifies the MIME type of the file.
    The `bucket_name` parameter specifies the name of the bucket where the object will be uploaded. If not provided, it defaults to the value set in the AWS_STORAGE_BUCKET_NAME setting.
    The `expiration` parameter specifies the time in seconds until the presigned URL expires. If not provided, it defaults to 3600 seconds (1 hour).

    The method generates the Content-Disposition and Content-Type fields, which are required for the upload.
    It also generates a set of conditions to be applied to the presigned URL, including a condition on the Content-Disposition and an additional condition specifying that the Content-Type
    * must start with the provided file type.

    Once the presigned URL and form fields are generated, the method attempts to generate the presigned post using the `s3_client` specified in the code.
    If an error occurs during this process, a `ClientError` exception will be raised.

    The method returns a dictionary containing the presigned URL and the form fields required for the upload.
    """
    # Prepare the 'Fields' dictionary with the Content-Disposition and ContentType fields. These will get posted
    # along in the form-data while making the presigned POST request, which tells AWS how to handle the content being uploaded.
    fields = {
        "Content-Disposition": f"inline; filename=\"{object_name}\"",
        "Content-Type": file_type
    }

    # Prepare a list of conditions. These conditions must be met for this presigned POST request to be valid.
    # Here, a specific Content-Disposition is required and also the Content-Type is required to start with the given file_type.
    conditions = [
        {"Content-Disposition": f"inline; filename=\"{object_name}\""},
        ["starts-with", "$Content-Type", file_type]
    ]

    try:
        # Use the AWS S3 client to create the presigned post. It takes in the bucket_name, object_name (the name under
        # which the new object will be stored), Fields, Conditions, and the expiration time of the URL.
        # It generates a presigned POST URL along with the corresponding required fields as a dictionary.
        response = s3_client.generate_presigned_post(bucket_name,
                                                     object_name,
                                                     Fields=fields,
                                                     Conditions=conditions,
                                                     ExpiresIn=expiration)
    except ClientError as e:
        # If there's an error during the creation of presigned post, raise the client error.
        raise

    # Return the presigned post URL and required fields as a dictionary.
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
