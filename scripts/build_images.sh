#!/bin/bash
# Build all DEAN Docker images

set -e

echo "🏗️  Building DEAN Docker Images"
echo "==============================="

# Get the DEAN root directory
DEAN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEAN_ROOT"

# Build orchestration server
echo -e "\n📦 Building dean/orchestration..."
docker build -f Dockerfile -t dean/orchestration:latest .
echo "✅ dean/orchestration built successfully"

# Build IndexAgent
echo -e "\n📦 Building dean/indexagent..."
docker build -f docker/Dockerfile.indexagent -t dean/indexagent:latest .
echo "✅ dean/indexagent built successfully"

# Build Evolution API
echo -e "\n📦 Building dean/evolution-api..."
docker build -f docker/Dockerfile.evolution -t dean/evolution-api:latest .
echo "✅ dean/evolution-api built successfully"

# Build Airflow
echo -e "\n📦 Building dean/airflow..."
docker build -f docker/Dockerfile.airflow -t dean/airflow:latest .
echo "✅ dean/airflow built successfully"

# Tag images for export
echo -e "\n🏷️  Tagging images for production..."
docker tag dean/orchestration:latest dean/orchestration:production
docker tag dean/indexagent:latest dean/indexagent:production
docker tag dean/evolution-api:latest dean/evolution-api:production
docker tag dean/airflow:latest dean/airflow:production

# List built images
echo -e "\n📋 Built images:"
docker images | grep "dean/" | grep -E "(latest|production)"

echo -e "\n✅ All images built successfully!"
echo -e "\n📤 To save images for transfer:"
echo "mkdir -p images"
echo "docker save dean/orchestration:production | gzip > images/dean-orchestration.tar.gz"
echo "docker save dean/indexagent:production | gzip > images/dean-indexagent.tar.gz"
echo "docker save dean/evolution-api:production | gzip > images/dean-evolution-api.tar.gz"
echo "docker save dean/airflow:production | gzip > images/dean-airflow.tar.gz"