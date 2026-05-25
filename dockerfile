FROM python:3.13-slim

RUN apt-get update && apt-get install -y git gcc libffi-dev

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install pytest responses

EXPOSE 5000
