#!/bin/bash
set -e

echo "🔨 Building frontend..."
cd frontend
export REACT_APP_BACKEND_URL=""
yarn install --frozen-lockfile
yarn build
echo "✅ Frontend build complete!"
