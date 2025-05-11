import os
import click
import sqlite3
from flask import current_app
from flask.cli import with_appcontext

def column_exists(db_path, table_name, column_name):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    conn.close()
    return column_name in columns

def execute_sql_file(db_path, file_path):
    conn = sqlite3.connect(db_path)
    with open(file_path, 'r') as f:
        sql = f.read()
        conn.executescript(sql)
    conn.close()

def is_migration_applied(db_path, filename):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM migrations WHERE filename = ?", (filename,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def mark_migration_as_applied(db_path, filename):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO migrations (filename, succeeded) VALUES (?, 1)", (filename,))
    conn.commit()
    conn.close()

@click.command('dartmouth-migrations')
@with_appcontext
def dartmouth_migrations():
    """Run specific Dartmouth migration files."""
    db_path = os.environ.get('FLASK_INSTANCE_PATH') + "/" + current_app.config['DATABASE_NAME']
    migration_folder = os.path.join(current_app.root_path, 'dartmouth-migrations')
    if not os.path.exists(migration_folder):
        click.echo(f"Migration folder '{migration_folder}' does not exist.")
        return

    migration_files = sorted(
        [os.path.join(migration_folder, f) for f in os.listdir(migration_folder) if f.endswith('.sql')]
    )

    for file_path in migration_files:
        filename = os.path.basename(file_path)
        if is_migration_applied(db_path, filename):
            click.echo(f"Skipping already applied migration: {filename}")
        else:
            try:
                if "rename_openai_columns" in filename:
                    if column_exists(db_path, 'classes_user', 'openai_key'):
                        conn = sqlite3.connect(db_path)
                        conn.execute("PRAGMA foreign_keys = OFF")
                        conn.execute("BEGIN")
                        conn.execute("ALTER TABLE classes_user RENAME COLUMN openai_key TO dartmouth_key")
                        conn.execute("COMMIT")
                        conn.execute("PRAGMA foreign_keys = ON")
                        conn.close()

                    if column_exists(db_path, 'consumers', 'openai_key'):
                        conn = sqlite3.connect(db_path)
                        conn.execute("PRAGMA foreign_keys = OFF")
                        conn.execute("BEGIN")
                        conn.execute("ALTER TABLE consumers RENAME COLUMN openai_key TO dartmouth_key")
                        conn.execute("COMMIT")
                        conn.execute("PRAGMA foreign_keys = ON")
                        conn.close()
                else:
                    execute_sql_file(db_path, file_path)
                click.echo(f"Applied migration: {filename}")
                mark_migration_as_applied(db_path, filename)
            except sqlite3.OperationalError as e:
                click.echo(f"Failed to apply migration: {filename}. Error: {e}")

    click.echo('Dartmouth migrations applied successfully.')

def register_commands(app):
    app.cli.add_command(dartmouth_migrations)