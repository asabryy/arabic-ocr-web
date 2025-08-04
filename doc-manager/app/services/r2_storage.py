# app/services/r2_storage.py

import boto3
from botocore.exceptions import ClientError
from typing import IO, List
from app.schemas.document import DocumentInfo
from app.services.storage import FileStorage
from fastapi import HTTPException
from app.core.config import settings
import os
import time

class R2FileStorage(FileStorage):
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        )
        self.bucket = settings.R2_BUCKET_NAME

    def _key(self, user_id: str, filename: str) -> str:
        return f"{user_id}/{filename}"

    def save_file(self, user_id: str, filename: str, file_obj: IO) -> str:
        key = self._key(user_id, filename)
        self.s3.upload_fileobj(file_obj, self.bucket, key)
        return key

    def list_files(self, user_id: str) -> List[DocumentInfo]:
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=f"{user_id}/")
        contents = response.get("Contents", [])
        return [
            DocumentInfo(
                filename=obj["Key"].split("/", 1)[-1],
                size=obj["Size"],
                last_modified=time.mktime(obj["LastModified"].timetuple())
            )
            for obj in contents if not obj["Key"].endswith(".settings.json")
        ]

    def delete_file(self, user_id: str, filename: str) -> None:
        key = self._key(user_id, filename)
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    def get_path(self, user_id: str, filename: str) -> str:
        key = self._key(user_id, filename)
        try:
            url = self.s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=3600
            )
            return url
        except ClientError:
            raise HTTPException(status_code=404, detail="File not found")
