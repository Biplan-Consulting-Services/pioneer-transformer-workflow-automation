# N3 — deploying the three parent-sync flows, and testing them

Written 2026-09-10, the night before cutover. `n3-parent-sync-flow-spec.md` says what the
flows *are*; the runbook's 4.2 says *when* they go on. Neither said how a generated
definition JSON becomes a flow in the tenant, or how you would know it worked. This does.

**These are new flows.** The `_inbox`/`_outbox` version loop in the repo README assumes a
flow that already exists in the tenant to export *from*. It does not apply until after the
first deploy — see Part 3.

---

## Part 0 · Preconditions

| # | check | why |
|---|---|---|
| 0.1 | **`Order Items` create-or-update trigger flow is OFF** | every unit N3 writes fires it once. Leave it off for the whole test, or the run history fills with noise you then have to read past. |
| 0.2 | **The transfer flow is OFF** | it writes the same 48 parent columns from the same sources. Not harmful — same values — but a concurrent write makes a failed test ambiguous. |
| 0.3 | `python scripts/verify_n3_flows.py` prints `RESULT: OK` | 19/5/24 fields, guards match, pagination 5000, every Choice/Lookup reads `?['Value']`. |

🔴 **Do not turn the N3 flows on and leave them on tonight.** Until the transfer flow is
deleted at cutover, both own the same columns. Test, then turn them back off. Enabling for
real is runbook step 4.2.

---

## Part 1 · Deploy

Power Automate has no "import a definition" for a *new* flow. The route is the one already
in use here: build a shell, then overwrite its definition with the generated JSON using the
browser extension that exposes the raw JSON in the designer.

**Per flow — three of them, one at a time:**

1. **Create → Automated cloud flow.** Name it exactly:

   | file in `workflow-data/n3-flows/` | flow name | trigger list |
   |---|---|---|
   | `Order_Items__sync_from_Order.definition.json` | `Order Items - sync from Order` | `Order` |
   | `Order_Items__sync_from_Models.definition.json` | `Order Items - sync from Models` | `Models` |
   | `Order_Items__sync_from_Model_Revisions.definition.json` | `Order Items - sync from Model Revisions` | `Model Revisions` |

   Trigger: **SharePoint — When an item is created or modified**.

2. **Configure the trigger in the shell before pasting anything.** Site Address =
   `https://ermcopower.sharepoint.com/sites/PioneerPlanificatio`, List Name = the parent
   list from the table above.

   🔑 **This step is the one that is easy to skip, and it is not cosmetic.** The pasted JSON
   refers to its connection by name only — `"connectionName": "shared_sharepointonline"` —
   and that name resolves to an actual connection through a binding the *shell* carries,
   not through anything in the definition. Paste into a shell that never had a configured
   SharePoint action and the actions come back unbound.

3. **Save the shell.** A flow with only a trigger saves fine.

4. **Open the JSON editor extension, replace the definition with the file's contents, save.**
   The generated files are the bare `definition` object — `$schema` / `contentVersion` /
   `parameters` / `triggers` / `actions` — which is the same shape the extension hands back,
   so it is a straight swap, not a merge.

5. **Reopen the designer and look at every action.** Expected: list names render as names
   (`Order Items`), not raw GUIDs, and no action shows a connection warning. If one does,
   click it, pick the SharePoint connection, save — then re-check that action's parameters.
   A rebind sometimes blanks them, which is the failure this step exists to catch.

6. **Leave the flow OFF.** Testing turns one on at a time.

---

## Part 2 · The test

### The rig — one unit exercises all three flows

Found by profiling the 2026-09-09 exports. **Order Items ID 994** is the *only* unit of all
three of its parents:

```
Order Items ID 994
   parent Order            E21003R1        (Order list ID 520)   -- 1 unit,  HAS a folder
   parent Model            M-ATCO-0002     (Model_Code 1147003)  -- 1 unit
   parent Model Revision   MR-ATCO-0002-V1                       -- 1 unit
```

So every fan-out is exactly 1 row, and the blast radius of a mistake is one row on an
`Order Creation`-step order that has not entered production. Order `E21003R1` having a
folder is what makes it the right order — it is the only test that exercises the new URL
column.

### Test A · `Order Items - sync from Models` — the no-op test (do this one first)

Smallest flow, 5 fields, and **all 5 already match** between `M-ATCO-0002` and unit 994. So
the correct result is that the flow runs and *writes nothing*.

1. Turn the flow ON.
2. Edit the `Models` row `M-ATCO-0002` — change **`Notes`**. Verified against `MODELS_MAP`:
   the Models flow syncs only `Estimated Effort`, `Latest Model Revision`, `Model_ID`,
   `Modification_Status` and `Parent Model`, so `Notes` is safely outside it. Save.
3. Open the run.

| expect | meaning |
|---|---|
| `Get units of this parent` returns **1** item | the fan-out filter on `ModelId` works |
| `needsUpdate` = **false** | ✅ **the real result.** All 5 read expressions produce exactly what is stored — including the 2 lookups read `?['Value']`. |
| `Update unit` **skipped** | the guard suppresses the write |
| unit 994 unchanged | |

🔴 **If `needsUpdate` is true, a read expression is wrong.** Open the `needsUpdate` Compose
in the run and read its resolved inputs — the field whose two sides disagree is the broken
one. This is the R22 failure mode caught before it writes 979 rows instead of after.

Then turn the flow OFF.

### Test B · `Order Items - sync from Model Revisions` — same test, 24 fields

`MR-ATCO-0002-V1` also matches unit 994 on all 24. Same method — but **the field to edit
is different here**, and it is worth being careful about:

⚠️ On `Model Revisions`, unlike `Models`, **`Notes` and `Spec_ID` are both among the 24.**
Editing either would make this a write test instead of a no-op test. Of the columns on that
list, only four are not synced: `Client` (a lookup — changing it means something) and three
dead `*_TextField` mirrors.

**Edit `Pioneer_Model_Code_TextField`** on `MR-ATCO-0002-V1`. It is a mirror whose sync flow
has been off since 2026-08-21, N3 makes it redundant, and runbook 4.3 retires it — so a
stray value there costs nothing. Save, then read the run.

Expect: 1 item, `needsUpdate` **false**, no write.

⚠️ **Only this revision is a clean no-op.** On most other revisions `Model Description`
differs, because that is the R22 multichoice correction sitting unpasted in transfer `v007`.
If you test a second parent and Description writes, that is the known gap, not a new bug.

Then turn the flow OFF.

### Test C · `Order Items - sync from Order` — the one that writes

19 fields. Two of them differ, and both differences are expected:

```
field           Order E21003R1                                   unit 994
--------------  -----------------------------------------------  -----------------
Price           '0.00 $'                                         '$0.00'      DIFFERS
Order Folder    /sites/PioneerPlanificatio/Order%20Library/...    (empty)      DIFFERS
```

The other 17 match exactly.

**Run 1 — does it write the right thing?**

1. Turn the flow ON.
2. Edit `Order` `E21003R1` (list ID 520): set **`Sales Notes`** to `N3 test 2026-09-10`. It
   is one of the 19, so this is a deliberate third difference that proves a write lands.
3. Read the run, then read unit 994.

| expect | |
|---|---|
| `Get units of this parent` returns **1** | fan-out on `OrderNumberId` works |
| `needsUpdate` = **true** | |
| `Update unit` runs **once** | one call carrying all fields — not one call per field |
| `Order - Sales Notes` = `N3 test 2026-09-10` | the write lands |
| **`Order - Order Folder` is a working link to `/sites/PioneerPlanificatio/Order%20Library/E21003R1`** | 🔑 **the thing this test exists for** |
| the other 16 unchanged | |

🔴 **`Order Folder` is the one unproven expression in all three flows.** The *write* shape
is sourced — the connector renders a URL column as one input box, so it takes a bare string.
The *read* — `?['Url']` — is reasoned from REST's `SP.FieldUrlValue`, and there is no
captured connector payload anywhere in this repo showing a Hyperlink column. So:

| what unit 994 shows | diagnosis | fix |
|---|---|---|
| a working link | ✅ `?['Url']` correct | none |
| **empty** | the connector returns the URL as a bare string, so `?['Url']` on a string is null | drop it — in `scripts/gen_n3_flows.py` make the `url` kind return the bare `b`, regenerate, re-paste |
| literal text `{"Url":"...","Description":"..."}` | read is right, but the object reached the write box | keep `?['Url']`; the paste did not take — re-check that action's parameter |

**Run 2 — does the guard hold?** This is the more important half.

4. Edit `Order` `E21003R1` again, this time changing a field that is **not** one of the 19.
   `Lead Time` is a good choice — verified absent from `ORDER_MAP`, and it is a per-order
   override nothing downstream trusts anyway (see the repo CLAUDE.md on FRM13). Save.

| expect | |
|---|---|
| `needsUpdate` = **false** | ✅ the guard suppresses. Every one of the 19 now matches. |
| `Update unit` skipped | |

🔴 **If `needsUpdate` is true on run 2, the guard is permanently defeated** and every future
edit to any order rewrites all of its units. Read the resolved `needsUpdate` inputs to find
the field. Prime suspect: **`Price`**.

Then turn the flow OFF.

### ⚠️ The Price watch item — a decision, not a bug

`Order.Price` is a currency/number column; `Order Items.OrdPrice` is **Text** (spec rule 5,
deliberate). N3 reads `Price` raw and writes it into Text, so the connector stringifies it.
Measured on the 2026-09-09 exports, the stored side reads `$471,735.89` and the parent side
`471,735.89 $` — **all 1,013 matched units differ**, on the exports' rendering at least.

This does **not** permanently defeat the guard: once N3 writes a unit, the stored value *is*
what N3 reads, so the second pass matches and the guard starts holding. Run 2 above is what
confirms that.

What it does mean is a **one-time reformat of `OrdPrice` across ~1,013 units** the first
time each parent is touched after cutover — `$471,735.89` becoming something like
`471735.89`. Nothing computes from `OrdPrice` (the viewer reads `Orders` directly, and
Price CAD / Price USD are native formula columns), so this is cosmetic. But staff will see
it, so it should be a decision rather than a surprise. **Run 1 shows the exact new format on
unit 994 — decide then.**

### Cleanup

With all three flows **OFF**, revert the three test edits: `Sales Notes` on `E21003R1` back
to empty, `Notes` on `M-ATCO-0002` back to its original value, and
`Pioneer_Model_Code_TextField` on `MR-ATCO-0002-V1` back to what it held (or just leave that
one — it is a dead mirror being retired at 4.3). Reverting a parent with the flow off leaves unit
994 still holding the test string — that is fine and expected; the first real run after
cutover corrects it.

`Order - Order Folder` on unit 994: **leave it.** It is correct, and X5 skips rows that
already have one.

---

## Part 3 · After the test — put them under version control

The three flows now exist in the tenant, so the normal loop applies from here.

```bash
mkdir "workflow-data/Order Items - sync from Order"
mkdir "workflow-data/Order Items - sync from Models"
mkdir "workflow-data/Order Items - sync from Model Revisions"
```

For each: copy the flow's JSON out of the extension into that folder's `_inbox/`, then

```bash
python scripts/flow_version.py --flow "Order Items - sync from Order" intake \
    --note "v001 first deploy, tested on unit 994"
```

which records it as a `pulled` version — a fact about what was live. From then on the repo
README's rule holds: **snapshot before you modify.**

⚠️ `flow_version.py` will not create the folder for you; it errors with
`no such flow folder`. That is deliberate — it stops a typo in `--flow` from silently
starting a new history.

**And export the `.zip` for each** (Power Automate → Export → Package). A definition-only
JSON cannot restore a flow; only the package carries `connectionsMap`/`apisMap`. JSON for
editing, `.zip` for rollback.
