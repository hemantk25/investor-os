#!/bin/bash
cd "$(dirname "$0")"
npx tailwindcss@3 -c app/tailwind/tailwind.config.js -i app/tailwind/input.css -o app/static/app.css --minify
