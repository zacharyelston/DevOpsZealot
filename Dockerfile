FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Copy requirements and install Python dependencies
COPY container_requirements.txt .
RUN pip install --no-cache-dir -r container_requirements.txt

# Copy the worker scripts
COPY container_worker/ ./

# Make the run script executable
RUN chmod +x run_job.py

# Set default command
CMD ["python", "run_job.py"]