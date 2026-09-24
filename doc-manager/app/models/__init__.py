"""Importing the package registers doc-manager's tables on the shared MetaData."""

from app.models import conversion_attempt  # noqa: F401

__all__ = ["conversion_attempt"]
