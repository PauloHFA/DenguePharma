FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir --no-deps .
RUN useradd --create-home worker
USER worker
CMD ["python", "-m", "denguepharma_workers.runtime"]
