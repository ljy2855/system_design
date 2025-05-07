FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file into the container
COPY uv.lock pyproject.toml ./

RUN pip install --no-cache-dir uv==0.6.3 && \
    uv sync

# Copy the rest of the application code into the container
COPY . .

CMD ["uv", "run", "uvicorn", "--host", "0.0.0.0", "--port", "8000", "main:app"]