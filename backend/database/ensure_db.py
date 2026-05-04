import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys
import os

# Ayarları config.py üzerinden okuyabilmek için backend dizinini path'e ekliyoruz
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.config import DB_CONFIG

def create_db():
    try:
        # Connect to default postgres database using config values
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        target_db = DB_CONFIG['dbname']
        
        # Check if target_db exists
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'")
        exists = cur.fetchone()
        
        if not exists:
            print(f"Creating database '{target_db}'...")
            cur.execute(f"CREATE DATABASE \"{target_db}\"")
            print(f"Database '{target_db}' created successfully.")
        else:
            print(f"Database '{target_db}' already exists.")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error creating database: {e}")

if __name__ == "__main__":
    create_db()
