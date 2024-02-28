FROM python:3.9-slim

WORKDIR /bot
COPY . /bot/
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
CMD ["python3", "-u", "/bot/main.py"]
