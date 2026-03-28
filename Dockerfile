FROM python:3.11-slim
WORKDIR /app
COPY app/ /app/
COPY mlops/ /app/mlops/
COPY models/ /app/models/
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "app.py"]
