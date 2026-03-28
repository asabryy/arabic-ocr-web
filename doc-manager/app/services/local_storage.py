import os
from typing import IO

from fastapi import HTTPException

from app.core.config import settings
from app.schemas.document import DocumentInfo
from app.services.storage import FileStorage

_SIDECAR_SUFFIXES = (".settings.json", ".status", ".docx")


class LocalFileStorage(FileStorage):
    def _user_path(self, user_id: str) -> str:
        path = os.path.join(settings.UPLOAD_DIR, user_id)
        os.makedirs(path, exist_ok=True)
        return path

    def _status_path(self, user_id: str, filename: str) -> str:
        return os.path.join(self._user_path(user_id), f"{filename}.status")

    def save_file(self, user_id: str, filename: str, file_obj: IO) -> str:
        path = os.path.join(self._user_path(user_id), filename)
        with open(path, "wb") as f:
            f.write(file_obj.read())
        self.set_status(user_id, filename, "pending")
        return path

    def list_files(self, user_id: str) -> list[DocumentInfo]:
        path = self._user_path(user_id)
        files = []
        for fname in os.listdir(path):
            if any(fname.endswith(suffix) for suffix in _SIDECAR_SUFFIXES):
                continue
            full_path = os.path.join(path, fname)
            if not os.path.isfile(full_path):
                continue
            stat = os.stat(full_path)
            files.append(DocumentInfo(
                filename=fname,
                size=stat.st_size,
                last_modified=stat.st_mtime,
                status=self.get_status(user_id, fname),
            ))
        return files

    def delete_file(self, user_id: str, filename: str) -> None:
        path = os.path.join(self._user_path(user_id), filename)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        os.remove(path)
        for suffix in _SIDECAR_SUFFIXES:
            sidecar = f"{path}{suffix}"
            if os.path.exists(sidecar):
                os.remove(sidecar)

    def get_path(self, user_id: str, filename: str) -> str:
        path = os.path.join(self._user_path(user_id), filename)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found")
        return path

    def file_exists(self, user_id: str, filename: str) -> bool:
        path = os.path.join(self._user_path(user_id), filename)
        return os.path.exists(path)

    def set_status(self, user_id: str, filename: str, status: str) -> None:
        with open(self._status_path(user_id, filename), "w") as f:
            f.write(status)

    def get_status(self, user_id: str, filename: str) -> str:
        path = self._status_path(user_id, filename)
        if not os.path.exists(path):
            return "pending"
        with open(path) as f:
            return f.read().strip()
