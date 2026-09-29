// Duke Energy RFP - Pioneer OTD 2024-2026 slide. Reads otd.json written by build_otd.py.
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

const J = JSON.parse(fs.readFileSync(path.join(__dirname, "otd.json"), "utf8"));
const OUT = process.argv[2];

const C = {
  ink: "1B2A38", muted: "5B6B7A", grid: "E3E8EE", card: "F2F5F8",
  y2024: "A9BCCF", y2025: "5E8DB5", y2026: "1F4E79", white: "FFFFFF",
};
const pct = (x) => Math.round(x * 100);
const Y = Object.fromEntries(J.yearly.map((y) => [String(y.period), y]));
const Q = J.quarterly;
const jsEnd = new Date(J.js_end + "T12:00:00");
const endLabel = jsEnd.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
const gain = pct(Y["2026"].otd) - pct(Y["2024"].otd);
const q3_2026 = Q.find((q) => q.period === "2026-Q3");
const sustained = Q.filter((q) => q.period >= "2025-Q2");
const minSust = Math.min(...sustained.map((q) => pct(q.otd)));

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.title = "Pioneer Transformers - On-Time Delivery 2024-2026";
const s = pres.addSlide();
s.background = { color: C.white };

s.addText("On-Time Delivery Performance, 2024 – 2026", {
  x: 0.5, y: 0.3, w: 9, h: 0.55, fontFace: "Cambria", fontSize: 28, bold: true, color: C.ink, margin: 0, isTextBox: true,
});
s.addText(`Pioneer Transformers  ·  share of transformer units delivered on time vs. the initial promised date`, {
  x: 0.5, y: 0.85, w: 9, h: 0.3, fontFace: "Calibri", fontSize: 13, color: C.muted, margin: 0, isTextBox: true,
});

// ---- stat cards
const cards = [
  { k: "2024", label: "2024", fill: C.card, num: C.y2025, txt: C.ink, sub: C.muted },
  { k: "2025", label: "2025", fill: C.card, num: C.y2026, txt: C.ink, sub: C.muted },
  { k: "2026", label: "2026 YTD", fill: C.y2026, num: C.white, txt: C.white, sub: "D6E2EE" },
];
const cw = 2.85, cg = 0.225, cy = 1.35, ch = 1.1;
cards.forEach((c, i) => {
  const x = 0.5 + i * (cw + cg);
  const y = Y[c.k];
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: cy, w: cw, h: ch, fill: { color: c.fill }, line: { color: c.fill }, rectRadius: 0.08 });
  s.addText(`${pct(y.otd)}%`, {
    x: x + 0.2, y: cy + 0.12, w: 1.45, h: 0.85, fontFace: "Calibri", fontSize: 44, bold: true, color: c.num, margin: 0, valign: "middle", isTextBox: true,
  });
  s.addText([
    { text: c.label, options: { fontSize: 15, bold: true, color: c.txt, breakLine: true } },
    { text: `${y.on_time.toLocaleString("en-US")} of ${y.units.toLocaleString("en-US")} units on time`, options: { fontSize: 11, color: c.sub } },
  ], { x: x + 1.65, y: cy + 0.17, w: cw - 1.75, h: 0.76, fontFace: "Calibri", margin: 0, valign: "middle", isTextBox: true });
});

// ---- quarterly chart: one series per year so each year gets its own shade
const labels = Q.map((q) => q.period.replace(/^(\d{4})-(Q\d)$/, "$2 '$1").replace(/'20/, "'"));
const series = ["2024", "2025", "2026"].map((yr) => ({
  name: yr, labels, values: Q.map((q) => (q.period.startsWith(yr) ? pct(q.otd) : null)),
}));
s.addChart(pres.charts.BAR, series, {
  x: 0.35, y: 2.65, w: 5.95, h: 2.45,
  barDir: "col", barGrouping: "stacked", barGapWidthPct: 45,
  chartColors: [C.y2024, C.y2025, C.y2026],
  showValue: true, dataLabelPosition: "inEnd", dataLabelColor: C.white, dataLabelFontSize: 9, dataLabelFontBold: true,
  dataLabelFormatCode: '0"%"',
  valAxisMinVal: 0, valAxisMaxVal: 100, valAxisMajorUnit: 25, valAxisLabelFormatCode: '0"%"',
  valAxisLabelFontSize: 9, valAxisLabelColor: C.muted, valGridLine: { color: C.grid, size: 0.75 },
  catAxisLabelFontSize: 9, catAxisLabelColor: C.muted, catGridLine: { style: "none" }, catAxisLineShow: false,
  showLegend: false,
  showTitle: true, title: "On-time delivery by quarter", titleFontSize: 11, titleColor: C.ink, titleFontFace: "Calibri",
});

// ---- commentary
const bullets = [
  [`+${gain} points`, ` improvement in on-time delivery since 2024.`],
  [`${minSust}%+ every quarter`, ` since Q2 2025, sustained through 2026.`],
  [`${pct(q3_2026.otd)}% in Q3 2026`, `, the strongest quarter of the period.`],
  [`Late shipments are shorter:`, ` median delay down from ${Y["2024"].median_days_late} days (2024) to ${Y["2026"].median_days_late} days (2026).`],
];
s.addText(bullets.map((b, i) => ({
  text: "", options: {},
  _parts: b,
})).flatMap((b, i) => [
  { text: b._parts[0], options: { bold: true, color: C.y2026, bullet: { indent: 12 } } },
  { text: b._parts[1], options: { color: C.ink, breakLine: i < bullets.length - 1 } },
]), {
  x: 6.55, y: 2.75, w: 2.95, h: 2.3, fontFace: "Calibri", fontSize: 12, margin: 0, valign: "top", paraSpaceAfter: 8, isTextBox: true,
});

s.addText(
  `On time = delivered no later than 8 calendar days after the initial promised date. Counted per transformer unit; ` +
  `excludes repairs, services and sub-assemblies. 2026 YTD = Jan 1 – ${endLabel}. ` +
  `Source: Pioneer ERP (Jobscope) shipment records and production tracking.`,
  { x: 0.5, y: 5.13, w: 9, h: 0.36, fontFace: "Calibri", fontSize: 8.5, color: C.muted, margin: 0, valign: "top", isTextBox: true },
);

s.addNotes(
  `Units: 2024 ${Y["2024"].units}, 2025 ${Y["2025"].units}, 2026 YTD ${Y["2026"].units}. ` +
  `Without the 8-day grace: ${pct(Y["2024"].otd_strict)}% / ${pct(Y["2025"].otd_strict)}% / ${pct(Y["2026"].otd_strict)}%. ` +
  `Order level (every unit of the order on time): ${pct(Y["2024"].orders_all_on_time)}% / ${pct(Y["2025"].orders_all_on_time)}% / ${pct(Y["2026"].orders_all_on_time)}%. ` +
  `Delivery dates: FRM10-12 archive for 2024-2025, Jobscope shipments for 2026. Promised date: initial promised date per unit. ` +
  `Full data and reconciliation: "Pioneer OTD 2024-2026 - backup data.xlsx".`,
);

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f));
