Zbuduj od zera repozytorium Python o nazwie `mcp-universal-server` będące zdalnym MCP serverem (Streamable HTTP) dla wielu agentów Claude Code w sieci LAN/VPN. Serwer będzie uruchamiany na jednej VM (Proxmox). Projekt ma być uniwersalny i łatwy do rozszerzania o nowe narzędzia (pluginy) oraz o router do innych modeli (llm.query). Priorytet: bezpieczeństwo (twarde guardrails), multi-tenant, audyt.

Wymagania techniczne:
- Python 3.11+
- FastAPI + Uvicorn
- MCP Python SDK (Model Context Protocol) w trybie Streamable HTTP (NIE SSE).
- Pydantic lub dataclasses + pydantic dla konfiguracji, a do walidacji wejścia narzędzi użyj pydantic.
- Testy: pytest.
- Strukturalne logowanie JSON (stdout).

Wymagania architektoniczne:
1) Oddziel core od transportu:
   - core: registry pluginów, policy engine, connectors, config, audit
   - transport: adapter FastAPI /mcp
2) Plugin system:
   - narzędzia/resources/prompts jako moduły w `src/plugins/...`
   - każdy plugin ma manifest: name, title, description, capabilities (np. network:outbound, llm:query, fs:read, db:read), oraz handler.
   - rejestracja pluginów jest centralna (loader) i możliwa do sterowania przez config (enable/disable).
3) Policy engine (middleware dla każdego tool-call):
   - narzędzie musi być na allowliście per-agent/per-tenant
   - capability gating: tool.capabilities ⊆ allowed_capabilities dla danego agenta
   - network egress allowlist: outbound HTTP tylko do hostów/portów z configu (domyślnie pusto)
   - limity: max_payload_bytes, max_response_bytes, timeout_seconds, concurrency, rate_limit per agent
   - budżety dla llm.query: max_tokens_per_request + max_cost_per_day (licznik per agent)
   - redakcja sekretów i PII w logach
   - każdy deny ma czytelny powód (lista reasons)
4) Auth i multi-agent:
   - prosta, solidna autoryzacja: Bearer token w nagłówku Authorization.
   - token mapuje się na agent_id i tenant_id (konfiguracja w pliku).
   - policy i budżety działają per-agent.
   - odrzuć żądania bez tokenu.
5) Dostarcz przykładowe MCP elementy:
   Tools:
     - core.echo (zwraca text)
     - core.sum (sumuje a,b)
     - llm.query (router do innych modeli)
   Resources:
     - about://server (opis serwera i wersja)
     - about://policies (aktualne zasady effective config, bez sekretów)
   Prompts:
     - review_pr (szablon code review)
     - tool_usage (krótkie zasady bezpiecznego użycia tooli)
6) llm.query:
   - wspólny interfejs providerów: `providers/openai.py`, `providers/anthropic.py`, `providers/local.py`
   - jeśli brak klucza API, zwróć błąd użytkowy (nie crash)
   - allowlist modeli per provider w configu
   - egress host allowlist musi obejmować domeny providerów, inaczej deny
   - response: tylko tekst + metadane usage jeśli dostępne
   - wejście: ogranicz rozmiar i zablokuj “wklejanie repo” (np. deny jeśli input > X KB lub wykryje bardzo duże bloki kodu; implementuj prostą heurystykę + twardy limit bajtów)
7) Deployment:
   - dodaj Dockerfile + docker-compose.yml (opcjonalnie reverse proxy pomiń, ale przygotuj HEALTHCHECK).
   - dodaj też systemd unit example w README (opcjonalnie).
8) README:
   - jak uruchomić (lokalnie i na VM)
   - jak skonfigurować agentów (tokeny)
   - jak dodać nowy plugin/tool
   - jak podłączyć Claude Code: `claude mcp add --transport http ...` (podaj przykład URL i nagłówka z tokenem)
   - jak ustawić egress allowlist dla OpenAI/Anthropic
9) Konfiguracja:
   - plik `config.yaml` (lub json) + ENV override dla sekretów.
   - bezpieczne defaulty: network egress OFF, dozwolone tylko core.echo i core.sum dla przykładowego agenta.
   - `.env.example`
10) Testy:
   - unit test policy: allow/deny na allowliście narzędzi
   - unit test egress: deny jeśli host nie na allowliście
   - unit test llm.query: deny jeśli model nie na allowliście lub brak budgetu
   - test auth: 401 bez tokenu

Wymagania jakości:
- Kod ma być czytelny, małe moduły, dobre typy, czytelne błędy.
- Nigdy nie loguj sekretów.
- stdout/stderr: serwer MCP nie może mieszać protokołu z logami; logi idą przez logger (stdout w JSON jest OK w HTTP, ale upewnij się, że odpowiedzi HTTP nie zawierają logów).

Na końcu:
- wypisz drzewo plików,
- pokaż przykładowy `config.yaml` z dwoma agentami (różne uprawnienia),
- podaj komendy: instalacja, uruchomienie (uvicorn), docker build/run,
- podaj przykładową komendę `claude mcp add --transport http ...` używając tokenu.


Poniżej masz **dwa gotowe prompty** do wklejenia w Claude Code, żeby wygenerował Ci **remote MCP server na Pythonie** działający na jednej VM i obsługujący wielu agentów po LAN/VPN. Wersja A jest „produkcyjna” (FastAPI + Streamable HTTP + auth + policy), wersja B jest „minimum” (szybki start). U Ciebie celowałbym w A.

---

## Prompt A (rekomendowany): Python + FastAPI + MCP (Streamable HTTP), multi-agent, policy engine, pluginy

Skopiuj 1:1:

```text
Zbuduj od zera repozytorium Python o nazwie `mcp-universal-server` będące zdalnym MCP serverem (Streamable HTTP) dla wielu agentów Claude Code w sieci LAN/VPN. Serwer będzie uruchamiany na jednej VM (Proxmox). Projekt ma być uniwersalny i łatwy do rozszerzania o nowe narzędzia (pluginy) oraz o router do innych modeli (llm.query). Priorytet: bezpieczeństwo (twarde guardrails), multi-tenant, audyt.

Wymagania techniczne:
- Python 3.11+
- FastAPI + Uvicorn
- MCP Python SDK (Model Context Protocol) w trybie Streamable HTTP (NIE SSE).
- Pydantic lub dataclasses + pydantic dla konfiguracji, a do walidacji wejścia narzędzi użyj pydantic.
- Testy: pytest.
- Strukturalne logowanie JSON (stdout).

Wymagania architektoniczne:
1) Oddziel core od transportu:
   - core: registry pluginów, policy engine, connectors, config, audit
   - transport: adapter FastAPI /mcp
2) Plugin system:
   - narzędzia/resources/prompts jako moduły w `src/plugins/...`
   - każdy plugin ma manifest: name, title, description, capabilities (np. network:outbound, llm:query, fs:read, db:read), oraz handler.
   - rejestracja pluginów jest centralna (loader) i możliwa do sterowania przez config (enable/disable).
3) Policy engine (middleware dla każdego tool-call):
   - narzędzie musi być na allowliście per-agent/per-tenant
   - capability gating: tool.capabilities ⊆ allowed_capabilities dla danego agenta
   - network egress allowlist: outbound HTTP tylko do hostów/portów z configu (domyślnie pusto)
   - limity: max_payload_bytes, max_response_bytes, timeout_seconds, concurrency, rate_limit per agent
   - budżety dla llm.query: max_tokens_per_request + max_cost_per_day (licznik per agent)
   - redakcja sekretów i PII w logach
   - każdy deny ma czytelny powód (lista reasons)
4) Auth i multi-agent:
   - prosta, solidna autoryzacja: Bearer token w nagłówku Authorization.
   - token mapuje się na agent_id i tenant_id (konfiguracja w pliku).
   - policy i budżety działają per-agent.
   - odrzuć żądania bez tokenu.
5) Dostarcz przykładowe MCP elementy:
   Tools:
     - core.echo (zwraca text)
     - core.sum (sumuje a,b)
     - llm.query (router do innych modeli)
   Resources:
     - about://server (opis serwera i wersja)
     - about://policies (aktualne zasady effective config, bez sekretów)
   Prompts:
     - review_pr (szablon code review)
     - tool_usage (krótkie zasady bezpiecznego użycia tooli)
6) llm.query:
   - wspólny interfejs providerów: `providers/openai.py`, `providers/anthropic.py`, `providers/local.py`
   - jeśli brak klucza API, zwróć błąd użytkowy (nie crash)
   - allowlist modeli per provider w configu
   - egress host allowlist musi obejmować domeny providerów, inaczej deny
   - response: tylko tekst + metadane usage jeśli dostępne
   - wejście: ogranicz rozmiar i zablokuj “wklejanie repo” (np. deny jeśli input > X KB lub wykryje bardzo duże bloki kodu; implementuj prostą heurystykę + twardy limit bajtów)
7) Deployment:
   - dodaj Dockerfile + docker-compose.yml (opcjonalnie reverse proxy pomiń, ale przygotuj HEALTHCHECK).
   - dodaj też systemd unit example w README (opcjonalnie).
8) README:
   - jak uruchomić (lokalnie i na VM)
   - jak skonfigurować agentów (tokeny)
   - jak dodać nowy plugin/tool
   - jak podłączyć Claude Code: `claude mcp add --transport http ...` (podaj przykład URL i nagłówka z tokenem)
   - jak ustawić egress allowlist dla OpenAI/Anthropic
9) Konfiguracja:
   - plik `config.yaml` (lub json) + ENV override dla sekretów.
   - bezpieczne defaulty: network egress OFF, dozwolone tylko core.echo i core.sum dla przykładowego agenta.
   - `.env.example`
10) Testy:
   - unit test policy: allow/deny na allowliście narzędzi
   - unit test egress: deny jeśli host nie na allowliście
   - unit test llm.query: deny jeśli model nie na allowliście lub brak budgetu
   - test auth: 401 bez tokenu

Wymagania jakości:
- Kod ma być czytelny, małe moduły, dobre typy, czytelne błędy.
- Nigdy nie loguj sekretów.
- stdout/stderr: serwer MCP nie może mieszać protokołu z logami; logi idą przez logger (stdout w JSON jest OK w HTTP, ale upewnij się, że odpowiedzi HTTP nie zawierają logów).

Na końcu:
- wypisz drzewo plików,
- pokaż przykładowy `config.yaml` z dwoma agentami (różne uprawnienia),
- podaj komendy: instalacja, uruchomienie (uvicorn), docker build/run,
- podaj przykładową komendę `claude mcp add --transport http ...` używając tokenu.
```

---

## Prompt B (minimum): szybki MCP HTTP server w Pythonie (bez pełnego multi-tenant)

Jeśli chcesz najpierw „odpalić cokolwiek” i dopiero potem usztywniać:

```text
Zrób minimalny zdalny MCP server w Pythonie (Streamable HTTP) pod Claude Code. Użyj MCP Python SDK + FastAPI. Wystaw tools: echo i sum, resource about://server, prompt review_pr. Dodaj proste Bearer auth (jeden token w ENV). Dodaj allowlist tooli w configu. Dodaj README z uruchomieniem i `claude mcp add --transport http ...` + header Authorization. Dodaj pytest minimalnie dla auth i allowlist.
```

---

### Drobna uwaga praktyczna (żeby Ci to działało z Claude Code od razu)

Claude Code przy HTTP zwykle potrzebuje:

* stabilnego URL (`https://mcp.<twoja_domena_vpn>/mcp`)
* tokenu per agent (nagłówek `Authorization: Bearer ...`)
* sensownego `health` (np. `/healthz`) do monitoringu VM

Jeśli chcesz, mogę Ci też dopisać **gotowy przykład konfiguracji Caddy/Nginx** pod TLS + mTLS albo header injection po VPN — ale to już po tym, jak Claude wygeneruje repo.


