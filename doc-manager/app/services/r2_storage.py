import time
from typing import IO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.core.config import settings
from app.schemas.document import DocumentInfo
from app.services.storage import FileStorage

_SIDECAR_SUFFIXES = (".settings.json", ".status", ".docx")


class R2FileStorage(FileStorage):
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=settings.R2_ENDPOINT_URL,
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            config=Config(signature_version="s3v4"),
        )
        self.bucket = settings.R2_BUCKET_NAME

    def _key(self, user_id: str, filename: str) -> str:
        return f"{user_id}/{filename}"

    def _status_key(self, user_id: str, filename: str) -> str:
        return f"{user_id}/{filename}.status"

    def save_file(self, user_id: str, filename: str, file_obj: IO) -> str:
        key = self._key(user_id, filename)
        self.s3.upload_fileobj(file_obj, self.bucket, key)
        self.set_status(user_id, filename, "pending")
        return key

    def list_files(self, user_id: str) -> list[DocumentInfo]:
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=f"{user_id}/")
        contents = response.get("Contents", [])
        files = []
        for obj in contents:
            fname = obj["Key"].split("/", 1)[-1]
            if any(fname.endswith(suffix) for suffix in _SIDECAR_SUFFIXES):
                continue
            files.append(DocumentInfo(
                filename=fname,
                size=obj["Size"],
                last_modified=time.mktime(obj["LastModified"].timetuple()),
                status=self.get_status(user_id, fname),
            ))
        return files

    def delete_file(self, user_id: str, filename: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=self._key(user_id, filename))
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=self._status_key(user_id, filename))
        except ClientError:
            pass

    def get_path(self, user_id: str, filename: str) -> str:
        key = self._key(user_id, filename)
        try:
            return self.s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=3600,
            )
        except ClientError:
            raise HTTPException(status_code=404, detail="File not found")

    def file_exists(self, user_id: str, filename: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=self._key(user_id, filename))
            return True
        except ClientError:
            return False

    def set_status(self, user_id: str, filename: str, status: str) -> None:
        self.s3.put_object(
            Bucket=self.bucket,
            Key=self._status_key(user_id, filename),
            Body=status.encode(),
        )

    def get_status(self, user_id: str, filename: str) -> str:
        try:
            obj = self.s3.get_object(Bucket=self.bucket, Key=self._status_key(user_id, filename))
            return obj["Body"].read().decode().strip()
        except ClientError:
            return "pending"
