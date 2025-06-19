# Use a modern Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set the working directory in the container
WORKDIR /app

# Copy the entire project into the container
COPY . .

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Add the virtual environment's bin to the PATH
    PATH="/app/.venv/bin:$PATH"

# Create a virtual environment and install dependencies from the lock file
# This leverages Docker's build cache for faster builds.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv && \
    uv sync --no-dev

# Install tini, a lightweight init system for containers, to handle signals properly
RUN apt-get update && \
    apt-get install -y --no-install-recommends tini && \
    rm -rf /var/lib/apt/lists/*

# Expose the port the app will run on
EXPOSE 8000

# Set tini as the entrypoint to properly manage the application process
ENTRYPOINT ["/usr/bin/tini", "--"]

# Command to run the application using Gunicorn, a production-ready WSGI server
CMD ["gunicorn", "--workers", "4", "--worker-class", "gevent", "--bind", "0.0.0.0:8000", "api.app:app"]