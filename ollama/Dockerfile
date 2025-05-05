FROM ollama/ollama:latest

# Start Ollama on port 11434 to prepare model before Cloud Run can start serving on dynamic port
RUN ollama serve & \
    sleep 10 && \
    ollama pull nomic-embed-text

# Expose the required Cloud Run port
EXPOSE 11434

# Now Ollama should listen to the dynamic port provided by Cloud Run
CMD ["ollama", "serve"]
