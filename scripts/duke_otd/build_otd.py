"""Duke Energy RFP - Pioneer OTD 2024-2026. Builds the unit-level dataset, the yearly/quarterly
summary, a sensitivity table and the 2026 reconciliation, and writes the backup workbook + a JSON
the slide generator reads.

Rules (see README in the output folder):
  * Unit = one transformer, `NNNNN-u/N` in the FRM10-12 archive, `NNNNN-u` in Jobscope shipments.
    SA / WRG / OS- / E / P / W orders are excluded (same exclusions as Jose's shipments query).
  * Delivery date: 2024-2025 = archive Delivery Date on units with Location = LI (delivered).
    2026 = Jobscope Shipment Date (actual ship record); archive LI units missing from Jobscope
    are added with the archive date and flagged.
  * Promised date: archive Initial Promised Date (per unit); fallback Jobscope DATE PROMISED
    (job level) when the archive has none.
  * On time = delivered <= promised + 8 days (Power BI grace period).
"""
import collections, datetime as dt, json, re, sys, warnings
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

warnings.filterwarnings("ignore")
ROOT = Path(r"C:\Users\solei\OneDrive\Documents\Biplan\claude\Clients\Pioneer Transformer\Workflow-Automation")
ARCHIVE = ROOT / "workbooks" / "Archive active 2026-09-28 1152.xlsx"
JOSE = ROOT / "Requests" / "Jose Data"
OUT = ROOT / "Requests" / "Duke OTD"
OUT.mkdir(exist_ok=True)
GRACE = 8
START = dt.date(2024, 1, 1)


def table(path, name):
    wb = openpyxl.load_workbook(path, data_only=True)
    for s in wb.worksheets:
        if name in s.tables:
            rows = [[c.value for c in r] for r in s[s.tables[name].ref]]
            return [dict(zip(rows[0], r)) for r in rows[1:]]
    raise KeyError(name)


def d(v):
    if isinstance(v, dt.datetime):
        return v.date()
    return v if isinstance(v, dt.date) else None


arc = table(ARCHIVE, "TableArchiveFRM10_12")
ship = table(JOSE / "Ship and Jobs.xlsx", "qry_Shipments_YTD")
jobs = table(JOSE / "Ship and Jobs.xlsx", "qry_JOBS")

JS_END = max(d(r["Shipment Date"]) for r in ship if d(r["Shipment Date"]))
print("Jobscope shipments end", JS_END)

# ---------------- archive units
unit_re = re.compile(r"^(\d{5})-(\d+)/(\d+)$")
excl = collections.Counter()
arc_u = {}
for r in arc:
    o = r["Order"].strip() if isinstance(r["Order"], str) else ""
    m = unit_re.match(o)
    if not m:
        kind = ("blank" if not o else "sub-assembly (SA)" if o.endswith("SA") else "repair (WRG)" if o.startswith("WRG")
                else "service line (OS-)" if o.startswith("OS") else "other non-unit order (E/P/W/R)")
        excl[kind] += 1
        continue
    key = f"{m.group(1)}-{m.group(2)}"
    prev = arc_u.get(key)
    # duplicate unit keys: keep the delivered (LI) row with a date
    if prev is not None:
        excl["duplicate unit row"] += 1
        if prev["Location"] == "LI" and d(prev["Delivery Date"]):
            continue
    arc_u[key] = r

# archive Client is unreliable (most 2025 units read KORTICK); take the customer from Jobscope
cust_job = {r["Shop Number"]: r["CustName"] for r in jobs if r["Shop Number"]}
prom_job = {r["Shop Number"]: d(r["DATE PROMISED"]) for r in jobs if r["Shop Number"] and d(r["DATE PROMISED"])}


def ipd(r):
    v = d(r["Initial Promised Date"]) if r else None
    return v if v and v.year < 2090 else None


units = []  # final unit-level rows


def add(key, job, client, delivered, dsrc, promised, psrc, arc_row, js_date):
    late = (delivered - promised).days
    units.append(dict(unit=key, job=job, client=cust_job.get(job) or client,
                      archive_client=arc_row["Client"] if arc_row else None, delivered=delivered, delivery_source=dsrc,
                      promised=promised, promised_source=psrc, days_vs_promise=late,
                      on_time=late <= GRACE, on_time_strict=late <= 0,
                      archive_delivery=d(arc_row["Delivery Date"]) if arc_row else None,
                      archive_location=arc_row["Location"] if arc_row else None,
                      jobscope_ship=js_date, jobscope_promised=prom_job.get(job),
                      year=delivered.year, quarter=f"{delivered.year}-Q{(delivered.month - 1) // 3 + 1}"))


# 2024-2025 from archive
for key, r in arc_u.items():
    dl = d(r["Delivery Date"])
    if not dl or not (START <= dl <= dt.date(2025, 12, 31)):
        continue
    if r["Location"] != "LI":
        excl["2024-25 archive date but not delivered (Location != LI)"] += 1
        continue
    job = key.split("-")[0]
    pr, ps = ipd(r), "archive IPD"
    if not pr:
        pr, ps = prom_job.get(job), "Jobscope promised (fallback)"
    if not pr:
        excl["2024-25 no promised date in either source"] += 1
        continue
    add(key, job, r["Client"], dl, "archive", pr, ps, r, None)

# 2026 from Jobscope shipments
js_units = {}
for r in ship:
    k = r["Shop Numbers"]
    sd = d(r["Shipment Date"])
    if not k or not sd:
        continue
    if k.endswith("-xx"):  # unit suffix not parseable in the ship description: keep, count once per row
        k = f"{k}#{len([x for x in js_units if x.startswith(k)])}"
    js_units.setdefault(k, (sd, r["CustomerName"]))
for k, (sd, cust) in js_units.items():
    job = k.split("-")[0]
    a = arc_u.get(k)
    pr, ps = ipd(a), "archive IPD"
    if not pr:
        pr, ps = prom_job.get(job), "Jobscope promised (fallback)"
    if not pr:
        excl["2026 Jobscope unit with no promised date"] += 1
        continue
    add(k, job, a["Client"] if a else cust, sd, "Jobscope shipment", pr, ps, a, sd)
# archive-delivered 2026 units Jobscope does not have
for key, r in arc_u.items():
    dl = d(r["Delivery Date"])
    if not dl or dl.year != 2026 or key in js_units:
        continue
    if r["Location"] != "LI" or dl > JS_END:
        excl["2026 archive date not a confirmed delivery (not LI, or after " + str(JS_END) + ")"] += 1
        continue
    job = key.split("-")[0]
    pr, ps = ipd(r), "archive IPD"
    if not pr:
        pr, ps = prom_job.get(job), "Jobscope promised (fallback)"
    if pr:
        add(key, job, r["Client"], dl, "archive (not in Jobscope)", pr, ps, r, None)

# ---------------- summaries
def summarize(rows, keyf):
    s = collections.defaultdict(lambda: [0, 0, 0, []])
    for u in rows:
        b = s[keyf(u)]
        b[0] += 1; b[1] += u["on_time"]; b[2] += u["on_time_strict"]
        if not u["on_time"]:
            b[3].append(u["days_vs_promise"])
    out = []
    for k in sorted(s):
        n, g, st, late = s[k]
        late.sort()
        out.append(dict(period=k, units=n, on_time=g, otd=g / n, otd_strict=st / n,
                        late=n - g, median_days_late=late[len(late) // 2] if late else 0))
    return out


yearly = summarize(units, lambda u: u["year"])
quarterly = summarize(units, lambda u: u["quarter"])
orders_y = collections.defaultdict(lambda: collections.defaultdict(list))
for u in units:
    orders_y[u["year"]][u["job"]].append(u["on_time"])
order_level = {y: (sum(all(v) for v in j.values()), len(j)) for y, j in orders_y.items()}
for y in yearly:
    y["orders"] = order_level[y["period"]][1]
    y["orders_all_on_time"] = order_level[y["period"]][0] / order_level[y["period"]][1]
    y["clients"] = len({u["client"] for u in units if u["year"] == y["period"]})
for r in yearly:
    print(r)
print([(q["period"], q["units"], round(q["otd"] * 100)) for q in quarterly])

# sensitivity: 2026 alternative (Jobscope promise instead of archive IPD); archive-only method all years
sens = []
for y in (2024, 2025, 2026):
    U = [u for u in units if u["year"] == y]
    jp = [u for u in U if u["jobscope_promised"]]
    sens.append(dict(year=y, method="Chosen method", units=len(U), otd=sum(u["on_time"] for u in U) / len(U)))
    sens.append(dict(year=y, method="Promised = Jobscope DATE PROMISED (job level)", units=len(jp),
                     otd=sum((u["delivered"] - u["jobscope_promised"]).days <= GRACE for u in jp) / len(jp)))
    sens.append(dict(year=y, method="No grace period (strict)", units=len(U), otd=sum(u["on_time_strict"] for u in U) / len(U)))
    sens.append(dict(year=y, method="Order level (all units of the order on time)", units=order_level[y][1],
                     otd=order_level[y][0] / order_level[y][1]))
arc_only_2026 = []
for key, r in arc_u.items():
    dl, pr = d(r["Delivery Date"]), ipd(r)
    if dl and pr and dl.year == 2026 and r["Location"] == "LI" and dl <= JS_END:
        arc_only_2026.append((dl - pr).days <= GRACE)
sens.append(dict(year=2026, method="Delivery = archive Delivery Date (archive only)", units=len(arc_only_2026),
                 otd=sum(arc_only_2026) / len(arc_only_2026)))

# 2026 reconciliation
recon = []
for k, (sd, cust) in js_units.items():
    a = arc_u.get(k)
    ad = d(a["Delivery Date"]) if a else None
    cat = ("not in archive" if not a else "archive has no delivery date" if not ad else "same date" if ad == sd
           else "within 3 days" if abs((ad - sd).days) <= 3 else "differs > 3 days")
    recon.append(dict(unit=k, client=cust, jobscope_ship=sd, archive_delivery=ad,
                      archive_location=a["Location"] if a else None,
                      diff_days=(ad - sd).days if ad else None, category=cat))
for key, r in arc_u.items():
    dl = d(r["Delivery Date"])
    if dl and dl.year == 2026 and key not in js_units:
        recon.append(dict(unit=key, client=r["Client"], jobscope_ship=None, archive_delivery=dl,
                          archive_location=r["Location"], diff_days=None,
                          category="archive only - cancelled (AN)" if r["Location"] == "AN"
                          else "archive only - delivered (LI)" if r["Location"] == "LI"
                          else "archive only - not delivered yet (planned date)"))
recon_sum = collections.Counter(x["category"] for x in recon)
print(recon_sum)

# ---------------- workbook
wb = openpyxl.Workbook()
H = Font(bold=True, color="FFFFFF"); HF = PatternFill("solid", fgColor="1F3A4D")


def sheet(title, rows, cols, fmts=None):
    ws = wb.create_sheet(title)
    ws.append(cols)
    for c in ws[1]:
        c.font, c.fill = H, HF
    for r in rows:
        ws.append([r.get(c) for c in cols])
    for i, c in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = max(12, min(45, len(c) + 4))
        for (f, fmt) in (fmts or {}).items():
            if f == c:
                for cell in ws.iter_cols(min_col=i, max_col=i, min_row=2):
                    for x in cell:
                        x.number_format = fmt
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    return ws


wb.remove(wb.active)
pct = "0.0%"
sheet("Yearly", yearly, ["period", "units", "on_time", "late", "otd", "otd_strict", "median_days_late", "orders", "orders_all_on_time", "clients"],
      {"otd": pct, "otd_strict": pct, "orders_all_on_time": pct})
sheet("Quarterly", quarterly, ["period", "units", "on_time", "late", "otd", "otd_strict", "median_days_late"], {"otd": pct, "otd_strict": pct})
sheet("Sensitivity", sens, ["year", "method", "units", "otd"], {"otd": pct})
sheet("Units", units, ["unit", "job", "client", "archive_client", "year", "quarter", "delivered", "delivery_source", "promised", "promised_source",
                       "days_vs_promise", "on_time", "on_time_strict", "archive_delivery", "archive_location", "jobscope_ship", "jobscope_promised"],
      {"delivered": "yyyy-mm-dd", "promised": "yyyy-mm-dd", "archive_delivery": "yyyy-mm-dd", "jobscope_ship": "yyyy-mm-dd", "jobscope_promised": "yyyy-mm-dd"})
sheet("Reconciliation 2026", recon, ["unit", "client", "category", "jobscope_ship", "archive_delivery", "diff_days", "archive_location"],
      {"jobscope_ship": "yyyy-mm-dd", "archive_delivery": "yyyy-mm-dd"})
sheet("Exclusions", [dict(reason=k, rows=v) for k, v in excl.most_common()], ["reason", "rows"])
ws = wb.create_sheet("Method", 0)
for line in (__doc__.strip().splitlines() + ["", f"Archive copy: {ARCHIVE.name}", f"Jobscope: Ship and Jobs.xlsx (shipments {min(v[0] for v in js_units.values())} to {JS_END})",
                                            f"Built {dt.datetime.now():%Y-%m-%d %H:%M}"]):
    ws.append([line])
ws.column_dimensions["A"].width = 120
wb.save(OUT / "Pioneer OTD 2024-2026 - backup data.xlsx")

json.dump(dict(yearly=yearly, quarterly=quarterly, sens=sens, recon=dict(recon_sum), excl=dict(excl),
               js_end=str(JS_END), grace=GRACE,
               promised_sources=collections.Counter(u["promised_source"] for u in units),
               delivery_sources=collections.Counter(u["delivery_source"] for u in units)),
          open(Path(sys.argv[0]).with_name("otd.json"), "w"), indent=1, default=str)
print("delivery sources", collections.Counter((u["year"], u["delivery_source"]) for u in units))
print("promised sources", collections.Counter((u["year"], u["promised_source"]) for u in units))
print("excl", dict(excl))
duke = [u for u in units if u["client"] and "DUKE" in u["client"].upper()]
print("Duke units", len(duke), collections.Counter((u["year"], u["on_time"]) for u in duke), {u["client"] for u in duke})
print("all-customers with DUKE in Jobscope JOBS:", {c for c in cust_job.values() if c and "DUKE" in c.upper()})
