import boto3

s3_client = boto3.client("s3", aws_access_key_id="", aws_secret_access_key="")

bucket_name = "materiah"


def save_buckets_objects(folder: str, bucket_name: str):
    bucket = s3_client.list_objects_v2(Bucket=bucket_name)

    for obj in bucket.get("Contents", []):
        obj_key = obj['Key']
        if obj_key[-1] == "/":
            continue
        s3_client.download_file(Bucket=bucket, Key=obj_key, FileName=rf"{folder}\{obj_key}")


filename = r"file path"
s3_client.upload_file(Filename=filename, Bucket="bucket_name", Key="foldername/filename")

s3_client.delete_object(Bukcet="buckt_name", Key="file path")


def create_psurl(bucket_name, key, maxsize=4000):
    s3_client.generate_presigned_url('put', Params={'Bucket': bucket_name, 'Key': key, 'ContentLength': maxsize,
                                                    'ContentType': ''}, ExpireIn=15 * 60)


# FOR DJANGO STORAGES - branch storages in FSORI:
AWS_ACCESS_KEY_ID = ""
AWS_SECRET_ACCESS_KEY = ""
AWS_STORAGE_BUCKET_NAME = ""
AWS_S3_REGION_NAME = ""
AWS_DEFAULT_ACL = "public-read"

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto'

# DEFINE MODEL IN DJANGO MODELS

# class GeneralFile(models.model):
#     title = "charfield model"
#     file = "filefield model"
