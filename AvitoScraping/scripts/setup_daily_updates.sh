#!/bin/bash

# Setup script for daily updates
# This script sets up a cron job to run the update_database.py script daily
# and creates a systemd service for more reliable execution (if available)

# Get the absolute path to the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$PROJECT_DIR/data/logs"

# Load environment variables
source "$PROJECT_DIR/.env"

# Default update time is 3:00 AM
UPDATE_HOUR=${UPDATE_HOUR:-3}
UPDATE_MINUTE=${UPDATE_MINUTE:-0}

# Make the wrapper script executable
chmod +x "$PROJECT_DIR/scripts/run_update.sh"

# Setup method depends on the system
if command -v systemctl &> /dev/null && [ -d "/etc/systemd/system" ] && [ "$(id -u)" -eq 0 ]; then
    # Using systemd (requires root)
    echo "Setting up systemd service and timer..."
    
    # Create systemd service file
    cat > "/etc/systemd/system/avito-scraping.service" << EOF
[Unit]
Description=Avito Scraping Service
After=network.target

[Service]
Type=oneshot
ExecStart=$PROJECT_DIR/scripts/run_update.sh
User=$(whoami)
WorkingDirectory=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF
    
    # Create systemd timer file
    cat > "/etc/systemd/system/avito-scraping.timer" << EOF
[Unit]
Description=Run Avito Scraping Service daily

[Timer]
OnCalendar=*-*-* $UPDATE_HOUR:$UPDATE_MINUTE:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
    
    # Reload systemd, enable and start the timer
    systemctl daemon-reload
    systemctl enable avito-scraping.timer
    systemctl start avito-scraping.timer
    
    echo "Systemd timer set up successfully."
    echo "To check status: systemctl status avito-scraping.timer"
    echo "To view logs: journalctl -u avito-scraping.service"
    
else
    # Using cron (fallback method)
    echo "Setting up cron job..."
    
    if ! command -v crontab &> /dev/null; then
        echo "Warning: crontab is not available. Daily updates will not be scheduled."
        echo "You can run updates manually with: $PROJECT_DIR/scripts/run_update.sh"
        exit 1
    fi
    
    # Create the cron job
    CRON_JOB="$UPDATE_MINUTE $UPDATE_HOUR * * * $PROJECT_DIR/scripts/run_update.sh"
    
    # Check if the cron job already exists
    if crontab -l 2>/dev/null | grep -q "$PROJECT_DIR/scripts/run_update.sh"; then
        echo "Cron job already exists. Updating..."
        (crontab -l 2>/dev/null | grep -v "$PROJECT_DIR/scripts/run_update.sh"; echo "$CRON_JOB") | crontab -
    else
        echo "Adding new cron job..."
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    fi
    
    echo "Cron job set up successfully."
    echo "To view scheduled jobs: crontab -l"
    echo "To edit scheduled jobs: crontab -e"
fi

# Create a log rotation configuration
LOGROTATE_CONFIG="$PROJECT_DIR/scripts/logrotate.conf"
cat > "$LOGROTATE_CONFIG" << EOF
$PROJECT_DIR/data/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 $(whoami) $(id -gn)
}
EOF

echo -e "\nLog rotation configuration created at $LOGROTATE_CONFIG"
echo "You can set up log rotation with: sudo logrotate -f $LOGROTATE_CONFIG"

echo -e "\nDaily update scheduled to run at $UPDATE_HOUR:$UPDATE_MINUTE"
echo "You can also run updates manually with: $PROJECT_DIR/scripts/run_update.sh"
