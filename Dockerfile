FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements/base/base.txt .
RUN pip install --upgrade pip \
    && pip install -r base.txt

COPY main.py .
COPY controllers/ controllers/
COPY models/ models/
COPY util/ util/

RUN groupadd --system app && useradd --system --gid app --no-create-home --shell /usr/sbin/nologin app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/', timeout=2)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
