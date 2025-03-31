# AvitoScraping

A project to scrape and analyze commercial transport listings from Avito.ru.

## Project Overview

This project collects data on the most popular commercial transport models in Russia as of March 31, 2025 from Avito.ru. It includes:

1. Research to identify the top 20 most selling commercial transport models in Russia
2. Web scraping scripts to collect price, seller, and city information from Avito.ru
3. Database integration to store the collected data in Neon PostgreSQL
4. Automated daily updates to keep the data current

## Project Structure

- `src/` - Source code for the scraping and database operations
- `data/` - Data files including research results and temporary storage
- `docs/` - Documentation files
- `scripts/` - Shell scripts for automation and scheduling

## Requirements

- Python 3.8+
- PostgreSQL database (Neon)
- Required Python packages (see requirements.txt)

## Setup

1. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure database connection in `.env` file:
   ```
   DATABASE_URL=postgresql://neondb_owner:npg_RS2UfVBu7eiY@ep-morning-term-a2o6ardi-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```

3. Run the initial research script:
   ```bash
   python src/research_models.py
   ```

4. Run the scraping script:
   ```bash
   python src/scrape_avito.py
   ```

5. Set up automated daily updates:
   ```bash
   # For cron job setup (standard method)
   ./scripts/setup_daily_updates.sh

   # For systemd timer setup (requires root)
   sudo ./scripts/setup_daily_updates.sh
   ```

   The script will automatically set up the most appropriate scheduling method for your system.

## Usage

- To manually update the database:
  ```bash
  python src/update_database.py
  ```

- To view the latest data:
  ```bash
  python src/view_data.py
  ```

## Data Structure

Each model has its own table in the database with the following columns:
- `id` - Unique identifier
- `title` - Listing title
- `price` - Price in rubles
- `seller` - Seller name/type (private or dealer)
- `city` - Location of the listing
- `url` - Link to the original listing
- `date_added` - When the listing was added to our database
- `last_updated` - When the listing was last updated
