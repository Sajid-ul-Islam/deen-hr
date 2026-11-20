# Biometric Device Integration for Frappe HR

This module synchronizes real-time punch logs from on-premise biometric attendance machines directly into **Frappe HR's `Employee Checkin`** DocType.

---

## Supported Devices

- **ZKTeco / eSSL** (Protocol: standalone UDP/TCP port 4370 via `pyzk`)
- **Hikvision / Dahua** (via HTTP Push or ISAPI event polling)
- **ADMS / Push SDK** (Cloud push enabled devices can push directly to custom endpoints in `deen_hr`)

---

## How It Works

1. **Mapping:** The user ID enrolled on the biometric machine matches either:
   * The `Employee` ID in Frappe (e.g. `HR-EMP-00001` or `101`), OR
   * The `Attendance Device ID` field inside Frappe HR's **Employee** record.
2. **Synchronization:** The script fetches punches from the device and sends an authenticated `POST` request to `/api/resource/Employee Checkin`.
3. **Auto Attendance:** In Frappe HR, when **Auto Attendance** is enabled in the Shift Type, Frappe matches punch logs with shift timings to mark:
   * **Present**
   * **Late Entry**
   * **Early Exit**
   * **Absent / Half-day**

---

## Setup & Running

```bash
# 1. Install dependencies
pip install requests pyzk schedule

# 2. Copy and update configuration
cp biometric/config.example.json biometric/config.json

# 3. Test sync manually
python -m biometric.sync_service
```

To run as a continuous background daemon on Windows or Linux, you can schedule it via Windows Task Scheduler, systemd service, or a cron job.
