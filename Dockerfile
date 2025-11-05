FROM python:3.9-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY data/ ./data/

# Create data directory if it doesn't exist
RUN mkdir -p data

# Expose port
EXPOSE 8050

# Run dashboard
CMD ["python", "src/dashboard.py"]


