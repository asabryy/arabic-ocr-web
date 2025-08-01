from abc import ABC, abstractmethod
from typing import IO, List, Protocol

# Avoid importing DocumentInfo to prevent circular import

class FileLike(Protocol):
    def read(self) -> bytes: ...

class FileStorage(ABC):
    @abstractmethod
    def save_file(self, user_id: str, filename: str, file_obj: IO) -> str:
        pass

    @abstractmethod
    def list_files(self, user_id: str) -> List[dict]:  # Return dict instead of DocumentInfo
        pass

    @abstractmethod
    def delete_file(self, user_id: str, filename: str) -> None:
        pass

    @abstractmethod
    def get_path(self, user_id: str, filename: str) -> str:
        pass