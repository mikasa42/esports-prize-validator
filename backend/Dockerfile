FROM python:3.10-slim AS common
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

# SQLAlchemy é usado pelo simulador externo.
FROM common AS official
COPY requirements-official.txt .
RUN pip install --no-cache-dir -r requirements-official.txt
EXPOSE 8001
CMD ["uvicorn", "src.simulator.official_api_server:app", "--host", "0.0.0.0", "--port", "8001"]

FROM common AS backend
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
