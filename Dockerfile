FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=12321 \
    FLASK_APP=run.py

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY run.py ./

RUN mkdir -p /app/uploads/licenses /app/uploads/third_party /app/uploads/factory /app/uploads/exports /app/instance

VOLUME ["/app/uploads", "/app/instance"]

EXPOSE 12321

CMD ["python", "run.py"]
