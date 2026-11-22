FROM python:3.12-slim

WORKDIR /work
COPY requirements.txt requirements-mcp.lock ./
# The offline Anthropic tests use an httpx transport.
RUN python3 -m pip install --no-cache-dir -r requirements.txt anthropic==0.109.1

RUN useradd --create-home --shell /bin/bash tester
COPY . .
ENV PYTHONDONTWRITEBYTECODE=1
USER tester

CMD ["bash"]
