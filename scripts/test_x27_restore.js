// Mock-SharePoint test for x27_restore.js.   node scripts/test_x27_restore.js [path-to-x27]
const fs = require("fs");
const path = require("path");
const SRC = fs.readFileSync(process.argv[2] || path.join(__dirname, "x27_restore.js"), "utf8");
let failures = 0;
const assert = (c, m) => { if (!c) { failures++; console.log("ASSERT FAILED: " + m); } else console.log("ok: " + m); };

function world() {
  return {
    guids: { "Order Items": "oi-guid", "Order": "ord-guid" },
    rows: {
      "oi-guid": {
        1: { Id: 1, Title: "U-1", MdlLatestModelRevision: "MR-NEW", OrdLDs: false },     // holds expect -> restore
        2: { Id: 2, Title: "U-2", MdlLatestModelRevision: "MR-OLD" },                    // already restored
        3: { Id: 3, Title: "U-3", MdlLatestModelRevision: "SOMEONE-ELSE" },              // changed since -> conflict
        5: { Id: 5, Title: "U-5", Location: "Zone B" },                                  // restore to null (clear)
        6: { Id: 6, Title: "DOWN", MdlLatestModelRevision: "MR-NEW" },                   // read-back throttled forever
      },
      "ord-guid": { 10: { Id: 10, Title: "O-10", Price: 250 } },                          // parent: number restore
    },
    patches: [],
  };
}

function makeFetch(W) {
  const res = (status, body) => ({ ok: status < 400, status, statusText: String(status), headers: { get: () => null },
    json: async () => body, text: async () => JSON.stringify(body) });
  return async (url, opt) => {
    opt = opt || {}; const hdr = opt.headers || {};
    if (url.endsWith("/_api/contextinfo")) return res(200, { FormDigestValue: "d" });
    let m = url.match(/getbytitle\('([^']+)'\)\?\$select=Id$/);
    if (m) return W.guids[m[1]] ? res(200, { Id: W.guids[m[1]] }) : res(404, {});
    m = url.match(/lists\(guid'([^']+)'\)\/items\((\d+)\)(\?\$select=(.*))?$/);
    if (m) {
      const tbl = W.rows[m[1]], row = tbl && tbl[m[2]];
      if (!row) return res(404, { error: "gone" });
      if (hdr["X-HTTP-Method"] === "MERGE") {
        const body = JSON.parse(opt.body); W.patches.push({ list: m[1], id: +m[2], body }); Object.assign(row, body);
        if (row.Title === "DOWN") row._down = true;
        return res(204, {});
      }
      if (row._down) return res(503, {});
      const out = {}; for (const f of (m[4] || "").split(",")) if (f) out[f] = f in row ? row[f] : null;
      return res(200, out);
    }
    return res(404, { error: "unmocked " + url });
  };
}

async function run(name, plan, { dry = true, windowPlan } = {}) {
  const W = world(); globalThis.fetch = makeFetch(W); globalThis.window = {};
  let src = SRC.replace("const BACKOFF_MS = 2000", "const BACKOFF_MS = 1");
  if (windowPlan !== undefined) {
    if (windowPlan !== "UNSET") globalThis.window.x27plan = windowPlan;
    src = src.replace("const PLAN = null;", "const PLAN = window.x27plan;");
  } else src = src.replace("const PLAN = null;", "const PLAN = " + JSON.stringify(plan) + ";");
  if (!dry) src = src.replace("const DRY = true;", "const DRY = false;");
  const logs = [], orig = { log: console.log, error: console.error, table: console.table };
  console.log = (...a) => logs.push(a.join(" ")); console.error = (...a) => logs.push("ERR " + a.join(" "));
  console.table = (t) => logs.push("TABLE " + JSON.stringify(t));
  try { await eval(src); } finally { Object.assign(console, orig); }
  console.log("\n##### " + name + " [" + logs.length + " lines]\n" + logs.join("\n"));
  W.logs = logs; W.x27 = globalThis.window.x27; return W;
}

(async () => {
  const PLAN = { counts: { unsupported: 1 }, warnings: ["Restoring Order rows FIRES the N3 sync flows"], entries: [
    { list: "Order Items", id: 1, title: "U-1", field: "MdlLatestModelRevision", expect: "MR-NEW", restore: "MR-OLD" },
    { list: "Order Items", id: 1, title: "U-1", field: "OrdLDs", expect: false, restore: true },
    { list: "Order Items", id: 2, title: "U-2", field: "MdlLatestModelRevision", expect: "MR-NEW", restore: "MR-OLD" },
    { list: "Order Items", id: 3, title: "U-3", field: "MdlLatestModelRevision", expect: "MR-NEW", restore: "MR-OLD" },
    { list: "Order Items", id: 4, title: "U-4", field: "MdlLatestModelRevision", expect: "MR-NEW", restore: "MR-OLD" },
    { list: "Order Items", id: 5, title: "U-5", field: "Location", expect: "Zone B", restore: null },
    { list: "Order Items", id: 6, title: "DOWN", field: "MdlLatestModelRevision", expect: "MR-NEW", restore: "MR-OLD" },
    { list: "Order", id: 10, title: "O-10", field: "Price", expect: 250, restore: 200 },
    { list: "Order Items", id: 1, title: "U-1", field: "RevModelDescription", expect: "[\"A\"]", restore: "[\"B\"]", unsupported: "nested" },
  ] };

  let W = await run("A dry", PLAN);
  assert(W.patches.length === 0, "dry writes nothing");
  assert(/^MODE: RESTORE \(DRY\), 8 fields on 7 rows/.test(W.logs[0]) && /1 unsupported entries NOT restored/.test(W.logs[0]), "MODE line first, counts unsupported");
  assert(W.logs.some(l => /FIRES the N3 sync flows/.test(l)), "plan warnings printed");
  assert(W.x27.conflicts.length === 1 && W.x27.conflicts[0].id === 3, "row changed since -> CONFLICT, only row 3");
  assert(W.x27.already.length === 1 && W.x27.already[0].id === 2, "row already holding restore -> already restored");
  assert(W.x27.gone.length === 1 && W.x27.gone[0].id === 4, "missing row -> gone");

  W = await run("B apply", PLAN, { dry: false });
  const by = (l, id) => W.patches.find(p => p.list === l && p.id === id);
  assert(by("oi-guid", 1) && by("oi-guid", 1).body.MdlLatestModelRevision === "MR-OLD" && by("oi-guid", 1).body.OrdLDs === true,
         "row 1: both fields restored in ONE merge, boolean typed");
  assert(!by("oi-guid", 3), "the conflict row is NEVER written");
  assert(!by("oi-guid", 2), "the already-restored row is not rewritten");
  assert(by("oi-guid", 5) && by("oi-guid", 5).body.Location === null, "restore to null clears the field");
  assert(by("ord-guid", 10) && by("ord-guid", 10).body.Price === 200, "parent list row restored (number)");
  assert(!W.patches.some(p => "RevModelDescription" in p.body), "unsupported entry never written");
  assert(W.x27.unverified.length === 1 && W.x27.unverified[0].id === 6 && W.logs.some(l => /verification INCOMPLETE/.test(l)),
         "throttled read-back -> unverified, reported, no throw");
  assert(W.logs.some(l => /every restored field verified \(of those re-read\)/.test(l)), "summary after incomplete verification");

  W = await run("C no plan", null, { dry: false });
  assert(W.patches.length === 0 && W.logs.some(l => /no plan/.test(l)), "no plan -> abort");
  W = await run("D window var unset", null, { dry: false, windowPlan: "UNSET" });
  assert(W.patches.length === 0 && W.logs.some(l => /undefined/.test(l)), "unset window plan -> abort");
  W = await run("E only unsupported", { entries: [PLAN.entries[8]] }, { dry: false });
  assert(W.patches.length === 0 && W.logs.some(l => /0 restorable entries/.test(l)), "zero restorable -> abort");

  console.log("\n" + (failures ? failures + " FAILED" : "ALL PASS"));
  process.exitCode = failures ? 1 : 0;
})();
