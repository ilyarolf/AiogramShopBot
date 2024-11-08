FROM python:3.9-slim

WORKDIR /bot
COPY . .
RUN apt-get update && apt-get upgrade -y
RUN apt-get install -y gcc
RUN apt-get install -y sqlcipher
RUN apt-get install libsqlcipher-dev
RUN rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "run.py"]