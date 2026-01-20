import difflib
from datetime import datetime
from pathlib import Path
import argparse

from normalize import normalize_config


def ensure_out_dir(date_str: str) -> Path:
    out_dir = Path("outputs") / date_str
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def unified_diff(a_lines, b_lines, a_name, b_name) -> str:
    diff = difflib.unified_diff(
        a_lines,
        b_lines,
        fromfile=a_name,
        tofile=b_name,
        lineterm="",
        n=3,
    )
    return "\n".join(diff) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Diff Huawei VRP config backups.")
    parser.add_argument("--baseline", required=True, help="baseline date folder, e.g. 2026-01-18")
    parser.add_argument("--current", required=True, help="current date folder, e.g. 2026-01-19")
    args = parser.parse_args()

    base_dir = Path("backups") / args.baseline
    curr_dir = Path("backups") / args.current

    if not base_dir.exists():
        raise SystemExit(f"Baseline folder not found: {base_dir}")
    if not curr_dir.exists():
        raise SystemExit(f"Current folder not found: {curr_dir}")

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = ensure_out_dir(date_str)

    base_files = {p.name: p for p in base_dir.glob("*.cfg")}
    curr_files = {p.name: p for p in curr_dir.glob("*.cfg")}
    common = sorted(set(base_files) & set(curr_files))

    if not common:
        raise SystemExit("No common *.cfg files to diff. Ensure both folders have same device filenames.")

    changed = 0
    for fname in common:
        a_path = base_files[fname]
        b_path = curr_files[fname]

        # 关键改动：读“全文”，然后 normalize 成 list[str]（每行以 \n 结尾）
        a_text = a_path.read_text(encoding="utf-8", errors="ignore")
        b_text = b_path.read_text(encoding="utf-8", errors="ignore")
        a_lines = normalize_config(a_text)
        b_lines = normalize_config(b_text)

        diff_text = unified_diff(
            a_lines, b_lines,
            a_name=f"{args.baseline}/{fname}",
            b_name=f"{args.current}/{fname}",
        )

        out_file = out_dir / f"diff_{Path(fname).stem}.txt"
        out_file.write_text(diff_text, encoding="utf-8")

        meaningful = [
            line for line in diff_text.splitlines()
            if line.startswith(("+", "-")) and not line.startswith(("+++","---"))
        ]
        if meaningful:
            changed += 1



        print(f"[OK] wrote {out_file}")

    meta = out_dir / "meta.txt"
    meta.write_text(f"baseline={args.baseline}\ncurrent={args.current}\n", encoding="utf-8")


    print(f"Done. Devices diffed={len(common)} Changed={changed}")


if __name__ == "__main__":
    main()
