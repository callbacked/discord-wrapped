import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.db = sqlite3.connect('user_activity.db')
        self.db.row_factory = sqlite3.Row  
        self.setup_database()
        
    def setup_database(self):
        cursor = self.db.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER,
                guild_id INTEGER,
                messages_sent INTEGER DEFAULT 0,
                reactions_added INTEGER DEFAULT 0,
                voice_time INTEGER DEFAULT 0,
                stream_time INTEGER DEFAULT 0,
                deafen_time INTEGER DEFAULT 0,
                opt_in_date TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mention_stats (
                user_id INTEGER,
                guild_id INTEGER,
                mentioned_id INTEGER,
                mention_type TEXT,
                mention_count INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id, mentioned_id, mention_type)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER,
                guild_id INTEGER,
                name TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id, guild_id)
            )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_traits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            server_id INTEGER,
            trait_type TEXT,
            original_name TEXT,
            custom_name TEXT,
            description TEXT,
            message_ratio REAL,
            message_threshold INTEGER,
            reaction_threshold INTEGER,
            voice_ratio REAL,
            voice_threshold INTEGER,
            stream_threshold INTEGER,
            deafen_ratio REAL,
            deafen_threshold INTEGER,
            UNIQUE(admin_id, server_id, trait_type, original_name)
        )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                message_count INTEGER DEFAULT 0,
                reaction_count INTEGER DEFAULT 0,
                voice_time INTEGER DEFAULT 0,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, guild_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mentioned_user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                mention_count INTEGER DEFAULT 0,
                last_mention TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, mentioned_user_id, guild_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_card_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                server_id INTEGER NOT NULL,
                settings TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, server_id)
            )
        ''')
        
        self.db.commit()