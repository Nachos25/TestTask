"""Main module for running the AutoRia scraper."""
import asyncio
import os
import signal
import sys
from datetime import datetime
import pytz

import schedule
from loguru import logger

from .config import CONFIG
from .database import db
from .scraper import run_scraper


# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add(
    "logs/autoria_scraper.log",
    rotation="10 MB",
    retention="1 week",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)


def get_local_time():
    """Get current time in the configured timezone."""
    timezone = pytz.timezone(CONFIG["scraper"]["timezone"])
    return datetime.now(timezone)


def create_dump_job():
    """Create database dump job."""
    logger.info("Running database dump job")
    if db.create_dump():
        logger.info("Database dump created successfully")
    else:
        logger.error("Failed to create database dump")


async def setup_schedule():
    """Set up scheduled jobs."""
    # Create dumps directory if it doesn't exist
    os.makedirs("dumps", exist_ok=True)
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Schedule scraping job
    scrape_time = CONFIG["scraper"]["scrape_schedule_time"]
    logger.info(f"Scheduling scraping job at {scrape_time}")
    schedule.every().day.at(scrape_time).do(lambda: asyncio.create_task(run_scraper()))
    
    # Schedule database dump job
    dump_time = CONFIG["scraper"]["dump_schedule_time"]
    logger.info(f"Scheduling database dump job at {dump_time}")
    schedule.every().day.at(dump_time).do(create_dump_job)
    
    logger.info("Scheduled jobs set up")


async def run_scheduler():
    """Run scheduled jobs."""
    await setup_schedule()
    
    logger.info("Starting scheduler")
    
    # Calculate time to next scrape run for initial run
    scrape_time = CONFIG["scraper"]["scrape_schedule_time"]
    hour, minute = map(int, scrape_time.split(":"))
    
    now = get_local_time()
    scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    # If the scheduled time is in the past, run immediately
    if now > scheduled_time:
        logger.info("Running initial scrape job immediately")
        await run_scraper()
    
    # Run the scheduler
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


async def shutdown(signal, loop):
    """Shutdown gracefully."""
    logger.info(f"Received exit signal {signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    for task in tasks:
        task.cancel()
    
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()
    logger.info("Shutdown complete")


def main():
    """Main entry point for the application."""
    logger.info("Starting AutoRia scraper")
    
    loop = asyncio.get_event_loop()
    
    # Register signal handlers
    signals = (signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown(s, loop))
        )
    
    try:
        # Initialize database
        loop.run_until_complete(db.connect())
        loop.run_until_complete(db.init_db())
        
        # Start scheduler
        loop.run_until_complete(run_scheduler())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        loop.run_until_complete(db.disconnect())
        loop.close()
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    main() 