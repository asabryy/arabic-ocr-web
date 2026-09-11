from abc import ABC, abstractmethod
from typing import IO


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
