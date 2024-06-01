# Use a pre-built image that includes Python and PhantomJS
FROM ghcr.io/chosomeister/python-phantomjs:3.9

# Set the working directory inside the container
WORKDIR /app/

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Update package list and install ffmpeg in a single RUN command to reduce image layers
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Define the default command to run the application
CMD ["python3", "bot.py"]
