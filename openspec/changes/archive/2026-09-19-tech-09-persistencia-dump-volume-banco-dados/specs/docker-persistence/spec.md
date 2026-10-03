# Delta Spec: Persistência do PostgreSQL via Bind Mount

## ADDED Requirements

### Requirement: Persistência via Bind Mount no Repositório
O serviço de banco de dados `lumi-db` DEVE persistir seus dados relacionais e vetoriais em um bind mount apontando diretamente para o diretório local `./docker/data` dentro do repositório.

#### Scenario: Configuração do Volume no Docker Compose
- **GIVEN** o arquivo `docker-compose.yml` na raiz do projeto
- **WHEN** inspecionado o mapeamento de volumes do serviço `lumi-db`
- **THEN** o arquivo deve conter a montagem de volume `./docker/data:/var/lib/postgresql/data`
- **AND** a seção raiz `volumes:` não deve conter o volume nomeado `lumi_pgdata`.

#### Scenario: Estrutura da Pasta de Dados e Controle de Versão
- **GIVEN** a estrutura de diretórios do repositório
- **WHEN** inspecionado o diretório `docker/data/`
- **THEN** o diretório deve existir e conter o arquivo de marcação `.gitkeep`
- **AND** o arquivo `.gitignore` deve ignorar os arquivos internos `docker/data/*` mantendo o arquivo `!docker/data/.gitkeep`.
