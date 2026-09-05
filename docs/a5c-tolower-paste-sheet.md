# A5c — the 24 `toLower()` replacements, paste-ready

Generated 2026-09-05 from `workflow-data/Order Items Excel Transfer Flow 2026-09-05 1900
definition.json` by transforming the live expression text. **Nothing here was retyped** — the
"after" is the "before" with `equals(trim(X), 'EC')` rewritten to
`equals(toLower(trim(X)), 'ec')`, so a transcription slip cannot silently write nothing.

**Why this matters:** the guard is case-sensitive and three rows hold lowercase `ec`, which
falls through to `int('ec')` and throws. That surfaces as `Action 'Switch' failed` — the
iteration-497 failure. See `transfer-flow-forensics-2026-09-04.md` §9.1.

Do **both** actions. Skipping one leaves half the rows failing.

## `CreateOrderItem` — 12 fields

### `item/AssemblyDate`

```
@if(or(equals(trim(item()?['Assembly Date']), ''), equals(toLower(trim(item()?['Assembly Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Assembly Date'])))
```

### `item/AssemblyStatus/Value`

```
@if(equals(trim(item()?['Assembly Date']), ''), null, if(equals(toLower(trim(item()?['Assembly Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/CoilingDate`

```
@if(or(equals(trim(item()?['Coiling Date']), ''), equals(toLower(trim(item()?['Coiling Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Coiling Date'])))
```

### `item/CoilingStatus/Value`

```
@if(equals(trim(item()?['Coiling Date']), ''), null, if(equals(toLower(trim(item()?['Coiling Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/DryingDate`

```
@if(or(equals(trim(item()?['Drying Date']), ''), equals(toLower(trim(item()?['Drying Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Drying Date'])))
```

### `item/DryingStatus/Value`

```
@if(equals(trim(item()?['Drying Date']), ''), null, if(equals(toLower(trim(item()?['Drying Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/FinishingDate`

```
@if(or(equals(trim(item()?['Finishing Date']), ''), equals(toLower(trim(item()?['Finishing Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Finishing Date'])))
```

### `item/FinishingStatus/Value`

```
@if(equals(trim(item()?['Finishing Date']), ''), null, if(equals(toLower(trim(item()?['Finishing Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/StackingDate`

```
@if(or(equals(trim(item()?['Stacking Date']), ''), equals(toLower(trim(item()?['Stacking Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Stacking Date'])))
```

### `item/StackingStatus/Value`

```
@if(equals(trim(item()?['Stacking Date']), ''), null, if(equals(toLower(trim(item()?['Stacking Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/TestingDate`

```
@if(or(equals(trim(item()?['Testing Date']), ''), equals(toLower(trim(item()?['Testing Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Testing Date'])))
```

### `item/TestingStatus/Value`

```
@if(equals(trim(item()?['Testing Date']), ''), null, if(equals(toLower(trim(item()?['Testing Date'])), 'ec'), 'In Progress', 'Completed'))
```


## `UpdateOrderItem` — 12 fields

### `item/AssemblyDate`

```
@if(or(equals(trim(item()?['Assembly Date']), ''), equals(toLower(trim(item()?['Assembly Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Assembly Date'])))
```

### `item/AssemblyStatus/Value`

```
@if(equals(trim(item()?['Assembly Date']), ''), null, if(equals(toLower(trim(item()?['Assembly Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/CoilingDate`

```
@if(or(equals(trim(item()?['Coiling Date']), ''), equals(toLower(trim(item()?['Coiling Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Coiling Date'])))
```

### `item/CoilingStatus/Value`

```
@if(equals(trim(item()?['Coiling Date']), ''), null, if(equals(toLower(trim(item()?['Coiling Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/DryingDate`

```
@if(or(equals(trim(item()?['Drying Date']), ''), equals(toLower(trim(item()?['Drying Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Drying Date'])))
```

### `item/DryingStatus/Value`

```
@if(equals(trim(item()?['Drying Date']), ''), null, if(equals(toLower(trim(item()?['Drying Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/FinishingDate`

```
@if(or(equals(trim(item()?['Finishing Date']), ''), equals(toLower(trim(item()?['Finishing Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Finishing Date'])))
```

### `item/FinishingStatus/Value`

```
@if(equals(trim(item()?['Finishing Date']), ''), null, if(equals(toLower(trim(item()?['Finishing Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/StackingDate`

```
@if(or(equals(trim(item()?['Stacking Date']), ''), equals(toLower(trim(item()?['Stacking Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Stacking Date'])))
```

### `item/StackingStatus/Value`

```
@if(equals(trim(item()?['Stacking Date']), ''), null, if(equals(toLower(trim(item()?['Stacking Date'])), 'ec'), 'In Progress', 'Completed'))
```

### `item/TestingDate`

```
@if(or(equals(trim(item()?['Testing Date']), ''), equals(toLower(trim(item()?['Testing Date'])), 'ec')), null, addDays('1899-12-30', int(item()?['Testing Date'])))
```

### `item/TestingStatus/Value`

```
@if(equals(trim(item()?['Testing Date']), ''), null, if(equals(toLower(trim(item()?['Testing Date'])), 'ec'), 'In Progress', 'Completed'))
```


---

**24 expressions total.** After pasting, re-export the flow and confirm:

```
grep -c "toLower("  definition.json   # expect 28  (24 new + 4 already on Tanking/Delivery)
grep -c "'EC'"      definition.json   # expect 0
```

The 4 pre-existing `toLower()` calls are on `Tanking` and `Delivery`, which are deliberately
not mapped (A5b) — leave them alone.
