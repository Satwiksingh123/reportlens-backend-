FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The sibling service packages live OUTSIDE /app deliberately: docker-compose bind-mounts the
# host's services/api over /app for live reload, which would shadow anything placed inside it.
# They go on PYTHONPATH rather than being pip-installed because their pyproject files declare
# no [build-system], so installing would lean on setuptools auto-discovery guessing the right
# top-level directories - fragile for no benefit here.
COPY services/medical_parser/medical_parser /opt/packages/medical_parser
COPY services/ocr_engine/ocr_engine         /opt/packages/ocr_engine
COPY services/rag/rag                       /opt/packages/rag
COPY services/llm_service/llm_service       /opt/packages/llm_service
ENV PYTHONPATH=/opt/packages

COPY services/api .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
