# -*- coding: utf-8 -*-
"""The ListSchema record at the top of a SharePoint CSV export carries every
field's real internal Name. That is the authoritative source for flow
expressions -- REST keeps timing out, and retyping an internal name is how
Planned Delivery Date silently wrote nothing."""
import csv, io, re, json, sys

csv.field_size_limit(10 ** 7)

def schema_fields(path):
    raw = io.open(path, encoding="utf-8-sig", newline="").read()
    # The schema JSON is full of commas, so the CSV reader shreds it into
    # hundreds of "fields". Rejoin the whole first record before parsing.
    rec = next(csv.reader(io.StringIO(raw)))
    blob = ",".join(rec).split("=", 1)[1]
    try:
        obj = json.loads(blob)
        xmls = obj["schemaXmlList"]
    except Exception:                                       # fall back to regex
        xmls = re.findall(r'<Field\b.*?(?:/>|</Field>)', blob, re.S)
    out = []
    for x in xmls:
        # Attributes appear either unescaped (JSON parsed) or as \" (regex
        # fallback on the raw blob). Accept both rather than assuming.
        def g(a, x=x):
            m = (re.search(a + r'=\\"(.*?)\\"', x) or re.search(a + r'="([^"]*)"', x))
            return m.group(1) if m else ""
        out.append({"display": g("DisplayName"), "name": g("Name"),
                    "static": g("StaticName"), "type": g("Type"),
                    "readonly": g("ReadOnly"), "choices": re.findall(r"<CHOICE>([^<]*)</CHOICE>", x),
                    "fillin": g("FillInChoice")})
    return out

if __name__ == "__main__":
    path = sys.argv[1]
    fs = schema_fields(path)
    print("parsed %d field definitions" % len(fs))
    wanted = [w.lower() for w in sys.argv[2:]] or None
    for f in fs:
        if wanted and not any(w in f["display"].lower() for w in wanted):
            continue
        extra = ""
        if f["choices"]:
            extra = "  CHOICES=%s fillin=%s" % (f["choices"][:6], f["fillin"] or "?")
        print("  %-34s Name=%-36s Type=%-10s%s" % (f["display"], f["name"], f["type"], extra))
