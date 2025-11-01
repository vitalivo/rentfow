                      ┌─────────────────┐
                      │    Frontend     │◄──┐ i18n (ru/en)
                      │   (React/Vite)  │   │
                      └────────┬────────┘   │
                               │ HTTP        │
                               ▼             │
┌─────────────┐      ┌─────────────────┐     │
│   Django    │◄────►│   API Gateway   │     │
│ (Auth, CRUD)│      │ (Nginx / Traefik)│     │
└──────┬──────┘      └─────────────────┘     │
       │                 ▲        ▲          │
       │                 │ gRPC   │ gRPC      │
       ▼                 │        │           │
┌─────────────┐          ├────────┴────────┐ │
│ PostgreSQL  │◄─────────┤  Shared Proto   ├─┤
│  (Primary)  │          │   Definitions   │ │
└─────────────┘          └─────────────────┘ │
                                              │
┌──────────────────┐                          │
│   FastAPI (Async)  │◄────────────────────────┘
│ (Events, WS)       │
└─────────┬──────────┘
          │ WebSocket
          ▼
┌──────────────────────┐
│ External Services    │
│ - Telegram Bot API   │
│ - Email (SMTP)       │
└──────────────────────┘
          ▲
          │
          └─── AKHQ (Web UI for Kafka) → http://localhost:8080