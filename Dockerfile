FROM python:3.9-alpine

WORKDIR /bot
COPY . /bot/
RUN sudo apt-get install python-dev
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONUNBUFFERED=1
CMD ["python3", "-u", "/bot/main.py"]
