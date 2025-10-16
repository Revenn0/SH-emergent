# 📦 DATABASE MIGRATION GUIDE

Este guia mostra como migrar todos os dados do seu banco antigo para o novo Neon PostgreSQL.

---

## 🎯 OPÇÃO 1: MIGRAÇÃO AUTOMÁTICA (RECOMENDADO)

### Passo 1: Configurar URLs dos Bancos

Edite `backend/.env` e adicione a URL do banco ANTIGO:

```bash
# Banco ANTIGO (Replit ou outro)
OLD_DATABASE_URL=postgresql://old_user:old_pass@old_host/old_db

# Banco NOVO (Neon - já configurado)
DATABASE_URL=postgresql://neondb_owner:npg_pn2Rbyv4ElIG@ep-sweet-sea-absj090r-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

### Passo 2: Executar Script de Migração

```bash
python migrate_database.py
```

O script irá:
- ✅ Conectar aos dois bancos
- ✅ Migrar todas as tabelas em ordem
- ✅ Atualizar sequences automaticamente
- ✅ Mostrar progresso em tempo real

---

## 🎯 OPÇÃO 2: MIGRAÇÃO MANUAL COM SQL

### Passo 1: Exportar Dados do Banco Antigo

```bash
# Conecte ao banco antigo e execute:
pg_dump -h OLD_HOST -U OLD_USER -d OLD_DATABASE \
  --data-only \
  --inserts \
  --table=users \
  --table=tracker_alerts \
  --table=sync_checkpoints \
  --table=bikes \
  --table=bike_notes \
  --table=email_sync_runs \
  --table=refresh_tokens \
  > migration_data.sql
```

### Passo 2: Importar para Neon

```bash
psql "postgresql://neondb_owner:npg_pn2Rbyv4ElIG@ep-sweet-sea-absj090r-pooler.eu-west-2.aws.neon.tech/neondb?sslmode=require" \
  -f migration_data.sql
```

---

## 🎯 OPÇÃO 3: MIGRAÇÃO VIA INTERFACE WEB

Se você estiver usando Replit Database ou outra interface web:

### Passo 1: Exportar via Interface

1. Acesse o painel do seu banco antigo
2. Use a opção "Export" ou "Backup"
3. Escolha formato SQL ou CSV

### Passo 2: Importar no Neon

1. Acesse: https://console.neon.tech
2. Selecione seu projeto `neondb`
3. Use "SQL Editor" ou "Import"
4. Cole/Upload os dados exportados

---

## 🔍 VERIFICAÇÃO PÓS-MIGRAÇÃO

Após migrar, execute estas queries para verificar:

```sql
-- Verificar contagem de registros
SELECT 'users' as table_name, COUNT(*) FROM users
UNION ALL
SELECT 'tracker_alerts', COUNT(*) FROM tracker_alerts
UNION ALL
SELECT 'sync_checkpoints', COUNT(*) FROM sync_checkpoints
UNION ALL
SELECT 'bikes', COUNT(*) FROM bikes
UNION ALL
SELECT 'bike_notes', COUNT(*) FROM bike_notes
UNION ALL
SELECT 'email_sync_runs', COUNT(*) FROM email_sync_runs
UNION ALL
SELECT 'refresh_tokens', COUNT(*) FROM refresh_tokens;

-- Verificar usuário admin
SELECT username, email, created_at FROM users WHERE username = 'admin';

-- Verificar alertas recentes
SELECT COUNT(*) FROM tracker_alerts 
WHERE created_at > NOW() - INTERVAL '7 days';
```

---

## ⚠️ TROUBLESHOOTING

### Erro: "Connection refused"
- Verifique se as credenciais do banco antigo estão corretas
- Confirme que o banco antigo está acessível

### Erro: "Duplicate key violation"
- Limpe o banco Neon antes de migrar:
  ```sql
  TRUNCATE users, tracker_alerts, sync_checkpoints, bikes, bike_notes, email_sync_runs, refresh_tokens CASCADE;
  ```

### Erro: "Foreign key constraint"
- O script já migra em ordem correta
- Se necessário, desabilite constraints temporariamente:
  ```sql
  SET session_replication_role = 'replica';
  -- importar dados aqui
  SET session_replication_role = 'origin';
  ```

---

## ✅ CHECKLIST FINAL

Após a migração:

- [ ] Todos os usuários foram migrados
- [ ] Todos os alertas foram migrados
- [ ] As bikes estão todas presentes
- [ ] Login funciona com as credenciais antigas
- [ ] Dashboard mostra os dados corretos
- [ ] Atualizar `backend/.env` (remover OLD_DATABASE_URL)
- [ ] Reiniciar backend: `Backend workflow`

---

## 🆘 SUPORTE

Se tiver problemas:

1. Execute o script de migração novamente (é seguro)
2. Verifique os logs do script para erros específicos
3. Use a opção manual com pg_dump se o script falhar

**Importante**: O script usa `ON CONFLICT DO NOTHING`, então é seguro executar múltiplas vezes!
