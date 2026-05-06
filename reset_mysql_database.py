"""
Script to drop and recreate MySQL database for fresh migration
"""
import pymysql
from decouple import config

# Get database credentials from .env
DB_NAME = config('DB_NAME', default='bufia_db')
DB_USER = config('DB_USER', default='root')
DB_PASSWORD = config('DB_PASSWORD', default='')
DB_HOST = config('DB_HOST', default='localhost')
DB_PORT = config('DB_PORT', default=3306, cast=int)

try:
    # Connect to MySQL server (not to specific database)
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    
    cursor = connection.cursor()
    
    # Drop database if exists
    print(f"Dropping database '{DB_NAME}' if it exists...")
    cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
    
    # Create fresh database
    print(f"Creating database '{DB_NAME}'...")
    cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    
    connection.commit()
    print(f"\n✓ Database '{DB_NAME}' has been reset successfully!")
    print("\nNext steps:")
    print("1. Run: py manage.py migrate")
    print("2. Run: py manage.py createsuperuser")
    
except pymysql.Error as e:
    print(f"\n✗ Error: {e}")
    print("\nTroubleshooting:")
    print("- Check your .env file has correct DB_USER and DB_PASSWORD")
    print("- Verify MySQL service is running")
    print("- Ensure the user has permission to create/drop databases")
    
finally:
    if 'connection' in locals() and connection.open:
        cursor.close()
        connection.close()
