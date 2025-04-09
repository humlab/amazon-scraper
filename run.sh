#!/bin/bash

today=$(date +%Y%m%d)

mkdir -p logs
PYTHONPATH=. poetry run python amazon_scraper/scripts/main.py >& logs/nohup.out.${today}.log
