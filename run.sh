#!/bin/bash

today=$(date +%Y%m%d)

PYTHONPATH=. poetry run python amazon_scraper/scripts/main.py >& nohup.out.${today}.log
