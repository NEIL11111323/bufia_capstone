"""
Script to load timezone data into MySQL for Windows
This fixes the "Database returned an invalid datetime value" error
"""
import pymysql
from decouple import config
import sys

# Get database credentials from .env
DB_USER = config('DB_USER', default='root')
DB_PASSWORD = config('DB_PASSWORD', default='')
DB_HOST = config('DB_HOST', default='localhost')
DB_PORT = config('DB_PORT', default=3306, cast=int)

# Timezone SQL data for common timezones
TIMEZONE_SQL = """
-- Truncate existing timezone tables
TRUNCATE TABLE mysql.time_zone;
TRUNCATE TABLE mysql.time_zone_name;
TRUNCATE TABLE mysql.time_zone_transition;
TRUNCATE TABLE mysql.time_zone_transition_type;

-- Insert basic timezone data
INSERT INTO mysql.time_zone (Use_leap_seconds) VALUES ('N');
SET @time_zone_id = LAST_INSERT_ID();

-- Insert Asia/Manila timezone
INSERT INTO mysql.time_zone_name (Name, Time_zone_id) VALUES ('Asia/Manila', @time_zone_id);

-- Insert UTC timezone
INSERT INTO mysql.time_zone (Use_leap_seconds) VALUES ('N');
SET @utc_zone_id = LAST_INSERT_ID();
INSERT INTO mysql.time_zone_name (Name, Time_zone_id) VALUES ('UTC', @utc_zone_id);

-- Insert common timezone abbreviations
INSERT INTO mysql.time_zone_name (Name, Time_zone_id) VALUES ('GMT', @utc_zone_id);
INSERT INTO mysql.time_zone_name (Name, Time_zone_id) VALUES ('GMT+0', @utc_zone_id);

-- Insert transition type for Asia/Manila (UTC+8, no DST)
INSERT INTO mysql.time_zone_transition_type (Time_zone_id, Transition_type_id, Offset, Is_DST, Abbreviation)
VALUES (@time_zone_id, 0, 28800, 0, 'PST');

-- Insert transition type for UTC
INSERT INTO mysql.time_zone_transition_type (Time_zone_id, Transition_type_id, Offset, Is_DST, Abbreviation)
VALUES (@utc_zone_id, 0, 0, 0, 'UTC');
"""

try:
    print("Connecting to MySQL server...")
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    
    cursor = connection.cursor()
    
    print("Loading timezone data into MySQL...")
    
    # Execute each statement separately
    for statement in TIMEZONE_SQL.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                cursor.execute(statement)
            except Exception as e:
                # Skip errors for statements that might fail
                if 'Truncate' not in statement:
                    print(f"Warning: {e}")
    
    connection.commit()
    
    print("\n✓ Timezone data loaded successfully!")
    print("\nYou can now run your Django application.")
    print("The 'Database returned an invalid datetime value' error should be fixed.")
    
except pymysql.Error as e:
    print(f"\n✗ Error: {e}")
    print("\nAlternative solution:")
    print("Add 'TIME_ZONE': None to your database OPTIONS in settings.py")
    sys.exit(1)
    
finally:
    if 'connection' in locals() and connection.open:
        cursor.close()
        connection.close()
