#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database update script for the AvitoScraping project.
This script runs the scraping process to update the database with the latest listings.
It can be scheduled to run daily.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
import schedule
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the scraping script
from src.scrape_avito import main as scrape_main

# Load environment variables
load_dotenv()

# Configure logging
def setup_logging():
    """Set up logging with rotation."""
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f'update_{datetime.now().strftime("%Y%m%d")}.log')

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger('update_database')

logger = setup_logging()

def update_job():
    """Run the update job."""
    logger.info("Starting database update job...")

    try:
        # Run the scraping process
        scrape_main()

        # Log completion
        logger.info("Database update job completed successfully.")
    except Exception as e:
        logger.error(f"Error in database update job: {e}", exc_info=True)

def schedule_update():
    """Schedule the update job to run daily."""
    update_hour = int(os.getenv("UPDATE_HOUR", "3"))
    update_minute = int(os.getenv("UPDATE_MINUTE", "0"))

    schedule_time = f"{update_hour:02d}:{update_minute:02d}"
    logger.info(f"Scheduling daily update at {schedule_time}")

    schedule.every().day.at(schedule_time).do(update_job)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

def main():
    """Main function to run or schedule the update process."""
    print("AvitoScraping Database Update")
    print("-----------------------------")

    # Change to the project root directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)

    # Parse command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == '--now':
        print("Running update job now...")
        update_job()
    else:
        print("Starting scheduled update job...")
        schedule_update()

if __name__ == "__main__":
    main()
