from app.core.config import settings
from app.services.storage import FileStorage


def get_storage() -> FileStorage:
    if settings.STORAGE_BACKEND == "r2":
        from app.services.r2_storage import R2FileStorage
        return R2FileStorage()
    from app.services.local_storage import LocalFileStorage
    return LocalFileStorage()
