// Run the simulator's core (no DOM) under node: node viewer/check_core.js [order] [seed] [repeat]
// Prints per-fault verdict counts and measurement errors so the JS port can be checked without a browser.
const fs = require("fs");
const path = require("path");

const html = fs.readFileSync(path.join(__dirname, "perception_sim.html"), "utf8");
const src = html.match(/<script id="core">([\s\S]*?)<\/script>/)[1];
const mod = { exports: {} };
new Function("module", src)(mod);
const CORE = mod.exports;

const [order = "demo_original10", seed = "20261009", repeat = "3"] = process.argv.slice(2);
const faultP = Object.fromEntries(CORE.FAULTS.map(f => [f.key, f.p]));
const stream = CORE.makeStream(order, +seed, faultP, +repeat);
const { catalog, ranges, counts } = CORE.catalogOf(CORE.ORDERS[order]);
const ctx = { cam: CORE.cameraModel(), catalog, ranges, remaining: Object.fromEntries(Object.entries(counts).map(([k, v]) => [k, v * repeat])), stamp: 0 };

const table = {}, errs = [];
const t0 = Date.now();
for (const fb of stream) {
  const r = CORE.processBox(fb, ctx);
  const kind = r.verdict.kind + (r.verdict.route === "PLAN" && r.verdict.uncertain ? " δ" : "");
  (table[fb.fault] ??= {})[kind] = (table[fb.fault][kind] || 0) + 1;
  if (r.meas && ["none", "label_fail", "weight_loss", "glare"].includes(fb.fault)) {
    const s = r.meas.size, t = fb.size;
    errs.push([Math.abs(s.x - Math.max(t.x, t.y)), Math.abs(s.y - Math.min(t.x, t.y)), Math.abs(s.z - t.z), fb.box_id, fb.sku]);
  }
}
console.log(`${order} x${repeat} seed ${seed}: ${stream.length} boxes, ${((Date.now() - t0) / stream.length).toFixed(0)} ms/box`);
for (const [f, kinds] of Object.entries(table)) console.log(f.padEnd(12), JSON.stringify(kinds));
const max = i => Math.max(...errs.map(e => e[i])) * 1000;
console.log(`size error on undamaged boxes (mm): long ${max(0).toFixed(1)}, short ${max(1).toFixed(1)}, height ${max(2).toFixed(1)}`);
