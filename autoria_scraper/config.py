"""Configuration module for AutoRia scraper."""
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

CONFIG: Dict[str, Any] = {
    "database": {
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "host": os.getenv("POSTGRES_HOST", "db"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "autoria"),
    },
    "scraper": {
        "start_url": os.getenv(
            "START_URL",
            "https://auto.ria.com/uk/search/?indexName=auto,order_auto,newauto_search"
            "&categories.main.id=1&country.import.usa.not=-1&price.currency=1"
            "&abroad.not=0&custom.not=1&page=0&size=100"
        ),
        "scrape_schedule_time": os.getenv("SCRAPE_SCHEDULE_TIME", "12:00"),
        "dump_schedule_time": os.getenv("DUMP_SCHEDULE_TIME", "00:00"),
        "timezone": os.getenv("TIMEZONE", "Europe/Kiev"),
        "concurrency": int(os.getenv("CONCURRENCY", "5")),
        "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "30")),
        "request_delay": float(os.getenv("REQUEST_DELAY", "1")),
        "max_retries": int(os.getenv("MAX_RETRIES", "3")),
    }
} 