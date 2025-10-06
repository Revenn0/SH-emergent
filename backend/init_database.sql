-- ============================================================
-- MOTORCYCLE TRACKER - DATABASE INITIALIZATION SCRIPT
-- ============================================================
-- Este script cria todas as tabelas necessárias e o usuário admin
-- Execute este script manualmente no banco de produção se necessário
-- ============================================================

-- 1. Criar tabela de usuários
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR,
    gmail_email VARCHAR,
    gmail_app_password VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Criar tabela de alertas do tracker
CREATE TABLE IF NOT EXISTS tracker_alerts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    email_id VARCHAR NOT NULL,
    alert_type VARCHAR,
    alert_time VARCHAR,
    location VARCHAR,
    latitude VARCHAR,
    longitude VARCHAR,
    device_serial VARCHAR,
    tracker_name VARCHAR,
    account_name VARCHAR,
    raw_body TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR DEFAULT 'New',
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMP,
    acknowledged_by VARCHAR,
    notes TEXT,
    assigned_to VARCHAR,
    favorite BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, email_id)
);

-- 3. Criar tabela de checkpoints de sincronização
CREATE TABLE IF NOT EXISTS sync_checkpoints (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL UNIQUE,
    last_email_id VARCHAR,
    last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Criar tabela de histórico de sincronizações
CREATE TABLE IF NOT EXISTS email_sync_runs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    source VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    emails_read INTEGER DEFAULT 0,
    emails_new INTEGER DEFAULT 0,
    error_summary TEXT,
    log_json TEXT
);

-- 5. Criar usuário admin (username: admin, password: dimension)
-- IMPORTANTE: Se você já tem um usuário admin, este comando não fará nada
-- Se quiser resetar a senha do admin, delete a linha existente primeiro
INSERT INTO users (id, username, email, password_hash, full_name)
VALUES (
    gen_random_uuid()::text,
    'admin',
    'admin@tracker.com',
    '$argon2id$v=19$m=65536,t=3,p=4$f+/9f2+tNSbkvBdCqLXWug$71qoWgl2+HskI16Wg48mG0iDoHVQzu+/422m5tKaOeM',
    'Administrator'
)
ON CONFLICT (username) DO NOTHING;

-- ============================================================
-- VERIFICAÇÃO - Execute estas queries para confirmar
-- ============================================================

-- Verificar se as tabelas foram criadas
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Verificar se o usuário admin existe
SELECT id, username, email, full_name FROM users WHERE username = 'admin';

-- ============================================================
-- RESULTADO ESPERADO:
-- - 4 tabelas: users, tracker_alerts, sync_checkpoints, email_sync_runs
-- - 1 usuário admin com username='admin'
-- ============================================================
