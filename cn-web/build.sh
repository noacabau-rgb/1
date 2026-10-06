#!/usr/bin/env sh
# Builds cn-web/index.html (standalone page) from src/page.html.
# src/page.html holds the <head> part above the <!--BODY--> marker and the body below it.
set -e
cd "$(dirname "$0")"
{
  printf '<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
  sed '/<!--BODY-->/,$d' src/page.html
  printf '</head>\n<body>\n'
  sed '1,/<!--BODY-->/d' src/page.html
  printf '</body>\n</html>\n'
} > index.html
echo "index.html built"
