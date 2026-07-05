# ============= DATABASE HANDLER =============
import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_file):
        self.db_file = db_file
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_file) if os.path.dirname(db_file) else '.', exist_ok=True)
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip TEXT,
                port INTEGER,
                service TEXT,
                action TEXT,
                username TEXT,
                password TEXT,
                user_agent TEXT,
                country TEXT,
                city TEXT,
                payload TEXT
            )
        ''')
        self.conn.commit()
    
    def log_connection(self, ip, port, service, action, username=None, password=None, 
                      user_agent=None, country=None, city=None, payload=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO connections (ip, port, service, action, username, password, user_agent, country, city, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (ip, port, service, action, username, password, user_agent, country, city, payload))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Database error: {e}")
    
    def close(self):
        try:
            self.conn.close()
        except:
            pass
