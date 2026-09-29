// Duke Energy RFP - Pioneer OTD 2024-2026 slide, ERMCO dashboard look (red header/footer bands,
// white cards with red title strips on light grey, red bars + light-blue reference line).
// Reads otd.json written by build_otd.py.
//   node build_slide.js <out.pptx> [monthly]     (default: quarterly chart)
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const J = JSON.parse(fs.readFileSync(path.join(__dirname, "otd.json"), "utf8"));
const OUT = process.argv[2];
const MONTHLY = process.argv[3] === "monthly";
const LOGO = path.join(path.dirname(OUT), "ERMCO-Pioneer-Transformers.png");

const C = {
  red: "D11F35", redDark: "A8182B", blue: "8DB6D6", page: "EDEDED", card: "FFFFFF",
  ink: "262626", muted: "6B6B6B", grid: "E4E4E4", white: "FFFFFF",
};
const FONT = "Calibri";
const pct = (x) => Math.round(x * 100);
const Y = Object.fromEntries(J.yearly.map((y) => [String(y.period), y]));
const Q = J.quarterly;
const M = J.monthly;
const jsEnd = new Date(J.js_end + "T12:00:00");
const endLabel = jsEnd.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
const gain = pct(Y["2026"].otd) - pct(Y["2024"].otd);

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.title = "Pioneer Transformers - On-Time Delivery 2024-2026";
const s = pres.addSlide();
s.background = { color: C.page };

// ---- header band + logo tile
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 10, h: 0.82, fill: { color: C.red }, line: { color: C.red } });
s.addText("On-Time Delivery Performance, 2024 – 2026", {
  x: 0.3, y: 0.1, w: 7.4, h: 0.42, fontFace: FONT, fontSize: 24, bold: true, color: C.white, margin: 0, valign: "middle", isTextBox: true,
});
s.addText("Share of transformer units delivered on time vs. the initial promised date", {
  x: 0.3, y: 0.51, w: 7.4, h: 0.24, fontFace: FONT, fontSize: 11, color: C.white, margin: 0, valign: "middle", isTextBox: true,
});
s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.9, y: 0.1, w: 1.85, h: 0.62, fill: { color: C.white }, line: { color: C.white }, rectRadius: 0.05 });
s.addImage({ path: LOGO, x: 7.99, y: 0.135, w: 1.67, h: 1.67 * 672 / 1900, altText: "ERMCO Pioneer Transformers" });

// ---- footer band
s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 5.2, w: 10, h: 0.425, fill: { color: C.red }, line: { color: C.red } });
s.addText(
  `On time = delivered no later than 8 calendar days after the initial promised date  ·  counted per transformer unit; ` +
  `excludes repairs, services and sub-assemblies  ·  2026 YTD = Jan 1 – ${endLabel}${MONTHLY ? " (September partial)" : ""}  ·  ` +
  `Source: Pioneer ERP (Jobscope) shipment records and production tracking`,
  { x: 0.3, y: 5.2, w: 9.4, h: 0.425, fontFace: FONT, fontSize: 8, color: C.white, margin: 0, valign: "middle", align: "center", isTextBox: true },
);

// ---- card helper: white rounded card with a red title strip
function card(x, y, w, h, title) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w, h, fill: { color: C.card }, line: { color: "D9D9D9", width: 0.5 }, rectRadius: 0.06,
    shadow: { type: "outer", color: "000000", opacity: 0.18, blur: 4, offset: 1.5, angle: 90 },
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h: 0.3, fill: { color: C.red }, line: { color: C.red }, rectRadius: 0.06 });
  s.addShape(pres.shapes.RECTANGLE, { x, y: 0.15 + y, w, h: 0.15, fill: { color: C.red }, line: { color: C.red } }); // square off the strip's bottom corners
  s.addText(title, { x, y, w, h: 0.3, fontFace: FONT, fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle", margin: 0, isTextBox: true });
}

// ---- left column: one stat card per year
const top = 0.97, bottom = 5.06, colW = 2.0, gap = 0.15;
const statH = (bottom - top - 2 * gap) / 3;
[["2024", "2024"], ["2025", "2025"], ["2026", "2026 YTD"]].forEach(([k, label], i) => {
  const y = top + i * (statH + gap);
  card(0.25, y, colW, statH, label);
  s.addText(`${pct(Y[k].otd)}%`, {
    x: 0.25, y: y + 0.32, w: colW, h: statH - 0.62, fontFace: FONT, fontSize: 34, bold: true,
    color: k === "2026" ? C.red : C.ink, align: "center", valign: "middle", margin: 0, isTextBox: true,
  });
  s.addText(`${Y[k].on_time.toLocaleString("en-US")} of ${Y[k].units.toLocaleString("en-US")} units on time`, {
    x: 0.25, y: y + statH - 0.32, w: colW, h: 0.24, fontFace: FONT, fontSize: 10, color: C.muted, align: "center", valign: "middle", margin: 0, isTextBox: true,
  });
});

// ---- chart: red OTD bars, value above each bar. (A light-blue "year overall" line was tried: it runs
// at bar-top height and collides with the labels; the year figures are on the stat cards instead.)
function bars(periods, labels) {
  return [{ name: "OTD %", labels, values: periods.map((p) => pct(p.otd)) }];
}
const barOpts = {
  barDir: "col", barGapWidthPct: MONTHLY ? 35 : 55, chartColors: [C.red],
  showValue: true, dataLabelPosition: "outEnd", dataLabelColor: C.ink, dataLabelFontSize: MONTHLY ? 7 : 9,
  dataLabelFormatCode: MONTHLY ? "0" : '0"%"',
};
const axis = {
  valAxisMinVal: 0, valAxisMaxVal: 110, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"',
  valAxisLabelFontSize: 8, valAxisLabelColor: C.muted, valGridLine: { color: C.grid, size: 0.5 },
  catAxisLabelFontSize: MONTHLY ? 7 : 9, catAxisLabelColor: C.muted, catGridLine: { style: "none" },
  showLegend: false,
};
const cx = 0.25 + colW + gap;

const bulletRuns = (items, size) => items.flatMap((b, i) => [
  { text: b[0], options: { bold: true, color: C.red, bullet: { indent: 11 } } },
  { text: b[1], options: { color: C.ink, breakLine: i < items.length - 1 } },
]);

if (!MONTHLY) {
  const cw = 4.9;
  card(cx, top, cw, bottom - top, "On-Time Delivery % by Quarter");
  const labels = Q.map((q) => q.period.replace(/^(\d{4})-(Q\d)$/, "$2 '$1").replace(/'20/, "'"));
  s.addChart(pres.charts.BAR, bars(Q, labels), { x: cx + 0.08, y: top + 0.38, w: cw - 0.16, h: bottom - top - 0.45, ...barOpts, ...axis, catAxisLabelFontSize: 8, catAxisLabelRotate: -90 });

  const hx = cx + cw + gap, hw = 9.75 - hx;
  card(hx, top, hw, bottom - top, "Highlights");
  const q3 = Q.find((q) => q.period === "2026-Q3");
  const minSust = Math.min(...Q.filter((q) => q.period >= "2025-Q2").map((q) => pct(q.otd)));
  s.addText(bulletRuns([
    [`+${gain} points`, ` improvement in on-time delivery since 2024.`],
    [`${minSust}%+ every quarter`, ` since Q2 2025, sustained through 2026.`],
    [`${pct(q3.otd)}% in Q3 2026`, `, the strongest quarter of the period.`],
    [`Late shipments are shorter:`, ` median delay down from ${Y["2024"].median_days_late} days (2024) to ${Y["2026"].median_days_late} days (2026).`],
  ]), { x: hx + 0.15, y: top + 0.45, w: hw - 0.28, h: bottom - top - 0.6, fontFace: FONT, fontSize: 11.5, margin: 0, valign: "top", paraSpaceAfter: 9, isTextBox: true });
} else {
  const cw = 9.75 - cx, chH = 2.95;
  card(cx, top, cw, chH, "On-Time Delivery % by Month");
  const mnames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const labels = M.map((m) => {
    const mo = Number(m.period.slice(5, 7));
    return mo === 1 ? `${mnames[0]} '${m.period.slice(2, 4)}` : mnames[mo - 1];
  });
  s.addChart(pres.charts.BAR, bars(M, labels), { x: cx + 0.05, y: top + 0.36, w: cw - 0.1, h: chH - 0.4, ...barOpts, ...axis, catAxisLabelRotate: -90 });

  const hy = top + chH + gap, hh = bottom - hy;
  card(cx, hy, cw, hh, "Highlights");
  const recent = M.filter((m) => m.period >= "2025-04");
  const minRecent = Math.min(...recent.map((m) => pct(m.otd)));
  const best = M.reduce((a, b) => (b.otd > a.otd ? b : a));
  const bestLabel = new Date(best.period + "-15T12:00:00").toLocaleDateString("en-US", { month: "long", year: "numeric" });
  [
    [`+${gain} points`, ` of on-time delivery since 2024.`],
    [`${minRecent}%+ every month`, ` since April 2025.`],
    [`${pct(best.otd)}% in ${bestLabel}`, `, the best month of the period.`],
    [`Shorter delays:`, ` median lateness ${Y["2024"].median_days_late} → ${Y["2026"].median_days_late} days.`],
  ].forEach((b, i) => {
    s.addText(bulletRuns([b]), {
      x: cx + 0.15 + (i % 2) * (cw / 2), y: hy + 0.36 + Math.floor(i / 2) * 0.27, w: cw / 2 - 0.2, h: 0.27,
      fontFace: FONT, fontSize: 10.5, margin: 0, valign: "middle", isTextBox: true,
    });
  });
}

s.addNotes(
  `Units: 2024 ${Y["2024"].units}, 2025 ${Y["2025"].units}, 2026 YTD ${Y["2026"].units}. ` +
  `Without the 8-day grace: ${pct(Y["2024"].otd_strict)}% / ${pct(Y["2025"].otd_strict)}% / ${pct(Y["2026"].otd_strict)}%. ` +
  `Order level (every unit of the order on time): ${pct(Y["2024"].orders_all_on_time)}% / ${pct(Y["2025"].orders_all_on_time)}% / ${pct(Y["2026"].orders_all_on_time)}%. ` +
  `Delivery dates: FRM10-12 archive for 2024-2025, Jobscope shipments for 2026. Promised date: initial promised date per unit. ` +
  `Full data and reconciliation: "Pioneer OTD 2024-2026 - backup data.xlsx".`,
);

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f));
