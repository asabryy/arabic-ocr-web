# Importing a model module registers its table on Base.metadata. conversion_attempt
# is listed here because alembic/env.py imports only billing/usage/user by name.
from app.models import conversion_attempt  # noqa: F401
