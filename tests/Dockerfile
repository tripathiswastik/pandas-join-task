# Python Version: 3.11 (python:3.11-slim@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72)
# Purpose: Isolated verifier container running pytest suite and emitting CTRF JSON and reward scores.
# Runs-in: Verifier container (/tests) in isolated network-restricted separate environment mode.
FROM python:3.11-slim@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72

WORKDIR /app
RUN mkdir -p /app/data /app/output /logs/verifier

COPY requirements.txt /tests/requirements.txt
RUN pip install --no-cache-dir -r /tests/requirements.txt

WORKDIR /tests
COPY . /tests/
RUN chmod +x /tests/test.sh
