#!/bin/bash

echo "🚀 Starting deployment process..."

# Build frontend with empty backend URL (uses relative paths)
echo "📦 Building frontend..."
cd frontend
export REACT_APP_BACKEND_URL=""
yarn build

if [ $? -ne 0 ]; then
    echo "❌ Frontend build failed!"
    exit 1
fi

echo "✅ Frontend built successfully!"

# Start backend server (which will serve both API and frontend)
echo "🔧 Starting backend server..."
cd ..
uvicorn backend.server:app --host 0.0.0.0 --port 8080
