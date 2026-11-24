FROM python:3.12-slim

WORKDIR /work
COPY requirements.txt requirements-mcp.lock ./
# The offline Anthropic tests use an httpx transport.
RUN python3 -m pip install --no-cache-dir -r requirements.txt anthropic==0.109.1

# The shim and tests/test_secret_guard.py need the git program.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash tester
COPY . .
ENV PYTHONDONTWRITEBYTECODE=1
USER tester

# Prepare the shim cache at build time. The build has network. The test run has none.
RUN python3 -c "import sys; sys.path.insert(0, 'scripts'); import check_context as c; spec, commit = c.pinned(); c.ensure_environment(spec, commit)"

CMD ["bash"]
