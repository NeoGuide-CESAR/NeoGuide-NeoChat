# Design: TECH-09 - Persistência do PostgreSQL via Bind Mount no Repositório

## Architecture Decisions

### 1. Bind Mount vs Named Volume
- **Decisão:** Utilizar bind mount relativo `./docker/data:/var/lib/postgresql/data` no serviço `lumi-db` do Docker Compose.
- **Justificativa:** O bind mount mantém os dados no diretório local do projeto, facilitando inspeções diretas, limpeza atômica da base em desenvolvimento e persistência visível ao desenvolvedor.

### 2. Tratamento no Git e Estrutura de Diretórios
- **Decisão:**
  - Criar o diretório `docker/data/` contendo um arquivo `.gitkeep` vazio para assegurar que a pasta exista ao clonar o repositório.
  - Atualizar o `.gitignore` na raiz com:
    ```gitignore
    # Docker — dados persistentes do banco local
    docker/data/*
    !docker/data/.gitkeep
    ```
- **Justificativa:** Evita que os arquivos binários pesados e dependentes de plataforma do cluster PostgreSQL (WAL, tabelas, catálogos) sejam versionados acidentalmente no repositório Git, mantendo apenas a estrutura da pasta.

### 3. Remoção do Volume Global `lumi_pgdata`
- **Decisão:** Remover a seção `volumes:` do nível raiz do `docker-compose.yml` que continha `lumi_pgdata: driver: local`.
- **Justificativa:** Eliminar artefatos legados ou configurações órfãs no Docker Compose, prevenindo confusão na equipe.

### 4. Validação Automatizada (TDD)
- **Decisão:** Implementar testes estáticos de configuração em `tests/unit/test_docker_persistence.py` usando parse do arquivo e `pathlib.Path` para garantir:
  1. A pasta `docker/data` existe no projeto e contém `.gitkeep`.
  2. `docker-compose.yml` mapeia `./docker/data:/var/lib/postgresql/data` para o serviço `lumi-db`.
  3. `docker-compose.yml` não declara `lumi_pgdata` nem como volume do serviço nem como volume de primeiro nível.
  4. `.gitignore` contém as regras para ignorar os dados de `docker/data/*` preservando `.gitkeep`.
