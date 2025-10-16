#!/usr/bin/env python3
"""
Database Migration Script
Migrates all data from old database to new Neon database
"""

import asyncpg
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

# Database URLs
OLD_DATABASE_URL = os.getenv('OLD_DATABASE_URL', os.getenv('DATABASE_URL'))
NEW_DATABASE_URL = os.getenv('DATABASE_URL')

async def migrate_database():
    """Migrate all data from old database to new database"""
    
    print("=" * 60)
    print("DATABASE MIGRATION SCRIPT")
    print("=" * 60)
    print()
    
    # Check URLs
    if not OLD_DATABASE_URL or not NEW_DATABASE_URL:
        print("❌ ERROR: Database URLs not found!")
        print("Please set OLD_DATABASE_URL and DATABASE_URL in backend/.env")
        return
    
    if OLD_DATABASE_URL == NEW_DATABASE_URL:
        print("⚠️  WARNING: OLD_DATABASE_URL and DATABASE_URL are the same!")
        confirm = input("Continue anyway? (yes/no): ")
        if confirm.lower() != 'yes':
            return
    
    print(f"Old Database: {OLD_DATABASE_URL[:30]}...")
    print(f"New Database: {NEW_DATABASE_URL[:30]}...")
    print()
    
    try:
        # Connect to both databases
        print("📡 Connecting to old database...")
        old_conn = await asyncpg.connect(OLD_DATABASE_URL)
        
        print("📡 Connecting to new database...")
        new_conn = await asyncpg.connect(NEW_DATABASE_URL)
        
        print("✅ Connected to both databases")
        print()
        
        # Tables to migrate (in order to respect foreign keys)
        tables = [
            'users',
            'tracker_alerts',
            'sync_checkpoints',
            'bikes',
            'bike_notes',
            'email_sync_runs',
            'refresh_tokens'
        ]
        
        total_migrated = 0
        
        for table in tables:
            print(f"📦 Migrating table: {table}")
            
            # Check if table exists in old database
            exists = await old_conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
                """,
                table
            )
            
            if not exists:
                print(f"   ⚠️  Table {table} does not exist in old database, skipping...")
                continue
            
            # Get count
            count = await old_conn.fetchval(f"SELECT COUNT(*) FROM {table}")
            print(f"   Found {count} rows")
            
            if count == 0:
                print(f"   ⏭️  No data to migrate")
                continue
            
            # Get all columns
            columns = await old_conn.fetch(
                """
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = $1
                ORDER BY ordinal_position
                """,
                table
            )
            column_names = [col['column_name'] for col in columns]
            
            # Fetch all data
            rows = await old_conn.fetch(f"SELECT * FROM {table}")
            
            # Insert into new database
            migrated = 0
            for row in rows:
                try:
                    # Build INSERT statement
                    cols = ', '.join(column_names)
                    placeholders = ', '.join([f'${i+1}' for i in range(len(column_names))])
                    values = [row[col] for col in column_names]
                    
                    query = f"""
                        INSERT INTO {table} ({cols})
                        VALUES ({placeholders})
                        ON CONFLICT DO NOTHING
                    """
                    
                    await new_conn.execute(query, *values)
                    migrated += 1
                except Exception as e:
                    print(f"   ⚠️  Error migrating row: {str(e)}")
            
            print(f"   ✅ Migrated {migrated}/{count} rows")
            total_migrated += migrated
            print()
        
        # Update sequences for serial columns
        print("🔄 Updating sequences...")
        for table in tables:
            try:
                # Get max id if table has serial id
                max_id = await new_conn.fetchval(f"""
                    SELECT COALESCE(MAX(id), 0) FROM {table} 
                    WHERE EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = '{table}' AND column_name = 'id'
                    )
                """)
                
                if max_id:
                    await new_conn.execute(f"""
                        SELECT setval(pg_get_serial_sequence('{table}', 'id'), {max_id + 1}, false)
                    """)
                    print(f"   ✅ Updated {table} sequence to {max_id + 1}")
            except Exception as e:
                # Table might not have serial id, skip
                pass
        
        print()
        print("=" * 60)
        print(f"✅ MIGRATION COMPLETE!")
        print(f"Total rows migrated: {total_migrated}")
        print("=" * 60)
        
        # Close connections
        await old_conn.close()
        await new_conn.close()
        
    except Exception as e:
        print()
        print("❌ MIGRATION FAILED!")
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_database())
