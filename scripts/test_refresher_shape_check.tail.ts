
// ---- test harness appended to a copy of the script (never shipped) ----
function mockTable(headers: string[], rows: any[][]) {
    return {
        getHeaderRowRange: () => ({ getValues: () => [headers] }),
        getRangeBetweenHeaderAndTotal: () => ({
            getRowCount: () => rows.length,
            getColumn: (i: number) => ({ getValues: () => rows.map(r => [r[i]]) }),
        }),
    };
}
function mockWorkbook(tables: Record<string, any>) {
    return { getTable: (n: string) => tables[n] } as any;
}
function rowFor(headers: string[], dateText: boolean) {
    return headers.map(h => isDateColumnName(h) ? (dateText ? "2/20/2024 12:00:00 AM" : 45342) : "x");
}
const logs: string[] = [];
const realLog = console.log;
console.log = (m: string) => { logs.push(m); };
function run(label: string, tables: Record<string, any>, expectFail: boolean) {
    logs.length = 0;
    checkLegacyShapes(mockWorkbook(tables));
    const failed = logs.some(l => l.indexOf("SHAPE CHECK FAILED") !== -1);
    realLog(`${failed === expectFail ? "ok  " : "FAIL"} ${label}${failed ? " -> " + logs.join(" ").slice(0, 140) : ""}`);
    return failed === expectFail;
}
const base = (frm1012: string[], dateText = false) => ({
    TableArchiveFRM10_12: mockTable(frm1012, [rowFor(frm1012, dateText)]),
    TableArchiveFRM11: mockTable(PINNED_FRM11, [rowFor(PINNED_FRM11, false)]),
    TableArchiveFRM13: mockTable(PINNED_FRM13, [rowFor(PINNED_FRM13, false)]),
});
const withBo = PINNED_FRM10_12.concat(PINNED_FRM10_12_BO);
const renamed = PINNED_FRM10_12.slice(); renamed[5] = "Phase";
const swapped = PINNED_FRM10_12.slice(); [swapped[1], swapped[2]] = [swapped[2], swapped[1]];
const results = [
    run("today's 93-column shape passes", base(PINNED_FRM10_12), false),
    run("93 + 18 BO columns passes", base(withBo), false),
    run("renamed column is reported", base(renamed), true),
    run("reordered column is reported", base(swapped), true),
    run("extra unexpected column is reported", base(withBo.concat(["Surprise"])), true),
    run("text date is reported", base(PINNED_FRM10_12, true), true),
    run("missing FRM11 table is reported", { ...base(PINNED_FRM10_12), TableArchiveFRM11: undefined }, true),
];
realLog(results.every(x => x) ? "ALL PASS" : "SOME FAILED");
