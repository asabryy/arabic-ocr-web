# auth-service/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ✅ Install Alembic (in case it's not in requirements.txt)
RUN pip install alembic

# ✅ Copy all app code
COPY ./app ./app

# ✅ Copy Alembic config and migration scripts
COPY ./alembic.ini ./alembic.ini
COPY ./alembic ./alembic

# Optional: Verify files are copied
RUN echo "Copied alembic.ini and alembic folder"

# Expose port (for FastAPI — not needed for Alembic job)
EXPOSE 8000

# Default command for app containers (not used for Alembic job)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
