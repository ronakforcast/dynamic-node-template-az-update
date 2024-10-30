# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set environment variables for Python
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Copy requirements file to the container
COPY requirements.txt /app/requirements.txt

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app

# Run the Python script
CMD ["python", "main.py"]