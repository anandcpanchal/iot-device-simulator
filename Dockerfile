FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if any (none needed for this simple app)

# Copy requirements or just install directly since we used uv pip
# We'll just run pip install for simplicity in Docker
RUN pip install fastapi uvicorn paho-mqtt aiosqlite python-multipart

COPY . .

# Create data directory
RUN mkdir -p data/csv

ENV MQTT_HOST=localhost
ENV MQTT_PORT=1883
ENV MQTT_USERNAME=backend_service
ENV MQTT_PASSWORD=secure_password

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
