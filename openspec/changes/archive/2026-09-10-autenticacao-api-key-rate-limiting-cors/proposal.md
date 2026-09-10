# Proposal: Autenticação por API Key, Rate-Limiting e Middleware CORS

## Context
A API do Lumi (NeoGuide) atua como um assistente normativo inteligente para engenheiros de telecomunicações, orquestrando fluxos RAG e chamadas a modelos de fundação (LLMs como Google Gemini e Anthropic Claude). O consumo dessas APIs externas envolve custos financeiros por token e restrições de cota. Além disso, a comunicação com interfaces clientes (como o frontend Next.js) exige políticas de compartilhamento de recursos entre origens (CORS) estritas e seguras.

## Motivation & Value
Para proteger os recursos computacionais do serviço, evitar custos imprevistos decorrentes de loops de requisições ou abusos (RNF-11) e garantir o controle de acesso à API, é indispensável introduzir:
1. **Autenticação por API Key (`X-API-Key`)**: Validação de chave secreta configurada no ambiente para autorizar requisições.
2. **Rate-Limiting com Janela Deslizante**: Mecanismo em memória, thread-safe e assíncrono para limitar o volume de chamadas por minuto por chave/cliente, respondendo com HTTP 429 quando o limite for excedido.
3. **Middleware CORS**: Controle explícito de origens permitidas (`cors_origins`), viabilizando a integração do frontend web em desenvolvimento e produção.

## Scope

### In-Scope
- Criação do módulo `src/lumi/api/__init__.py` e `src/lumi/api/deps.py`.
- Implementação de `verify_api_key` utilizando `APIKeyHeader` e validação em tempo constante (`secrets.compare_digest`), retornando HTTP 401 com mensagem `"Invalid or missing API Key"`.
- Implementação da classe `RateLimiter` baseada no algoritmo de sliding window (janela deslizante), thread-safe com bloqueio assíncrono (`asyncio.Lock`), retornando HTTP 429 com mensagem padronizada e header `Retry-After`.
- Implementação da dependência combinada `api_key_and_rate_limit`.
- Adição do endpoint `/api/v1/auth/check` em `src/lumi/main.py` protegido pela dependência combinada.
- Validação e reforço da configuração do `CORSMiddleware` em `src/lumi/main.py` com `settings.cors_origins`.
- Suíte completa de testes unitários em `tests/unit/test_api_security.py` cobrindo 401, 200, 429, reset de janela e preflight CORS OPTIONS.

### Out-of-Scope
- Armazenamento distribuído de rate-limiting via Redis (reservado para escala horizontal futura; a implementação em memória atende o MVP/single-instance).
- Gestão multi-tenant de chaves de API em banco de dados relacional (chaves fixas por ambiente no `Settings`).
- Autenticação de usuários finais via JWT/OAuth2 (coberto em tarefas futuras de gestão de usuários).
