# Match this to `requires-python` / .python-version in pyproject.toml
FROM python:3.14-slim

# Install uv by copying the binary from its official image
# (pin a version instead of :latest once you're happy with the setup)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1) Install dependencies first. This layer is cached until
#    pyproject.toml or uv.lock change, which makes rebuilds fast.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# 2) Copy the project code and finish the install
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# 3) Collect static files (dummy values: settings only need to import)
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=sqlite:////tmp/build.db \
    python manage.py collectstatic --noinput

# Run as a non-root user
RUN useradd --system --no-create-home --home-dir /home/app app
# gunicorn's control server reads the user's home directory; it must exist
# and be writable by the app user.
RUN mkdir -p /home/app && chown -R app:app /home/app
# Directories the app must be able to write to at runtime: the ML artifacts
# (trained on first boot by the entrypoint) and collectstatic output.
RUN mkdir -p ml/artifacts staticfiles && chown -R app:app ml/artifacts staticfiles
USER app

# Prepare the database, import data, train the model if missing — then exec CMD.
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]