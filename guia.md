# Guia NEXUS AI — Servidor + APK (VPS Linux)

Passo a passo para subir o **backend** na VPS e gerar o **APK Android** com Flet.

> O APK **nunca** leva chaves OpenRouter/OpenAI/etc.  
> Só a URL do backend + `NEXUS_API_KEY` (nas Configurações do app).

---

## Requisitos da VPS

| Recurso | Mínimo | Recomendado |
|--------|--------|-------------|
| SO | Ubuntu 22.04+ / Debian 12+ | Ubuntu 24.04 **x86_64** (APK) |
| Arch | **aarch64 OK só para API** | **x86_64 obrigatório para APK** |
| RAM | 2 GB (só API) | 4 GB+ (8 GB+ para APK) |
| Disco livre | 5 GB (só API) | **25 GB+** se for gerar APK |
| Rede | Porta 443 (HTTPS) ou 8000 (teste) | Domínio + Nginx |

Ferramentas:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl unzip build-essential
```

> **Não** use o Python do Termux/Android (`*-linux-android`) no venv. Use `/usr/bin/python3` (glibc).

---

## 1. Clonar / copiar o projeto

```bash
# Exemplo
cd /opt
sudo git clone <SEU_REPO> nexus-ai
sudo chown -R $USER:$USER /opt/nexus-ai
cd /opt/nexus-ai
```

Ou envie a pasta `nexus-ai` por `scp`/`rsync`.

---

## 2. Configurar o servidor (backend)

### 2.1 Bootstrap

```bash
cd /opt/nexus-ai
bash server/scripts/setup.sh
```

Isso cria `.venv`, instala `requirements.txt` e pastas de dados.

### 2.2 Editar `.env`

```bash
nano .env
```

Obrigatório:

```bash
NEXUS_API_KEY=uma-chave-longa-e-aleatoria
```

APIs externas (recomendado — uma chave só):

```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

Opcional (só se **não** usar OpenRouter):

```bash
OPENAI_API_KEY=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
```

Modelos locais (opcional; pesados):

```bash
LLAMA_MODEL_PATH=/opt/nexus-ai/models/llama
QWEN_MODEL_PATH=/opt/nexus-ai/models/qwen
LOCAL_RUNTIME=auto
```

### 2.3 Subir o backend (teste rápido)

```bash
bash scripts/run_backend.sh
# ou:
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Teste:

```bash
curl http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $NEXUS_API_KEY" http://127.0.0.1:8000/v1/health
```

Diagnóstico:

```bash
bash server/scripts/nexus-doctor
```

### 2.4 Systemd (produção)

```bash
sudo useradd -r -m -d /opt/nexus-ai nexus || true
sudo cp server/systemd/nexus-backend.service /etc/systemd/system/
# Ajuste User=/WorkingDirectory=/caminho do venv no .service se preciso
sudo systemctl daemon-reload
sudo systemctl enable --now nexus-backend
sudo systemctl status nexus-backend
```

Logs:

```bash
journalctl -u nexus-backend -f
# ou, se usou scripts/run_backend.sh:
tail -f /opt/nexus-ai/logs/backend.log
```

### 2.5 Nginx + HTTPS (recomendado)

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo cp server/nginx/nexus.conf /etc/nginx/sites-available/nexus
sudo nano /etc/nginx/sites-available/nexus   # troque YOUR_DOMAIN
sudo ln -sf /etc/nginx/sites-available/nexus /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d SEU_DOMINIO.com
```

O app Android deve usar:

```text
https://SEU_DOMINIO.com
```

---

## 3. Compilar o APK (Flet)

### 3.1 O que já está preparado no projeto

```text
nexus-ai/
├── main.py                 # entrypoint do APK
├── pyproject.toml          # org, product, permissões Android
├── requirements-app.txt    # deps só do cliente (flet, httpx)
├── assets/icon.png         # ícone
├── app/                    # UI Flet
└── scripts/build_apk.sh    # script de build
```

### 3.2 Arquitetura (importante)

O build do APK **só funciona em Linux x86_64**. Em `aarch64` (ex.: VPS ARM, Termux/PRoot) o Flet falha com:

```text
RuntimeError: Unsupported platform: Linux-aarch64
```

Google não publica Android cmdline-tools para Linux ARM, e o Flutter também não inclui `gen_snapshot` Android para host `linux-arm64`. Use uma VPS/PC **amd64** ou CI (`ubuntu-latest`). O backend em aarch64 continua ok.

### 3.3 Espaço em disco

O primeiro `flet build apk` baixa **Flutter + Android SDK** (vários GB).

```bash
df -h .
# ideal: ≥ 20–25 GB livres
```

### 3.4 Dependências extras para o build

```bash
sudo apt install -y git curl unzip openjdk-17-jdk clang cmake ninja-build pkg-config libgtk-3-dev
```

### 3.5 Gerar o APK

```bash
cd /opt/nexus-ai
source .venv/bin/activate
pip install -r requirements-app.txt flet-cli

bash scripts/build_apk.sh
```

Variáveis opcionais:

```bash
BUILD_VERSION=1.0.1 BUILD_NUMBER=2 bash scripts/build_apk.sh
```

Equivalente manual:

```bash
flet build apk . \
  --product "NEXUS AI" \
  --org com.nexusai \
  --project nexus-ai \
  --build-version 1.0.0 \
  --build-number 1 \
  --module-name main \
  --exclude .venv backend tests data server scripts __pycache__ .git .github build \
  --yes \
  --permissions microphone \
  -o build/apk
```

### 3.6 Onde fica o APK

```bash
find build -name '*.apk'
# tipicamente: build/apk/*.apk
```

Baixe para o PC/celular:

```bash
scp user@SUA_VPS:/opt/nexus-ai/build/apk/*.apk .
```

Instalar:

```bash
adb install -r nexus-ai.apk
```

Ou copie o arquivo e abra no Android (permitir “fontes desconhecidas”).

### 3.7 Configurar o app no celular

1. Abra **NEXUS AI**
2. Vá em **Configurações**
3. Preencha:
   - **URL do backend:** `https://SEU_DOMINIO.com` (sem barra no final)
   - **API Key:** o mesmo `NEXUS_API_KEY` do `.env` da VPS
4. Salve e teste o chat (modo **AUTO**)

---

## 4. Fluxo completo (resumo)

```text
[Celular APK]  --HTTPS-->  [Nginx:443]  -->  [FastAPI :8000]
                                              |
                                         OpenRouter / locais
```

1. VPS: `setup.sh` → `.env` → `run_backend.sh` ou systemd  
2. VPS: Nginx + Certbot  
3. VPS: `build_apk.sh` → copiar APK  
4. Celular: URL + `NEXUS_API_KEY`  

---

## 5. Testar o cliente no desktop (sem APK)

Na VPS ou no PC:

```bash
cd /opt/nexus-ai
source .venv/bin/activate
flet run main.py
# ou: flet run app/main.py
```

---

## 6. Problemas comuns

| Sintoma | Solução |
|--------|---------|
| `pydantic-core` / maturin / Android SOABI | Recrie o venv com `/usr/bin/python3` (`bash server/scripts/setup.sh`) |
| `No space left on device` no APK | Liberar ≥20 GB; apagar `~/.flet` e `build/` e tentar de novo |
| `git: not found` no build | `sudo apt install git` |
| APK abre mas chat falha | URL HTTPS correta + `NEXUS_API_KEY` igual ao `.env` |
| `401` | API key errada no app |
| `Nenhum modelo disponível` | Defina `OPENROUTER_API_KEY` (ou baixe modelos locais) |
| OOM / VPS pequena | Só API via OpenRouter; não carregue Llama/Qwen |

Limpar cache de build Flutter/Flet:

```bash
rm -rf ~/.flet build
```

---

## 7. Segurança

- **Não** coloque `OPENROUTER_API_KEY` / OpenAI / Gemini / Claude no APK  
- FastAPI só em `127.0.0.1`; Nginx na frente  
- Use `NEXUS_API_KEY` forte  
- Se a chave vazou em chat/log, **revogue** no painel do provedor e gere outra  

---

## 8. Comandos úteis

```bash
# Doctor
bash server/scripts/nexus-doctor

# Testes do backend
source .venv/bin/activate && pytest -q

# Chat rápido
source .env
curl -s -H "Authorization: Bearer $NEXUS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","stream":false,"messages":[{"role":"user","content":"oi"}]}' \
  http://127.0.0.1:8000/v1/chat/completions
```

---

## Estrutura relevante

```text
nexus-ai/
├── guia.md                 ← este arquivo
├── main.py                 ← entry APK / flet run
├── pyproject.toml
├── requirements.txt        ← backend
├── requirements-app.txt    ← cliente Flet
├── app/                    ← UI Android
├── backend/                ← FastAPI
├── server/scripts/         ← setup, doctor, nginx, systemd
├── scripts/build_apk.sh
├── scripts/run_backend.sh
└── assets/icon.png
```
