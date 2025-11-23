FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt  # Create requirements.txt with deps
RUN apt-get install -y --no-install-recommends ca-certificates
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]