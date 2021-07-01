import asyncio
import os

import dotenv

from app.database.database import Database

dotenv.load_dotenv()

print("Initializing Database...")
db = Database(
    os.getenv("DB_NAME"),
    os.getenv("DB_USER"),
    os.getenv("DB_PASSWORD"),
)
asyncio.run(db.init_database(create_data=True))
print("Database Initialized.")
