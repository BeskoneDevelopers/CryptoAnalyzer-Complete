FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd -m appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/staticfiles \
    && chown -R appuser:appuser /app

USER appuser

CMD ["gunicorn", "crypto_analyzer_app.wsgi:application", "--bind", "0.0.0.0:8000"]
