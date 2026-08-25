FROM python:3.12.8-slim

WORKDIR /app

COPY requirments.txt .
RUN pip install --no-cache-dir -r requirments.txt

COPY src/ ./src/

CMD [ "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
