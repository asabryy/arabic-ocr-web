# app/services/local_storage.py

import os
from typing import IO, List
from fastapi import HTTPException
from app.core.config import settings
from app.schemas.document import DocumentInfo
from app.services.storage import FileStorage

class LocalFileStorage(FileStorage):
    def _user_path(self, user_id: str) -> str:
        path = os.path.join(settings.UPLOAD_DIR, user_id)
        os.makedirs(path, exist_ok=True)
        return path

    def save_file(self, user_id: str, filename: str, file_obj: IO) -> str:
        path = os.path.join(self._user_path(user_id), filename)
        with open(path, "wb") as f:
            f.write(file_obj.read())
        return path

    def list_files(self, user_id: str) -> List[DocumentInfo]:
        path = self._user_path(user_id)
        files = []
        for fname in os.listdir(path):
            full_path = os.path.join(path, fname)
            if os.path.isfile(full_path) and not fname.endswith(".settings.json"):
                stat = os.stat(full_path)
                files.append(DocumentInfo(
                    filename=fname,
                    size=stat.st_size,
                    last_modified=stat.st_mtime
                ))
        return files

    def delete_file(self, user_id: str, filename: str) -> None:
        path = os.path.join(self._user_path(user_id), filename)
        if os.path.exists(path):
            os.remove(path)
        else:
            raise HTTPException(status_code=404, detail="File not found")

    def get_path(self, user_id: str, filename: str) -> str:
        path = os.path.join(self._user_path(user_id), filename)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        return path
