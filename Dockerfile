FROM python:3.12-slim
WORKDIR /app
COPY src ./src
COPY sql ./sql
ENV PYTHONPATH=/app/src PIPELINE_DATA_DIR=/app/data PYTHONUNBUFFERED=1
CMD ["python", "-m", "pipeline.run", "all", "--days", "30"]
