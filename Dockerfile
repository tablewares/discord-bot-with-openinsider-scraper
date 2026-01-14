# Use an official Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy dependency file first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p data
VOLUME ["/app/data"]

# Copy application code
COPY . .

# Command to run the app
CMD ["python", "bot.py"]
