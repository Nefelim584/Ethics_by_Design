"""
Migration: add is_approved column to the users table.

Run once:
    python migrate_add_is_approved.py

Existing users will be set to is_approved = TRUE so they keep their access.
New registrations will default to FALSE (pending admin approval).
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://ethics:ethics_password@localhost:5432/ethics",
)

engine = create_engine(DATABASE_URL, echo=True, future=True)

with engine.connect() as conn:
    # Add column if it doesn't already exist
    conn.execute(text("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_approved BOOLEAN NOT NULL DEFAULT FALSE;
    """))

    # Approve all existing users so they aren't locked out
    conn.execute(text("""
        UPDATE users SET is_approved = TRUE WHERE is_approved = FALSE;
    """))

    conn.commit()

print("Migration complete: is_approved column added and all existing users approved.")

