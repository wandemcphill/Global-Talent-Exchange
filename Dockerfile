FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/srv/gtex/backend

WORKDIR /srv/gtex

COPY backend/requirements.txt backend/requirements.txt

RUN pip install --upgrade pip \
    && pip install -r backend/requirements.txt

COPY backend ./backend

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "180"]

