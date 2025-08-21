#!/bin/bash

docker compose exec zwd-backend bash -c "

echo 'Checking for outdated dependencies'
uv pip list --outdated

echo 'Upgrading dependencies...'
uv lock --upgrade

echo 'Syncing dependencies'
uv sync --frozen

echo 'Exporting dependencies to a requirements.txt file' and installing them into the system interpreter
uv export --frozen --format requirements-txt > /tmp/req.txt
uv pip install --system -r /tmp/req.txt

rm /tmp/req.txt
"
