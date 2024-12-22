# src/gened/migrations/[timestamp]_rename_api_keys.py

def up(db):
    """Rename OpenAI key columns to Dartmouth key columns"""
    db.execute("ALTER TABLE classes_user RENAME COLUMN openai_key TO dartmouth_key")
    db.execute("ALTER TABLE consumers RENAME COLUMN openai_key TO dartmouth_key")
    db.commit()

def down(db):
    """Revert key column names back to OpenAI"""
    db.execute("ALTER TABLE classes_user RENAME COLUMN dartmouth_key TO openai_key")
    db.execute("ALTER TABLE consumers RENAME COLUMN dartmouth_key TO openai_key") 
    db.commit()