# Should the parent-synced Choice columns be Choice on Order Items?

User's position, 2026-09-08: **yes** — a parent column that is `Choice` should be `Choice`
on `Order Items`, not flattened to `Text`.

**Measured, and the position holds.** `N2`'s blanket "Choice → Text" rule was over-broad.
But it was guarding something real, and the fix is a sharper rule rather than dropping it.

## What N2's rule was actually protecting against

> A synced `Choice` **silently rejects any value outside its option list, per row, inside
> the flow** — the `Family` failure mode.

That is true and it is the right thing to fear: the failure is per-row and quiet. The
error in the rule was assuming the child column could receive values the parent never
held. It can't — **unless the child is stricter than the parent.**

## The sharper rule: mirror the parent exactly, permissiveness included

If `Order Items`' copy carries **the parent's own option list and the parent's own
`FillInChoice` setting**, then by construction it can never reject a value the parent
accepted. The hazard doesn't need to be tolerated; it can be designed out.

Two things make that safe in practice:

1. **Generate the option list from the parent's schema, never by hand.** The same
   single-source trick used for `Step Status`, where the options are built from the parse
   table. A hand-typed second copy is exactly how a Choice write starts failing per row.
2. **Copy `FillInChoice` too.** This is the part that would have been missed.

## Why copying `FillInChoice` is not optional

| | |
|---|---|
| Safe as a **strict** Choice today | **8 of 11** — all live data inside the option list |
| Carry **out-of-list** values | **3** |

All three are on `Model Revisions`, and all three have `FillInChoice="TRUE"` **on the
parent** — free text was permitted there, so that is where the dirt entered:

| source | options | distinct values | out-of-list |
|---|---|---|---|
| `Model_x0020_Type` | 9 | 24 | 21 |
| `Description` (MultiChoice) | 17 | 22 | 14 |
| `Oil_x0020_Type` | 8 | 9 | 3 |

And a good share of those are **cosmetic variants of real options** — `LUMINOL`/`Luminol`,
`MIDEL`/`Midel`, `Substation`/`SUBSTATION`, `ZIG ZAG`/`ZIG-ZAG`, `POWER LTC`/`POWER-LTC` —
plus a literal `0`. This is `R19`'s finding again, where 405 of 522 apparent conflicts were
cosmetic. **A strict Choice on these would reject real rows because of a capital letter.**

Mirroring `FillInChoice="TRUE"` accepts them exactly as the parent does. It also makes the
dirt *visible* in a dropdown-plus-other UI rather than invisible in free text, which is a
side benefit: it turns a data-quality problem into something someone can see and clean.

## The plan — 10 columns

Generated into `scripts/_choice_plan.json`, options read from each parent's own schema:

| Order Items column | mirrors | options | fill-in |
|---|---|---|---|
| `MdlModificationStatus` | Models | 5 | FALSE |
| `OrdIndexing` | Order | 2 | **TRUE** |
| `OrdNewmodeltobecreated` | Order | 2 | FALSE |
| `OrdOrderStep` | Order | 14 | FALSE |
| `OrdOrderType` | Order | 6 | FALSE |
| `OrdWETWETP` | Order | 2 | **TRUE** |
| `RevCoreType` | Model Revisions | 4 | **TRUE** |
| `RevFamily` | Model Revisions | 4 | FALSE |
| `RevModelType` | Model Revisions | 9 | **TRUE** |
| `RevOilType` | Model Revisions | 8 | **TRUE** |

**`RevModelDescription` is deliberately excluded.** Its source is `MultiChoice`, so a
matching column needs **array** writes — and it is the `R22` column just fixed to store a
joined string. Making it MultiChoice re-opens exactly the shape that put 110 characters of
JSON on 979 rows. Keep it as text holding `A; B`.

## 🔴 The coupling that must not be missed

**All 10 columns are written with a plain parameter key today** (`item/OrdOrderType`), on
both write actions. A Choice column needs `item/OrdOrderType/Value`.

Converting the columns **without** changing the flow is a silent failure: the connector's
expected shape changes and the writes stop landing, with nothing reporting an error. That
is **10 × 2 = 20 mapping edits**, and they must be in the **same change** as the
conversion.

So this is not a column job, it is one coordinated change:

1. snapshot the transfer flow (already versioned — `v006` is the confirmed-live parent)
2. author `v007`: 20 keys gain `/Value`, plus the `R22` `RevModelDescription` join fix,
   plus `R7`'s BO-mapping strip if that is wanted in the same pass
3. convert the 10 columns
4. paste `v007`
5. verify by read-back on a handful of rows — never from run status, which reports
   `Failed` even on a healthy run

⚠️ **Order matters within that.** Between step 3 and step 4 the flow is writing plain keys
into Choice columns. Do not leave a run in that window.

## 🔄 SUPERSEDED — make the PARENT strict instead of mirroring its permissiveness

User's counter-proposal, same day, and **it is the better plan**:

> Can't we just change the parent to be strict on the unsafe columns? They'll become strict
> in the near future anyway. It was only made flexible because FRM10-12 had inconsistent
> data. Put all the current values in as options, then slowly phase out the non-standard
> ones as they disappear.

Mirroring `FillInChoice="TRUE"` propagates the cause; making the parent strict removes it.
Free text is *where the dirt entered*, so closing it stops new dirt at the source, and
seeding every present value means nothing breaks on day one.

✅ **Adopted.** But it needs one change of order, because of what checking it turned up.

### Clean BEFORE seeding, not after — most "non-standard values" are not values

Seeding every present value would create ~28 options on `Model Type` and ~29 on
`Model Description`. Most of those are not values in need of an option — they are values
**in the wrong column, or duplicated across two columns**. Seeding them would make the
mix-up permanent, which is the opposite of the intent.

**The two columns' contents have been crossed over:**

| finding | rows |
|---|---|
| `Description` holds `NETWORK` while `Model Type` **already reads `NETWORK`** | **146** |
| `Model Type` holds a value that is a **`Model Description` option** (`ZIG-ZAG + SA`, `C2`, `POWER-W`, `MALT`, `LTC`, `PARTS`, `FLAT FRONT`, `POWER-S`…) | **72** |

The 146 are **pure duplication** — every one already carries `NETWORK` in `Model Type`, so
removing the `Description` selection loses nothing and needs no decision. That alone is 67%
of that column's out-of-list rows.

### The worklist — `reports/Model Revisions choice cleanup 2026-09-08.csv`

Generated by `scripts/gen_choice_cleanup_worklist.py` (reads the export, writes nothing to
the tenant). **384 rows, tiered by how much judgement each needs:**

| tier | rows | what |
|---|---|---|
| **AUTO** | **263** | mechanical and deterministic — no engineering input |
| **REVIEW** | **121** | a person decides — but only **19 distinct decisions** cover all of them |

The AUTO tier:

| action | rows | |
|---|---|---|
| `Description`: remove `NETWORK` | 146 | duplicates `Model Type` |
| `Model Type` → move the value to `Model Description` | 54 | it is a Description option; MultiChoice, so nothing is lost |
| `Model Type`: snap to the real option | 30 | case/spacing variants, **and all 25 `SUBMERSIBLE` rows** |
| `Model Type`: clear | 20 | `0` and other non-values |
| `Oil Type`: snap to the real option | 8 | `LUMINOL`→`Luminol`, `MIDEL`→`Midel` |
| `Description`: snap to the real option | 3 | `ZIG ZAG`→`ZIG-ZAG`, `SPARE PARTS`→`SPAREPARTS` |
| `Oil Type`: clear | 2 | `0` |

🔑 **`SUBMERSIBLE` resolves itself.** 25 rows say only `SUBMERSIBLE` against options
`1PH SUBMERSIBLE` / `3PH SUBMERSIBLE`, and the `Phases` column settles every one:
**17 at 3 phases, 8 at 1 phase, zero unresolvable.** Deterministic, no human needed — the
same technique N8 used to resolve the `Jui` ambiguity from each unit's own data.

The 19 decisions, largest first: `PADMOUNT` in `Model Type` (33 rows, suggest
`3PH PAD (PADMOUNT)`), `PADMOUNT` in `Description` (33 — it is a Type value, not a
Description), `VAULT-1PH`→`1PH-VAULT` (13), `POWER-LTC` (8), `SUBSTATION LTC`→**two
selections** `SUBSTATION` + `LTC` (7), `ANNEX` (5+5, no obvious target), `SUBWAY-1PH` (4),
then eleven one- and two-row items.

### The payoff: the option lists barely need to grow

After cleanup, the only values with **no** home in an existing option list are `ANNEX`
(10 rows) and three one-offs — `PROTOTYPE`, `Goujon`, `PLAQUE ANCRAGE`. So instead of
seeding ~28 and ~29 options and phasing them out for months, this needs **at most a handful
of new options**, and the phase-out list is nearly empty before it starts.

🟢 **`Oil Type` is the clean starter: 10 row fixes and it goes fully strict with ZERO new
options.** Do that one first — it rehearses the whole approach on a small surface.

### Sequencing

1. **`Oil Type` first** — 10 rows, no new options, strict.
2. Run the AUTO tier for `Model Type` / `Description` (263 rows).
3. Take the 19 decisions; apply the REVIEW tier.
4. Add the few genuinely-new options.
5. **Then** set `FillInChoice="FALSE"` on all six parent columns (`Model Type`, `Oil Type`,
   `Description`, `Core Type`, `Indexing`, `WET-WETP`). The last three are **already
   clean** — nothing to fix, so they can go strict at any time.
6. Create the 10 `Order Items` columns as Choice, options generated from the parent schema.
7. Author `v007` with the 20 `/Value` key changes, pasted in the same window as (6).

⚠️ **Making a Choice column strict does not validate existing data** — SharePoint only
constrains *new* entry, so legacy values keep displaying and simply cannot be re-selected.
That is what makes the phase-out work. It is also why the cleanup cannot be skipped: the
parent tolerates a legacy value, but **the child column still rejects it on write**, so
every value present in the data must be an option on the child regardless of the parent.

## Worth adding: an option-list drift detector

The residual risk after all this is **drift** — someone adds an option to the parent's
Choice column and not to the child's. The next row carrying the new value fails, per row,
quietly.

That is cheap to catch: compare each `Order Items` Choice column's options against its
parent's and report differences. It turns the one remaining silent failure into a check
that can run whenever the lists are exported. **Not built yet** — worth doing before these
columns go live, not after.

## Related, and deliberately unchanged

`Step Status` also became a Choice column in the same conversation, but for a different
reason and by a different argument: it is **staff-maintained**, its vocabulary is closed at
8 values from FRM10-12's authoritative `TableValidationStatusCode`, and nothing writes it
after N8's one-time pass. See `status-date-autostamp-spec.md`.
