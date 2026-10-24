const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync(`${__dirname}/modern_dashboard/dashboard.js`, 'utf8');
let created = 0, destroyed = 0;
let configs = [];
const host = { innerHTML: '', classList: { add() {} } };
const context = {
  Chart: function(canvas, config) {
    created++;
    configs.push(config);
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
vm.runInContext(source.slice(source.indexOf('const trendControls'), source.indexOf('function wireRaceFilterButtons')), context);
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
// Date filtering must use calendar days rather than the last N records.
const rows = [
  {date:'2026-10-01', total_races:1, total_points:100, ppr:100, unique_racers:2, br_count:0},
  {date:'2026-10-20', total_races:1, total_points:100, ppr:100, unique_racers:2, br_count:0},
  {date:'2026-10-21', total_races:9, total_points:90, ppr:10, unique_racers:4, br_count:3},
];
let selected = context.selectTrendWindow(rows, {range:'7', grouping:'daily', compare:false});
assert.strictEqual(selected.rows.length, 2);
selected = context.selectTrendWindow(rows, {range:'custom', from:'2026-10-22', to:'2026-10-20', grouping:'daily'});
assert.strictEqual(selected.rows.length, 0);
assert(selected.label.includes('valid'));
const grouped = context.groupTrendRows(rows.slice(1), 'weekly');
assert.strictEqual(grouped.length, 1);
assert.strictEqual(grouped[0].total_races, 10);
assert.strictEqual(grouped[0].ppr, 19); // Weighted, not the mean of 100 and 10.
assert.strictEqual(grouped[0].unique_racers, 3); // Average daily, not distinct weekly racers.
selected = context.selectTrendWindow([
  {date:'2026-10-14',total_races:2}, {date:'2026-10-21',total_races:3}
], {range:'7', grouping:'daily', compare:true});
assert.strictEqual(selected.previous[0].date, '2026-10-21');
assert.strictEqual(selected.previousOriginal[0].date, '2026-10-14');
assert.strictEqual(context.trendDate('2026-02-30'), null);
// Rendering with a comparison must produce a second dataset and preserve filter state.
context.Chart = function(canvas, config) { configs.push(config); this.destroy = () => {}; };
vm.runInContext("trendControls.range = '7'; trendControls.metric = 'ppr'; trendControls.compare = true;", context);
const comparisonData = {race_trends:{daily_current_season:[
  {date:'2026-10-14',total_races:2,total_points:200,ppr:100},
  {date:'2026-10-21',total_races:3,total_points:900,ppr:300},
]}};
context.renderRaceTrends(comparisonData);
assert.strictEqual(configs.at(-1).data.datasets.length,2);
assert.strictEqual(configs.at(-1).data.datasets[1].data[0],100);
assert(host.innerHTML.includes('(previous: 100.00)'));
context.renderRaceTrends(comparisonData);
assert.strictEqual(configs.at(-1).data.datasets.length,2);
context.renderRaceTrends({race_trends:{daily_current_season:[
  {date:'2026-10-13',total_races:2,total_points:200,ppr:100},
  {date:'2026-10-21',total_races:3,total_points:900,ppr:300},
]}});
assert.strictEqual(configs.at(-1).data.labels[0], '2026-10-20');
assert.strictEqual(configs.at(-1).data.datasets[0].data[0], null);
assert.strictEqual(configs.at(-1).data.datasets[1].data[0], 100);
context.Chart = undefined;
context.renderRaceTrends(comparisonData);
assert(host.innerHTML.includes('Previous period (aligned)'));
let csvContent = '', clicked = false, revoked = false;
context.Blob = function(parts) { csvContent = parts.join(''); };
context.URL = {createObjectURL: () => 'blob:test', revokeObjectURL: () => { revoked = true; }};
context.document.createElement = () => ({click: () => {clicked = true;}});
context.exportTrendCsv();
assert(clicked && revoked);
assert(csvContent.includes('"previous","2026-10-14"'));
assert(csvContent.includes('"current","2026-10-21"'));
console.log('Filters: calendar ranges, invalid dates, weekly weighted PPR, winner averages, comparison datasets, SVG comparison, CSV dates, and refresh persistence passed.');
console.log('Charts: six series, refresh cleanup, SVG fallback, and empty data passed.');
