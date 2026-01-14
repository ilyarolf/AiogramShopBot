FROM python:3.12-slim

WORKDIR /bot
COPY . .
RUN rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "run.py"]