/*
================================================================================
SCRIPT DE MIGRAÇÃO PARA PRODUÇÃO - TRACKER ALERT SYSTEM
================================================================================

OBJETIVO:
Este script migra todos os dados do banco de desenvolvimento para o banco de 
produção, incluindo estrutura de tabelas e dados existentes.

IMPORTANTE - LEIA ANTES DE EXECUTAR:
1. FAÇA BACKUP COMPLETO do banco de produção antes de executar
2. Teste este script em um ambiente de staging primeiro
3. Execute as partes na ordem indicada
4. Não interrompa a execução durante uma transação
5. Verifique os logs após cada etapa

ESTRUTURA DO SCRIPT:
- PARTE 1: Criar estrutura de tabelas no banco de produção
- PARTE 2: Exportar dados do banco de desenvolvimento (executar no DEV)
- PARTE 3: Importar dados no banco de produção (executar no PROD)
- PARTE 4: Validação e verificação de integridade

COMO CONECTAR AOS BANCOS DE DADOS:
- Desenvolvimento: psql $DATABASE_URL (variável de ambiente do Replit)
- Produção: psql "postgresql://usuario:senha@host:porta/database"

ORDEM DE EXECUÇÃO:
1. Conectar ao banco de PRODUÇÃO e executar PARTE 1
2. Conectar ao banco de DESENVOLVIMENTO e executar PARTE 2
3. Copiar os dados gerados da PARTE 2
4. Conectar ao banco de PRODUÇÃO e executar PARTE 3
5. Executar PARTE 4 para validar

================================================================================
*/


-- ============================================================================
-- PARTE 1: CRIAR ESTRUTURA DE TABELAS (EXECUTAR NO BANCO DE PRODUÇÃO)
-- ============================================================================

/*
Esta seção cria todas as tabelas necessárias no banco de produção.
Use CREATE TABLE IF NOT EXISTS para evitar erros se as tabelas já existirem.
*/

BEGIN;

-- Tabela de Usuários
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

COMMENT ON TABLE users IS 'Armazena informações de usuários do sistema';
COMMENT ON COLUMN users.gmail_email IS 'Email do Gmail para sincronização IMAP';
COMMENT ON COLUMN users.gmail_app_password IS 'App Password do Gmail (criptografado)';

-- Tabela de Alertas do Tracker
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
    UNIQUE(user_id, email_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE tracker_alerts IS 'Armazena alertas de rastreamento sincronizados do Gmail';
COMMENT ON CONSTRAINT tracker_alerts_user_id_email_id_key ON tracker_alerts IS 'Garante que não haja alertas duplicados por usuário';

-- Índices para melhor performance
CREATE INDEX IF NOT EXISTS idx_tracker_alerts_user_id ON tracker_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_tracker_alerts_status ON tracker_alerts(status);
CREATE INDEX IF NOT EXISTS idx_tracker_alerts_created_at ON tracker_alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tracker_alerts_alert_type ON tracker_alerts(alert_type);

-- Tabela de Checkpoints de Sincronização
CREATE TABLE IF NOT EXISTS sync_checkpoints (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL UNIQUE,
    last_email_id VARCHAR,
    last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE sync_checkpoints IS 'Controla o ponto de sincronização de emails para cada usuário';
COMMENT ON COLUMN sync_checkpoints.last_email_id IS 'ID do último email sincronizado para controle incremental';

-- Tabela de Histórico de Sincronização
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
    log_json TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE email_sync_runs IS 'Log de execuções de sincronização de email';

CREATE INDEX IF NOT EXISTS idx_email_sync_runs_user_id ON email_sync_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_email_sync_runs_started_at ON email_sync_runs(started_at DESC);

-- Tabela de Refresh Tokens (Sistema de Autenticação por Cookies)
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    token_hash VARCHAR NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

COMMENT ON TABLE refresh_tokens IS 'Armazena hashes de refresh tokens para autenticação JWT';
COMMENT ON COLUMN refresh_tokens.token_hash IS 'Hash SHA256 do refresh token para validação segura';

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

COMMIT;

/*
PARTE 1 CONCLUÍDA - Estrutura de tabelas criada com sucesso
Verifique se todas as tabelas foram criadas:
  \dt - lista todas as tabelas
  \d users - mostra estrutura da tabela users
*/


-- ============================================================================
-- PARTE 2: EXPORTAR DADOS DO DESENVOLVIMENTO (EXECUTAR NO BANCO DE DEV)
-- ============================================================================

/*
INSTRUÇÕES:
1. Conecte-se ao banco de DESENVOLVIMENTO
2. Execute os comandos abaixo
3. Salve os resultados em arquivos separados ou copie para usar na PARTE 3

IMPORTANTE: 
- Os dados sensíveis (senhas) já estão em formato hash, é seguro exportar
- NÃO exporte a tabela refresh_tokens (tokens expiram, serão recriados)
*/

-- Exportar Usuários
-- Salvar resultado como: users_data.sql
SELECT 
    'INSERT INTO users (id, username, email, password_hash, full_name, gmail_email, gmail_app_password, created_at, updated_at) VALUES ' ||
    string_agg(
        format('(%L, %L, %L, %L, %L, %L, %L, %L, %L)',
            id, username, email, password_hash, full_name, 
            gmail_email, gmail_app_password, created_at, updated_at
        ),
        ', ' || E'\n'
    ) || ';' as insert_statement
FROM users;

-- Exportar Alertas do Tracker
-- Salvar resultado como: tracker_alerts_data.sql
-- NOTA: Exportar em lotes se houver muitos registros (>10000)
SELECT 
    'INSERT INTO tracker_alerts (id, user_id, email_id, alert_type, alert_time, location, latitude, longitude, device_serial, tracker_name, account_name, raw_body, created_at, status, acknowledged, acknowledged_at, acknowledged_by, notes, assigned_to, favorite) VALUES ' ||
    string_agg(
        format('(%L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L, %L)',
            id, user_id, email_id, alert_type, alert_time, location, 
            latitude, longitude, device_serial, tracker_name, account_name,
            raw_body, created_at, status, acknowledged, acknowledged_at,
            acknowledged_by, notes, assigned_to, favorite
        ),
        ', ' || E'\n'
    ) || ';' as insert_statement
FROM tracker_alerts;

-- Se houver muitos alertas, exportar em lotes de 1000:
-- WHERE id BETWEEN 1 AND 1000
-- WHERE id BETWEEN 1001 AND 2000
-- etc.

-- Exportar Checkpoints de Sincronização
-- Salvar resultado como: sync_checkpoints_data.sql
SELECT 
    'INSERT INTO sync_checkpoints (id, user_id, last_email_id, last_sync_at) VALUES ' ||
    string_agg(
        format('(%L, %L, %L, %L)',
            id, user_id, last_email_id, last_sync_at
        ),
        ', ' || E'\n'
    ) || ';' as insert_statement
FROM sync_checkpoints;

-- Exportar Histórico de Sincronização
-- Salvar resultado como: email_sync_runs_data.sql
SELECT 
    'INSERT INTO email_sync_runs (id, user_id, started_at, completed_at, source, status, emails_read, emails_new, error_summary, log_json) VALUES ' ||
    string_agg(
        format('(%L, %L, %L, %L, %L, %L, %L, %L, %L, %L)',
            id, user_id, started_at, completed_at, source, status,
            emails_read, emails_new, error_summary, log_json
        ),
        ', ' || E'\n'
    ) || ';' as insert_statement
FROM email_sync_runs;

-- Verificação: Contagem de registros a serem exportados
SELECT 'users' as tabela, COUNT(*) as total FROM users
UNION ALL
SELECT 'tracker_alerts', COUNT(*) FROM tracker_alerts
UNION ALL
SELECT 'sync_checkpoints', COUNT(*) FROM sync_checkpoints
UNION ALL
SELECT 'email_sync_runs', COUNT(*) FROM email_sync_runs;

/*
PARTE 2 CONCLUÍDA - Dados exportados
Copie os resultados dos SELECT acima para usar na PARTE 3
*/


-- ============================================================================
-- PARTE 3: IMPORTAR DADOS NO PRODUÇÃO (EXECUTAR NO BANCO DE PROD)
-- ============================================================================

/*
INSTRUÇÕES:
1. Conecte-se ao banco de PRODUÇÃO
2. Cole os comandos INSERT gerados na PARTE 2 entre BEGIN e COMMIT
3. Execute a transação completa
4. Em caso de erro, a transação será revertida automaticamente

IMPORTANTE:
- Use ON CONFLICT para evitar duplicação de dados
- A ordem de importação é importante devido às Foreign Keys
*/

BEGIN;

-- Desabilitar triggers temporariamente (opcional, para performance)
-- SET session_replication_role = replica;

-- ============================================
-- 3.1 - IMPORTAR USUÁRIOS
-- ============================================
-- Cole aqui o resultado de users_data.sql da PARTE 2
-- Use ON CONFLICT para atualizar se o usuário já existir

-- EXEMPLO (substitua pelos dados reais):
-- INSERT INTO users (id, username, email, password_hash, full_name, gmail_email, gmail_app_password, created_at, updated_at) 
-- VALUES 
--   ('uuid-1', 'admin', 'admin@tracker.com', 'hash...', 'Administrator', NULL, NULL, '2025-01-01', '2025-01-01')
-- ON CONFLICT (id) DO UPDATE SET
--   username = EXCLUDED.username,
--   email = EXCLUDED.email,
--   password_hash = EXCLUDED.password_hash,
--   full_name = EXCLUDED.full_name,
--   gmail_email = EXCLUDED.gmail_email,
--   gmail_app_password = EXCLUDED.gmail_app_password,
--   updated_at = CURRENT_TIMESTAMP;

-- ============================================
-- 3.2 - IMPORTAR ALERTAS DO TRACKER
-- ============================================
-- Cole aqui o resultado de tracker_alerts_data.sql da PARTE 2
-- Use ON CONFLICT DO NOTHING para evitar duplicação

-- EXEMPLO (substitua pelos dados reais):
-- INSERT INTO tracker_alerts (id, user_id, email_id, alert_type, ...) 
-- VALUES (...)
-- ON CONFLICT (user_id, email_id) DO NOTHING;

-- Resetar a sequência do ID após importação
SELECT setval('tracker_alerts_id_seq', (SELECT MAX(id) FROM tracker_alerts));

-- ============================================
-- 3.3 - IMPORTAR CHECKPOINTS
-- ============================================
-- Cole aqui o resultado de sync_checkpoints_data.sql da PARTE 2

-- EXEMPLO (substitua pelos dados reais):
-- INSERT INTO sync_checkpoints (id, user_id, last_email_id, last_sync_at)
-- VALUES (...)
-- ON CONFLICT (user_id) DO UPDATE SET
--   last_email_id = EXCLUDED.last_email_id,
--   last_sync_at = EXCLUDED.last_sync_at;

-- Resetar a sequência do ID após importação
SELECT setval('sync_checkpoints_id_seq', (SELECT MAX(id) FROM sync_checkpoints));

-- ============================================
-- 3.4 - IMPORTAR HISTÓRICO DE SINCRONIZAÇÃO
-- ============================================
-- Cole aqui o resultado de email_sync_runs_data.sql da PARTE 2

-- EXEMPLO (substitua pelos dados reais):
-- INSERT INTO email_sync_runs (id, user_id, started_at, completed_at, source, status, emails_read, emails_new, error_summary, log_json)
-- VALUES (...)
-- ON CONFLICT (id) DO NOTHING;

-- Resetar a sequência do ID após importação
SELECT setval('email_sync_runs_id_seq', (SELECT MAX(id) FROM email_sync_runs));

-- Reabilitar triggers (se foram desabilitados)
-- SET session_replication_role = DEFAULT;

COMMIT;

/*
PARTE 3 CONCLUÍDA - Dados importados
Se houve erro, a transação foi revertida (ROLLBACK automático)
Caso contrário, os dados foram importados com sucesso (COMMIT)
*/


-- ============================================================================
-- PARTE 4: VALIDAÇÃO E VERIFICAÇÃO (EXECUTAR NO BANCO DE PROD)
-- ============================================================================

/*
Execute os comandos abaixo para validar a migração
*/

-- ============================================
-- 4.1 - CONTAGEM DE REGISTROS
-- ============================================
SELECT 
    'CONTAGEM DE REGISTROS APÓS MIGRAÇÃO' as descricao;

SELECT 'users' as tabela, COUNT(*) as total FROM users
UNION ALL
SELECT 'tracker_alerts', COUNT(*) FROM tracker_alerts
UNION ALL
SELECT 'sync_checkpoints', COUNT(*) FROM sync_checkpoints
UNION ALL
SELECT 'email_sync_runs', COUNT(*) FROM email_sync_runs
UNION ALL
SELECT 'refresh_tokens', COUNT(*) FROM refresh_tokens;

-- Compare com a contagem da PARTE 2 (exceto refresh_tokens que está vazio)

-- ============================================
-- 4.2 - VERIFICAR USUÁRIO ADMIN
-- ============================================
SELECT 
    'VERIFICAÇÃO DO USUÁRIO ADMIN' as descricao;

SELECT 
    id, 
    username, 
    email, 
    full_name,
    created_at,
    CASE 
        WHEN gmail_email IS NOT NULL THEN 'Gmail Conectado'
        ELSE 'Gmail Não Conectado'
    END as status_gmail
FROM users 
WHERE username = 'admin';

-- Deve retornar pelo menos 1 registro (usuário admin)

-- ============================================
-- 4.3 - VERIFICAR INTEGRIDADE DAS FOREIGN KEYS
-- ============================================
SELECT 
    'VERIFICAÇÃO DE INTEGRIDADE - FOREIGN KEYS' as descricao;

-- Verificar se todos os tracker_alerts têm usuários válidos
SELECT 
    'Alertas órfãos (sem usuário)' as verificacao,
    COUNT(*) as quantidade
FROM tracker_alerts ta
LEFT JOIN users u ON ta.user_id = u.id
WHERE u.id IS NULL;

-- Deve retornar 0

-- Verificar se todos os sync_checkpoints têm usuários válidos
SELECT 
    'Checkpoints órfãos (sem usuário)' as verificacao,
    COUNT(*) as quantidade
FROM sync_checkpoints sc
LEFT JOIN users u ON sc.user_id = u.id
WHERE u.id IS NULL;

-- Deve retornar 0

-- Verificar se todos os email_sync_runs têm usuários válidos
SELECT 
    'Sync runs órfãos (sem usuário)' as verificacao,
    COUNT(*) as quantidade
FROM email_sync_runs esr
LEFT JOIN users u ON esr.user_id = u.id
WHERE u.id IS NULL;

-- Deve retornar 0

-- ============================================
-- 4.4 - VERIFICAR CONSTRAINTS ÚNICOS
-- ============================================
SELECT 
    'VERIFICAÇÃO DE CONSTRAINTS ÚNICOS' as descricao;

-- Verificar duplicatas de username
SELECT 
    'Usernames duplicados' as verificacao,
    username, 
    COUNT(*) as quantidade
FROM users
GROUP BY username
HAVING COUNT(*) > 1;

-- Deve retornar 0 linhas

-- Verificar duplicatas de email
SELECT 
    'Emails duplicados' as verificacao,
    email, 
    COUNT(*) as quantidade
FROM users
GROUP BY email
HAVING COUNT(*) > 1;

-- Deve retornar 0 linhas

-- Verificar duplicatas de alertas
SELECT 
    'Alertas duplicados (user_id + email_id)' as verificacao,
    user_id,
    email_id,
    COUNT(*) as quantidade
FROM tracker_alerts
GROUP BY user_id, email_id
HAVING COUNT(*) > 1;

-- Deve retornar 0 linhas

-- ============================================
-- 4.5 - VERIFICAR ÍNDICES
-- ============================================
SELECT 
    'VERIFICAÇÃO DE ÍNDICES' as descricao;

SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('users', 'tracker_alerts', 'sync_checkpoints', 'email_sync_runs', 'refresh_tokens')
ORDER BY tablename, indexname;

-- Deve mostrar todos os índices criados na PARTE 1

-- ============================================
-- 4.6 - ESTATÍSTICAS GERAIS
-- ============================================
SELECT 
    'ESTATÍSTICAS GERAIS DO SISTEMA' as descricao;

-- Alertas por tipo
SELECT 
    'Distribuição de Alertas por Tipo' as metrica,
    alert_type,
    COUNT(*) as quantidade
FROM tracker_alerts
GROUP BY alert_type
ORDER BY quantidade DESC;

-- Alertas por status
SELECT 
    'Distribuição de Alertas por Status' as metrica,
    status,
    COUNT(*) as quantidade
FROM tracker_alerts
GROUP BY status
ORDER BY quantidade DESC;

-- Usuários com Gmail conectado
SELECT 
    'Usuários com Gmail Conectado' as metrica,
    COUNT(*) as quantidade
FROM users
WHERE gmail_email IS NOT NULL;

-- ============================================
-- 4.7 - TESTE DE CONEXÃO DO SISTEMA
-- ============================================
/*
Para testar se o sistema pode se conectar ao banco de produção:

1. Atualize a variável DATABASE_URL no ambiente de produção
2. Inicie a aplicação
3. Tente fazer login com o usuário admin
4. Verifique os logs do servidor

Credenciais padrão do admin (se não alteradas):
- Username: admin
- Password: dimension
*/

-- ============================================
-- FIM DA VALIDAÇÃO
-- ============================================

/*
================================================================================
CHECKLIST PÓS-MIGRAÇÃO:
================================================================================

[ ] Todas as tabelas foram criadas com sucesso (PARTE 1)
[ ] Dados foram exportados do desenvolvimento (PARTE 2)
[ ] Dados foram importados na produção (PARTE 3)
[ ] Contagem de registros está correta (4.1)
[ ] Usuário admin existe e está acessível (4.2)
[ ] Não há registros órfãos (4.3)
[ ] Não há duplicatas (4.4)
[ ] Índices foram criados (4.5)
[ ] Sistema está funcionando na produção (4.7)
[ ] Backup foi realizado antes da migração
[ ] Documentação foi atualizada com nova conexão de produção

================================================================================
TROUBLESHOOTING:
================================================================================

ERRO: "duplicate key value violates unique constraint"
SOLUÇÃO: Use ON CONFLICT DO NOTHING ou DO UPDATE nos INSERTs

ERRO: "insert or update on table violates foreign key constraint"
SOLUÇÃO: Verifique a ordem de importação (users primeiro, depois as demais)

ERRO: "relation already exists"
SOLUÇÃO: Normal se a tabela já existe, continue com a próxima etapa

PERFORMANCE LENTA:
SOLUÇÃO: Desabilite triggers temporariamente ou importe em lotes menores

DADOS NÃO APARECEM NO SISTEMA:
SOLUÇÃO: Verifique DATABASE_URL, reinicie o servidor, limpe cache do browser

================================================================================
SUPORTE:
================================================================================

Em caso de problemas:
1. Verifique os logs do PostgreSQL
2. Verifique os logs da aplicação
3. Execute novamente a PARTE 4 (Validação)
4. Se necessário, faça ROLLBACK e restaure o backup

================================================================================
*/
