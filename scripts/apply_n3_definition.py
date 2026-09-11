# -*- coding: utf-8 -*-
"""Put a generated N3 definition into a real flow shell, keeping its connections.

    python scripts/apply_n3_definition.py --flow "Models - Create or Update Trigger" \
                                          --defn Order_Items__sync_from_Models

Then:  python scripts/flow_version.py --flow "<same>" stage vNNN
       and paste _outbox/PASTE-ME.json back into the designer's JSON editor.

WHY THIS EXISTS -- the two halves of a flow live in different places
  `gen_n3_flows.py` writes the `definition` object: triggers, actions, mappings.
  That is the whole flow *logic* and none of its *bindings*. The binding lives one
  level up, in the flow-editor wrapper the browser extension hands back:

      { "$schema": "https://power-automate-tools.local/flow-editor.json#",
        "connectionReferences": {
            "shared_sharepointonline": {
                "connectionName": "shared-sharepointonl-98111a58-...",   <- the real one
                "connectionReferenceLogicalName": "new_sharedsharepointonline_89e9a",
                ... } },
        "definition": { ... } }

  Inside the definition every action says only `"connectionName":
  "shared_sharepointonline"` -- a *name*, resolved through that wrapper. So pasting a
  bare definition into the editor drops `connectionReferences` and the actions come
  back unbound, which is the failure this script exists to make impossible.

  The connection id is tenant-specific and per-flow. It cannot be generated, guessed,
  or copied between flows -- it can only come from the shell the user built. So the
  merge is always: THEIR wrapper, OUR definition.

WHAT IT ASSERTS BEFORE WRITING
  - the shell's trigger list GUID matches the one the generated definition targets,
    so a definition can never land on a flow watching the wrong list
  - the generated trigger is OpenApiConnection + recurrence (a polling trigger), the
    shape both the shell and the live trigger flow actually use
  - the wrapper carries a connectionReferences entry for every connectionName the
    definition refers to
"""
import argparse, io, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
N3 = os.path.join(ROOT, "workflow-data", "n3-flows")

LIST_NAME = {
    "6fe35dfe-2b7d-455a-abe3-056abb386733": "Order",
    "b43a5140-0f9d-4ac1-9019-43b897074224": "Models",
    "e2ff8703-b590-4648-b181-9b47cf3883ba": "Model Revisions",
}


def die(msg):
    print("ABORT: %s" % msg)
    sys.exit(1)


def newest_pulled(flow):
    """The shell to merge into: the newest version PROVEN to have been in the tenant.

    `pulled` and `applied` both qualify, and for the same reason: a pulled version was
    exported from the tenant, and an applied one is a local version a later pull matched
    by hash. Either way its connectionReferences carry a real connection id.

    `local` never qualifies. It has never been in the tenant, so its connection block is
    whatever it was authored from and proves nothing.

    ⚠️ Taking the NEWEST of those, not the oldest, is the point. Merging into a stale
    shell silently reverts everything that changed since -- which is exactly what
    happened to the transfer flow on 2026-09-10, where v007 was authored from a stored
    v006 that had been hand-edited live and never re-exported.
    """
    h = json.load(io.open(os.path.join(ROOT, "workflow-data", flow, "history.json"),
                          encoding="utf-8"))
    live = [v for v in h["versions"] if v.get("state") in ("pulled", "applied")]
    if not live:
        die("no `pulled` or `applied` version in %s -- export the shell out of the "
            "designer and run `flow_version.py intake` first. A local version is not a "
            "shell: it has never been in the tenant, so its connectionReferences prove "
            "nothing." % flow)
    return sorted(live, key=lambda v: v["v"])[-1]


def collect_connection_names(node, acc):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "connectionName" and isinstance(v, str):
                acc.add(v)
            collect_connection_names(v, acc)
    elif isinstance(node, list):
        for v in node:
            collect_connection_names(v, acc)
    return acc


def trigger_of(defn):
    trg = list((defn.get("triggers") or {}).values())
    if len(trg) != 1:
        die("expected exactly one trigger, found %d" % len(trg))
    return trg[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--flow", required=True,
                    help="folder under workflow-data/ holding the shell's history")
    ap.add_argument("--defn", required=True,
                    help="basename in workflow-data/n3-flows/, with or without "
                         ".definition.json")
    ap.add_argument("--note", default=None)
    ap.add_argument("--no-snapshot", action="store_true",
                    help="write the merged file to stdout path only, do not version it")
    a = ap.parse_args()

    # ---------------------------------------------------------------- the shell
    v = newest_pulled(a.flow)
    fold = os.path.join(ROOT, "workflow-data", a.flow)
    shell_path = os.path.join(fold, v["files"]["definition"])
    shell = json.load(io.open(shell_path, encoding="utf-8"))

    if "connectionReferences" not in shell:
        die("%s carries no connectionReferences -- that is the half this merge needs.\n"
            "       Export the flow from the designer's JSON editor (not Export > "
            "Package) and intake that." % os.path.basename(shell_path))

    # ------------------------------------------------------------ the definition
    name = a.defn
    if not name.endswith(".definition.json"):
        name += ".definition.json"
    defn_path = os.path.join(N3, name)
    if not os.path.exists(defn_path):
        die("no such generated definition: %s" % defn_path)
    defn = json.load(io.open(defn_path, encoding="utf-8"))

    # ------------------------------------------------------------------- asserts
    shell_trg = trigger_of(shell["definition"])
    new_trg = trigger_of(defn)

    shell_tbl = ((shell_trg.get("inputs") or {}).get("parameters") or {}).get("table")
    new_tbl = ((new_trg.get("inputs") or {}).get("parameters") or {}).get("table")
    if shell_tbl != new_tbl:
        die("the shell watches a different list than this definition targets.\n"
            "       shell      : %s  (%s)\n"
            "       definition : %s  (%s)\n"
            "       Point the shell's trigger at the right list, re-export, re-intake."
            % (shell_tbl, LIST_NAME.get(shell_tbl, "unknown"),
               new_tbl, LIST_NAME.get(new_tbl, "unknown")))

    if new_trg.get("type") != "OpenApiConnection" or not new_trg.get("recurrence"):
        die("the generated trigger is not a polling trigger (type=%s, recurrence=%s).\n"
            "       SharePoint's create-or-modified trigger POLLS. Run "
            "gen_n3_flows.py and verify_n3_flows.py first."
            % (new_trg.get("type"), new_trg.get("recurrence")))

    want = collect_connection_names(defn, set())
    have = set(shell["connectionReferences"].keys())
    missing = want - have
    if missing:
        die("the definition refers to connections the shell cannot resolve: %s\n"
            "       have: %s\n"
            "       Add an action using that connector to the shell, save, re-export."
            % (sorted(missing), sorted(have)))

    # --------------------------------------------------------------------- merge
    merged = dict(shell)
    merged["definition"] = defn
    # The editor's own shells carry `outputs`; keep the shape it expects.
    merged["definition"].setdefault("outputs", {})

    print("shell      : %s" % os.path.basename(shell_path))
    print("definition : %s" % name)
    print("trigger    : %s on %s (%s)"
          % (new_trg["type"], LIST_NAME.get(new_tbl, new_tbl), new_tbl))
    print("connections: %s  -> all resolved by the shell" % sorted(want))
    n_fields = sum(1 for _ in json.dumps(defn).split('"item/')) - 1
    print("write targets in definition: %d" % n_fields)

    tmp = os.path.join(tempfile.gettempdir(), "n3-merged-%s.json" % a.defn)
    io.open(tmp, "w", encoding="utf-8").write(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n")

    if a.no_snapshot:
        print("\nmerged -> %s   (not versioned)" % tmp)
        return 0

    note = a.note or ("N3 %s pasted into the shell, connectionReferences kept from v%03d"
                      % (a.defn, v["v"]))
    cmd = [sys.executable, os.path.join(HERE, "flow_version.py"),
           "--flow", a.flow, "snapshot", tmp, "--local",
           "--parent", "v%03d" % v["v"], "--note", note]
    print()
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
