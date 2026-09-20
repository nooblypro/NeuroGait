import assert from 'assert';
import { aggregateTimeline, computeAggregatedStats } from '../frontend/src/timeline_aggregator.js';

console.log('Running Timeline Aggregator Unit Tests...');

// Test 1: Empty input
assert.deepStrictEqual(aggregateTimeline([]), []);
assert.deepStrictEqual(computeAggregatedStats([]), {
  totalIntervals: 0,
  fogCount: 0,
  borderlineCount: 0,
  normalCount: 0,
  avgConfidence: '0.0%',
  dominantCue: 'None',
  totalDuration: 0.0
});
console.log('✓ Test 1: Empty input handled');

// Test 2: Overlapping windows from user prompt example
const promptExample = [
  { start: 0.0, end: 8.2, confidence: 0.15, type: 'Normal', primary_cue: 'stride_width' },
  { start: 7.3, end: 8.3, confidence: 0.45, type: 'Borderline', primary_cue: 'accel_rms' },
  { start: 7.4, end: 8.4, confidence: 0.20, type: 'Normal', primary_cue: 'stride_width' },
  { start: 7.5, end: 8.6, confidence: 0.50, type: 'Borderline', primary_cue: 'gyro_x_var' },
  { start: 7.7, end: 32.1, confidence: 0.10, type: 'Normal', primary_cue: 'stride_width' }
];

const agg1 = aggregateTimeline(promptExample);
console.log('Aggregated prompt example:', agg1);

// Verify strictly non-overlapping
for (let i = 0; i < agg1.length - 1; i++) {
  assert(agg1[i + 1].start >= agg1[i].end, `Overlap detected between ${agg1[i].end} and ${agg1[i + 1].start}`);
}
console.log('✓ Test 2: Overlapping example aggregated with strictly zero overlaps');

// Test 3: Zero-FoG Case stats
const stats1 = computeAggregatedStats(agg1);
assert.strictEqual(stats1.totalIntervals, agg1.length);
assert.strictEqual(stats1.fogCount, agg1.filter(e => e.type === 'FoG').length);
assert.strictEqual(stats1.borderlineCount, agg1.filter(e => e.type === 'Borderline').length);
assert.strictEqual(stats1.normalCount, agg1.filter(e => e.type === 'Normal').length);
assert.strictEqual(stats1.dominantCue, 'None', 'Dominant cue should be None when zero FoG');
console.log('✓ Test 3: Zero-FoG stats and dominant cue verified');

// Test 4: With FoG intervals
const fogExample = [
  { start: 0.0, end: 5.0, confidence: 0.10, type: 'Normal', primary_cue: 'stride_width' },
  { start: 4.0, end: 7.0, confidence: 0.75, type: 'FoG', primary_cue: 'gyro_z_var' },
  { start: 6.0, end: 9.0, confidence: 0.85, type: 'FoG', primary_cue: 'gyro_z_var' },
  { start: 8.5, end: 12.0, confidence: 0.50, type: 'Borderline', primary_cue: 'accel_rms' }
];

const agg2 = aggregateTimeline(fogExample);
const stats2 = computeAggregatedStats(agg2);
for (let i = 0; i < agg2.length - 1; i++) {
  assert(agg2[i + 1].start >= agg2[i].end, `Overlap detected in fogExample: ${agg2[i].end} > ${agg2[i + 1].start}`);
}
assert(stats2.fogCount > 0);
assert.strictEqual(stats2.dominantCue, 'gyro_z_var');
console.log('✓ Test 4: FoG aggregation and dominant cue attribution verified');

console.log('ALL UNIT TESTS PASSED SUCCESSFULLY!');
