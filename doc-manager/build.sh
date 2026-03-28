#!/bin/bash
# build.sh

# Load .env into current shell
set -o allexport
source .env
set +o allexport

# Pass env vars as Docker build args
docker build -t ahmedsabryrl/doc-manager:latest .

docker push ahmedsabryrl/doc-manager:latest

kubectl rollout restart deployment/doc-manager
