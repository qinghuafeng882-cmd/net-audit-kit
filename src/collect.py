import json
import os
from datetime import datetime
from pathlib import Path

import yaml
from netmiko import ConnectHandler


def load_inventory(inv_path: str) -> list[dict]:
    with open(inv_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    devices = data.get("devices", [])
    if not devices:
        raise ValueError("Inventory is empty: expected 'devices' list.")
    return devices


def ensure_output_dir() -> Path:
    # outputs/YYYY-MM-DD/
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path("outputs") / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def collect_one(device: dict) -> dict:
    conn = None

    conn_params = dict(device)  # copy
    device_name = conn_params.pop("name", None)  # Netmiko doesn't accept "name"

    result = {
        "name": device_name,
        "host": device.get("host"),
        "ok": False,
        "error": None,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
        "version_raw": None,
        "clock_raw": None,
    }

    try:
        conn = ConnectHandler(**conn_params)
        result["version_raw"] = conn.send_command("display version")
        result["clock_raw"] = conn.send_command("display clock")
        result["ok"] = True
        return result
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        return result
    finally:
        try:
            if conn:
                conn.disconnect()
        except Exception:
            pass



def main():
    inv_path = os.environ.get("INVENTORY", "inventory/devices.secret.yaml")
    devices = load_inventory(inv_path)

    out_dir = ensure_output_dir()
    facts_path = out_dir / "facts.json"

    all_results = []
    for dev in devices:
        all_results.append(collect_one(dev))

    payload = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "inventory": inv_path,
        "total": len(all_results),
        "success": sum(1 for r in all_results if r["ok"]),
        "failed": sum(1 for r in all_results if not r["ok"]),
        "results": all_results,
    }

    with open(facts_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[OK] Wrote: {facts_path}")
    print(f"Success={payload['success']} Failed={payload['failed']}")


if __name__ == "__main__":
    main()
