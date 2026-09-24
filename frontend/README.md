# Mini DNS Server frontend

Next.js App Router monitoring console for the Python Mini DNS Server backend. It renders only API/WebSocket data: DNS responses, cache entries, logs, simulation state, and analytics.

## Run

```powershell
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`. Start the backend first at `http://127.0.0.1:8000`. The client uses `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`; change them in `.env.local` for another host.

Pages: dashboard, manual DNS resolution (including server-provided resolution flow), automatic simulation controls, TTL-countdown cache explorer, analytics, paginated logs, and status/settings. The common API client is in `lib/api.ts`; real-time event handling is in `hooks/useLiveData.ts`.
