import re

# 按需扩展：这些行通常不应参与审计 diff（示例）
DROP_PATTERNS = [
    r"^#.*$",                      # 注释
    r"^!.*$",                      # 某些设备风格
    r"^return$",                   # VRP 输出尾部
    r"^.*generated.*$",            # 自动生成标记
]

def normalize_config(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.rstrip()

        # 去空行（可选：如果你想保留结构就不要跳过）
        if not line:
            continue

        # 统一多空格
        line = re.sub(r"\s+", " ", line).strip()

        # 丢弃无意义行
        drop = False
        for p in DROP_PATTERNS:
            if re.match(p, line, flags=re.IGNORECASE):
                drop = True
                break
        if drop:
            continue

        lines.append(line + "\n")
    return lines
