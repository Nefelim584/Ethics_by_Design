"""
One-off migration: add num_speakers, prompt, and output_format columns
to the existing `transcripts` table.

Run once:  python migrate_add_transcript_fields.py
"""

import os

from sqlalchemy import create_engine, inspect, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://ethics:ethics_password@localhost:5432/ethics",
)

engine = create_engine(DATABASE_URL, echo=True, future=True)


def migrate():
    inspector = inspect(engine)

    if "transcripts" not in inspector.get_table_names():
        print("Table 'transcripts' does not exist yet — nothing to migrate.")
        print("It will be created automatically on next app start via init_db().")
        return

    existing_columns = {col["name"] for col in inspector.get_columns("transcripts")}

    with engine.begin() as conn:
        if "num_speakers" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE transcripts ADD COLUMN num_speakers INTEGER"
            ))
            print("Added column: num_speakers")
        else:
            print("Column num_speakers already exists — skipping")

        if "prompt" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE transcripts ADD COLUMN prompt TEXT"
            ))
            print("Added column: prompt")
        else:
            print("Column prompt already exists — skipping")

        if "output_format" not in existing_columns:
            conn.execute(text(
                "ALTER TABLE transcripts ADD COLUMN output_format VARCHAR(16) DEFAULT 'txt'"
            ))
            print("Added column: output_format")
        else:
            print("Column output_format already exists — skipping")

    print("Migration complete.")


if __name__ == "__main__":
    migrate()

