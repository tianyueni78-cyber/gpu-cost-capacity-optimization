FROM python:3.11.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --create-home --uid 10001 appuser
COPY saas_control /app/saas_control
COPY gpu-data/src /app/gpu-data/src
COPY gpu-data/sample_data /app/gpu-data/sample_data
RUN --mount=type=cache,target=/root/.cache/pip pip install /app/saas_control
USER appuser
CMD ["uvicorn", "saas_control.app.runtime:app", "--host", "0.0.0.0", "--port", "8000"]
