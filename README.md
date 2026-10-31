# IT Helpdesk & Service Management System

A full-stack web application for managing IT support requests in an organization. Employees can report problems, IT engineers can investigate and resolve them, and administrators can manage teams, monitor service-level agreements (SLAs), and review support performance.

**Project status:** Local development release (Phases 1–10). Frontend deployment to Vercel and backend deployment to Oracle Cloud are planned/in progress. **Do not treat this repository as production-ready until the security and deployment checklist has been completed.**

## Features

### Employee
- Register and sign in; create and track support tickets.
- Enter a title, description, category, and priority.
- View ticket status, conversation history, attachments, and troubleshooting recommendations.
- Chat with support, receive in-app message alerts, and verify or reopen resolutions.

### IT support engineer
- View assigned tickets, respond through Conversations, and update progress.
- Consult the searchable knowledge base and add private internal notes.
- Download authorized attachments and track activity history.

### Administrator
- Assign tickets and manage users, roles, active accounts, teams, and team membership.
- Configure SLA policies, inspect breaches, and review notifications.
- Maintain knowledge-base articles and review analytics and downloadable reports.
- Configure category-to-team routing, engineer recommendations, and optional workload-based automatic assignment.

### Additional capabilities
- Ticket lifecycle: **Open → Assigned → In Progress → Resolved → Closed**; reopening when a fix doesn't work.
- SLA response/resolution deadlines and breach monitoring.
- Rule/keyword-based category and priority suggestions (not generative AI).
- Secure-access checks for ticket attachments (PNG, JPG, JPEG, PDF, TXT) and internal notes.
- In-app notifications and right-side incoming-message previews; polling rather than WebSockets.
- CSV/Excel reports and dashboard statistics.
- Responsive React UI with a fixed desktop navigation sidebar.

## Technology stack

| Area | Technology |
| --- | --- |
| Frontend | React, Vite, JavaScript, CSS, Lucide React |
| Backend / API | Python, Flask, Flask-SQLAlchemy |
| Authentication | Flask session authentication and Werkzeug password hashing |
| Database | SQLite (local development) |
| Scheduling / SLA | Python SLA logic and background monitoring |
| Analytics / export | Reporting endpoints and CSV/Excel export |
| Source control | Git and GitHub |
| Planned hosting | Vercel (frontend), Oracle Cloud (backend) |

## Repository layout

```text
IT-Helpdesk-Starter/
├── backend/
│   ├── app.py                 # Flask application and API routes
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example           # Local environment template
│   ├── sla_phase3.py          # SLA monitoring
│   ├── phase7_ticket_tools.py # Attachments and internal notes
│   ├── phase8_admin.py        # Users and teams
│   ├── phase9_routing.py      # Routing and recommendations
│   └── seed_detailed_articles.py  # Optional detailed sample articles
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── main.jsx
│   │   ├── Conversations.jsx
│   │   ├── KnowledgeBase.jsx
│   │   ├── TicketTools.jsx
│   │   ├── SlaCenter.jsx
│   │   ├── AdminManagement.jsx
│   │   ├── RoutingSettings.jsx
│   │   ├── Analytics.jsx
│   │   └── style.css
│   └── ...
└── README.md
```

> Some helper modules were added during later phases. Keep the latest versions of the Phase 1–10 files together. Do not replace the latest `app.py` with an earlier phase's version.

## Run locally on Windows (PowerShell)

### Prerequisites

- **Python 3.10+** (`py --version`)
- **Node.js** compatible with the project's Vite version (`node --version` and `npm --version`)
- **Git** (`git --version`)

### 1. Clone the project

```powershell
git clone https://github.com/Zeenat-25/IT-Helpdesk-System.git
cd IT-Helpdesk-System
```

If the repository is private, you must sign in with an account that has access. If you've already downloaded it to `C:\Users\AAA\Desktop\IT-Helpdesk-Starter`, open PowerShell in that folder instead; you don't need to clone again.

### 2. Start the Flask backend (Terminal 1)

From the project root:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Generate a private application secret:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Open `backend/.env` and replace `SECRET_KEY=replace-with-a-long-random-secret` with that value. Leave `FRONTEND_ORIGIN=http://localhost:5173` for local development.

Initialize the demo accounts and optional built-in sample knowledge-base articles:

```powershell
.\.venv\Scripts\python.exe -m flask --app app seed
.\.venv\Scripts\python.exe -m flask --app app seed-knowledge
```

If `seed_detailed_articles.py` exists and you'd like the longer example articles:

```powershell
.\.venv\Scripts\python.exe seed_detailed_articles.py
```

Start Flask:

```powershell
.\.venv\Scripts\python.exe app.py
```

The development API runs on **http://127.0.0.1:5000**. Check **http://127.0.0.1:5000/api/health**.

**Returning to an existing installation?** Do not recreate the database or overwrite a configured `.env`. Normally, just start `app.py` using your existing `.venv`.

### 3. Start React (Terminal 2)

Open a second PowerShell terminal in the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. During local development, Vite proxies `/api` requests to Flask.

### 4. Demo accounts (local testing only)

Run the backend `seed` command first.

| Role | Email | Password |
| --- | --- | --- |
| Administrator | `admin@demo.local` | `Demo12345!` |
| Engineer | `engineer@demo.local` | `Demo12345!` |
| Employee | `employee@demo.local` | `Demo12345!` |

**Never use these predictable accounts in a public deployment.** Remove/disable demo accounts, change passwords, and review access controls before hosting.

## Basic demonstration

1. **Employee:** Sign in, create a ticket such as *Office Wi-Fi not connecting*, and upload a test screenshot if needed.
2. **Administrator:** Open Tickets, assign the ticket to an engineer, and review the SLA deadline and activity history.
3. **Engineer:** Open Conversations, reply to the employee, add an internal note, and mark the ticket **Resolved**.
4. **Employee:** Confirm the issue is fixed to **Close** it, or **Reopen** the ticket if it persists.
5. **Administrator:** Open Knowledge Base, Analytics & Reports, SLA Policies, Users & Teams, and Smart Routing to test the other modules.

For chat-alert testing, use separate browser profiles for employee, engineer, and administrator. Incoming message notifications are polled periodically, so alerts may not appear instantly.

## Testing and verification

Before publishing, test:

- [ ] Registration, login, logout, session expiration and role-based permissions.
- [ ] Ticket creation, assignment, reassignment, search/filtering, status transitions, closing and reopening.
- [ ] Conversations and right-side message alerts for the relevant participants.
- [ ] File upload size/type validation; no unauthorized file downloads or internal-note access.
- [ ] Knowledge-base search, admin article editing, and ticket suggestions.
- [ ] SLA rules, breach creation, duplicate prevention and notification handling.
- [ ] User/team administration, inactive accounts, auto-routing toggle and manual override.
- [ ] Analytics totals, date filters and CSV/Excel exports.
- [ ] Database backup/restore and regression tests after upgrades.

The separate **Phase 10 complete test plan** (distributed with the Phase 10 update) contains detailed manual test cases for all modules.

## Useful commands

```powershell
# In backend/: list registered API endpoints
.\.venv\Scripts\python.exe -m flask --app app routes

# In backend/: seed demo accounts (local only)
.\.venv\Scripts\python.exe -m flask --app app seed

# In frontend/: verify the production bundle builds
npm run build

# In repository root: commit and push changes
git add README.md
git commit -m "docs: add project README and local setup"
git push origin main
```

## Troubleshooting

**`Unexpected token '<' ... is not valid JSON`**  
Usually means a frontend API request received HTML instead of JSON. Confirm Flask is running and that the route exists (`flask --app app routes`). Verify Vite's API proxy configuration when testing locally.

**`GET /api/auth/me` returns `401` before login**  
Usually expected when no active session exists. If login fails too, confirm the demo accounts were seeded into the same SQLite database that Flask is using.

**`.venv` points to a missing Python executable**  
Recreate only the virtual environment, not the SQLite database:

```powershell
# Run in backend/, with Flask stopped
Remove-Item -Recurse -Force .venv
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**`cd backend` says the folder doesn't exist**  
You're probably already in the `backend` directory. Check `Get-Location` before changing folders.

**Frontend loads on Vercel but login fails**  
Expected until a live Flask backend is configured and reachable. The frontend must point to the deployed API, and the backend must support the frontend origin, HTTPS, and production cookie/security settings.

## Deployment plan (not yet complete)

**Frontend — Vercel**
- Import this GitHub repository.
- Set **Root Directory** to `frontend`.
- Framework: **Vite**; Build Command: `npm run build`; Output Directory: `dist`.
- Once Oracle is ready, configure the production API URL and ensure the frontend actually uses it. `VITE_` variables are public; never store secrets in them.

**Backend — Oracle Cloud**
- Provision a suitable Ubuntu VM and deploy Flask behind a production application server and HTTPS reverse proxy.
- Configure secrets, allowed frontend origin, secure cross-origin session handling, database persistence, upload storage, process supervision and backups.
- Oracle Always Free capacity/availability are not guaranteed. An idle free instance can be subject to reclamation under Oracle's policies.

**Security tasks before public release**
- Disable Flask debug mode and remove demonstration accounts.
- Set strong private secrets and configure HTTPS-only cookies with appropriate `SameSite`, CORS and CSRF protection.
- Add login rate limiting, verify role permissions, restrict file upload/download access, and validate server-side data.
- Protect SQLite data and uploaded files with regular off-machine backups; consider PostgreSQL for multi-user production workloads.
- Add monitoring, error logging, and a migration plan. Do not commit `.env`, databases, attachments, private keys, `.venv` or `node_modules`.

## Notes

This repository is an educational/full-stack development project. Its auto-classification uses configurable rules and keyword heuristics; it should not be described as a trained AI model. Local development and feature implementation are distinct from a security-reviewed production deployment.
