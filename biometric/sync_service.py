"""
Biometric Attendance Synchronization Service for Frappe HR.

Reads attendance logs from biometric device (e.g. ZKTeco via pyzk or direct network API)
and posts check-in logs to the Frappe HR DocType: "Employee Checkin".
"""

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DeenHR.BiometricSync")


class FrappeHRClient:
    """Client for Frappe REST API to manage Employee Checkins."""

    def __init__(self, site_url: str, api_key: str, api_secret: str, timeout: int = 15):
        self.site_url = site_url.rstrip("/")
        self.timeout = timeout
        self.headers = {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def check_connection(self) -> bool:
        try:
            url = f"{self.site_url}/api/method/frappe.auth.get_logged_user"
            res = requests.get(url, headers=self.headers, timeout=self.timeout)
            if res.status_code == 200:
                user = res.json().get("message")
                logger.info("Successfully connected to Frappe as: %s", user)
                return True
            logger.error("Authentication failed (HTTP %s): %s", res.status_code, res.text)
            return False
        except Exception as e:
            logger.error("Failed to connect to Frappe server: %s", e)
            return False

    def push_employee_checkin(
        self,
        employee_id: str,
        timestamp: datetime,
        log_type: str = "IN",
        device_id: Optional[str] = None,
    ) -> bool:
        """
        Creates an Employee Checkin record in Frappe HR.
        Frappe HR Auto Attendance uses these records to calculate shift attendance.
        """
        url = f"{self.site_url}/api/resource/Employee Checkin"
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "employee": employee_id,
            "time": formatted_time,
            "log_type": log_type,  # "IN" or "OUT"
            "device_id": device_id or "BIOMETRIC_DEVICE",
        }

        try:
            res = requests.post(
                url, headers=self.headers, json=payload, timeout=self.timeout
            )
            if res.status_code in (200, 201):
                logger.info(
                    "Pushed check-in for %s at %s (%s)",
                    employee_id,
                    formatted_time,
                    log_type,
                )
                return True
            elif res.status_code == 409 or "already exists" in res.text.lower():
                logger.debug("Duplicate check-in skipped: %s at %s", employee_id, formatted_time)
                return True
            else:
                logger.error("Failed to push check-in (%s): %s", res.status_code, res.text)
                return False
        except Exception as e:
            logger.error("Error sending checkin to Frappe: %s", e)
            return False


class BiometricDeviceConnector:
    """
    Interface for Biometric Devices.
    Supports ZKTeco / Standalone IP Devices.
    """

    def __init__(self, device_config: Dict[str, Any]):
        self.device_config = device_config
        self.ip = device_config.get("ip", "192.168.1.201")
        self.port = device_config.get("port", 4370)
        self.timeout = device_config.get("timeout", 10)

    def fetch_attendance_logs(self) -> List[Dict[str, Any]]:
        """
        Connects to the device and retrieves punch logs.
        Install 'pyzk' for ZKTeco devices (`pip install pyzk`).
        """
        logs = []
        try:
            from zk import ZK  # type: ignore

            zk = ZK(self.ip, port=self.port, timeout=self.timeout)
            conn = zk.connect()
            logger.info("Connected to Biometric Device at %s:%s", self.ip, self.port)

            attendances = conn.get_attendance()
            for record in attendances:
                logs.append({
                    "user_id": str(record.user_id),
                    "timestamp": record.timestamp,
                    "punch": record.punch,
                    "status": record.status,
                })

            conn.disconnect()
            logger.info("Retrieved %d attendance records from device.", len(logs))
        except ImportError:
            logger.warning(
                "pyzk library not installed. Install via 'pip install pyzk' "
                "or customize fetch_attendance_logs() for your device model."
            )
        except Exception as e:
            logger.error("Biometric device communication error: %s", e)

        return logs


def load_config() -> Dict[str, Any]:
    config_path = Path(__file__).parent / "config.json"
    example_path = Path(__file__).parent / "config.example.json"

    target_path = config_path if config_path.exists() else example_path
    if not target_path.exists():
        raise FileNotFoundError(f"Missing config file at {config_path}")

    with open(target_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    logger.info("Initializing DEEN HR Biometric Sync Service...")
    config = load_config()

    frappe_cfg = config.get("frappe", {})
    client = FrappeHRClient(
        site_url=frappe_cfg.get("site_url", "http://localhost:8000"),
        api_key=frappe_cfg.get("api_key", ""),
        api_secret=frappe_cfg.get("api_secret", ""),
        timeout=frappe_cfg.get("timeout", 15),
    )

    device_cfg = config.get("device", {})
    connector = BiometricDeviceConnector(device_cfg)

    sync_cfg = config.get("sync", {})
    device_id = sync_cfg.get("device_id", "MAIN_DEVICE")

    if not client.check_connection():
        logger.warning(
            "Could not authenticate with Frappe HR server. "
            "Please check config.json credentials."
        )

    logs = connector.fetch_attendance_logs()
    for log in logs:
        client.push_employee_checkin(
            employee_id=log["user_id"],
            timestamp=log["timestamp"],
            log_type="IN",
            device_id=device_id,
        )

    logger.info("Biometric sync cycle finished.")


if __name__ == "__main__":
    main()
