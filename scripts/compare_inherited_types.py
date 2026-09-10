# -*- coding: utf-8 -*-
"""Compare every inherited Order Items column against its parent's type.

    python scripts/compare_inherited_types.py
    python scripts/compare_inherited_types.py --converge   # also the guard check

WHY THIS EXISTS
  The design rule for the 48 parent-sync columns is **the child's type matches the
  parent's**, with one deliberate exception: Choice and Lookup sources are flattened
  to Text (spec rule 5), because a synced Choice silently rejects any value outside
  its option list, per row, inside the flow.

  Nothing checked that rule. It was asserted in a doc, measured once by hand on
  2026-09-08 as "26 of 27 match", and that figure covered only the columns whose
  source resolved out of the flow definition -- roughly half of them. This reads the
  types out of both lists' own schemas and checks all of them, including the
  inherited columns that sit OUTSIDE the `Parent Sync` group and were never in scope
  for that count at all. That is where the two unplanned mismatches were.

  Same family as every other drift this repo has been bitten by: an assertion in a
  doc with nothing comparing it to the platform.

WHAT IT READS
  The `ListSchema={...}` record at the head of each SharePoint "Export to CSV". Two
  parsing traps, both hit while writing this:
    - the record spans multiple lines and multiple CSV cells; read the raw text
    - `Type="` also matches inside `FromBaseType="FALSE"`, and `Name="` inside
      `StaticName=`/`DisplayName=`. Anchor every attribute with a lookbehind or the
      whole table comes out wrong in a way that still looks plausible.

THE CONVERGENCE CHECK (--converge)
  Separate from types, and arguably worse. Spec rule 2: writing `null` does not clear
  a SharePoint field, it leaves the old value. So for any unit where the PARENT is
  empty and the CHILD is not:

      guard   : coalesce(child,'') != coalesce(parent,'')  ->  'X' != ''  ->  TRUE
      write   : null                                       ->  child keeps 'X'
      next run: identical, forever

  The guard never settles on those rows. It is not an infinite loop -- the flow only
  runs when the parent is edited -- and it does not corrupt anything, because the
  null write is a no-op. What it costs is a wasted Update per unit on every parent
  edit, each firing the Order Items trigger flow once, which is precisely the
  fan-out the guard exists to prevent.

  🔴 TRUST THE MECHANISM, NOT THIS COUNT. The join here is
  `Model_Revision_ID_TextField` -> `Model_Revion_ID`, because a Lookup column is
  invisible in an export. That mirror's sync flow has been OFF since 2026-08-21, so
  it is stale, and 24 of the 391 revisions carry a `M-` model id in the revision-id
  column. The reported number is therefore an artifact of a bad join as much as a
  real measurement -- treat it as "this case exists", not as "N rows".

  Measuring it properly means reading `ModelRevisionId` / `OrderNumberId` /
  `ModelId` over REST and joining on those. Worth doing before N3 is enabled at
  runbook 4.2; not worth guessing at from exports.
"""
import argparse, collections, io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LISTS = os.path.join(ROOT, "sharepoint-lists")

SYSTEM = {"Title", "ID", "Created", "Modified", "Author", "Editor", "ContentType",
          "Attachments", "ComplianceAssetId", "AppAuthor", "AppEditor",
          "_UIVersionString", "_ColorTag", "LinkTitle", "LinkTitleNoMenu"}

# display-name prefix -> parent list, the convention N2 used for the 48
PREFIX = {"Order - ": "Order", "Model - ": "Models", "Mod. Rev. - ": "Model Revisions"}

# ("TargetInternal", "SourceInternal", "kind") as the generator writes them
TRIPLE = re.compile(r'\(\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"')


def newest(stem):
    # Anchor on the "{List} {YYYY-MM-DD} {HHMM}.csv" convention, NOT a prefix match:
    # `startswith("Order ")` also matches every `Order Items ...` export, and picks
    # the wrong one on sort. That silently compared Order Items against itself and
    # reported 25 columns as having "no parent column found".
    pat = re.compile(re.escape(stem) + r" \d{4}-\d{2}-\d{2} \d{3,4}\.csv$", re.I)
    c = sorted(f for f in os.listdir(LISTS) if pat.match(f))
    if not c:
        raise SystemExit("no export found for %r in %s" % (stem, LISTS))
    return os.path.join(LISTS, c[-1])


def schema(path):
    """internal name -> {Type, DisplayName, Group}, from the ListSchema record."""
    raw = io.open(path, encoding="utf-8-sig", newline="").read(8_000_000)
    raw = raw.replace('\\"', '"')
    out = {}
    for m in re.finditer(r"<Field\b[^>]*>", raw):
        x = m.group(0)
        def g(k):
            # (?<![A-Za-z]) or Type= matches FromBaseType=, Name= matches StaticName=
            hit = re.search(r'(?<![A-Za-z])' + k + r'="([^"]*)"', x)
            return hit.group(1) if hit else None
        n = g("Name")
        if n and n not in out:
            out[n] = {"Type": g("Type"), "DisplayName": g("DisplayName"),
                      "Group": g("Group")}
    return out


def rows_of(path):
    """Data rows, skipping the ListSchema record (which spans lines)."""
    sys.path.insert(0, HERE)
    from load_exports import load
    return load(os.path.abspath(path))


def build():
    oi = schema(newest("Order Items"))
    par = {n: schema(newest(n)) for n in ("Order", "Models", "Model Revisions")}
    bydisp = {n: {(f["DisplayName"] or "").strip(): (k, f)
                  for k, f in d.items() if f["DisplayName"]}
              for n, d in par.items()}

    pairs = []          # (bucket, child_internal, child_display, child_type,
                        #  parent_list, parent_internal, parent_display, parent_type)
    for n, f in oi.items():
        if n in SYSTEM or n.startswith("_"):
            continue
        dn = (f["DisplayName"] or "").strip()

        # 1. the Parent Sync group -- matched by the "<Parent> - <Column>" convention
        if f["Group"] == "Parent Sync":
            for pre, pl in PREFIX.items():
                if dn.startswith(pre):
                    src = dn[len(pre):].strip()
                    hit = bydisp[pl].get(src)
                    pairs.append(("parent-sync", n, dn, f["Type"], pl,
                                  hit[0] if hit else None, src,
                                  hit[1]["Type"] if hit else None))
                    break
            else:
                pairs.append(("parent-sync", n, dn, f["Type"], None, None, None, None))
            continue

        # 2. outside the group: same internal name on a parent
        for pl in ("Order", "Models", "Model Revisions"):
            if n in par[pl] and par[pl][n]["Type"]:
                pairs.append(("inherited", n, dn, f["Type"], pl, n,
                              par[pl][n]["DisplayName"], par[pl][n]["Type"]))
                break
        else:
            # 3. outside the group: same display name, different internal name
            for pl in ("Models", "Model Revisions", "Order"):
                hit = bydisp[pl].get(dn)
                if hit and hit[1]["Type"]:
                    pairs.append(("inherited", n, dn, f["Type"], pl, hit[0],
                                  hit[1]["DisplayName"], hit[1]["Type"]))
                    break
    return pairs


def map_kinds():
    """target internal name -> map kind, read from the generator, the authority."""
    src = io.open(os.path.join(HERE, "gen_n3_flows.py"), encoding="utf-8").read()
    out = {}
    for nm in ("ORDER_MAP", "MODELS_MAP", "REV_MAP"):
        blk = src.split(nm + " = [", 1)[1].split("\n]", 1)[0]
        for m in re.finditer(TRIPLE, blk):
            out[m.group(1)] = m.group(3)
    return out


# Choice/Lookup -> Text is spec rule 5: deliberate, and the reason is real.
def classify(ct, pt):
    if ct == pt:
        return "match"
    if pt in ("Choice", "Lookup", "LookupMulti") and ct == "Text":
        return "by design (rule 5)"
    if pt == "MultiChoice" and ct == "Note":
        return "R22 column"
    return "UNPLANNED"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--converge", action="store_true",
                    help="also count units the change-guard can never settle")
    a = ap.parse_args()

    pairs = build()
    kinds = map_kinds()
    buckets = collections.Counter()
    print("%-28s %-11s %-16s %-26s %-12s %s"
          % ("child (Order Items)", "child", "parent list", "parent column",
             "parent", "verdict"))
    print("-" * 118)
    for bucket, n, dn, ct, pl, pn, pdn, pt in sorted(pairs, key=lambda r: (r[0], r[1])):
        if pt is None:
            # A Lookup column is absent from a SharePoint export entirely -- values AND
            # schema (see the repo CLAUDE.md). So "not in the parent schema" is the
            # expected reading for a lookup source, not a missing column. Take the kind
            # from the generator rather than inferring it from the absence.
            if kinds.get(n) == "lookup" and ct == "Text":
                v = "by design (rule 5)"
            elif kinds.get(n) == "lookup":
                v = "UNPLANNED (lookup source, child is %s not Text)" % ct
            else:
                v = "no parent column found"
        else:
            v = classify(ct, pt)
        buckets[v] += 1
        if v == "match":
            continue
        print("%-28s %-11s %-16s %-26s %-12s %s"
              % (n[:28], ct, pl or "-", (pdn or "-")[:26], pt or "-", v))

    print()
    total = sum(buckets.values())
    for k, v in buckets.most_common():
        print("  %-26s %d" % (k, v))
    print("  %-26s %d" % ("TOTAL inherited columns", total))

    if not a.converge:
        return 0

    # ---------------------------------------------------------------- convergence
    print("\n" + "=" * 70)
    print("CONVERGENCE -- units the change-guard can never settle")
    print("  parent empty + child not empty  =>  guard fires, write is null,")
    print("  null does not clear, so the next run is identical. Forever.")
    print("=" * 70)
    oi = rows_of(newest("Order Items"))
    par_rows = {"Order": rows_of(newest("Order")),
                "Models": rows_of(newest("Models")),
                "Model Revisions": rows_of(newest("Model Revisions"))}
    KEY = {"Order": ("Order - Order Number", "Order Number"),
           "Models": ("Model_ID_TextField", "Model_ID"),
           "Model Revisions": ("Model_Revision_ID_TextField", "Model_Revion_ID")}
    N = lambda v: (v or "").strip()
    grand = collections.Counter()
    for pl, (childkey, parentkey) in KEY.items():
        idx = {N(r.get(parentkey)): r for r in par_rows[pl]}
        cols = [(dn, dn[len(pre):].strip())
                for pre, l in PREFIX.items() if l == pl
                for dn in [p[2] for p in pairs if p[0] == "parent-sync" and p[2].startswith(pre)]]
        per = collections.Counter()
        for u in oi:
            p = idx.get(N(u.get(childkey)))
            if not p:
                continue
            for childdisp, srcdisp in cols:
                cv, pv = N(u.get(childdisp)), N(p.get(srcdisp))
                if cv and not pv:
                    per[childdisp] += 1
        print("\n  %s" % pl)
        if not per:
            print("     none")
        for c, k in per.most_common(8):
            print("     %-34s %d units" % (c, k))
        grand[pl] = sum(per.values())
    print("\n  (unit, column) pairs that can never settle: %d" % sum(grand.values()))
    print("  ⚠️ an export cannot see Lookup or Calculated columns, so this is a floor.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
