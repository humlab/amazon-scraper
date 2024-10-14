#!/bin/bash

today=$(date +%Y%m%d)

PYTHONPATH=. python amazon_scraper/scripts/main.py >& nohup.out.${today}.log
