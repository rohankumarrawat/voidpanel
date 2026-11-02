# ==============================================================================
# VOIDONYX CLOUD WORKSPACE — DOCKERFILE
# ==============================================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

EXPOSE 8000

CMD ["gunicorn", "voidpanel_project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
