# AvitoScraping Usage Guide

This document provides a guide on how to use the AvitoScraping project.

## Prerequisites

Before using the AvitoScraping project, ensure you have the following:

1. Python 3.8 or higher installed
2. PostgreSQL database (Neon)
3. Access to Avito.ru (the script is designed to work with the Russian version of the site)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd AvitoScraping
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure the environment variables by creating a `.env` file:
   ```
   # Database connection string
   DATABASE_URL=postgresql://neondb_owner:npg_RS2UfVBu7eiY@ep-morning-term-a2o6ardi-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require

   # Scraping settings
   SCRAPING_DELAY=2
   MAX_RETRIES=3
   USER_AGENT_ROTATION=true

   # Update settings
   UPDATE_HOUR=3  # 3 AM
   UPDATE_MINUTE=0
   ```

## Basic Usage

### Running the Entire Process

To run the entire process from research to scraping, use the `run_all.sh` script:

```bash
./scripts/run_all.sh
```

This script will:
1. Research the top commercial transport models
2. Set up the database tables
3. Scrape data from Avito.ru
4. Display a summary of the collected data

### Running Individual Steps

You can also run each step individually:

1. Research the top commercial transport models:
   ```bash
   python src/research_models.py
   ```

2. Set up the database tables:
   ```bash
   python src/setup_database.py
   ```

3. Scrape data from Avito.ru:
   ```bash
   python src/scrape_avito.py
   ```

4. View the collected data:
   ```bash
   python src/view_data.py
   ```

### Setting Up Automated Daily Updates

To set up automated daily updates, use the `setup_daily_updates.sh` script:

```bash
# For cron job setup (standard method)
./scripts/setup_daily_updates.sh

# For systemd timer setup (requires root)
sudo ./scripts/setup_daily_updates.sh
```

The script will automatically choose the most appropriate scheduling method for your system:

1. **Systemd Timer** (if available and running as root): More reliable and includes better logging
2. **Cron Job** (fallback method): Standard scheduling method available on most systems

The updates will run daily at the time specified in the `.env` file (default is 3:00 AM).

The script also sets up log rotation to manage log files efficiently.

You can also run the update script manually:

```bash
python src/update_database.py --now
```

## Viewing Data

The `view_data.py` script provides several options for viewing the collected data:

1. View metadata for all models:
   ```bash
   python src/view_data.py
   ```

2. View data for a specific model:
   ```bash
   python src/view_data.py --table <table_name>
   ```

3. View statistics for a specific model:
   ```bash
   python src/view_data.py --table <table_name> --stats
   ```

4. Limit the number of rows displayed:
   ```bash
   python src/view_data.py --table <table_name> --limit 20
   ```

## Troubleshooting

### Database Connection Issues

If you encounter database connection issues:

1. Check that the `DATABASE_URL` in the `.env` file is correct
2. Ensure that the database is accessible from your network
3. Check that the database user has the necessary permissions

### Scraping Issues

If you encounter scraping issues:

1. Check that Avito.ru is accessible from your network
2. Increase the `SCRAPING_DELAY` in the `.env` file to avoid rate limiting
3. Check the log files in the `data` directory for error messages

### Update Issues

If you encounter update issues:

1. **For Cron Jobs**:
   - Check that the cron job is set up correctly:
     ```bash
     crontab -l
     ```
   - Check the log files in the `data/logs` directory:
     ```bash
     ls -la data/logs/
     cat data/logs/update_YYYYMMDD.log  # Replace YYYYMMDD with the actual date
     ```

2. **For Systemd Timers**:
   - Check the timer status:
     ```bash
     systemctl status avito-scraping.timer
     ```
   - Check the service status:
     ```bash
     systemctl status avito-scraping.service
     ```
   - View the service logs:
     ```bash
     journalctl -u avito-scraping.service
     ```

3. **Manual Testing**:
   - Run the update script manually to check for errors:
     ```bash
     ./scripts/run_update.sh
     ```

## Advanced Usage

### Customizing the Research Data

You can customize the research data by editing the `data/top_commercial_models.json` file. This file contains information about the top commercial transport models, including:

- Make and model information
- Vehicle type
- Table name for database storage
- Search terms for Avito.ru

### Customizing the Scraping Process

You can customize the scraping process by editing the `.env` file:

- `SCRAPING_DELAY`: The delay between requests (in seconds)
- `MAX_RETRIES`: The maximum number of retries for failed requests
- `USER_AGENT_ROTATION`: Whether to rotate user agents

### Customizing the Update Schedule

You can customize the update schedule by editing the `.env` file:

- `UPDATE_HOUR`: The hour to run the update (0-23)
- `UPDATE_MINUTE`: The minute to run the update (0-59)

Or by editing the cron job directly:

```bash
crontab -e
```

## Data Analysis

The collected data can be used for various analyses:

1. **Price Analysis**: Analyze the price distribution for each model
2. **Geographic Analysis**: Analyze the distribution of listings by city
3. **Seller Analysis**: Analyze the distribution of listings by seller type
4. **Temporal Analysis**: Analyze how listings change over time

Example queries:

1. Average price by model:
   ```sql
   SELECT model_table_name, AVG(price) as avg_price
   FROM avito_scraping_metadata m
   JOIN (
       SELECT 'gazel_next' as table_name, AVG(price) as avg_price FROM gazel_next WHERE price IS NOT NULL
       UNION ALL
       SELECT 'kamaz_5490' as table_name, AVG(price) as avg_price FROM kamaz_5490 WHERE price IS NOT NULL
       -- Add more models as needed
   ) p ON m.model_table_name = p.table_name
   GROUP BY model_table_name
   ORDER BY avg_price DESC;
   ```

2. Listings by city:
   ```sql
   SELECT city, COUNT(*) as count
   FROM gazel_next
   WHERE city IS NOT NULL
   GROUP BY city
   ORDER BY count DESC
   LIMIT 10;
   ```

3. Listings by seller type:
   ```sql
   SELECT seller_type, COUNT(*) as count
   FROM gazel_next
   WHERE seller_type IS NOT NULL
   GROUP BY seller_type
   ORDER BY count DESC;
   ```

## Exporting Data

You can export the collected data for use in other tools:

1. Export to CSV:
   ```bash
   psql "$DATABASE_URL" -c "COPY (SELECT * FROM gazel_next) TO STDOUT WITH CSV HEADER" > gazel_next.csv
   ```

2. Export to JSON:
   ```bash
   psql "$DATABASE_URL" -c "COPY (SELECT row_to_json(t) FROM (SELECT * FROM gazel_next) t) TO STDOUT" > gazel_next.json
   ```

3. Export to Excel (requires pandas):
   ```python
   import pandas as pd
   import psycopg2
   import os
   from dotenv import load_dotenv

   load_dotenv()
   conn = psycopg2.connect(os.getenv("DATABASE_URL"))
   df = pd.read_sql("SELECT * FROM gazel_next", conn)
   df.to_excel("gazel_next.xlsx", index=False)
   ```
