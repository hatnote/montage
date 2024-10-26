FROM python:3.9-slim

RUN apt-get update && apt-get install -y git

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 5000

# Start the application
CMD ["bash", "-c", "export PYTHONPATH=/app && python tools/create_schema.py && python -m montage"]