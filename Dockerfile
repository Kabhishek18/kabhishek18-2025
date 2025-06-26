# Start from the official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
# - procps contains `nc` (netcat) which is used in the entrypoint script
# - gcc and libmysqlclient-dev are needed to build the mysqlclient package
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY ./requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the entrypoint script and give it execute permissions
# This is a more reliable way to ensure permissions are set correctly
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Copy the rest of the application code into the container
COPY . /app/

