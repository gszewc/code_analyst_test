#!/bin/sh
# Inject runtime environment variables into index.html at container start.
# This avoids rebuilding the image when only the API URL changes.

INDEX="/usr/share/nginx/html/index.html"
API_BASE_URL="${API_BASE_URL:-http://localhost:8080}"

# Inject window.__ENV__ before closing </head>
sed -i "s|</head>|<script>window.__ENV__={API_BASE_URL:\"${API_BASE_URL}\"}</script></head>|" "$INDEX"

exec nginx -g 'daemon off;'
