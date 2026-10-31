# IT Helpdesk & Service Management System — Complete Test Plan
**Release candidate:** Phase 10 (local development; NOT yet deployed)  
**Baseline:** Phases 1–9 + 7.1 chat fix  
**Platform:** React/Vite + Python Flask + SQLite  
**Tester:** ____________________   **Date:** ____________________  
**Result key:** PASS / FAIL / BLOCKED / NOT TESTED

## 0. Safety and setup
1. Stop Flask and Vite. Back up `backend/helpdesk.db`, the `backend/instance_uploads/` folder, and `.env` to a private location outside the project. Never share `.env` or uploaded confidential files.
2. Copy ONLY Phase 10 replacement files (`backend/app.py`, `frontend/src/main.jsx`, `frontend/src/style.css`) to the same paths inside your existing Phase 9 project. Preserve `backend/sla_phase3.py`, `backend/phase7_ticket_tools.py`, `backend/phase8_admin.py`, `backend/phase9_routing.py`, all React component files, and the database.
3. Backend PowerShell (project path may differ):
   ```powershell
   cd F:\ZEENAT\IT-Helpdesk-Starter\backend
   .\.venv\Scripts\python.exe -m flask --app app routes
   .\.venv\Scripts\python.exe app.py
   ```
4. Frontend, **second** terminal:
   ```powershell
   cd F:\ZEENAT\IT-Helpdesk-Starter\frontend
   npm run dev
   ```
5. Open `http://localhost:5173`. Use seeded accounts only in the local test environment: `admin@demo.local`, `engineer@demo.local`, `employee@demo.local`, password `Demo12345!`. For simultaneous notification tests, use **separate browser profiles** (not two tabs of one profile, which share login cookies).
6. If demo accounts do not exist, back up DB before running `python -m flask --app app seed`. Do not reset or delete the SQLite file.

## 1. Test fixtures: realistic ticket examples
**T1 — Wi-Fi outage (High / Network):**  
Title: `Office laptop cannot connect to Wi-Fi`  
Description: `Since 9:30 AM my laptop cannot connect to the company Wi-Fi. Windows displays "Can't connect to this network". Restarting the laptop did not help. I cannot access internal applications and need network assistance.`

**T2 — Printer issue (Medium / Hardware):**  
Title: `Office printer queue is stuck`  
Description: `Print jobs from my Windows laptop remain in the queue. The printer has power and is connected, but no pages are printing. Restarting it did not help. Screenshot attached.`

**T3 — Business-wide outage (Critical / Network):**  
Title: `Entire department network unavailable`  
Description: `All members of our department have lost internet and internal network access. Business operations are stopped. Please escalate immediately.`

**T4 — Account locked (High / Access):**  
Title: `Company account locked after failed sign-in`  
Description: `My account reports it is locked after several attempts. Please verify my identity through the approved process and help restore account access.`

**Knowledge articles:** Wi-Fi connection troubleshooting, slow computer performance, Outlook sending/receiving, and account locked. If absent, load the existing article-seed script after confirming backend paths.

## 2. Phase 1 — Authentication & ticket lifecycle
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P1-01 | Sign in separately as Admin, Engineer, Employee | Correct role and sidebar visible | ___ |
| P1-02 | Employee creates T1 | Ticket saved, `Open`, visible to creator | ___ |
| P1-03 | Admin opens T1, assigns engineer | Assigned engineer and activity reflect change | ___ |
| P1-04 | Engineer changes status In Progress, sends reply, resolves | Status and messages saved | ___ |
| P1-05 | Employee confirms successful resolution | Ticket becomes Closed | ___ |
| P1-06 | With another resolved ticket, employee chooses Reopen | Reopened workflow works as implemented | ___ |
| P1-07 | Attempt wrong password / missing authentication | Login rejected / protected API returns 401 | ___ |

## 3. Phase 2 — Ticket filters, activity, workload
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P2-01 | Search ticket title and numeric ID | Correct matches | ___ |
| P2-02 | Filter by category, priority, status, assignment | Correct filtered rows | ___ |
| P2-03 | Assign, reply and change status | Corresponding timeline events recorded | ___ |
| P2-04 | Assign two active tickets to one engineer | Workload count updates | ___ |
| P2-05 | Refresh browser | Tickets and events persist | ___ |

## 4. Phase 3 — SLA monitoring
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P3-01 | Admin opens SLA Policies | Existing priority targets visible | ___ |
| P3-02 | Change Critical response 1 minute, resolution 2 minutes | Saved policy applies to NEW tickets | ___ |
| P3-03 | Employee creates T3; do not respond | Deadline fields populated | ___ |
| P3-04 | After deadlines, admin runs manual SLA scan | Breach alert(s) created as applicable | ___ |
| P3-05 | Run scan again | No duplicate alerts for same breach | ___ |
| P3-06 | Reopen older ticket after policy change | Historical due dates not silently rewritten | ___ |
| P3-07 | Restore original SLA settings after demo | Normal local test environment | ___ |

## 5. Phase 4 — Knowledge base
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P4-01 | Open Knowledge Base and search Wi-Fi | Relevant published article appears | ___ |
| P4-02 | Open article and read detailed steps | Description and procedure readable | ___ |
| P4-03 | Admin creates / updates draft | Changes persist; draft hidden from employee | ___ |
| P4-04 | Open T1 ticket | Appropriate troubleshooting suggestions if matching configured | ___ |
| P4-05 | Non-admin tries knowledge edit endpoint | 403; data remains unchanged | ___ |

## 6. Phase 5 — Analytics and exports
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P5-01 | Open Analytics as admin | Counts and charts load | ___ |
| P5-02 | Compare totals and statuses against ticket list | Counts make sense for filter | ___ |
| P5-03 | Apply date range with zero results | Clean empty statistics, no crash | ___ |
| P5-04 | Export CSV and XLSX | Files download and contain appropriate records | ___ |
| P5-05 | Employee tries Analytics API | Access denied | ___ |

## 7. Phase 6 — Fixed sidebar & general alerts
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P6-01 | Scroll long tickets / Knowledge Base / Analytics pages | Left sidebar stays fixed on desktop | ___ |
| P6-02 | Scroll with long navigation list | Profile and Sign out stay pinned at sidebar bottom | ___ |
| P6-03 | Admin assigns ticket; engineer logged in separately | Engineer sees in-app assignment alert after poll | ___ |
| P6-04 | Mark notification as read | Unread counter decreases | ___ |
| P6-05 | Reload Knowledge Base | Polished cards and filtering remain functional | ___ |

## 8. Phase 7 + 7.1 — Attachments, notes, conversations
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P7-01 | Employee uploads printer screenshot PNG to T2 | File saved and listed | ___ |
| P7-02 | Engineer downloads T2 PNG | Correct binary downloads | ___ |
| P7-03 | Upload unsupported extension or file over 4 MB | Server rejects upload | ___ |
| P7-04 | Engineer adds internal note | Admin/engineer can see it | ___ |
| P7-05 | Employee opens same ticket | Internal note not visible | ___ |
| P7-06 | Open Conversations from each role's sidebar | Accessible ticket threads shown | ___ |
| P7-07 | Reply in thread then refresh | Message persists, correct sender | ___ |
| P7-08 | Nonparticipant tries to download unrelated attachment | Denied | ___ |

## 9. Phase 8 — Users and teams
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P8-01 | Admin creates Network Support team | Team listed | ___ |
| P8-02 | Admin creates `network.demo@example.test` engineer | New engineer account exists | ___ |
| P8-03 | Assign engineer to team | Team membership saved | ___ |
| P8-04 | Deactivate test engineer, attempt login | Sign-in blocked | ___ |
| P8-05 | Reactivate account | Sign-in restored | ___ |
| P8-06 | Non-admin opens Users & Teams API | Denied | ___ |
| P8-07 | Admin tries to deactivate own account | Rejected | ___ |

## 10. Phase 9 — Smart routing
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P9-01 | Map Network category to Network Support | Config saved | ___ |
| P9-02 | Employee previews suggestion for T1 | Reasonable Network suggestion; priority editable | ___ |
| P9-03 | Enable auto assignment; employee creates fresh Network ticket | Eligible least-busy engineer assigned, if present | ___ |
| P9-04 | Assign ticket manually | Manual assignment not silently overwritten | ___ |
| P9-05 | Disable auto assignment; create ticket | Ticket remains unassigned until human action | ___ |

## 11. Phase 10 — Right-side message previews (NEW)
**Keep Admin, Engineer and Employee sessions logged in at the same time in different browser profiles.** Notifications use polling every ~3 seconds and may take longer under load. An existing notification from before login is intentionally **not** shown as a popup; inspect the Alerts page for existing unread notifications.

| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| P10-01 | Employee sends message in assigned T1 conversation | Engineer and active admin each get their own unread notification and right-side preview | ___ |
| P10-02 | Engineer sends reply in same conversation | Employee and admin see right-side message preview | ___ |
| P10-03 | Admin sends message | Employee and assigned engineer see preview; admin does not self-notify | ___ |
| P10-04 | Examine preview body | Shows sender, ticket ID, short message excerpt (up to ~115 chars) | ___ |
| P10-05 | Click Open conversation on preview | Opens Conversations with correct ticket; marks notification read | ___ |
| P10-06 | Wait around 9 seconds | Preview disappears; unread alert still in Alerts until read | ___ |
| P10-07 | Close preview with × | Closes preview without marking read | ___ |
| P10-08 | Refresh browser / sign out and back in | No flood of old popup notifications; unread Alerts still available | ___ |
| P10-09 | Employee sends 2 messages quickly | Multiple previews appear (limited to 4 visible); no duplicate notifications per user for one message | ___ |
| P10-10 | Unassigned ticket: employee sends message | Employee does not receive their own message; admins do; no engineer is invented | ___ |
| P10-11 | Disabled administrator account exists | Disabled admin receives no new message alerts | ___ |
| P10-12 | Recheck fixed sidebar and long-page scrolling | Position unchanged from Phase 6 | ___ |

## 12. Security, failure, and recovery checks (local release gate)
| ID | Steps | Expected outcome | Result |
|---|---|---|---|
| SEC-01 | Try accessing ticket API without login | 401 JSON; no ticket leaked | ___ |
| SEC-02 | Employee requests a different employee's ticket | 403/404; no private ticket data | ___ |
| SEC-03 | Employee attempts PATCH assignment/status as admin | 403; state unchanged | ___ |
| SEC-04 | Employee attempts to create internal note | Denied | ___ |
| SEC-05 | Test HTML/script-like text in message and article | Rendered as text; no code executes | ___ |
| SEC-06 | Confirm files, secrets, and database backups are NOT committed to public repository | No private data in source control | ___ |
| SEC-07 | Restart Flask and reload UI | Stored data persists; notifications still work | ___ |
| SEC-08 | Disconnect backend, attempt action, reconnect | UI displays useful error and recovers | ___ |
| SEC-09 | Confirm no production secrets are hard-coded; rotate demo credentials before deployment | Documented and ready for deployment phase | ___ |

## 13. Test evidence log
| Test ID | Actual result / failure | Browser console / Flask log | Screenshot or file | Owner |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |
| | | | | |

## 14. Acceptance / sign-off
- [ ] All Phase 10 message-preview tests pass.
- [ ] Critical auth/authorization tests pass (SEC-01 to SEC-04).
- [ ] Previous ticket creation → assign → reply → resolve → close workflow works.
- [ ] Attachments, Knowledge Base, SLA, Analytics and exports have passed regression checks.
- [ ] Database and upload backups verified.
- [ ] All failed/blocked cases documented with exact reproduction steps.

**Overall status:** PASS / FAIL / BLOCKED  
**Tester name:** ____________________   **Date:** ____________________  
**Known remaining bugs:** _________________________________________________

## 15. Deployment is intentionally postponed
This Phase 10 update is a **local testing release**, not a production security certification. Before public deployment, separately audit authentication/session configuration, CSRF protections, security headers, HTTPS, production secrets, rate limiting, database backups, multi-worker scheduler behavior, uploaded-file controls, logging, dependency versions, and deployment-specific load tests. No deployment or hosting settings are changed in this package.
