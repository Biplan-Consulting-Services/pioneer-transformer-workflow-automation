# -*- coding: utf-8 -*-
"""Replace the state board's task list with what is actually left.

    python scripts/update_state_board.py

Patches artifacts/cutover-state-board.html in place: swaps the "Do this next"
section for a current one and resets the saved ticks. Everything else on the page --
the decisions, the value-conversion table, the styling, the in-page save -- is left
exactly as it was.

The board is the live list the user works from, so it is edited rather than rebuilt.
"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))
BOARD = os.path.join(os.path.dirname(HERE), "artifacts", "cutover-state-board.html")

LANES = [
 ("you", "Now &mdash; before 22:00", "the only staff-facing work that can finish before the freeze", [
  ("FRLBL", "Verify three French UI labels",
   "Open the classic view-settings page <b>in French</b> and confirm they read exactly "
   "&laquo;&nbsp;Regrouper par&nbsp;&raquo;, &laquo;&nbsp;R&eacute;duits&nbsp;&raquo; and "
   "&laquo;&nbsp;Limite d&rsquo;&eacute;l&eacute;ments&nbsp;&raquo;. Section 7 of the French "
   "handbook names them and they were reasoned, never read off the screen. Thirty seconds "
   "&mdash; and staff search for those exact words, so a wrong one makes them doubt the parts "
   "that are right."),
  ("PUBHB", "Publish the handbook",
   "<code>staff-handbook-sharepoint.md</code> and <code>-fr.md</code> onto a SharePoint page. "
   "Depends on nothing, and the email needs its link &mdash; so it is the one staff-facing "
   "thing that can genuinely be finished now."),
  ("EMAILNOW", "Send the email",
   "Tensed for exactly this: <em>la bascule se fait ce soir&hellip; quand vous arriverez demain "
   "matin</em> &mdash; true when sent this evening and still true read over breakfast. It says "
   "plainly there is nothing to do tonight, so nobody feels summoned back. "
   "&#9888;&#65039; It does <b>not</b> ask anyone to save and close FRM10-12, because everyone "
   "had already left &mdash; so anything unsaved on a machine tonight will not reach SharePoint. "
   "First thing to suspect if the re-diff at step 9 turns up stale-looking units."),
  ("LINKS", "Fill the two links in the email",
   "<code>[LIEN]</code> the read-only workbook, <code>[LIEN GUIDE]</code> wherever the handbook "
   "is published. Neither was invented for you. A SharePoint page on the site is the obvious "
   "home for the handbook &mdash; staff are already there and it needs no separate permission."),
 ]),
 ("me", "Stage 1 &middot; Freeze", "22:00, once everyone is out of the workbooks", [
  ("EXP", "Re-export all four lists",
   "<code>Order Items</code>, <code>Order</code>, <code>Models</code>, "
   "<code>Model Revisions</code>. <b>This is the only data rollback</b>, and taking it now "
   "rather than earlier is the whole point of it being step one."),
  ("CLOSE", "Staff save and close FRM10-12",
   "&#128308; <b>Desktop Excel only.</b> A browser save corrupted this workbook on 09-09. "
   "Anything left unsaved never reaches SharePoint."),
  ("REFRESH", "Refresh FRM10-12 via the Office Script button",
   "&#128308; Never <b>Refresh All</b>, never COM <code>RefreshAll</code>. "
   "<code>TableOrders</code> reads the sheet table it writes back to, and a generic refresh "
   "re-lands it without six native formula columns."),
  ("V007", "Paste transfer <code>v007</code>",
   "Expect Create <b>122</b> / Update <b>130</b> <code>item/*</code>, <code>toLower(</code> "
   "<b>34</b>. Urgent rather than tidy: v006&rsquo;s mapping would re-install the R22 JSON blob "
   "on the 979 repaired rows as its last act."),
 ]),
 ("me", "Stage 2 &middot; The run", "one shot, then that flow is deleted", [
  ("RUN", "Run the flow once",
   "Full table, from the <b>Run</b> button on the detail page, not the canvas. Click "
   "<b>once</b> &mdash; a second concurrent run conflicts."),
  ("VERIFY", "Verify by reading data, never by status",
   "&#128308; <b>A healthy run still reports <code>Failed</code>.</b> Check stored times are "
   "<code>04:00</code>/<code>05:00Z</code>, and read the write action&rsquo;s raw inputs."),
  ("DIFF", "Re-diff both directions &rarr; 0",
   "Three units get <b>created</b>: <code>20877R1-1/1</code>, <code>P20002-1/1</code>, "
   "<code>P21911_A-1/1</code> &mdash; all three have Orders. Anything else appearing here is a "
   "new problem with no known explanation."),
  ("DELFLOW", "Delete the transfer flow",
   "Keep the <code>.zip</code> &mdash; it is the only artifact that re-imports. A "
   "definition-only JSON cannot restore a flow."),
  ("N8B", "Re-run <code>n8_split_status.js</code>",
   "&#128308; <b>Before any viewer refresh.</b> The run rewrites the composite "
   "<code>Status</code> from Excel and leaves the split pair stale &mdash; and the viewer now "
   "derives <code>Status</code> <em>from</em> that pair. Refresh in between and it shows "
   "yesterday&rsquo;s stamp, silently, because every value is well-formed."),
 ]),
 ("me", "Stage 2b &middot; Schema", "only now that the transfer flow is gone", [
  ("DELDUP", "Delete <code>Order - Order Number</code> and <code>Order - Qty</code>",
   "Duplicates of the <code>OrderNumber</code> lookup and the native <code>Qty</code>. Not "
   "before now &mdash; the transfer flow writes both until its final run."),
  ("N4", "Run <code>n4_convert_choice_columns.js</code>",
   "Dry run first; expect <b>12</b> columns. It mirrors each parent&rsquo;s option list "
   "<em>and</em> its <code>FillInChoice</code>, so no value cleanup is needed first."),
  ("REEXP", "Re-export Order Items",
   "&#128308; <b>Not optional.</b> The generator reads column types from this export to decide "
   "<code>item/X/Value</code> against <code>item/X</code>. A stale export silently produces the "
   "wrong shape, and a plain key into a Choice column stops landing without reporting anything."),
  ("REGEN", "<code>gen_n3_flows.py</code>, then <code>verify_n3_flows.py</code>",
   "Assertion 8 fails loudly if the export is stale. Expect <b>17 / 5 / 24 / 1</b>."),
  ("REPASTE", "Re-stage and re-paste three flows",
   "<b>Order</b> (7 choice targets), <b>Models</b> (1), <b>Model Revisions</b> (4). "
   "<b>Clients is unaffected</b> &mdash; its one field is a Number."),
 ]),
 ("me", "Stage 3 &middot; The viewer", "the irreversible part", [
  ("VREF", "Refresh the viewer, check the conversions",
   "<code>Tank</code>=<code>R</code>, <code>Location</code>=<code>XT</code>, "
   "<code>Frame</code>=<code>Plaspak</code> without erroring."),
  ("VCONS", "Verify <code>TableOrders</code> against all four consumers",
   "FRM09, FRM11, FRM13, BO Manager. <b>FRM11 hardest</b> &mdash; it reads ten columns by "
   "literal string and its purge rule tests <code>Location</code> in two-letter codes."),
  ("SNAP", "Snapshot the file you are about to overwrite",
   "Into <code>live-workbook-data/</code>. That snapshot is the rollback for the deploy; the "
   "Index row rolls back separately."),
  ("DEPLOY", "Deploy the viewer to <code>Revue/FRM10-12.xlsx</code>",
   "This overwrites the stale twin, which is why the snapshot comes first."),
  ("INDEX", "Edit the <code>Index</code> row by hand",
   "Item <b>Id 8</b>, field <code>Path</code> &mdash; a Hyperlink, so the form shows two boxes. "
   "Address &rarr; <code>&hellip;/FAB/Revue/FRM10-12.xlsx</code>, i.e. just drop "
   "<code>Formulaires/</code>. <b>Keep the <code>%20</code></b>; every other row is "
   "percent-encoded. Leave Display text alone."),
  ("PERM", "Break permission inheritance on the deployed file",
   "Staff <b>Read</b>, refresh operators <b>Edit</b>. A Power Query refresh has to save, so "
   "read-only-for-everyone breaks the very thing keeping FRM09 alive."),
  ("FRM09", "Refresh FRM09 and confirm it returns rows",
   "&#128308; The proof the repoint worked. A wrong path <b>does not error</b> &mdash; it keeps "
   "succeeding against a workbook that has stopped changing."),
 ]),
 ("me", "Stage 4 &middot; The flows", "gate: nothing here until every bulk write is finished", [
  ("STAMP", "REST-check <code>StepStatusStamped</code> = <code>StepStatus</code> on every row",
   "&#128308; If it has drifted, enabling the trigger flow re-stamps <b>246 real historical "
   "dates to today</b> &mdash; silently, because every value it writes is well-formed. Over "
   "REST, not from an export: the column is hidden, and hidden columns do not export."),
  ("TRIG", "Paste trigger <code>v002</code> and enable",
   "Watch 15 minutes. <b>If any run passes ten minutes, turn it straight back off.</b>"),
  ("ENABLE", "Enable the four sync flows, one at a time",
   "They share a throughput bucket. Order &middot; Models &middot; Model Revisions &middot; "
   "Clients &mdash; all four tested on single-unit parents today."),
  ("TEXTF", "Retire the two TextField syncs",
   "<code>Model Revisions</code> and <code>Order</code>, off since 2026-08-21 and made redundant "
   "by N3. One staff view still displays <code>Order_Number_TextField</code> &mdash; check that "
   "view before retiring rather than after."),
 ]),
 ("me", "Stage 5 &middot; Staff, and after", "after the switch", [
  ("X5", "Run <code>x5_backfill_order_folder.js</code>",
   "Fills the order-folder link on units whose order has one. Writes the <b>absolute</b> URL to "
   "match what the connector reads, so N3 does not rewrite them all once."),
  ("X7", "Run <code>x7_verify_parent_sync.js</code> on a few units",
   "Read-back of all 46 mapped fields against the three parents; expect <code>MISMATCH 0</code>. "
   "A <code>200</code> proves a request was accepted, not that the right value landed."),
 ]),
]


def main():
    parts, n = [], 0
    for cls, head, sub, items in LANES:
        body = []
        for tid, title, detail in items:
            n += 1
            body.append(
                '        <div class="it" data-id="%s">\n'
                '          <button class="box" aria-label="Mark done">&#10003;</button>\n'
                '          <div><div class="t"><span class="id">%d</span>%s</div>\n'
                '            <div class="w">%s</div></div>\n'
                '        </div>' % (tid, n, title, detail))
        parts.append(
            '    <div class="lane %s">\n'
            '      <div class="lanehead"><span class="tag">%s</span>\n'
            '        <span class="sub">%s</span></div>\n'
            '      <div class="items">\n%s\n      </div>\n'
            '    </div>' % (cls, head, sub, "\n\n".join(body)))

    block = (
        '      <h2>What is left to do</h2>\n'
        '      <span class="cnt">%d steps &middot; ticks save to this page</span>\n'
        '    </div>\n'
        '    <p class="intro">In order. The ordering is load-bearing in five places and those are\n'
        '      marked &#128308;. Everything below the next heading is finished: the four sync flows\n'
        '      are built and tested on single-unit parents, client lead times are seeded and\n'
        '      verified against FRM13, <code>Order.Lead Time</code> is synced on all 412 orders,\n'
        '      and the email and handbook are written.</p>\n\n%s\n\n' % (n, "\n\n".join(parts)))

    s = io.open(BOARD, encoding="utf-8").read()
    # Idempotent: on the first run the section is still called "Do this next";
    # after that it is the heading this script itself writes. Anchor on either, or
    # re-running silently fails with a substring error.
    for head in ('      <h2>What is left to do</h2>', '      <h2>Do this next</h2>'):
        if head in s:
            i = s.index(head)
            break
    else:
        raise SystemExit("cannot find the task-list heading in %s" % BOARD)
    j = s.index("      <h2>What is decided</h2>")
    s = s[:i] + block + s[j:]
    s = s.replace('<script id="app-state" type="application/json">{"tick":{"HIDE":1},"v":1}</script>',
                  '<script id="app-state" type="application/json">{"tick":{},"v":2}</script>', 1)
    io.open(BOARD, "w", encoding="utf-8", newline="\n").write(s)
    print("board updated: %d tasks across %d lanes" % (n, len(LANES)))


if __name__ == "__main__":
    main()
