#!/bin/bash

# Start Ollama in the background
ollama serve &

export GODEBUG=netdns=go+ipv4

# Wait for it to be ready
sleep 10

# Pull the model
ollama pull nomic-embed-text

# Keep container running
wait
