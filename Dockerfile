# Use a slim Python image
FROM python:3.11-slim

# Install necessary packages
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Download Cloud SQL Auth Proxy
RUN curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 \
    && chmod +x cloud_sql_proxy \
    && mv cloud_sql_proxy /usr/local/bin/

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Upgrade pip and install the Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose the port the application runs on
EXPOSE 8080

# Start the Cloud SQL Auth Proxy and your application
CMD ["sh", "-c", "cloud_sql_proxy -instances=$INSTANCE_CONNECTION_NAME=tcp:3306 & gunicorn --bind 0.0.0.0:8080 application:application"]
