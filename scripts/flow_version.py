# -*- coding: utf-8 -*-
"""Version control for Power Automate flow definitions.

THE RULE: nothing modifies a flow -- in the designer or here -- until the current
definition has been exported and snapshotted. These flows are production
automation with no undo, and a single mis-click on a List Name dropdown has wiped
every field mapping on both write actions before.

WHY THIS IS NOT JUST TIMESTAMPED FILES
--------------------------------------
Two people author these flows: the user, in the Power Automate designer, and this
repo, by patching exported JSON. That makes the history a fork, not a line. The
dangerous case is silent:

    v002  pulled          <- both sides start here
    v003  local (me)      <- I author a change from v002
                             ...meanwhile the designer is edited by hand
    paste v003  ->  the hand edit is gone, and nothing reported anything

So every version records a PARENT, and authoring refuses to proceed when its
parent is not the newest pulled version. Three states:

    pulled   exported from the tenant. It *was* live at `captured`. A fact.
    local    authored here. `parent` says what it was based on. Not in the tenant.
    applied  INFERRED, never asserted -- set only when a later pull carries the
             same content hash. A paste cannot prove itself; only an export can.

`history.json` is the source of truth; filenames are for humans and MANIFEST.md is
generated. Metadata never lives only in a filename.

USAGE
-----
    # after every export from Power Automate
    python flow_version.py snapshot <export.zip> --note "P3 toLower applied"

    # authoring locally: parent defaults to the newest pulled, and it refuses
    # to run if that is not what you based the file on
    python flow_version.py snapshot <patched.json> --local --note "D1D2" --parent v002

    python flow_version.py status            # what is live, what is pending, what forked
    python flow_version.py list
    python flow_version.py diff v002 v003
    python flow_version.py emit v003         # paste-ready shapes for an editor
"""
import json, io, os, re, sys, glob, zipfile, hashlib, argparse, datetime

WA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(WA, "workflow-data")
REGISTRY = os.path.join(ROOT, "flows.json")
DEFAULT_FLOW = "Order Items - excel transfer flow"
HIST = "history.json"


# ------------------------------------------------------------------ helpers
def now_iso(override=None):
    if override:
        dt = datetime.datetime.strptime(override.strip(), "%Y-%m-%d %H%M")
    else:
        dt = datetime.datetime.now()
    return dt.astimezone().replace(microsecond=0).isoformat()


def slugify(s, n=48):
    return (re.sub(r"[^A-Za-z0-9]+", "-", s or "snapshot").strip("-")[:n]) or "snapshot"


def read_any(path):
    """(doc, zip_bytes|None). Accepts an exported .zip or a bare .json."""
    if path.lower().endswith(".zip"):
        z = zipfile.ZipFile(path)
        cand = [n for n in z.namelist() if n.endswith("definition.json")]
        if not cand:
            raise SystemExit("no definition.json inside %s" % path)
        return json.loads(z.read(cand[0]).decode("utf-8-sig")), io.open(path, "rb").read()
    return json.load(io.open(path, encoding="utf-8")), None


def definition(doc):
    return doc.get("properties", {}).get("definition", doc.get("definition", doc))


def content_sha(doc):
    """Hash the DEFINITION only. The export wrapper carries volatile metadata, so
    hashing the whole document would report a change when nothing behavioural
    moved -- and this hash is what proves a paste landed."""
    return hashlib.sha256(
        json.dumps(definition(doc), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_actions(doc):
    d = definition(doc)
    try:
        sw = d["actions"]["Apply_to_each"]["actions"]["CheckOrderMatch"]["actions"]["Switch"]
    except Exception:
        return {}
    out = {}
    for case, act in (("No_Items_Found", "CreateOrderItem"), ("One_Item_Found", "UpdateOrderItem")):
        try:
            out[act] = sw["cases"][case]["actions"][act]["inputs"]["parameters"]
        except Exception:
            pass
    return out


def fingerprint(doc):
    """Cheap numbers that catch a wipe at a glance."""
    d = definition(doc)
    s = json.dumps(d, sort_keys=True)
    fp = {"toLower": s.count("toLower("), "ecUpper": s.count("'EC'"),
          "actions": len(d.get("actions", {}))}
    for act, P in write_actions(doc).items():
        fp[act] = len([k for k in P if k.startswith("item/")])
    lr = d.get("actions", {}).get("List_rows_present_in_a_table", {})
    fp["excelFile"] = lr.get("inputs", {}).get("parameters", {}).get("file")
    return fp


# ------------------------------------------------------------------ history
def flow_dir(flow):
    p = os.path.join(ROOT, flow)
    if not os.path.isdir(p):
        raise SystemExit("no such flow folder: %s\nmkdir it, or pass --flow" % p)
    return p


def load_hist(flow):
    p = os.path.join(flow_dir(flow), HIST)
    if os.path.exists(p):
        return json.load(io.open(p, encoding="utf-8"))
    return {"flow": {"folder": flow, "displayName": flow, "id": None,
                     "site": "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio"},
            "versions": []}


def save_hist(flow, h):
    io.open(os.path.join(flow_dir(flow), HIST), "w", encoding="utf-8").write(
        json.dumps(h, indent=2, ensure_ascii=False) + "\n")
    write_manifest(flow, h)


def by_v(h, n):
    for v in h["versions"]:
        if v["v"] == n:
            return v
    return None


def newest(h, state=None):
    vs = [v for v in h["versions"] if state is None or v["state"] == state]
    return vs[-1] if vs else None


def live(h):
    """The newest version we have PROOF was live: newest pulled-or-applied."""
    vs = [v for v in h["versions"] if v["state"] in ("pulled", "applied")]
    return vs[-1] if vs else None


def pending(h):
    return [v for v in h["versions"] if v["state"] == "local"]


def ancestors(h, v):
    """Every local version in v's parent chain, nearest first."""
    out, seen, cur = [], set(), v.get("parent")
    while cur is not None and cur not in seen:
        seen.add(cur)
        node = by_v(h, cur)
        if node is None:
            break
        out.append(node)
        cur = node.get("parent")
    return out


def roots_in_live(h, start, live_v):
    """True when `start` reaches the live version through pending drafts only.

    A chain of local drafts is legitimate -- v003 then v004 on top of it, pasted
    together as one edit. What is NOT legitimate is a chain rooted in something
    the tenant has moved past, which is the case the guard exists to catch.
    """
    seen = set()
    cur = start
    while cur is not None and cur not in seen:
        if cur == live_v:
            return True
        seen.add(cur)
        node = by_v(h, cur)
        if node is None or node["state"] != "local":
            return False
        cur = node.get("parent")
    return False


def parse_ref(h, ref):
    if ref in ("live", "latest"):
        return live(h) or newest(h)
    if ref == "head":
        return newest(h)
    m = re.match(r"^v?(\d+)$", str(ref))
    if not m:
        raise SystemExit("bad version ref %r" % ref)
    v = by_v(h, int(m.group(1)))
    if not v:
        raise SystemExit("no version v%03d" % int(m.group(1)))
    return v


# ------------------------------------------------------------------ manifest
def write_manifest(flow, h):
    L = ["# %s" % h["flow"].get("displayName", flow), "",
         "Flow definition history. Generated by `scripts/flow_version.py` from",
         "`history.json` — **edit neither by hand.**", "",
         "**Nothing modifies this flow until the current definition is exported and",
         "snapshotted here.**", "",
         "| state | meaning |", "|---|---|",
         "| `pulled` | exported from the tenant — *was live* at capture. A fact. |",
         "| `local` | authored in this repo. Not in the tenant. `parent` says what it was based on. |",
         "| `applied` | **inferred** — a later pull carried the same definition hash. A paste never claims this itself. |",
         "| `superseded` | its changes ARE live, folded into a later version. Nothing to do. |",
         "| `forked` | a later pull did *not* match, so this version was never applied and is now stale. **Investigate.** |",
         "",
         "| v | captured | state | parent | change | Create | Update | toLower | `'EC'` | sha |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for v in h["versions"]:
        fp = v.get("fingerprint", {})
        L.append("| **v%03d** | %s | `%s` | %s | %s | %s | %s | %s | %s | `%s` |" % (
            v["v"], v["captured"][:16].replace("T", " "), v["state"],
            ("v%03d" % v["parent"]) if v.get("parent") else "—",
            v.get("note", ""), fp.get("CreateOrderItem", "—"), fp.get("UpdateOrderItem", "—"),
            fp.get("toLower", "—"), fp.get("ecUpper", "—"), v["sha256"][:12]))
    lv = live(h)
    L += ["", "## Right now", ""]
    L.append("- **Live:** %s" % (("v%03d — %s" % (lv["v"], lv.get("note", "")))
                                 if lv else "unknown, nothing pulled yet"))
    p = pending(h)
    L.append("- **Pending (authored, not applied):** %s" %
             (", ".join("v%03d" % x["v"] for x in p) if p else "none"))
    L += ["", "## Reading the columns", "",
          "- **Create / Update** — `item/*` counts on the two write actions. These should only",
          "  ever go up; a drop is the mapping-wipe incident.",
          "- **toLower** — guarded `EC` tests. 4 before P3, 28 after.",
          "- **`'EC'`** — unguarded uppercase-only tests. 0 after P3.",
          "- **sha** — sha256 over the `definition` object alone, key-sorted, so the volatile",
          "  export wrapper does not make an unchanged flow look changed. Equal sha means",
          "  equal behaviour, and that is what proves a paste landed.", ""]
    io.open(os.path.join(flow_dir(flow), "MANIFEST.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


# ------------------------------------------------------------------ commands
def cmd_snapshot(a):
    doc, zb = read_any(a.src)
    sha = content_sha(doc)
    fp = fingerprint(doc)
    h = load_hist(a.flow)
    fold = flow_dir(a.flow)

    same = [v for v in h["versions"] if v["sha256"] == sha]
    if same and not a.local:
        # A pull that matches something we already have. If it matches a pending
        # local version, that is PROOF the paste landed.
        for v in same:
            if v["state"] == "local":
                v["state"] = "applied"
                v["appliedAt"] = now_iso(a.at)
                print("v%03d CONFIRMED APPLIED -- this pull carries its exact definition." % v["v"])
                # Keep the package that proved it. The .zip is the only artifact
                # that re-imports -- it carries connectionsMap/apisMap, so a
                # definition-only JSON cannot restore the flow.
                if zb and "package" not in v.get("files", {}):
                    pkg = v["files"]["definition"][:-5] + ".zip"
                    io.open(os.path.join(fold, pkg), "wb").write(zb)
                    v.setdefault("files", {})["package"] = pkg
                    print("     package attached: %s  (the only re-importable artifact)" % pkg)
                # Everything this version was built on is now live too, folded in.
                for anc in ancestors(h, v):
                    if anc["state"] == "local":
                        anc["state"] = "superseded"
                        anc["supersededBy"] = v["v"]
                        print("v%03d superseded by v%03d -- its changes are live, folded in."
                              % (anc["v"], v["v"]))
        # A pending version is only stale if the tenant is somewhere OTHER than
        # the version it was authored from. A pull that matches its parent means
        # nothing moved, so it stays perfectly valid -- forking it there would
        # cry wolf on every re-export.
        matched = {v["v"] for v in same}
        for other in pending(h):
            if other.get("parent") in matched:
                print("v%03d still pending and still valid -- the tenant is unchanged"
                      " at v%03d, which is what it was authored from." % (other["v"], other["parent"]))
                continue
            other["state"] = "forked"
            other["forkedAt"] = now_iso(a.at)
            print("v%03d marked FORKED -- authored on v%03d but the tenant is at v%03d."
                  % (other["v"], other.get("parent") or 0, sorted(matched)[-1]))
        save_hist(a.flow, h)
        print("no new version stored (identical to v%03d)" % same[0]["v"])
        return 0
    if same and a.local:
        print("identical to v%03d -- nothing to author" % same[0]["v"])
        return 0

    # A pull whose content matches nothing: any pending local never landed.
    if not a.local:
        for other in pending(h):
            other["state"] = "forked"
            other["forkedAt"] = now_iso(a.at)
            print("WARNING  v%03d marked FORKED -- authored but never applied, and the tenant"
                  % other["v"])
            print("         has since moved. Re-author from this new version.")

    # Fork guard on authoring.
    parent = None
    if a.local:
        lv = live(h)
        # Default to the newest pending draft when one exists, so a chain of
        # changes authored in sequence records its real ancestry.
        pend = pending(h)
        default = (pend[-1]["v"] if pend else (lv["v"] if lv else None))
        parent = parse_ref(h, a.parent)["v"] if a.parent else default
        if lv and not roots_in_live(h, parent, lv["v"]):
            raise SystemExit(
                "REFUSING: v%03d does not descend from the newest known-live version v%03d.\n"
                "Re-export the flow, snapshot it, and re-author on top of that -- "
                "otherwise pasting this reverts whatever changed in between." % (parent, lv["v"]))

    n = (h["versions"][-1]["v"] + 1) if h["versions"] else 1
    captured = now_iso(a.at)
    stem = "v%03d__%s__%s__%s" % (n, captured[:16].replace(":", "-"),
                                  "local" if a.local else "pulled", slugify(a.note))
    io.open(os.path.join(fold, stem + ".json"), "w", encoding="utf-8").write(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    files = {"definition": stem + ".json"}
    if zb:
        io.open(os.path.join(fold, stem + ".zip"), "wb").write(zb)
        files["package"] = stem + ".zip"      # the zip is what re-imports; the json does not

    rec = {"v": n, "captured": captured, "state": "local" if a.local else "pulled",
           "parent": parent, "note": a.note or "", "sha256": sha,
           "fingerprint": fp, "files": files,
           "appliedAt": None if a.local else captured,
           "source": os.path.basename(a.src)}
    if h["flow"].get("id") is None:
        h["flow"]["id"] = doc.get("name")
        h["flow"]["displayName"] = doc.get("properties", {}).get("displayName") or a.flow
    h["versions"].append(rec)
    save_hist(a.flow, h)

    print("v%03d  %s" % (n, stem + ".json"))
    print("      state=%s  parent=%s  sha=%s" % (
        rec["state"], ("v%03d" % parent) if parent else "-", sha[:12]))
    print("      Create %s / Update %s item/* | toLower %s | 'EC' %s" % (
        fp.get("CreateOrderItem", "?"), fp.get("UpdateOrderItem", "?"),
        fp.get("toLower"), fp.get("ecUpper")))
    if a.local:
        print("      NOT in the tenant. It becomes `applied` only when a later pull matches this sha.")
    return 0


def cmd_intake(a):
    """Ingest whatever the user dropped in _inbox/ as a pulled version.

    Shape is detected, not configured: the bare `definition` object, the full
    export document, or a .zip package all work -- and the hash covers the
    definition alone, so the same flow pasted in two different shapes gives the
    same hash and is correctly recognised as unchanged."""
    fold = flow_dir(a.flow)
    inbox = os.path.join(fold, "_inbox")
    if not os.path.isdir(inbox):
        raise SystemExit("no _inbox in %s" % fold)
    files = [f for f in sorted(glob.glob(os.path.join(inbox, "*")))
             if os.path.isfile(f) and os.path.splitext(f)[1].lower() in (".json", ".zip", ".txt")]
    if not files:
        print("_inbox is empty -- paste the JSON in there first")
        print("   %s" % inbox)
        return 1
    if len(files) > 1 and not a.all:
        print("more than one file in _inbox -- refusing to guess which is current:")
        for f in files:
            print("   %s" % os.path.basename(f))
        print("remove the stale ones, or pass --all to take them in filename order")
        return 1
    rc = 0
    for f in files:
        print("--- %s" % os.path.basename(f))
        try:
            klass = argparse.Namespace(src=f, note=a.note or "pasted from designer",
                                       local=False, parent=None, at=a.at, flow=a.flow)
            rc |= cmd_snapshot(klass)
        except SystemExit as e:
            print("   FAILED: %s" % e); rc = 1; continue
        except Exception as e:
            print("   FAILED to parse: %s" % e); rc = 1; continue
        os.remove(f)          # the version file is the record; the doorway stays clear
        print("   consumed (removed from _inbox)")
    return rc


def cmd_stage(a):
    """Put one version in _outbox/ as the single thing to paste back."""
    h = load_hist(a.flow)
    v = parse_ref(h, a.ref)
    fold = flow_dir(a.flow)
    out = os.path.join(fold, "_outbox")
    os.makedirs(out, exist_ok=True)
    for old in glob.glob(os.path.join(out, "PASTE-ME*")):
        os.remove(old)        # never two candidates
    doc = read_any(os.path.join(fold, v["files"]["definition"]))[0]
    # Editors disagree about which level they take. An extension reporting
    # `missing "definition" flow property` wants a WRAPPER holding a definition
    # key, not the definition itself -- so write every plausible shape and let the
    # tool decide, rather than guessing and having a paste fail (or half-succeed).
    props = doc.get("properties")
    shapes = {"PASTE-ME.definition.json": definition(doc)}
    if props:
        shapes["PASTE-ME.properties.json"] = props
        shapes["PASTE-ME.minimal.json"] = {
            k: props[k] for k in ("definition", "connectionReferences") if k in props}
        shapes["PASTE-ME.full.json"] = doc
    for fn, obj in shapes.items():
        io.open(os.path.join(out, fn), "w", encoding="utf-8").write(
            json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
    fp = v.get("fingerprint", {})
    par = by_v(h, v["parent"]) if v.get("parent") else None
    pf = par.get("fingerprint", {}) if par else {}
    L = ["# Paste this back", "",
         "**v%03d \u2014 %s**" % (v["v"], v.get("note", "")), "",
         "## Which file", "",
         "Editors disagree about which level they take. Try in this order:", "",
         "| file | shape | use when |",
         "|---|---|---|",
         "| `PASTE-ME.properties.json` | `{apiId, displayName, definition, connectionReferences}` | the editor says **missing `definition` flow property** \u2014 it wants a wrapper |",
         "| `PASTE-ME.definition.json` | the bare `definition` (`$schema` / `triggers` / `actions`) | the editor shows `triggers` and `actions` at its top level |",
         "| `PASTE-ME.minimal.json` | just `{definition, connectionReferences}` | the wrapper is rejected for having extra keys |",
         "| `PASTE-ME.full.json` | the whole export document | last resort |", "",
         "`connectionReferences` is carried through **unchanged from what is live**, so none",
         "of these rebinds a connection.", ""]
    if par:
        L += ["Authored from **v%03d** (%s), which is what the flow was at %s." % (
                  par["v"], par.get("note", ""), par["captured"][:16].replace("T", " ")), ""]
    L += ["## After pasting, check these in the editor", "",
          "| | before | after |", "|---|---|---|"]
    for k, label in (("CreateOrderItem", "`CreateOrderItem` item/* fields"),
                     ("UpdateOrderItem", "`UpdateOrderItem` item/* fields"),
                     ("toLower", "`toLower(` occurrences"),
                     ("ecUpper", "unguarded `'EC'`")):
        L.append("| %s | %s | **%s** |" % (label, pf.get(k, "—"), fp.get(k, "—")))
    L += ["", "## Then close the loop", "",
          "Save in Power Automate, copy the JSON back out into `_inbox/`, and tell me.",
          "`flow_version.py intake` will confirm by hash — if it matches, v%03d flips to" % v["v"],
          "`applied`. Until then it stays `local`: I do not mark my own work as landed.", "",
          "If it does **not** match, v%03d is marked `forked` and I report exactly what" % v["v"],
          "differs — which is the signal that something else changed underneath.", ""]
    io.open(os.path.join(out, "PASTE-ME.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("staged v%03d -> _outbox/PASTE-ME.definition.json" % v["v"])
    print("  %s" % v.get("note", ""))
    print("  expect after paste: Create %s / Update %s | toLower %s | 'EC' %s" % (
        fp.get("CreateOrderItem"), fp.get("UpdateOrderItem"), fp.get("toLower"), fp.get("ecUpper")))
    return 0


def cmd_status(a):
    h = load_hist(a.flow)
    if not h["versions"]:
        print("no versions yet"); return 0
    lv, p = live(h), pending(h)
    print("flow      : %s" % h["flow"].get("displayName"))
    print("versions  : %d" % len(h["versions"]))
    print("LIVE      : %s" % (("v%03d  %s  (%s)" % (lv["v"], lv.get("note", ""), lv["captured"][:16]))
                              if lv else "UNKNOWN -- nothing pulled"))
    print("pending   : %s" % (", ".join("v%03d (%s)" % (x["v"], x.get("note", "")) for x in p) or "none"))
    if len(p) > 1:
        tip = p[-1]
        print("            ^ these chain -- paste only v%03d, it contains the rest" % tip["v"])
    forked = [v for v in h["versions"] if v["state"] == "forked"]
    if forked:
        print("forked    : %s   <-- authored but never applied" %
              ", ".join("v%03d" % v["v"] for v in forked))
    for x in p:
        # Use the same chain rule as the authoring guard: a draft built on another
        # pending draft is fine as long as the chain roots in the live version.
        if lv and not roots_in_live(h, x.get("parent"), lv["v"]):
            print("\nSTALE  v%03d was authored on v%03d but v%03d is live." % (x["v"], x["parent"], lv["v"]))
            print("       Pasting it would revert the difference. Re-author it.")
    return 0


def cmd_list(a):
    h = load_hist(a.flow)
    print("%-5s %-17s %-9s %-6s %-26s %6s %6s %8s %6s %s" %
          ("v", "captured", "state", "parent", "note", "Create", "Update", "toLower", "'EC'", "sha"))
    for v in h["versions"]:
        fp = v.get("fingerprint", {})
        print("%-5s %-17s %-9s %-6s %-26s %6s %6s %8s %6s %s" % (
            "v%03d" % v["v"], v["captured"][:16].replace("T", " "), v["state"],
            ("v%03d" % v["parent"]) if v.get("parent") else "-", (v.get("note") or "")[:26],
            fp.get("CreateOrderItem", "-"), fp.get("UpdateOrderItem", "-"),
            fp.get("toLower", "-"), fp.get("ecUpper", "-"), v["sha256"][:12]))
    return 0


def cmd_diff(a):
    h = load_hist(a.flow)
    A, B = parse_ref(h, a.a), parse_ref(h, a.b)
    da = read_any(os.path.join(flow_dir(a.flow), A["files"]["definition"]))[0]
    db = read_any(os.path.join(flow_dir(a.flow), B["files"]["definition"]))[0]
    print("v%03d %s (%s)  ->  v%03d %s (%s)\n" % (
        A["v"], A.get("note", ""), A["state"], B["v"], B.get("note", ""), B["state"]))
    fa, fb = fingerprint(da), fingerprint(db)
    for k in sorted(set(fa) | set(fb)):
        x, y = fa.get(k), fb.get(k)
        print("  %-16s %-38s %s" % (k, x, ("-> %s" % y) if x != y else "="))
    print()
    Pa, Pb = write_actions(da), write_actions(db)
    for act in ("CreateOrderItem", "UpdateOrderItem"):
        if act not in Pa or act not in Pb:
            continue
        add = sorted(set(Pb[act]) - set(Pa[act])); rm = sorted(set(Pa[act]) - set(Pb[act]))
        ch = sorted(k for k in set(Pa[act]) & set(Pb[act]) if Pa[act][k] != Pb[act][k])
        print("  %s: +%d  -%d  ~%d" % (act, len(add), len(rm), len(ch)))
        for k in add: print("      + %s" % k)
        for k in rm:  print("      - %s     <-- REMOVED" % k)
        for k in ch:  print("      ~ %s" % k)
    return 0


def cmd_emit(a):
    """Write the shapes a JSON editor might want, next to the version."""
    h = load_hist(a.flow)
    v = parse_ref(h, a.ref)
    fold = flow_dir(a.flow)
    doc = read_any(os.path.join(fold, v["files"]["definition"]))[0]
    stem = os.path.join(fold, v["files"]["definition"][:-5])
    outs = {".definition-only.json": definition(doc),
            ".parameters-only.json": write_actions(doc)}
    for suf, obj in outs.items():
        io.open(stem + suf, "w", encoding="utf-8").write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
        print("wrote %s" % os.path.basename(stem + suf))
    print("\nfull export document : %s" % v["files"]["definition"])
    print("definition object    : %s" % os.path.basename(stem + ".definition-only.json"))
    print("the two write actions: %s" % os.path.basename(stem + ".parameters-only.json"))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", default=DEFAULT_FLOW)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot"); s.add_argument("src")
    s.add_argument("--note", default=""); s.add_argument("--local", action="store_true")
    s.add_argument("--parent", help="version this was authored from (default: newest live)")
    s.add_argument("--at", help="override capture time, 'YYYY-MM-DD HHMM', for backfills")
    s.set_defaults(fn=cmd_snapshot)
    s = sub.add_parser("intake"); s.add_argument("--note", default="")
    s.add_argument("--at"); s.add_argument("--all", action="store_true")
    s.set_defaults(fn=cmd_intake)
    s = sub.add_parser("stage"); s.add_argument("ref"); s.set_defaults(fn=cmd_stage)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("diff"); s.add_argument("a"); s.add_argument("b"); s.set_defaults(fn=cmd_diff)
    s = sub.add_parser("emit"); s.add_argument("ref"); s.set_defaults(fn=cmd_emit)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
