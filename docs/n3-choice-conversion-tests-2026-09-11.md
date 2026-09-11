# Testing the three N3 flows after the Choice conversion — 2026-09-11

The 2026-09-10 tests passed as **no-ops**: the change-guard found nothing different and
skipped the write, so the write path was never executed. That is exactly how the
`select()` defect survived its test and then took down the cutover run. These tests
**write**, and they write to the columns n4 converted.

What changed since those tests: 13 `Order Items` columns went Text → Choice, and the
three flows now address them as `item/X/Value` instead of `item/X`. A plain key into a
Choice column is **accepted and lands nothing** — no error, no row, no signal — so
"the run succeeded" proves nothing here. Every test below is verified by reading the
child row back.

Run the three in order, one flow at a time (they share a throughput bucket). Turn each
flow **on** for its test and **off** again afterwards: enabling for real is step 31,
after the step 29 mirror check.

---

## Test 1 · Order → `Order - Order Type` (7 converted targets)

**Parent:** the Order behind unit **`21611-1/1`**. Today: `Order Type = Standard`,
`Client Date Status = Confirmed`.

1. On the Order, change **Order Type** `Standard` → `Repair`.
2. Wait for the flow (polling trigger, 1 minute).
3. Read the child back (snippet below). Expect `OrdOrderType = "Repair"`.
4. Change it back to `Standard` and confirm the child follows.

Both values are in the option list and this column is **fill-in FALSE**, so it is the
strict case: a value outside the list would be rejected per row.

## Test 2 · Models → `Model - Modification_Status` (1 converted target)

**Parent:** the Model behind unit **`21040W2-1/1`**. Today: `Modification_Status =
Up to Date`.

1. Change **Modification_Status** `Up to Date` → `Minor Changes`.
2. Expect the child's `MdlModificationStatus = "Minor Changes"`. Revert.

## Test 3 · Model Revisions → `Mod. Rev. - Model Description` 🔴 **the one that matters**

**Parent:** revision **`MR-OTHY-0010-V1`**, the only revision on unit **`21657-1/1`**.
Today its `Model Description` is **`VAULT-1PH`**, which is **not in the option list** —
it exists only because the column allows fill-in values.

That is the live risk. **583 rows hold an off-list Model Description and 735 hold an
off-list Model Type.** If the connector cannot write an off-list value into a fill-in
Choice through `item/X/Value`, then every one of those rows breaks the moment its parent
is touched — and it breaks per row, inside the flow, silently.

1. Change the revision's **Model Description** from `VAULT-1PH` to `NETWORK`
   (also off-list, so this tests fill-in in both directions).
2. Expect the child's `RevModelDescription = "NETWORK"`.
3. Change it back to `VAULT-1PH` and confirm.

⚠️ If step 2 comes back **blank** rather than wrong, that is the silent-Choice failure and
the flows must not be enabled. If it comes back as the old value, the write was rejected.
Either way, stop and say so.

This is also the A/B for the fix made earlier tonight: the same column was tested
NETWORK → PADMOUNT on `M-AUEN-0002` at 03:52 **while it was still a Note**, and landed a
clean string. Now it is a Choice, which is a different write path entirely.

---

## Reading the child back

```js
(async () => {
  const site = "https://ermcopower.sharepoint.com/sites/PioneerPlanificatio";
  const oi   = "d6468ec5-c7b5-44a3-8ce0-f81f059b671d";
  const units = ["21611-1/1", "21040W2-1/1", "21657-1/1"];
  const sel = "Id,Title,OrdOrderType,OrdClientDateStatus,MdlModificationStatus," +
              "RevModelDescription,RevModelType,Modified";
  for (const u of units) {
    const j = await fetch(`${site}/_api/web/lists(guid'${oi}')/items`
      + `?$select=${sel}&$filter=Title eq '${u.replace(/'/g, "''")}'`,
      { headers: { accept: "application/json;odata=nometadata" } }).then(r => r.json());
    (j.value || []).forEach(x => console.log(u.padEnd(14), JSON.stringify(x)));
  }
})();
```

## What each outcome means

| child reads | meaning |
|---|---|
| the new value | ✅ the `/Value` write works for that column |
| **blank** | 🔴 the classic silent Choice failure — the key did not match, nothing landed |
| the **old** value | the write was rejected, or the change-guard wrongly saw no change |
| unchanged and `Modified` unchanged | the flow never fired — check it is on, and wait a full minute |
