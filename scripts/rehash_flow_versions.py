# -*- coding: utf-8 -*-
"""Recompute every stored version hash, and re-derive applied/forked from it.

    python scripts/rehash_flow_versions.py            # dry run
    python scripts/rehash_flow_versions.py --apply

WHY THIS EXISTS
  `content_sha` gained a canonicaliser on 2026-09-10, because the Power Automate
  designer round-trips a pasted definition through its own serialiser: it drops
  empty `runAfter: {}` and materialises `else: {"actions": {}}`. Behaviourally
  nothing, but it meant a faithful paste hashed differently from what was authored,
  so every paste reported FORKED. The Order flow's v003 did exactly that -- pasted,
  tested, working, and recorded as never applied.

  Hashes already in `history.json` were computed the old way, so they stay wrong
  until recomputed. This does that from the stored definition files, then re-derives
  each local version's state under the repo's own rule:

      a `local` version is `applied` if some LATER `pulled` version carries the
      same definition hash -- a paste cannot prove itself, only an export can

  It only ever PROMOTES. A local version with no matching pull stays exactly as it
  was, and an existing `applied` is never cleared -- see the comment at that rule for
  why absence of a matching pull is not evidence of absence in this scheme.

  ⚠️ This edits history.json, which the repo README says not to do by hand. That
  rule is about not asserting states; this recomputes them from the stored artifacts
  under the documented rule, which is the opposite. Dry run first regardless.

  ⚠️ AND READ THE DRY RUN PROPERLY. The first version of this script looked up the
  hash under `sha` when the field is `sha256`, so every hash read as None, nothing
  matched anything, and it proposed demoting two correctly-applied versions of the
  transfer flow to `local`. A repair tool that silently reads the wrong key does
  more damage than the bug it fixes. If a dry run proposes REMOVING an `applied`,
  stop and find out why before applying.
"""
import argparse, glob, io, json, os, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WD = os.path.join(ROOT, "workflow-data")
sys.path.insert(0, HERE)
from flow_version import content_sha  # the NEW, canonicalising one


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    total_changed = 0
    for hist_path in sorted(glob.glob(os.path.join(WD, "*", "history.json"))):
        fold = os.path.dirname(hist_path)
        flow = os.path.basename(fold)
        h = json.load(io.open(hist_path, encoding="utf-8"))
        versions = h.get("versions", [])
        changed = []

        # 1. recompute every hash from the stored definition file
        for v in versions:
            fn = (v.get("files") or {}).get("definition")
            if not fn:
                continue
            p = os.path.join(fold, fn)
            if not os.path.exists(p):
                continue
            new = content_sha(json.load(io.open(p, encoding="utf-8")))
            if new != v.get("sha256"):
                changed.append("v%03d sha %s -> %s" % (v["v"], str(v.get("sha256"))[:12], new[:12]))
                v["sha256"] = new

        # 2. re-derive applied/forked: a local version is applied if a LATER pull
        #    carries the same hash. Ordering matters -- an earlier pull proves
        #    nothing about a version authored after it.
        pulls = [(x["v"], x["sha256"]) for x in versions if x.get("state") == "pulled"]
        for v in versions:
            if v.get("state") not in ("local", "forked", "applied"):
                continue
            # PROMOTE ONLY. Never clear an existing `applied`.
            #
            # `applied` is not always evidenced by a stored `pulled` version: intake
            # deliberately stores NOTHING when a drop matches an existing version, and
            # flips that version to `applied` instead. So the confirming export can be
            # gone from `versions` entirely -- the transfer flow's v004 and v006 are
            # exactly that, confirmed by drops that were archived rather than stored.
            #
            # An earlier pass of this script applied the symmetric rule and proposed
            # demoting both to `local`. That would have thrown away the only record
            # that two production pastes ever landed, to fix a hash. Absence of a
            # matching pull is not evidence of absence here.
            if v.get("state") == "applied":
                continue
            if any(pv > v["v"] and psha == v["sha256"] for pv, psha in pulls):
                changed.append("v%03d %s -> applied" % (v["v"], v.get("state")))
                v["state"] = "applied"

        if not changed:
            continue
        total_changed += len(changed)
        print("\n%s" % flow)
        for c in changed:
            print("   " + c)
        if a.apply:
            shutil.copy2(hist_path, hist_path + ".bak")
            io.open(hist_path, "w", encoding="utf-8").write(
                json.dumps(h, indent=2, ensure_ascii=False) + "\n")
            print("   written (previous kept as history.json.bak)")

    print("\n%d change(s)%s" % (total_changed, "" if a.apply else " -- DRY RUN, nothing written"))
    if total_changed and a.apply:
        print("Re-run `flow_version.py --flow \"<flow>\" status` to see the result,")
        print("and regenerate MANIFEST.md if you rely on it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
