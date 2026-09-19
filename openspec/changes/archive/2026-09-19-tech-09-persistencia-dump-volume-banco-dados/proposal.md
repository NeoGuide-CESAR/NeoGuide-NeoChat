# Proposal: TECH-09 - Persistência do PostgreSQL via Bind Mount no Repositório

## Context
Atualmente, o serviço `lumi-db` no `docker-compose.yml` utiliza um volume gerenciado global do Docker (`lumi_pgdata`) mapeado em `/var/lib/postgresql/data`. Volumes nomeados do Docker são armazenados internamente pelo daemon do Docker (geralmente em `/var/lib/docker/volumes` no Linux ou no subsistema WSL2/Hyper-V no Windows), o que dificulta inspeções diretas, backups simples por cópia de arquivo e o versionamento ou reset rápido da base de dados local durante o ciclo de desenvolvimento da equipe.

## Motivation & Value
Substituir o volume nomeado `lumi_pgdata` por um bind mount direto apontando para a pasta física `./docker/data` na raiz do repositório:
- Proporciona transparência total sobre onde os arquivos de dados do PostgreSQL e pgvector estão fisicamente persistidos.
- Permite backup, inspeção e exclusão manual ou programática imediata da pasta `./docker/data` para reset completo do banco local sem necessitar de comandos especiais de gerenciamento de volumes (`docker volume rm`).
- Garante conformidade e reprodutibilidade de setup local mantendo a pasta `./docker/data/` rastreada no Git através de `.gitkeep`, enquanto ignora os arquivos internos gerados pelo PostgreSQL via `.gitignore`.

## Scope
### In-Scope
- Atualizar `docker-compose.yml`:
  - Configurar bind mount `./docker/data:/var/lib/postgresql/data` no serviço `lumi-db`.
  - Remover a declaração do volume gerenciado global `volumes: lumi_pgdata`.
- Criar a pasta `./docker/data/` com o arquivo de marcação `.gitkeep`.
- Atualizar `.gitignore` para ignorar o conteúdo interno gerado pelo PostgreSQL em `docker/data/*`, preservando `!docker/data/.gitkeep`.
- Atualizar `docs/08-CONFIGURACAO-E-EXECUCAO-LOCAL.md` e `README.md` refletindo o uso de bind mount `./docker/data`.
- Atualizar `tests/unit/test_docker_config.py` e criar `tests/unit/test_docker_persistence.py` para validar estaticamente a presença do bind mount e a ausência do volume nomeado `lumi_pgdata`.

### Out-of-Scope
- Alterações em drivers de produção ou provedores de nuvem gerenciados (AWS RDS, Supabase, Neon).
- Modificação nas migrações do Alembic ou nos schemas do banco de dados.
