FROM python:3.9-slim

RUN apt-get update && apt-get install -y git

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip

# Remove the py3votecore line from requirements.txt before installing
RUN grep -v "python3_vote_core" requirements.txt > requirements_filtered.txt && \
    pip install -r requirements_filtered.txt

# Install the python-vote-core package with the correct egg name
RUN pip install git+https://github.com/the-maldridge/python-vote-core.git@f0b01e7e24f80673c4c237ee9e6118e8986cf0bb#egg=python3_vote_core

EXPOSE 5000
