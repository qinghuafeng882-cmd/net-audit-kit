from datetime import datetime
from pathlib import Path
import json
import re

from jinja2 import Environment, FileSystemLoader


RISK_RULES = [
    ("ACL", [r"\bacl\b", r"traffic-filter", r"packet-filter"]),
    ("用户/AAA", [r"\blocal-user\b", r"\baaa\b", r"authentication-mode"]),
    ("接口配置", [r"\binterface\b", r"shutdown", r"undo shutdown", r"port link-type", r"port default vlan"]),
    ("路由", [r"\bip route-static\b", r"\bosfp\b", r"\bbgp\b", r"\brip\b"]),
    ("VLAN", [r"\bvlan\b", r"port trunk allow-pass vlan"]),
    ("NTP/SNMP", [r"\bntp\b", r"\bsnmp\b"]),
    ("SSH/Telnet", [r"\bssh\b", r"\bstelnet\b", r"\btelnet\b"]),
]


def count_diff_changes(diff_text: str) -> tuple[int, int]:
    added = 0
    removed = 0
    for line in diff_text.splitlines():
        if line.startswith(("+++","---","@@")):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed

def top_changes(diff_text: str, limit: int = 10) -> list[str]:
    out = []
    for line in diff_text.splitlines():
        if line.startswith(("+++","---","@@")):
            continue
        if line.startswith(("+", "-")):
            out.append(line)
        if len(out) >= limit:
            break
    return out


def detect_tags(diff_text: str) -> list[str]:
    tags = []
    lower = diff_text.lower()
    for tag, patterns in RISK_RULES:
        for p in patterns:
            if re.search(p, lower):
                tags.append(tag)
                break
    # 去重保持顺序
    seen = set()
    out = []
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return out


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path("outputs") / date_str
    if not out_dir.exists():
        raise SystemExit(f"outputs folder not found: {out_dir}")

    diff_files = sorted(out_dir.glob("diff_*.txt"))
    if not diff_files:
        raise SystemExit("No diff_*.txt found. Run diff.py first.")
    
    meta_path = out_dir / "meta.txt"
    baseline = current = ""
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("baseline="):
                baseline = line.split("=", 1)[1]
            if line.startswith("current="):
                current = line.split("=", 1)[1]


    # 可选：从 facts.json 取 host 信息（如果没有也不阻塞）
    facts_host_map = {}
    facts_path = out_dir / "facts.json"
    if facts_path.exists():
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        for r in facts.get("results", []):
            facts_host_map[r.get("name")] = r.get("host")

    devices = []
    changed = 0
    for p in diff_files:
        name = p.stem.replace("diff_", "")
        diff_text = p.read_text(encoding="utf-8", errors="ignore")

        added, removed = count_diff_changes(diff_text)
        is_changed = (added + removed) > 0
        if is_changed:
            changed += 1

        devices.append({
            "name": name,
            "host": facts_host_map.get(name, ""),
            "changed": is_changed,
            "added": added,
            "removed": removed,
            "tags": detect_tags(diff_text) if is_changed else [],
            "diff_file": p.name,
            "snippets": top_changes(diff_text, limit=10) if is_changed else [],
        })

    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    tpl = env.get_template("report.html.j2")
    html = tpl.render(
        run_at=datetime.now().isoformat(timespec="seconds"),
        total=len(devices),
        changed=changed,
        devices=devices,
        baseline=baseline, 
        current=current,
    )

    report_path = out_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"[OK] Wrote: {report_path}")


if __name__ == "__main__":
    main()
