"""Extract state and local data center restrictions from a saved datacenterbans.com page.

The site is a Next.js app that embeds its data as a React Server Components
payload (self.__next_f.push chunks). Rows are "id:value" lines where values
reference each other with "$id" and long strings are encoded as "id:T<hexlen>,<text>".

Usage: python3 -I scripts/parse_datacenterbans.py data/raw/datacenterbans/index.html data/raw/datacenterbans/
"""
import csv
import json
import re
import sys
from pathlib import Path


def decode_payload(html):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', html, re.S)
    return "".join(json.loads('"' + c + '"') for c in chunks)


def parse_rows(payload):
    """Split the RSC stream into {id: raw_value}, honoring T<hexlen> text rows."""
    rows, i, n = {}, 0, len(payload)
    head = re.compile(r"([0-9a-f]+):")
    while i < n:
        m = head.match(payload, i)
        if not m:
            nl = payload.find("\n", i)
            i = n if nl < 0 else nl + 1
            continue
        rid, j = m.group(1), m.end()
        t = re.match(r"T([0-9a-f]+),", payload[j:])
        if t:
            # Length is in UTF-8 bytes, not characters.
            start = j + t.end()
            size = int(t.group(1), 16)
            text = payload[start:].encode("utf-8")[:size].decode("utf-8", "ignore")
            rows[rid] = ("text", text)
            i = start + len(text)
        else:
            nl = payload.find("\n", j)
            nl = n if nl < 0 else nl
            rows[rid] = ("json", payload[j:nl])
            i = nl + 1
    return rows


def resolver(rows):
    cache = {}

    def get(rid):
        if rid in cache:
            return cache[rid]
        kind, raw = rows[rid]
        if kind == "text":
            val = raw
        else:
            try:
                val = json.loads(raw)
            except json.JSONDecodeError:
                val = raw
        cache[rid] = val
        val = resolve(val)
        cache[rid] = val
        return val

    def resolve(v):
        if isinstance(v, str) and v.startswith("$") and v[1:] in rows:
            return get(v[1:])
        if isinstance(v, list):
            return [resolve(x) for x in v]
        if isinstance(v, dict):
            return {k: resolve(x) for k, x in v.items()}
        return v

    return get


def main(html_path, out_dir):
    out = Path(out_dir)
    rows = parse_rows(decode_payload(Path(html_path).read_text(encoding="utf-8")))
    get = resolver(rows)

    states = []
    for rid, (kind, raw) in rows.items():
        if kind == "json" and raw.startswith('{"id":"') and '"fips":"' in raw and '"status":"' in raw:
            states.append(get(rid))
    states.sort(key=lambda s: s["fips"])

    with open(out / "states.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state", "state_fips", "name", "status", "tags", "last_updated", "n_bills", "n_local_actions", "summary"])
        for s in states:
            w.writerow([s["id"], s["fips"], s["name"], s["status"], ";".join(s.get("tags") or []),
                        s.get("lastUpdated"), len(s.get("bills") or []), len(s.get("localMoratoriums") or []),
                        s.get("summary")])

    bill_keys = sorted({k for s in states for b in (s.get("bills") or []) if isinstance(b, dict) for k in b})
    with open(out / "state_bills.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state"] + bill_keys)
        for s in states:
            for b in s.get("bills") or []:
                w.writerow([s["id"]] + [json.dumps(b.get(k)) if isinstance(b.get(k), (list, dict)) else b.get(k) for k in bill_keys])

    local_keys = ["locality", "countyFips", "type", "status", "date", "description", "url"]
    with open(out / "local_actions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["state"] + local_keys)
        for s in states:
            for a in s.get("localMoratoriums") or []:
                w.writerow([s["id"]] + [a.get(k) for k in local_keys])

    print(f"{len(states)} states, bill fields: {bill_keys}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
