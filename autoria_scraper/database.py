"""Database module for AutoRia scraper."""
import datetime
import os
import subprocess
from typing import Dict, Any, List, Optional

import asyncpg
from loguru import logger

from .config import CONFIG


class Database:
    """Database manager for AutoRia scraper."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.config = CONFIG["database"]

    async def connect(self) -> None:
        """Connect to the database."""
        if self.pool is not None:
            return

        logger.info("Connecting to the database...")
        try:
            self.pool = await asyncpg.create_pool(
                user=self.config["user"],
                password=self.config["password"],
                host=self.config["host"],
                port=self.config["port"],
                database=self.config["database"],
            )
            logger.info("Connected to the database")
        except Exception as e:
            logger.error(f"Failed to connect to the database: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        if self.pool is None:
            return

        logger.info("Disconnecting from the database...")
        await self.pool.close()
        self.pool = None
        logger.info("Disconnected from the database")

    async def init_db(self) -> None:
        """Initialize the database schema."""
        logger.info("Initializing database schema...")
        try:
            await self.connect()
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS cars (
                        id SERIAL PRIMARY KEY,
                        url TEXT UNIQUE NOT NULL,
                        title TEXT,
                        price_usd INTEGER,
                        odometer INTEGER,
                        username TEXT,
                        phone_number BIGINT,
                        image_url TEXT,
                        images_count INTEGER,
                        car_number TEXT,
                        car_vin TEXT,
                        datetime_found TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise

    async def save_car(self, car_data: Dict[str, Any]) -> bool:
        """
        Save car data to the database.
        Returns True if car was saved, False if it already exists.
        """
        if self.pool is None:
            await self.connect()

        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(
                    """
                    INSERT INTO cars (
                        url, title, price_usd, odometer, username, 
                        phone_number, image_url, images_count, 
                        car_number, car_vin, datetime_found
                    ) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (url) DO NOTHING
                    RETURNING id
                    """,
                    car_data["url"],
                    car_data["title"],
                    car_data["price_usd"],
                    car_data["odometer"],
                    car_data["username"],
                    car_data["phone_number"],
                    car_data["image_url"],
                    car_data["images_count"],
                    car_data["car_number"],
                    car_data["car_vin"],
                    datetime.datetime.now(datetime.timezone.utc),
                )
                return result is not None
        except Exception as e:
            logger.error(f"Failed to save car data: {e}")
            return False

    async def save_cars_batch(self, cars_data: List[Dict[str, Any]]) -> int:
        """
        Save a batch of car data to the database.
        Returns number of new cars saved.
        """
        if not cars_data:
            return 0

        if self.pool is None:
            await self.connect()

        saved_count = 0
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for car_data in cars_data:
                        result = await conn.fetchval(
                            """
                            INSERT INTO cars (
                                url, title, price_usd, odometer, username, 
                                phone_number, image_url, images_count, 
                                car_number, car_vin, datetime_found
                            ) 
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                            ON CONFLICT (url) DO NOTHING
                            RETURNING id
                            """,
                            car_data["url"],
                            car_data["title"],
                            car_data["price_usd"],
                            car_data["odometer"],
                            car_data["username"],
                            car_data["phone_number"],
                            car_data["image_url"],
                            car_data["images_count"],
                            car_data["car_number"],
                            car_data["car_vin"],
                            datetime.datetime.now(datetime.timezone.utc),
                        )
                        if result is not None:
                            saved_count += 1
            return saved_count
        except Exception as e:
            logger.error(f"Failed to save cars batch: {e}")
            return 0

    def create_dump(self) -> bool:
        """Create a database dump."""
        logger.info("Creating database dump...")
        os.makedirs("dumps", exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dump_file = f"dumps/autoria_dump_{timestamp}.sql"
        
        try:
            cmd = [
                "pg_dump",
                "-h", self.config["host"],
                "-p", str(self.config["port"]),
                "-U", self.config["user"],
                "-d", self.config["database"],
                "-f", dump_file,
            ]
            
            env = os.environ.copy()
            env["PGPASSWORD"] = self.config["password"]
            
            subprocess.run(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            
            logger.info(f"Database dump created: {dump_file}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create database dump: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Failed to create database dump: {e}")
            return False


# Database singleton instance
db = Database()


async def initialize_db():
    """Initialize database connection and schema."""
    await db.connect()
    await db.init_db() 