# syntax=docker/dockerfile:1

# 1. Start from an official image that already contains Python.
FROM python:3.12-slim

# 2. Python settings: no .pyc files, and print logs immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 3. All following commands run inside /app in the container.
WORKDIR /app

# 4. Copy ONLY requirements first, so Docker can cache the install step.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the project (anything in .dockerignore is skipped).
COPY . .

# 6. Run as a normal user instead of root (safer).
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# 7. Document the port the app listens on.
EXPOSE 5000

# 8. The command that starts the app. "app:app" = file app.py, variable app.
#    One worker only, because tokens and data are stored in memory.
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "1"]
