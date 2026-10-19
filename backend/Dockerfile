FROM python:3.11-slim


ENV PYTHONDONTWRITEBYTECODE=1 \
     PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
     && pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the application without root privileges.
RUN useradd --system --create-home --home-dir /home/cspm \
    --shell /usr/sbin/nologin cspm \
    && chown -R cspm:cspm /app

 EXPOSE 8000

USER cspm

 CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]