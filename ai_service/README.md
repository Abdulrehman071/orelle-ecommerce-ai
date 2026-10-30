# Multi-Agent AI Business Assistant

A separate **FastAPI service** that adds an AI assistant to the existing ORELLE shop (Django + React) without
changing how the shop works. One **Manager Agent** receives a natural-language request and delegates to three
specialists: **Customer Support**, **Sales Analytics** and **Marketing**.

```
 React shop (existing)               AI service (NEW, port 8001)                 Django shop (existing, port 8000)
 ┌────────────────────┐   HTTPS    ┌──────────────────────────────┐            ┌──────────────────────────┐
 │ chat widget        │──────────▶ │ FastAPI routes + auth + limits│            │ products, orders, users  │
 │ /assistant console │ same token │            │                  │  READ-ONLY │  (db.sqlite3)            │
 └────────────────────┘            │       Manager Agent           │───────────▶│                          │
                                   │   ┌────────┼─────────┐        │            └──────────────────────────┘
                                   │ Support  Analytics  Marketing │            ┌──────────────────────────┐
                                   │   └─── validated TOOLS ───┘   │──read/write▶│ assistant.sqlite3        │
                                   │            │ LLM (Claude)     │            │ tasks, tool logs, drafts │
                                   └──────────────────────────────┘            └──────────────────────────┘
```

## 1. What I found in your existing project (inspection report)

| Area | Finding | Consequence for the design |
|---|---|---|
| Backend | Django 6.1 + Django REST Framework, apps `accounts, catalog, cart, orders, promotions, storefront` | The AI service is a **separate** Python service; Django is untouched except one optional demo-data command |
| Frontend | React 19 + Vite + Tailwind (colors `ink/paper/signal`, fonts Oswald/Inter/IBM Plex Mono) | New UI reuses these tokens so it matches the shop |
| Database | **SQLite** (`backend/db.sqlite3`). 66 products, 1,008 variants (size×color, each with `stock`), 2 coupons | Mapped with SQLAlchemy, opened **read-only** |
| Orders | **0 orders** in the database | Analytics needs data → `seed_sample_orders` creates clearly-labelled demo orders (`DMO-…`) |
| Auth | DRF **Token** auth, token kept in browser `localStorage`; users have `role` = customer/staff/admin | We reuse the same token; no second login system |
| Policies | Delivery/returns/exchange text is **static text in `InfoPage.jsx`**, not in the DB | Copied verbatim into `data/store_policies.json` (keep in sync) |
| Money | PKR; free shipping ≥ 5,000; fees 250/600 (`orders/views.py`) | Same rules used in the policy tool and the marketing fact-checker |
| Gaps | No payment processing, no email sending, no business/store id column | Out of scope; `business_id` added on all assistant records for future multi-store use |

## 2. How it works (read this before your viva)

**Why a separate service?** Your spec asks for FastAPI; Django already exists. Keeping the AI in its own service means
a bug in it cannot break checkout, and it can be deployed, scaled or replaced independently.

**Why is the LLM never given the database?** The model can only *request a tool* (e.g. `best_selling_products` with
dates). Our code validates the arguments (Pydantic), checks the user's role, runs a fixed parameterised query, and returns
JSON. The model **cannot** run SQL, and every number in a report comes from our Python/SQL, not from the model's arithmetic.

**Two databases.** The shop DB is opened read-only (SQLite `query_only` + a guard that rejects anything but SELECT).
The assistant writes only to its own `assistant.sqlite3` (tasks, tool logs, drafts).

**Manager Agent.** (1) Asks the model for a *plan* (`support`/`analytics`/`marketing` steps) through a forced
structured tool call. (2) Removes duplicates, caps the plan at 3 steps, drops agents the user's role may not use.
(3) Runs steps **in order**; each result is passed to the next agent as **structured JSON** (not just prose).
(4) If a step fails, dependent steps are skipped. (5) Combines the answers. Agents never call each other, and every
agent loop has a hard round limit, so uncontrolled loops are impossible. If the model returns an invalid plan, a simple
keyword router takes over.

**Human in the loop.** Marketing output and support escalations are saved as **drafts**. Staff edit, approve or reject
them in the console. A deterministic **fact-checker** flags any price/discount/offer in a draft that is not backed by real
data (product prices, sale prices, *currently valid* coupons). Approving never publishes or sends anything.

### Roles (enforced in code, in the Manager *and* again inside every agent and tool)

| Role | Source | Agents | Notable limits |
|---|---|---|---|
| anonymous / customer | no token / `role=customer` | Support | sees availability, not exact stock; order lookup needs order no. + checkout email (or being the logged-in owner) |
| staff | `role=staff` | Support, Marketing, Analytics | can see exact stock + low-stock report; **cannot** read revenue/sales figures |
| admin | `role=admin` **or Django superuser** | all | everything above + sales reports |

### Tools

| Tool | Agent | Who | What |
|---|---|---|---|
| `search_products`, `get_product_details` | Support, Marketing | all | live catalogue, prices, availability |
| `get_store_policies` | Support, Marketing | all | official policy text |
| `lookup_order` | Support | all (privacy-checked) | status/tracking for ONE verified order |
| `escalate_to_human` | Support | all | creates a review item; sends nothing |
| `period_report`, `sales_summary`, `best_selling_products`, `sales_trend` | Analytics | admin | daily/weekly/monthly + custom ranges |
| `low_stock_report` | Analytics | staff, admin | configurable threshold |
| `get_confirmed_offers` | Marketing | staff, admin | the ONLY source for coupons/sales |
| `save_draft` | Marketing | staff, admin | saves editable draft + runs fact-check |

**Sales definitions:** cancelled orders are excluded; `revenue` = sum of `order.total` (items + shipping − discount);
dates are inclusive in `BUSINESS_TIMEZONE` (Asia/Karachi) because Django stores UTC.

## 3. Folder structure

```
ai_service/
├── app/
│   ├── main.py            FastAPI app + routes (chat, history, drafts)
│   ├── config.py          settings from environment variables
│   ├── auth.py            token → role; which agents each role may use
│   ├── db.py              read-only shop engine + assistant engine
│   ├── models_store.py    read-only mappings of the Django tables
│   ├── models_agent.py    assistant tables: task, tool_log, draft
│   ├── guardrails.py      marketing fact-checker
│   ├── agents/            runner.py (tool loop), specialists.py (3 agents), manager.py
│   ├── tools/             base.py (validation+RBAC), catalog, orders, sales, marketing
│   └── llm/               base.py (interface), anthropic_client.py
├── data/store_policies.json
├── tests/                 100 tests (pytest)
├── requirements.txt  requirements-dev.txt  .env.example  pytest.ini
backend/orders/management/commands/seed_sample_orders.py     (demo data, reversible)
frontend/src/ …  api/assistant.js, hooks/useAssistantChat.js, components/AssistantWidget.jsx,
                 components/assistant/{DraftCard,Results}.jsx, pages/AssistantConsole.jsx
```

## 4. Setup (Windows, step by step)

You need an **Anthropic API key** (https://console.anthropic.com → API keys; needs billing credit). Everything except
live AI answers works without it.

**A. Demo sales data** (your database currently has no orders):
```
cd outfitters-clone\backend
python manage.py seed_sample_orders          :: 150 demo orders over 90 days
:: remove later with:  python manage.py seed_sample_orders --clear
```
**B. Make sure your account is an admin.** Your existing superuser (`admin@outfitters.local`) is automatically treated as
admin. For another account, in `python manage.py shell`:
`from accounts.models import User; User.objects.filter(email="you@x.com").update(role="admin")`

**C. Start the AI service**
```
cd outfitters-clone\ai_service
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          :: then open .env and paste your ANTHROPIC_API_KEY
python -m app.init_db           :: creates the assistant's own tables (also done automatically on start)
uvicorn app.main:create_app --factory --port 8001 --reload
```
Check http://localhost:8001/health → `{"status":"ok","store_db":true,"llm_configured":true}` and docs at `/docs`.

**D. Start the shop as usual** (`python manage.py runserver` and `npm run dev` in `frontend`). Log in as the admin,
open **http://localhost:5173/assistant** (staff console). Every visitor also gets the floating chat button.

## 5. Connecting to your existing website
* **Login:** the React app already stores the DRF token; `src/api/assistant.js` sends it as `Authorization: Token …`.
  The service looks that token up (read-only) in `authtoken_token`.
* **URL:** `frontend/.env` → `VITE_ASSISTANT_URL=http://localhost:8001`.
* **CORS:** `ALLOWED_ORIGINS` in `ai_service/.env` must list your frontend origin.
* **Data:** `STORE_DB_URL` empty = `../backend/db.sqlite3`. For PostgreSQL, set it and use a SELECT-only DB user.
* **Policies:** edit `data/store_policies.json` whenever you change a policy on the website.

## 6. API and sample requests
| Endpoint | Who | Purpose |
|---|---|---|
| `GET /health` | anyone | service status, whether the AI key is configured |
| `GET /me` | anyone | role and allowed agents |
| `POST /chat` `{message, history[]}` | anyone (limited by role) | main entry point |
| `GET /history` | staff | activity log: status, agents, tools, duration, errors |
| `GET /drafts`, `PATCH /drafts/{id}`, `POST /drafts/{id}/approve` `{acknowledge_warnings}`, `POST /drafts/{id}/reject` | staff | review workflow |

```
curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" ^
  -d "{\"message\":\"Is the Leather Loafer in stock and what is your return policy?\"}"

curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" -H "Authorization: Token YOUR_TOKEN" ^
  -d "{\"message\":\"Analyze this month's sales, find the best-selling product and prepare a promotional Instagram post\"}"
```
Your token: log in on the site, then in the browser console run `localStorage.getItem('auth_token')`.

## 7. Tests
```
cd ai_service
pip install -r requirements-dev.txt
pytest
```
100 tests, no internet/API key needed (a scripted fake model replays model turns). They cover: report numbers vs
independent raw SQL; cancelled orders; timezone day boundaries; weekly/monthly periods; low-stock thresholds;
read-only shop DB; product search/stock/unavailable items; SQL-injection strings; order privacy (other customer's order,
wrong email); each agent alone; Manager routing, fallback, dedupe/cap, failure skipping; the full analytics→marketing
workflow with structured hand-off; prompt-injection attempts; RBAC; claim fact-checking; draft edit/approve/reject;
business isolation (two businesses sharing one assistant DB); rate limiting; CORS; input validation; Anthropic adapter
conversion and error mapping; end-to-end HTTP request → final answer.

## 8. Known limitations (please read)
1. **The real Anthropic API has NOT been called in development** (no key was available). The adapter's conversion and
   error handling are unit-tested with a stub; the agents are tested with a scripted model. Real answer quality, prompt
   wording and the exact model name (`ANTHROPIC_MODEL`) must be checked by you with your key. First step: ask
   "Is the Leather Loafer in stock?" in the widget and read the Activity tab.
2. The React UI was compiled and linted successfully but **not clicked through in a browser** here.
3. Verified against your real database schema: the service starts, token→role works, and report figures match raw SQL
   on the seeded copy. The demo orders are synthetic; real conclusions need real orders.
4. "Draft for review" is implemented as: factual product/policy/order-status answers are returned directly (read-only);
   refunds, complaints and anything uncertain become **escalations** for staff. Nothing is ever sent to a customer.
5. Rate limiter and history are per-process/in-memory or single-DB: use Redis/Postgres for multiple servers.
6. The fact-checker is a heuristic (prices, %, a short list of risky phrases). It reduces, not eliminates, wrong claims.
7. Analytics aggregates in Python after SELECT: fine for thousands of orders; move to SQL `GROUP BY` for very large data.
8. Policies are duplicated (website text + JSON file). Multi-store: assistant tables are ready (`business_id`), but the
   Django shop schema itself is single-store, so true multi-store needs a business column there.
9. Schema setup uses `create_all` (documented, idempotent), not Alembic migrations.
10. Chat history is sent by the browser and treated as untrusted text. No streaming; long requests wait for the full answer.
11. The `/assistant` console needs the admin role for sales figures; staff see stock and marketing only.

## 9. Git / GitHub (manual step)
```
cd outfitters-clone
git init && git add . && git commit -m "Add multi-agent business assistant"
:: create an empty repository on github.com, then:
git remote add origin https://github.com/<you>/<repo>.git && git push -u origin main
```
Before pushing make sure `.env` files with real keys are NOT added (`ai_service/.gitignore` already excludes `.env`);
also add `venv/` and `node_modules/` to a root `.gitignore`.

## 10. Viva cheat-sheet
* *"Is it just a chatbot?"* No: the model plans and calls validated tools; figures come from SQL/Python; drafts need human approval.
* *"How do you stop hallucinated prices?"* Facts only via tools; marketing drafts are fact-checked against the database.
* *"What if someone tricks the AI?"* Permissions are enforced in code outside the model; visitors are never even shown analytics tools (test: `test_prompt_injection_cannot_unlock_analytics_for_a_visitor`).
* *"Why multi-agent?"* Different jobs need different tools, permissions and prompts; the Manager keeps them coordinated and bounded.
* *"What would you do next?"* Streaming, Redis rate limits, Alembic, SELECT-only Postgres user, real publishing with approval, multi-store column.
