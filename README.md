# NEXUS AI

Plataforma pessoal multimodelo: **Android (Flet) + FastAPI + modelos locais (Llama 3.1 8B / Qwen 2.5 7B) + APIs oficiais (OpenAI, Gemini, Claude)**, com memória, voz, anexos, streaming real e roteamento inteligente.

O aplicativo Android **nunca** fala diretamente com Llama, Qwen, OpenAI, Gemini, Claude, Whisper ou o banco de memória. Tudo passa pelo backend NEXUS.

```
Android / Flet  --HTTPS-->  Nginx:443  -->  FastAPI:127.0.0.1:8000
                                              |
                                         Model Router
                                      /       |        \
                               Llama     Qwen      APIs externas
                               local     local   OpenAI/Gemini/Claude
```

## Recursos

- Chat com Markdown e blocos de código
- Streaming SSE real (não simulado)
- NEXUS AUTO + modos Somente Local / Econômico / Manual
- Memória de curto e longo prazo (SQLite + embeddings)
- Voz → Whisper (faster-whisper) → mesmo fluxo do chat
- Anexos TXT/PDF/DOCX/PNG/JPG/JPEG/WEBP
- Autenticação Bearer (`NEXUS_API_KEY`)
- HTTPS via Nginx
- Diagnóstico `nexus-doctor`
- Sem Dola / AIMLAPI / mocks no caminho funcional

## Estrutura

```
nexus-ai/
├── app/                 # Cliente Flet (Android/desktop)
├── backend/             # FastAPI
│   ├── providers/       # OpenAI, Gemini, Claude
│   ├── local_models/    # Llama, Qwen
│   ├── runtimes/        # llama.cpp, transformers, vLLM
│   ├── memory/          # curto/longo prazo, retrieval, privacy
│   ├── services/        # router, model manager, STT, streaming
│   └── routes/
├── server/              # scripts, systemd, nginx
├── tests/
├── docker-compose.yml
└── .env.example
```

## Instalação (VPS Linux)

```bash
git clone <repo> nexus-ai
cd nexus-ai
bash server/scripts/setup.sh
```

Edite `.env`:

```bash
cp .env.example .env
# Defina NEXUS_API_KEY forte
# Opcional: OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, HF_TOKEN
```

### Modelos locais

Os checkpoints **não** são baixados automaticamente (são gigantes).

```bash
bash server/scripts/check_hardware.sh
# Opcional em VPS com pouca RAM:
bash server/scripts/setup_swap.sh 16

# Transformers / HF snapshot:
bash server/scripts/download_llama.sh
bash server/scripts/download_qwen.sh

# Ou GGUF (llama.cpp):
bash server/scripts/download_llama.sh gguf
bash server/scripts/download_qwen.sh gguf
```

Paths padrão:

- `/opt/nexus-ai/models/llama`
- `/opt/nexus-ai/models/qwen`

IDs HF:

- `meta-llama/Llama-3.1-8B-Instruct` (pode exigir aceite de licença + `HF_TOKEN`)
- `Qwen/Qwen2.5-7B-Instruct`

Runtime:

```bash
LOCAL_RUNTIME=auto   # auto | llama_cpp | transformers | vllm
MODEL_MAX_LOADED=1
MODEL_KEEP_ALIVE=false
LLAMA_GPU_LAYERS=0
QWEN_GPU_LAYERS=0
```

Instale o runtime desejado, por exemplo:

```bash
# GGUF
pip install llama-cpp-python

# Transformers (CPU ou GPU)
pip install torch transformers accelerate

# Whisper local
pip install faster-whisper

# Embeddings locais (opcional; fallback hash embutido)
pip install sentence-transformers
```

### Backend

```bash
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Health:

```bash
curl http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $NEXUS_API_KEY" http://127.0.0.1:8000/v1/health
```

### Systemd

```bash
sudo useradd -r -m -d /opt/nexus-ai nexus || true
sudo cp -a . /opt/nexus-ai
sudo cp server/systemd/nexus-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nexus-backend
```

Modelos locais são carregados sob demanda pelo `ModelManager` (não exponha llama.cpp/vLLM/Transformers na internet).

### Nginx + HTTPS

```bash
sudo cp server/nginx/nexus.conf /etc/nginx/sites-available/nexus
# Edite YOUR_DOMAIN
sudo ln -s /etc/nginx/sites-available/nexus /etc/nginx/sites-enabled/
sudo certbot --nginx -d YOUR_DOMAIN
sudo nginx -t && sudo systemctl reload nginx
```

### Docker (opcional)

```bash
docker compose up -d --build
```

O sistema também roda sem Docker.

## Aplicativo (Flet / Android)

```bash
source .venv/bin/activate
flet run main.py
# ou: flet run app/main.py
```

APK (VPS/PC **Linux x86_64**, ≥20 GB livres — não funciona em aarch64/Termux):

```bash
bash scripts/build_apk.sh
```

Guia completo (servidor + APK + Nginx): ver **[guia.md](guia.md)**.

No app → **Configurações**:

- URL do NEXUS Backend (ex.: `https://seu-dominio.com`)
- NEXUS API Key

**Nunca** coloque chaves OpenAI/Gemini/Claude/OpenRouter/HF no APK.

## NEXUS AUTO

Modo padrão: **🤖 AUTO**

Fluxo: mensagem → memória relevante → análise de tarefa → capacidades → disponibilidade → router → modelo → streaming.

Modos:

| Modo | Comportamento |
|------|----------------|
| AUTO | Escolhe entre locais e APIs configuradas |
| SOMENTE LOCAL | Só Llama/Qwen/Whisper/embeddings locais |
| ECONÔMICO | Prioriza locais; API só se necessário |
| MANUAL | Usuário escolhe o modelo |

Em falha **não** há fallback silencioso — a UI oferece alternativas (Qwen, Llama, OpenAI, Gemini, Claude).

## Memória

- Curto prazo: conversa atual
- Longo prazo: tabela `memories` (preference, project, fact, …)
- Retrieval por embeddings (locais); **nunca** envia a base inteira a APIs externas
- Confirmação “🧠 Lembrar disso?” quando configurado
- CRUD em `/v1/memory`

## Voz

1. Toque 🎤 → grava → para  
2. `POST /v1/audio/transcriptions` (Whisper)  
3. Edita o texto → envia pelo mesmo chat/router  

## APIs principais

| Método | Path |
|--------|------|
| GET | `/health` |
| GET | `/v1/health` |
| GET | `/v1/models` |
| GET | `/v1/providers` |
| POST | `/v1/chat/completions` |
| POST | `/v1/router/choose` |
| POST | `/v1/audio/transcriptions` |
| CRUD | `/v1/memory` |
| GET/POST | `/v1/conversations`, `/v1/attachments` |

Chat (exemplo):

```bash
curl -N -H "Authorization: Bearer $NEXUS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","stream":true,"messages":[{"role":"user","content":"Olá"}]}' \
  https://seu-dominio.com/v1/chat/completions
```

## Segurança

- Bearer token obrigatório nas rotas `/v1/*` (exceto `/health` público)
- Rate limit, limite de tamanho, CORS configurável
- FastAPI só em `127.0.0.1` atrás do Nginx
- Logs sanitizados (sem Authorization / API keys / HF_TOKEN)
- Runtimes locais **não** são publicados na internet

## Testes

```bash
source .venv/bin/activate
pytest -q
```

## Diagnóstico

```bash
bash server/scripts/nexus-doctor
```

## Solução de problemas

| Sintoma | Ação |
|---------|------|
| `401` | Confira `NEXUS_API_KEY` no app e no servidor |
| Llama/Qwen offline | Baixe o modelo; confira paths e runtime instalado |
| OOM | `MODEL_MAX_LOADED=1`, swap, quantização GGUF |
| Whisper offline | `pip install faster-whisper` |
| API externa | Defina a chave no `.env` do servidor |
| Sem GPU | Deixe `*_GPU_LAYERS=0` (padrão) |

## Atualização

```bash
cd /opt/nexus-ai
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart nexus-backend
```

## Licenças

Respeite as licenças dos modelos (Meta Llama, Qwen) e dos provedores de API. O token Hugging Face permanece apenas no servidor.
