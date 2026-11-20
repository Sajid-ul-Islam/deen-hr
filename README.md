# DEEN HR (Frappe HR & Biometric Integration)

DEEN HR is an enterprise human resources management system built on top of [Frappe HR](https://github.com/frappe/hrms) and the [Frappe Framework](https://github.com/frappe/frappe), customized for specialized company workflows and direct biometric attendance device integration.

---

## Architecture Overview

```
┌─────────────────────────────────┐
│     Physical Biometric Device   │  (e.g., ZKTeco, eSSL, Hikvision)
└────────────────┬────────────────┘
                 │ Local LAN / TCP-IP / Push SDK
┌────────────────▼────────────────┐
│   Biometric Sync Service / API  │  (`biometric/sync_service.py`)
└────────────────┬────────────────┘
                 │ Authenticated Frappe REST API
┌────────────────▼────────────────┐
│      Frappe HR Core Engine      │
│  - DocType: `Employee Checkin`  │
│  - Auto Attendance Scheduler    │
│  - Shift Management & Roster    │
│  - Leave Ledger & Payroll       │
└─────────────────────────────────┘
```

### Key Components
1. **Frappe HR (`hrms`):** The primary open-source application powering leaves, shifts, holidays, expense claims, payroll, and appraisals.
2. **`deen_hr` (Custom Frappe App):** Custom DocTypes, client/server scripts, workflows, and overrides specific to DEEN HR requirements without modifying core code.
3. **`biometric` (Device Connector):** Independent sync utility designed to connect to the biometric device over the network, capture punch-in / punch-out events, and push them directly to Frappe HR's `Employee Checkin` document.

---

## Project Structure

```text
DEEN HR/
├── .gitignore
├── README.md
├── pyproject.toml
├── deen_hr/                   # Custom Frappe App
│   ├── __init__.py
│   ├── hooks.py              # Frappe app hooks (events, doctype overrides)
│   ├── modules.txt
│   └── patches.txt
├── biometric/                 # Biometric device sync service
│   ├── README.md
│   ├── __init__.py
│   ├── config.example.json   # Device IP, API keys, sync intervals
│   └── sync_service.py       # Sync daemon pushing to Employee Checkin
└── docker/                    # Local container development environment
    ├── .env.example
    └── docker-compose.yml
```

---

## How Biometric Integration Works in Frappe HR

Frappe HR natively processes attendance through the **`Employee Checkin`** DocType:

1. The biometric device records a punch: `{ user_id, timestamp, device_id }`.
2. The `biometric/sync_service.py` service queries the device (or receives device push data).
3. The sync service creates an `Employee Checkin` record via Frappe REST API:
   ```json
   POST /api/resource/Employee Checkin
   {
     "employee": "HR-EMP-00001",
     "time": "2026-11-20 09:05:22",
     "log_type": "IN",
     "device_id": "MAIN_GATE_01"
   }
   ```
4. Frappe HR's built-in **Auto Attendance** scheduler automatically evaluates `Employee Checkin` logs against employee shifts to mark the employee as **Present**, **Late Entry**, **Early Exit**, or **Half Day**.

---

## Getting Started

### 1. Requirements
* Git
* Python 3.10+
* Docker Desktop or Ubuntu (WSL2 recommended for Windows development)
* Network access to your biometric device

### 2. Biometric Service Configuration
1. Navigate to `biometric/`:
   ```bash
   cp biometric/config.example.json biometric/config.json
   ```
2. Edit `config.json` with:
   * Device IP and Port.
   * Frappe Site URL (e.g., `http://localhost:8000` or production domain).
   * Frappe API Key & API Secret (generated from an Admin user in Frappe Desk).
3. Run the service:
   ```bash
   python -m biometric.sync_service
   ```

---

## Frappe Bench Setup (When deploying to server/bench)

To install this custom app onto an existing Frappe Bench:

```bash
# In your bench directory:
bench get-app https://github.com/<your-username>/deen-hr.git
bench --site <your-site-name> install-app hrms
bench --site <your-site-name> install-app deen_hr
bench --site <your-site-name> migrate
```

---

## License

This project is licensed under the MIT License. Frappe and Frappe HR are licensed under GNU AGPLv3.
