from abc import ABC, abstractmethod
from typing import IO

from fastapi import HTTPException


def safe_name(name: str) -> str:
    """Reject anything that could escape its owner's prefix.

    `filename` reaches storage straight from a query string or a multipart header.
    Without this, `../2/secret.pdf` resolves into another user's directory — a
    cross-user read on local storage, and a cross-user write on any backend.
    Applied at the storage seam so no endpoint can forget it.
    """
    if not name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    # Covers "../x", "a/../../x", backslashes on any host, absolute paths, and NULs.
    if "/" in name or "\\" in name or "\x00" in name or name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


def safe_user_id(user_id: str) -> str:
    """Owner prefixes are ints or `trial/<uuid>`; nothing else may reach a path."""
    uid = str(user_id)
    if uid.startswith("trial/"):
        token = uid[len("trial/"):]
        if not token.isalnum():
            raise HTTPException(status_code=400, detail="Invalid owner")
        return uid
    if not uid.isdigit():
        raise HTTPException(status_code=400, detail="Invalid owner")
    return uid



class FileStorage(ABC):
    @abstractmethod
    def save_file(self, user_id: str, filename: str, file_obj: IO) -> str:
        pass

    @abstractmethod
    def list_files(self, user_id: str) -> list[dict]:
        pass

    @abstractmethod
    def delete_file(self, user_id: str, filename: str) -> None:
        pass

    @abstractmethod
    def get_path(self, user_id: str, filename: str) -> str:
        pass

    @abstractmethod
    def file_exists(self, user_id: str, filename: str) -> bool:
        pass

    @abstractmethod
    def set_status(self, user_id: str, filename: str, status: str) -> None:
        pass

    @abstractmethod
    def get_status(self, user_id: str, filename: str) -> str:
        pass

    @abstractmethod
    def save_meta(self, user_id: str, filename: str, meta: dict) -> None:
        """Persist small JSON metadata (e.g. page count) as a sidecar next to the file."""

    @abstractmethod
    def get_meta(self, user_id: str, filename: str) -> dict:
        """Return the sidecar metadata, or {} if none was saved."""
