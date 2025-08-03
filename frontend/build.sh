#!/bin/bash
# build.sh

# Load .env into current shell
set -o allexport
source .env
set +o allexport

# Pass env vars as Docker build args
docker build \
  --build-arg VITE_AUTH_API_URL=$VITE_AUTH_API_URL \
  --build-arg VITE_DOC_API_URL=$VITE_DOC_API_URL \
  -t ahmedsabryrl/frontend:latest .

docker push ahmedsabryrl/frontend:latest

kubectl rollout restart deployment/frontend
