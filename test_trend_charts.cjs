const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync(`${__dirname}/modern_dashboard/dashboard.js`, 'utf8');
let created = 0, destroyed = 0;
const host = { innerHTML: '', classList: { add() {} } };
const context = {
  Chart: function(canvas, config) {
    created++;
    assert.strictEqual(config.type, 'line');
    assert(config.data.datasets[0].data.every(v => v === null || Number.isFinite(v)));
    this.destroy = () => destroyed++;
  },
  document: { getElementById: () => ({}) },
  el: id => id === 'trend-charts' ? host : {},
  fmt: value => String(value), escapeHtml: value => String(value),
  buildAnalyticsGroupsMarkup: () => ({ markup: '', label: 'Analytics' }),
};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('const trendChartInstances'), source.indexOf('function wireRaceFilterButtons')), context);
const data = { race_trends: {
  season_series: [{ season_label: 'S1', total_races: 5, unique_racers: 3 }],
  daily_current_season: [{ date: '2026-10-23', total_races: 5, unique_racers: 3, ppr: 2.4, br_count: 1 }],
} };
context.renderRaceTrends(data);
assert.strictEqual(created, 6);
assert(host.innerHTML.includes('<canvas'));
context.renderRaceTrends(data);
assert.strictEqual(created, 12);
assert.strictEqual(destroyed, 6);
context.Chart = undefined;
context.renderRaceTrends(data);
assert.strictEqual(destroyed, 12);
assert(host.innerHTML.includes('<svg'));
context.renderRaceTrends({});
assert(host.innerHTML.includes('No trend data yet.'));
console.log('Charts: six series, refresh cleanup, SVG fallback, and empty data passed.');
