# AvitoScraping Implementation Guide

This document provides a detailed guide to the implementation of the AvitoScraping project.

## Project Overview

The AvitoScraping project is designed to collect and analyze data on commercial transport listings from Avito.ru. The project follows these main steps:

1. Research the top 20 most selling commercial transport models in Russia as of March 31, 2025
2. Scrape price, seller, and city information from Avito.ru for these models
3. Store the collected data in a Neon PostgreSQL database
4. Update the data daily to keep it current

## Technical Architecture

The project is built using Python and PostgreSQL, with the following components:

- **Research Module**: Identifies and processes the top commercial transport models
- **Database Module**: Sets up and manages the database tables
- **Scraping Module**: Collects data from Avito.ru
- **Update Module**: Schedules and runs daily updates
- **Viewing Module**: Provides tools to view and analyze the collected data

## Implementation Details

### 1. Research Module

The research module (`research_models.py`) loads pre-researched data on the top commercial transport models in Russia. This data includes:

- Make and model information
- Vehicle type (e.g., light truck, tractor unit)
- Table name for database storage
- Search terms for Avito.ru

The module processes this data and prepares it for the scraping process by:
- Displaying the models in a tabular format
- Exporting search terms for each model
- Creating a list of table names for the database setup

### 2. Database Module

The database module (`setup_database.py`) sets up the necessary tables in the Neon PostgreSQL database:

- Creates a table for each model with columns for listing details
- Creates a metadata table to track scraping status
- Initializes the metadata table with the model table names

Each model table has the following structure:
```sql
CREATE TABLE model_table_name (
    id SERIAL PRIMARY KEY,
    listing_id VARCHAR(255) UNIQUE,
    title TEXT NOT NULL,
    price INTEGER,
    seller_name TEXT,
    seller_type VARCHAR(50),
    city TEXT,
    url TEXT,
    description TEXT,
    date_added TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

The metadata table has the following structure:
```sql
CREATE TABLE avito_scraping_metadata (
    id SERIAL PRIMARY KEY,
    model_table_name VARCHAR(255) UNIQUE,
    last_scraped TIMESTAMP WITH TIME ZONE,
    total_listings INTEGER DEFAULT 0,
    last_status VARCHAR(50),
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 3. Scraping Module

The scraping module (`scrape_avito.py`) collects data from Avito.ru for each model:

- Searches for each model using the provided search terms
- Extracts listing details (title, price, seller, city, URL)
- Gets additional details for each listing (description)
- Saves the data to the appropriate database table

The module includes several features to ensure reliable scraping:
- User agent rotation to avoid detection
- Random delays between requests
- Retry logic for failed requests
- Error handling and logging

### 4. Update Module

The update module (`update_database.py`) schedules and runs daily updates:

- Can be run manually with the `--now` flag
- Can be scheduled to run at a specific time each day
- Uses the `schedule` library for scheduling
- Logs update status and errors

### 5. Viewing Module

The viewing module (`view_data.py`) provides tools to view and analyze the collected data:

- Shows metadata for all models
- Shows raw data for a specific model
- Shows statistics for a specific model (price, city, seller type)
- Formats the data for better readability

## Database Schema

### Model Tables

Each model has its own table with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| listing_id | VARCHAR(255) | Unique identifier for the listing |
| title | TEXT | Listing title |
| price | INTEGER | Price in rubles |
| seller_name | TEXT | Name of the seller |
| seller_type | VARCHAR(50) | Type of seller (private, dealer, unknown) |
| city | TEXT | Location of the listing |
| url | TEXT | Link to the original listing |
| description | TEXT | Detailed description of the listing |
| date_added | TIMESTAMP | When the listing was added to the database |
| last_updated | TIMESTAMP | When the listing was last updated |

### Metadata Table

The metadata table tracks the scraping status for each model:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| model_table_name | VARCHAR(255) | Name of the model table |
| last_scraped | TIMESTAMP | When the model was last scraped |
| total_listings | INTEGER | Total number of listings for the model |
| last_status | VARCHAR(50) | Status of the last scraping (initialized, scraping, completed, error) |
| last_error | TEXT | Error message if the last scraping failed |
| created_at | TIMESTAMP | When the metadata entry was created |
| updated_at | TIMESTAMP | When the metadata entry was last updated |

## Automation

The project includes shell scripts to automate the process:

- `run_all.sh`: Runs the entire process from research to scraping
- `setup_daily_updates.sh`: Sets up a cron job to run the update script daily

## Error Handling

The project includes comprehensive error handling:

- Each module includes try-except blocks to catch and handle errors
- Errors are logged to the console and log files
- The metadata table tracks scraping status and errors
- The update module includes retry logic for failed updates

## Security Considerations

The project includes several security features:

- Environment variables for sensitive information (database connection string)
- User agent rotation to avoid detection
- Random delays between requests to avoid rate limiting
- Error handling to prevent crashes

## Future Improvements

Potential improvements for the project:

1. **Proxy Rotation**: Add support for rotating proxies to avoid IP blocking
2. **Advanced Filtering**: Add support for filtering listings by price, year, etc.
3. **Image Scraping**: Add support for scraping and storing listing images
4. **Sentiment Analysis**: Add support for analyzing listing descriptions
5. **Price Prediction**: Add support for predicting listing prices based on features
6. **Email Notifications**: Add support for email notifications when new listings are found
7. **Web Interface**: Add a web interface for viewing and analyzing the data
