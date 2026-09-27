"""Generate docs/data-inventory.md: every SharePoint list and Excel table the automation touches,
with row counts and columns.

    python scripts/gen_data_inventory.py

Lists come from the SharePoint mirror (refresh it first: Refresh-SharePointMirror.ps1):
`live/Lists.csv` for row counts, `live/Columns.csv` for columns (it includes lookups, which a CSV
export omits). Excel tables are read straight from the table XML inside the newest copy of each
workbook, so their counts are only as fresh as that copy.
"""
import csv, glob, os, re, zipfile, datetime
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT = os.path.dirname(REPO)
LIVE = os.path.join(REPO, 'sharepoint-lists', 'mirror', 'live')
OUT = os.path.join(REPO, 'docs', 'data-inventory.md')

# SharePoint plumbing present on every list; listed once instead of per list.
SYSTEM = {'AppAuthor', 'AppEditor', 'Attachments', 'ComplianceAssetId', 'ContentType', 'DocIcon', 'Edit',
          'FolderChildCount', 'ItemChildCount', 'LinkTitle', 'LinkTitleNoMenu', '_ColorTag', '_IsRecord',
          '_UIVersionString', 'ID', 'Created', 'Modified', 'Author', 'Editor', 'SelectTitle',
          'LinkTitle2', '_ModerationStatus', '_ModerationComments', 'GUID', 'UniqueId'}
LIST_ORDER = ['Order Items', 'Order', 'Models', 'Model Revisions', 'Clients', 'Index', 'Models SA']
ROLE = {
    'Order Items': 'one row per unit; the core list',
    'Order': 'one row per order; its fields fan out to the units (Order sync flow)',
    'Models': 'transformer models; fan out to units (Models sync flow)',
    'Model Revisions': 'model revisions; fan out to units (Model Revisions sync flow)',
    'Clients': 'clients and lead times; fan out to units (Clients sync flow)',
    'Index': 'Title -> Path: how every workbook finds every other one',
    'Models SA': 'legacy SA models list, to be retired',
}

# Newest copy of each workbook that still matters. Older dated copies are skipped.
WORKBOOKS = [
    ('FRM10-12 (staff version frozen at cutover)', 'Workflow-Automation/workbooks/FRM10-12 final staff version pre-archive *.xlsx'),
    ('Archive active', 'Workflow-Automation/workbooks/Archive active.xlsx'),
    ('FRM11 - tank approval planning', 'Workflow-Automation/workbooks/PRO1.FRM11*.xlsx'),
    ('FRM13 - engineering / drawings', 'FRM10-12/linked-workbooks/PRO1.FRM13*.xlsx'),
    ('BO Manager', 'Workflow-Automation/workbooks/BO Manager*.xlsx'),
    ('BO Report', 'Workflow-Automation/workbooks/BO Report.xlsx'),
]


def is_standard(c):
    return c['internalName'] in SYSTEM or c['internalName'].startswith('_Compliance') or c['hidden'] == 'True'


def md(s):
    return str(s).replace('|', '\\|').replace('\n', ' ')


def lists_section():
    counts = {r['list']: r for r in csv.DictReader(open(os.path.join(LIVE, 'Lists.csv'), encoding='utf-8-sig'))}
    cols = defaultdict(list)
    for r in csv.DictReader(open(os.path.join(LIVE, 'Columns.csv'), encoding='utf-8-sig')):
        cols[r['list']].append(r)
    out = ['## SharePoint lists', '',
           'Every list also has the standard SharePoint columns `ID`, `Created`, `Modified`, `Created By` (`Author`), '
           '`Modified By` (`Editor`) and the usual plumbing (attachments, content type, compliance labels, version). '
           'They are left out below. **Created By / Modified By read `soleil.anker` on most rows because the flows and '
           'scripts write under that account.**', '',
           '**Use the internal name** in REST, Power Automate and Power Query. `fill` is the share of rows with a value '
           '(blank = not measured, e.g. calculated or lookup columns).', '']
    out += ['| list | rows | columns (excl. standard) | role |', '|---|---:|---:|---|']
    for name in LIST_ORDER:
        n = len([c for c in cols[name] if not is_standard(c)])
        out.append(f"| {name} | {counts.get(name, {}).get('itemCount', '?')} | {n} | {ROLE.get(name, '')} |")
    out.append('')
    for name in LIST_ORDER:
        rows = sorted((c for c in cols[name] if not is_standard(c)),
                      key=lambda c: c['displayName'].lower())
        types = Counter(c['type'].split(' ')[0] for c in rows)
        out += [f"### {name} — {counts.get(name, {}).get('itemCount', '?')} rows, {len(rows)} columns", '',
                ' · '.join(f'{t} {n}' for t, n in types.most_common()), '',
                '| display name | internal name | type | fill | notes |', '|---|---|---|---:|---|']
        for c in rows:
            note = []
            if c['lookupList']:
                note.append(f"lookup → {c['lookupList']}.{c['lookupShowField']}")
            if c['syncedFromList']:
                note.append(f"copy of {c['syncedFromList']}.{c['syncedFromField']}" + (f" ({c['syncedByFlow']})" if c['syncedByFlow'] else ''))
            if c['formula']:
                note.append('calculated')
            if c['choices']:
                ch = c['choices'].split('|') if '|' in c['choices'] else c['choices'].split(';')
                note.append(f"{len(ch)} choices")
            if c['required'] == 'True':
                note.append('required')
            if c['readOnly'] == 'True' and not c['formula']:
                note.append('read-only')
            fill = c['fillRate']
            try:
                fill = f'{float(fill):.0%}'
            except ValueError:
                pass
            out.append(f"| {md(c['displayName'])} | `{c['internalName']}` | {md(c['type'])} | {fill} | {md('; '.join(note))} |")
        out.append('')
    return out


def table_columns(z, name):
    x = z.read(name).decode('utf-8', 'ignore')
    tname = re.search(r'<table[^>]*\bname="([^"]+)"', x)
    ref = re.search(r'<table[^>]*\bref="([^"]+)"', x)
    colnames = [re.sub(r'\s+', ' ',re.sub(r'_x000[ad]_', ' ', c.replace('&amp;', '&'))).strip() for c in re.findall(r'<tableColumn[^>]*\bname="([^"]*)"', x)]
    m = re.match(r'[A-Z]+(\d+):[A-Z]+(\d+)', ref.group(1)) if ref else None
    rows = int(m.group(2)) - int(m.group(1)) if m else '?'
    return tname.group(1) if tname else name, rows, colnames


def excel_section():
    out = ['## Excel tables', '',
           'Read from the newest copy of each workbook in the repos, so the counts are dated (the date is the '
           "copy's file date). Row counts are the table's range minus the header.", '']
    for label, pat in WORKBOOKS:
        files = sorted(glob.glob(os.path.join(CLIENT, pat)), key=os.path.getmtime)
        if not files:
            out += [f'### {label}', '', f'_No copy found for `{pat}`._', '']
            continue
        f = files[-1]
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d')
        z = zipfile.ZipFile(f)
        tables = [table_columns(z, n) for n in z.namelist() if re.match(r'xl/tables/table\d+\.xml$', n)]
        tables.sort(key=lambda t: (-(t[1] if isinstance(t[1], int) else 0), t[0]))
        out += [f'### {label}', '', f"`{os.path.relpath(f, CLIENT)}` · copy dated {mt} · {len(tables)} tables", '',
                '| table | rows | cols | columns |', '|---|---:|---:|---|']
        for tname, rows, cn in tables:
            out.append(f"| `{md(tname)}` | {rows} | {len(cn)} | {md(', '.join(cn))} |")
        out.append('')
    return out


def main():
    asof = next(csv.DictReader(open(os.path.join(LIVE, 'Lists.csv'), encoding='utf-8-sig')), {})
    snap = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(LIVE, 'Columns.csv'))).strftime('%Y-%m-%d %H:%M')
    head = ['# Data inventory: lists, tables, row counts and columns', '',
            f'Generated by `scripts/gen_data_inventory.py` from the SharePoint mirror refreshed {snap} and the '
            'workbook copies in the repos. **Re-run it rather than editing.** It supersedes `column-reference.md` '
            'for SharePoint columns (that one is from the 09-11 export and has no lookup columns).', '']
    lines = head + lists_section() + excel_section()
    open(OUT, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print('wrote', os.path.relpath(OUT, REPO), len(lines), 'lines')


if __name__ == '__main__':
    main()
