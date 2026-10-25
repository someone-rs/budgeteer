"""Plain-text tables and ASCII bar charts (stdlib only)."""


def render_table(headers, rows):
    """Render a simple aligned table. Returns a string."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    sep = "  ".join("-" * w for w in widths)
    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers)), sep]
    for row in rows:
        lines.append("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)))
    return "\n".join(lines)


def render_bar_chart(items, width=40):
    """items: [(label, value_cents)]. Returns lines of an ASCII bar chart."""
    if not items:
        return ["(no data)"]
    max_val = max(v for _, v in items)
    lines = []
    label_w = max(len(label) for label, _ in items)
    for label, value in items:
        bar_len = int(round(value / max_val * width)) if max_val else 0
        bar = "#" * bar_len
        lines.append(f"{label.ljust(label_w)} | {bar} {value / 100:,.2f}")
    return lines
