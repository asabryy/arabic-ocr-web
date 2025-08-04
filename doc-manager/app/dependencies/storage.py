from app.services.local_storage import LocalFileStorage
from app.services.r2_storage import R2FileStorage
from app.core.config import settings

def get_storage():
    if settings.STORAGE_BACKEND == "r2":
        from app.services.r2_storage import R2FileStorage
        return R2FileStorage()
    else:
        from app.services.local_storage import LocalFileStorage
        return LocalFileStorage()