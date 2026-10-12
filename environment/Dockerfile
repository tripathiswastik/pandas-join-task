# Python Version: 3.11 (python:3.11-slim@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72)
# Purpose: Execution runtime sandbox for candidate agent solving the pandas pipeline reconciliation challenge.
# Runs-in: Agent execution container (/app) under Terminal-Bench separate environment mode.
FROM python:3.11-slim@sha256:d1053354624536b044162aaab1e418bd000ea35184fb1ae098ab3166b1072e72

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tmux asciinema \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pandas==2.2.2 numpy==1.26.4 pytest==8.3.2 pytest-json-ctrf==0.3.7

COPY app/ /app/

RUN mkdir -p /app/output

CMD ["/bin/bash"]
