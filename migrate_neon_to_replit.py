#!/usr/bin/env python3
"""
Script to migrate data from Neon PostgreSQL to Replit PostgreSQL
"""
import asyncpg
import asyncio
import os
from datetime import datetime

# Neon database URL (old database)
NEON_URL = "postgresql://neondb_owner:npg_pn2Rbyv4ElIG@ep-sweet-sea-absj090r-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Replit database URL (new database)
REPLIT_URL = os.environ.get('DATABASE_URL')

async def get_table_count(conn, table_name):
    """Get count of rows in a table"""
    try:
        result = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
        return result
    except Exception as e:
        print(f"  ⚠️  Error counting {table_name}: {e}")
        return 0

async def check_neon_data():
    """Check what data exists in Neon"""
    print("\n📊 Verificando dados no Neon...")
    print("-" * 50)
    
    try:
        neon_conn = await asyncpg.connect(NEON_URL)
        
        tables = ['users', 'tracker_alerts', 'bikes', 'bike_notes', 
                  'sync_checkpoints', 'email_sync_runs', 'refresh_tokens']
        
        total_rows = 0
        table_counts = {}
        
        for table in tables:
            count = await get_table_count(neon_conn, table)
            table_counts[table] = count
            total_rows += count
            print(f"  {table:20} {count:>8} rows")
        
        await neon_conn.close()
        
        print("-" * 50)
        print(f"  Total:              {total_rows:>8} rows")
        
        return table_counts, total_rows
        
    except Exception as e:
        print(f"❌ Erro ao conectar no Neon: {e}")
        return {}, 0

async def migrate_table(neon_conn, replit_conn, table_name, batch_size=100):
    """Migrate data from one table to another"""
    print(f"\n📦 Migrando tabela: {table_name}")
    
    try:
        # Get all data from Neon
        rows = await neon_conn.fetch(f"SELECT * FROM {table_name}")
        
        if not rows:
            print(f"  ✓ Tabela {table_name} vazia, nada a migrar")
            return 0
        
        # Get column names
        columns = list(rows[0].keys())
        
        # Prepare insert query
        placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
        columns_str = ', '.join(columns)
        
        # Insert in batches
        migrated = 0
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            
            for row in batch:
                values = [row[col] for col in columns]
                try:
                    await replit_conn.execute(
                        f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING",
                        *values
                    )
                    migrated += 1
                except Exception as e:
                    print(f"  ⚠️  Erro ao inserir linha: {e}")
        
        print(f"  ✓ {migrated} rows migradas com sucesso")
        return migrated
        
    except Exception as e:
        print(f"  ❌ Erro ao migrar {table_name}: {e}")
        return 0

async def migrate_all_data():
    """Main migration function"""
    print("\n" + "="*50)
    print("🚀 MIGRAÇÃO NEON → REPLIT")
    print("="*50)
    
    # Check Neon data first
    table_counts, total = await check_neon_data()
    
    if total == 0:
        print("\n⚠️  Nenhum dado encontrado no Neon para migrar")
        return
    
    print(f"\n📋 Serão migradas {total} rows no total")
    
    # Connect to both databases
    print("\n🔌 Conectando aos bancos de dados...")
    neon_conn = await asyncpg.connect(NEON_URL)
    replit_conn = await asyncpg.connect(REPLIT_URL)
    
    print("  ✓ Conectado ao Neon")
    print("  ✓ Conectado ao Replit")
    
    # Migrate tables in order (respecting foreign keys)
    tables_order = [
        'users',
        'refresh_tokens',
        'tracker_alerts', 
        'bikes',
        'bike_notes',
        'sync_checkpoints',
        'email_sync_runs'
    ]
    
    total_migrated = 0
    
    print("\n" + "="*50)
    print("📤 Iniciando migração...")
    print("="*50)
    
    for table in tables_order:
        if table in table_counts and table_counts[table] > 0:
            migrated = await migrate_table(neon_conn, replit_conn, table)
            total_migrated += migrated
    
    # Close connections
    await neon_conn.close()
    await replit_conn.close()
    
    print("\n" + "="*50)
    print(f"✅ MIGRAÇÃO CONCLUÍDA!")
    print(f"   Total migrado: {total_migrated} rows")
    print("="*50 + "\n")

async def verify_migration():
    """Verify data in Replit database after migration"""
    print("\n🔍 Verificando dados migrados no Replit...")
    print("-" * 50)
    
    try:
        replit_conn = await asyncpg.connect(REPLIT_URL)
        
        tables = ['users', 'tracker_alerts', 'bikes', 'bike_notes', 
                  'sync_checkpoints', 'email_sync_runs', 'refresh_tokens']
        
        total_rows = 0
        
        for table in tables:
            count = await get_table_count(replit_conn, table)
            total_rows += count
            print(f"  {table:20} {count:>8} rows")
        
        await replit_conn.close()
        
        print("-" * 50)
        print(f"  Total:              {total_rows:>8} rows")
        
    except Exception as e:
        print(f"❌ Erro ao verificar dados: {e}")

if __name__ == "__main__":
    print(f"\n⏰ Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    asyncio.run(migrate_all_data())
    asyncio.run(verify_migration())
    print(f"⏰ Finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
