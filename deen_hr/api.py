import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime


@frappe.whitelist(allow_guest=False)
def push_biometric_checkin(
    device_id: str,
    timestamp: str,
    user_id: str = None,
    employee: str = None,
    log_type: str = "IN",
    skip_auto_attendance: int = 0,
):
    """
    Standard Frappe HR Biometric Ingestion Endpoint.

    Accepts biometric punch log and creates a standard `Employee Checkin` document.
    Adheres strictly to the Frappe HR (hrms) DocType specifications.

    Parameters:
    - device_id: Identifier of the biometric machine.
    - timestamp: Date and time of the punch (e.g. '2026-11-20 09:05:00').
    - user_id: The biometric enrollment ID (matches Employee.attendance_device_id).
    - employee: Frappe Employee ID (e.g. 'HR-EMP-00001'). Optional if user_id is provided.
    - log_type: 'IN' or 'OUT'.
    - skip_auto_attendance: 0 or 1.
    """
    if not employee and not user_id:
        frappe.throw(_("Either 'employee' or 'user_id' (biometric enrollment ID) must be provided."))

    # 1. Resolve employee using Frappe HR's standard attendance_device_id if user_id is passed
    if not employee and user_id:
        employee_match = frappe.db.get_value(
            "Employee",
            {"attendance_device_id": str(user_id), "status": "Active"},
            "name",
        )
        if not employee_match:
            # Fallback check if user_id was set directly as the employee name
            if frappe.db.exists("Employee", str(user_id)):
                employee_match = str(user_id)
            else:
                frappe.throw(
                    _("No active Employee found matching Biometric Device ID: {0}").format(user_id)
                )
        employee = employee_match

    # 2. Parse and normalize timestamp
    punch_time = get_datetime(timestamp)

    # 3. Idempotency Check: prevent duplicate punch records within 60 seconds
    existing = frappe.db.sql(
        """
        SELECT name FROM `tabEmployee Checkin`
        WHERE employee = %s
          AND device_id = %s
          AND TIMESTAMPDIFF(SECOND, time, %s) BETWEEN -60 AND 60
        LIMIT 1
        """,
        (employee, device_id, punch_time),
    )

    if existing:
        return {
            "status": "skipped",
            "message": f"Duplicate punch within 60 seconds detected for {employee} at {punch_time}",
            "checkin_id": existing[0][0],
        }

    # 4. Insert native Employee Checkin document
    checkin_doc = frappe.get_doc(
        {
            "doctype": "Employee Checkin",
            "employee": employee,
            "time": punch_time,
            "log_type": log_type.upper(),
            "device_id": device_id,
            "skip_auto_attendance": int(skip_auto_attendance),
        }
    )
    checkin_doc.insert(ignore_permissions=True)

    return {
        "status": "success",
        "message": f"Check-in successfully recorded for {employee}",
        "checkin_id": checkin_doc.name,
        "time": str(checkin_doc.time),
        "log_type": checkin_doc.log_type,
    }


@frappe.whitelist(allow_guest=False)
def bulk_push_checkins(logs: list):
    """
    Accepts an array of punch records for batch ingestion.
    """
    import json

    if isinstance(logs, str):
        logs = json.loads(logs)

    results = []
    for entry in logs:
        try:
            res = push_biometric_checkin(
                device_id=entry.get("device_id"),
                timestamp=entry.get("timestamp"),
                user_id=entry.get("user_id"),
                employee=entry.get("employee"),
                log_type=entry.get("log_type", "IN"),
                skip_auto_attendance=entry.get("skip_auto_attendance", 0),
            )
            results.append(res)
        except Exception as e:
            results.append({"status": "error", "error": str(e), "entry": entry})

    return {"total": len(logs), "results": results}
