FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Copy startup script and make executable
COPY start.sh .
# Fix line endings (CRLF -> LF) for Windows compatibility
RUN sed -i 's/\r$//' start.sh
RUN chmod +x start.sh

# Start the application
CMD ["./start.sh"]
