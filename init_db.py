import sqlite3

def create_database():
    conn = sqlite3.connect('cricket_data.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL,
            country TEXT,
            batting_style TEXT,
            bowling_style TEXT,
            speciality TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_traits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            trait_type TEXT NOT NULL,
            description TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS batting_innings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batter_name TEXT NOT NULL,
            runs INTEGER NOT NULL,
            format TEXT NOT NULL,
            opposition TEXT,
            venue TEXT,
            result TEXT,
            vs_bowler TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bowling_spells (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bowler_name TEXT NOT NULL,
            wickets INTEGER NOT NULL,
            format TEXT NOT NULL,
            opposition TEXT,
            venue TEXT,
            economy REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS format_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bowler_name TEXT NOT NULL,
            format TEXT NOT NULL,
            avg_economy REAL,
            avg_wickets REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS head_to_head (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batter_name TEXT NOT NULL,
            bowler_name TEXT NOT NULL,
            innings INTEGER,
            dismissals INTEGER,
            runs_conceded INTEGER,
            avg_conceded REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS venues (
            venue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            pace TEXT,
            bounce TEXT,
            spin TEXT,
            swing TEXT,
            favours TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("Database and all tables created successfully!")

if __name__ == '__main__':
    create_database()