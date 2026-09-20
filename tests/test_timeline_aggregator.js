import assert from 'assert';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { aggregateTimeline, computeAggregatedStats, generateModelGroundedNarrative } from '../frontend/src/timeline_aggregator.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('Running Canonical Timeline Aggregator Parity Tests...');

// Test 1: Empty input
assert.deepStrictEqual(aggregateTimeline([]), []);
assert.deepStrictEqual(computeAggregatedStats([]), {
  totalIntervals: 0,
  fogCount: 0,
  borderlineCount: 0,
  normalCount: 0,
  avgConfidence: '0.0%',
  dominantCue: 'None',
  totalDuration: 0.0,
  fogDuration: 0.0,
  fogBurdenPct: 0.0,
  meanFogConfidence: 0.0,
  longestFog: null
});
console.log('✓ Test 1: Empty input handled correctly');

// Test 2: Canonical episode preservation without reclassification or mutation
const canonicalSample = [
  { start: 0.008, end: 4.708, confidence: 0.0393, type: 'Normal', primary_cue: 'gyro_z_var', data_mode: 'real' },
  { start: 4.708, end: 6.008, confidence: 0.8735, type: 'FoG', primary_cue: 'gyro_z_var', data_mode: 'real' },
  { start: 6.008, end: 6.208, confidence: 0.4205, type: 'Borderline', primary_cue: 'gyro_z_var', data_mode: 'real' }
];

const res2 = aggregateTimeline(canonicalSample);
assert.strictEqual(res2.length, 3);
assert.strictEqual(res2[0].type, 'Normal');
assert.strictEqual(res2[1].type, 'FoG');
assert.strictEqual(res2[2].type, 'Borderline');
assert.strictEqual(res2[1].start, 4.708);
assert.strictEqual(res2[1].end, 6.008);
assert.strictEqual(res2[1].confidence, 0.8735);
assert.strictEqual(res2[1].primary_cue, 'gyro_z_var');
console.log('✓ Test 2: Canonical episode fields and types strictly preserved without alteration');

// Test 3: Chronological sorting
const unsorted = [
  { start: 10.0, end: 12.0, confidence: 0.9, type: 'FoG', primary_cue: 'accel_rms', data_mode: 'real' },
  { start: 0.0, end: 5.0, confidence: 0.1, type: 'Normal', primary_cue: 'stride_width', data_mode: 'real' },
  { start: 5.0, end: 10.0, confidence: 0.5, type: 'Borderline', primary_cue: 'gyro_x_var', data_mode: 'real' }
];
const res3 = aggregateTimeline(unsorted);
assert.strictEqual(res3[0].start, 0.0);
assert.strictEqual(res3[1].start, 5.0);
assert.strictEqual(res3[2].start, 10.0);
console.log('✓ Test 3: Chronological sorting verified');

// Test 4: PDFE31_1 Canonical Fixture Parity
const fixturePath = path.resolve(__dirname, '../outputs/predictions/PDFE31_1.json');
if (fs.existsSync(fixturePath)) {
  const pdfe31Raw = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
  const pdfe31Timeline = aggregateTimeline(pdfe31Raw);
  const stats = computeAggregatedStats(pdfe31Timeline);

  assert.strictEqual(pdfe31Timeline.length, 75, `Expected 75 total episodes, got ${pdfe31Timeline.length}`);
  assert.strictEqual(stats.fogCount, 27, `Expected 27 FoG episodes, got ${stats.fogCount}`);
  assert.strictEqual(stats.borderlineCount, 24, `Expected 24 Borderline intervals, got ${stats.borderlineCount}`);
  assert.strictEqual(stats.normalCount, 24, `Expected 24 Normal intervals, got ${stats.normalCount}`);
  assert.strictEqual(stats.dominantCue, 'gyro_z_var');

  // Verify key ground-truth-overlapping predictions exist with exact boundaries
  const pred1 = pdfe31Timeline.find(e => Math.abs(e.start - 55.408) < 0.01 && Math.abs(e.end - 57.608) < 0.01);
  assert(pred1, 'Pred 1 (55.408–57.608s) must be present');
  assert.strictEqual(pred1.type, 'FoG');
  assert.strictEqual(pred1.confidence, 0.8711);
  assert.strictEqual(pred1.primary_cue, 'gyro_z_var');

  const pred2 = pdfe31Timeline.find(e => Math.abs(e.start - 58.008) < 0.01 && Math.abs(e.end - 61.208) < 0.01);
  assert(pred2, 'Pred 2 (58.008–61.208s) must be present');
  assert.strictEqual(pred2.type, 'FoG');
  assert.strictEqual(pred2.confidence, 0.8711);
  assert.strictEqual(pred2.primary_cue, 'gyro_z_var');

  // Verify narrative mentions 75 non-overlapping intervals and 27 FoG
  const narrative = generateModelGroundedNarrative(pdfe31Timeline, stats);
  assert(narrative.includes('75 non-overlapping classified intervals'));
  assert(narrative.includes('27 intervals as FoG'));

  console.log('✓ Test 4: PDFE31_1 local cached fixture parity verified (75 episodes, Pred 1: 55.408-57.608, Pred 2: 58.008-61.208)');
}

// Test 5: Production Canonical Reference Fixture Parity (Linux / AWS Canonical: 76 episodes)
const prodFixturePath = path.resolve(__dirname, 'fixtures/pdfe31_1_production_reference.json');
if (fs.existsSync(prodFixturePath)) {
  const prodRaw = JSON.parse(fs.readFileSync(prodFixturePath, 'utf8'));
  const prodTimeline = aggregateTimeline(prodRaw);
  const prodStats = computeAggregatedStats(prodTimeline);

  assert.strictEqual(prodTimeline.length, 76, `Expected 76 total episodes, got ${prodTimeline.length}`);
  assert.strictEqual(prodStats.fogCount, 27, `Expected 27 FoG episodes, got ${prodStats.fogCount}`);
  assert.strictEqual(prodStats.borderlineCount, 24, `Expected 24 Borderline intervals, got ${prodStats.borderlineCount}`);
  assert.strictEqual(prodStats.normalCount, 25, `Expected 25 Normal intervals, got ${prodStats.normalCount}`);
  assert.strictEqual(prodStats.dominantCue, 'gyro_z_var');

  // Verify key ground-truth-overlapping predictions exist with exact boundaries
  const pred1 = prodTimeline.find(e => Math.abs(e.start - 55.508) < 0.01 && Math.abs(e.end - 57.608) < 0.01);
  assert(pred1, 'Pred 1 (55.508–57.608s) must be present in production canonical output');
  assert.strictEqual(pred1.type, 'FoG');
  assert.strictEqual(pred1.confidence, 0.9018);
  assert.strictEqual(pred1.primary_cue, 'gyro_z_var');

  const pred2 = prodTimeline.find(e => Math.abs(e.start - 58.008) < 0.01 && Math.abs(e.end - 61.208) < 0.01);
  assert(pred2, 'Pred 2 (58.008–61.208s) must be present in production canonical output');
  assert.strictEqual(pred2.type, 'FoG');
  assert.strictEqual(pred2.confidence, 0.8898);
  assert.strictEqual(pred2.primary_cue, 'gyro_z_var');

  // Verify narrative mentions 76 non-overlapping intervals and 27 FoG
  const narrative = generateModelGroundedNarrative(prodTimeline, prodStats);
  assert(narrative.includes('76 non-overlapping classified intervals'));
  assert(narrative.includes('27 intervals as FoG'));

  console.log('✓ Test 5: PDFE31_1 production reference parity verified (76 episodes, Pred 1: 55.508-57.608, Pred 2: 58.008-61.208)');
}

console.log('\nALL TIMELINE AGGREGATOR TESTS PASSED SUCCESSFULLY!');

