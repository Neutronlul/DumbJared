# syntax=docker/dockerfile:1

FROM debian:bookworm-slim AS base


# First, build python in the `/python` directory and set up uv flags
FROM base AS pybuilder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

# Install Python to /python before the project for caching
RUN --mount=type=bind,source=.python-version,target=.python-version \
    uv python install $(cat .python-version)

# Define where the virtual environment will be created in dev/prodbuilder
WORKDIR /venv


FROM pybuilder AS devbuilder

# Install dependencies, only when needed
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy the appropriate entrypoint script
COPY entrypoint.dev.sh /entrypoint/


FROM pybuilder AS prodbuilder

# Install dependencies, only when needed
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev --group prod

# Copy the appropriate entrypoint script
COPY entrypoint.prod.sh /entrypoint/


# Copy the application code into an independent stage to avoid cache invalidation
FROM base AS source

COPY --exclude=entrypoint.*.sh \
     --exclude=pyproject.toml \
     --exclude=uv.lock \
     --exclude=.python-version \
     . /app


# Define the deployment-agnostic configuration
FROM base AS runtime

# Setup a non-root user
RUN groupadd --system --gid 10001 nonroot \
 && useradd --system --gid 10001 --uid 10001 --create-home nonroot

# Copy the Python installation
COPY --from=pybuilder --chown=python:python /python /python

# Place executables in the environment at the front of the path
ENV PATH="/venv/.venv/bin:$PATH"

# Set environment variable to indicate running in a container
# Currently only used to switch database settings
ENV IN_CONTAINER=1

# Use the non-root user to run our application
USER nonroot

# Use `/app` as the working directory
WORKDIR /app

# Expose the application port (same for dev and prod)
EXPOSE 8000


FROM runtime AS dev

# Copy in the virtual environment
COPY --from=devbuilder --chown=nonroot:nonroot /venv /venv

# Copy the appropriate entrypoint from the builder
COPY --from=devbuilder --chown=nonroot:nonroot \
     /entrypoint/entrypoint.dev.sh /usr/local/bin/entrypoint.dev.sh

# Copy the application from the source stage
COPY --from=source --chown=nonroot:nonroot /app /app

ENTRYPOINT [ "/usr/local/bin/entrypoint.dev.sh" ]

CMD [ "python", "manage.py", "runserver", "0.0.0.0:8000" ]


FROM runtime AS prod

# Copy in the virtual environment
COPY --from=prodbuilder --chown=nonroot:nonroot /venv /venv

# Copy the appropriate entrypoint from the builder
COPY --from=prodbuilder --chown=nonroot:nonroot \
     /entrypoint/entrypoint.prod.sh /usr/local/bin/entrypoint.prod.sh

# Copy the application from the source stage
COPY --from=source --chown=nonroot:nonroot /app /app

# Create directory for gunicorn socket
RUN mkdir -p /app/socket

# Bake static files into the image
RUN python manage.py collectstatic --noinput

ENTRYPOINT [ "/usr/local/bin/entrypoint.prod.sh" ]

CMD [ "gunicorn", "config.wsgi", "--bind=unix:/app/socket/gunicorn.sock", "--workers=3" ]