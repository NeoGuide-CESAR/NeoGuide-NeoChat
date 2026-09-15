# Design: Autenticação por API Key, Rate-Limiting e Middleware CORS

## Architecture & Layout

### 1. Injeção de Dependências FastAPI (`src/lumi/api/deps.py`)
A segurança na camada de transporte HTTP é implementada por meio de funções injetáveis de dependência (`Depends`), separando preocupações e permitindo reutilização em qualquer roteador ou endpoint:

1. **`verify_api_key`**:
   - Utiliza `fastapi.security.APIKeyHeader(name="X-API-Key", auto_error=False)`.
   - Lê a chave configurada em `Settings.api_key`.
   - Utiliza comparação em tempo constante (`secrets.compare_digest`) para prevenir ataques de temporização (timing attacks).
   - Se a chave for ausente ou inválida, levanta `fastapi.HTTPException(status_code=401, detail="Invalid or missing API Key")`.
   - Se válida, retorna o valor da chave (string).

2. **`RateLimiter`**:
   - Classe com padrão callable assíncrono (`async def __call__(self, request: Request, api_key: str = Depends(verify_api_key))`).
   - Mantém um dicionário interno `dict[str, list[float]]` mapeando cada identificador de cliente (chave de API ou IP) para uma lista de timestamps `time.time()`.
   - Utiliza `asyncio.Lock` para garantir thread-safety e atomicidade em operações de leitura, filtragem e inserção de timestamps.
   - Algoritmo de janela deslizante (Sliding Window):
     - Para cada requisição, calcula o corte `threshold = now - window_seconds`.
     - Remove timestamps mais antigos que `threshold`.
     - Se `len(timestamps) >= requests_per_minute`, calcula o tempo restante de bloqueio `retry_after = ceil(timestamps[0] + window_seconds - now)` e levanta `HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.", headers={"Retry-After": str(retry_after)})`.
     - Se estiver abaixo do limite, registra o timestamp atual `timestamps.append(now)`.
   - Fornece método `reset()` para limpar o histórico (essencial para testes e expiração controlada).

3. **`api_key_and_rate_limit`**:
   - Dependência combinada padrão instanciada com os parâmetros do `Settings` (`rate_limit_requests_per_minute`).
   - Pode ser utilizada diretamente como `Depends(api_key_and_rate_limit)` em qualquer endpoint.

### 2. Configuração de CORS (`src/lumi/main.py`)
- O `CORSMiddleware` é configurado na inicialização da aplicação FastAPI.
- A lista de origens é carregada a partir de `settings.cors_origins`.
- Permite credenciais (`allow_credentials=True`), todos os métodos HTTP (`allow_methods=["*"]`) e todos os cabeçalhos (`allow_headers=["*"]`), viabilizando o envio do cabeçalho customizado `X-API-Key` durante requisições complexas do navegador.

### 3. Endpoint de Verificação (`GET /api/v1/auth/check`)
- Registrado em `src/lumi/main.py` (ou roteador de autenticação).
- Protegido pela dependência `api_key_and_rate_limit`.
- Retorna payload simples `{"status": "authenticated", "message": "API Key is valid"}`.

### 4. Respostas HTTP e Tratamento de Erros
- **401 Unauthorized**: Retornado quando `X-API-Key` está ausente ou não coincide com `settings.api_key`. Payload: `{"detail": "Invalid or missing API Key"}`.
- **429 Too Many Requests**: Retornado quando a taxa de requisições do cliente ultrapassa a cota por minuto. Payload: `{"detail": "Rate limit exceeded. Try again later."}` acompanhado do cabeçalho `Retry-After`.
