/**
 * NeuroGait Presentation Layer: Non-Overlapping Timeline Aggregator
 *
 * Resolves overlapping sliding model windows into an exhaustive, strictly
 * non-overlapping timeline where every timestamp belongs to exactly one state:
 * - Normal (< 0.40 posterior probability)
 * - Borderline (0.40 <= probability < 0.60)
 * - FoG (>= 0.60 posterior probability)
 *
 * Deterministic Resolution Rule:
 * 1. Endpoints Partitioning: Collect all unique start/end timestamps from raw windows
 *    and construct disjoint elementary sub-intervals [t_j, t_{j+1}).
 * 2. Overlap Resolution: For each elementary sub-interval, evaluate all model windows
 *    covering the sub-interval midpoint. Compute the mean FoG probability across active
 *    windows: P_j = (1 / |W(j)|) * sum_{w in W(j)} w.confidence.
 *    Assign state according to clinical thresholds (FoG >= 0.60, Borderline >= 0.40, Normal < 0.40).
 *    Assign dominant cue from the covering window with highest classification confidence.
 * 3. Contiguous State Merging: Merge contiguous elementary intervals that share the same
 *    state into unified maximal non-overlapping intervals, weighting mean confidence by duration.
 *
 * Guarantees:
 * - next.start >= previous.end for all consecutive intervals (zero temporal overlap).
 * - Total intervals = FoG intervals + Borderline intervals + Normal intervals.
 * - Raw model predictions remain preserved internally without alteration.
 */

/**
 * Aggregates raw overlapping model prediction windows into a non-overlapping timeline.
 * @param {Array<{start: number, end: number, confidence: number, type: string, primary_cue?: string}>} rawWindows
 * @returns {Array<{start: number, end: number, confidence: number, type: 'Normal'|'Borderline'|'FoG', primary_cue: string}>}
 */
export function aggregateTimeline(rawWindows) {
  if (!rawWindows || !Array.isArray(rawWindows) || rawWindows.length === 0) {
    return [];
  }

  // 1. Collect and sort all unique endpoint timestamps
  const endpointsSet = new Set();
  for (const w of rawWindows) {
    if (typeof w.start === 'number' && typeof w.end === 'number' && w.end > w.start) {
      endpointsSet.add(Number(w.start.toFixed(3)));
      endpointsSet.add(Number(w.end.toFixed(3)));
    }
  }

  const timePoints = Array.from(endpointsSet).sort((a, b) => a - b);
  if (timePoints.length < 2) return [];

  // 2. Resolve each elementary sub-interval [t_j, t_{j+1})
  const elementary = [];
  for (let i = 0; i < timePoints.length - 1; i++) {
    const t0 = timePoints[i];
    const t1 = timePoints[i + 1];
    if (t1 - t0 < 0.001) continue; // Skip zero-duration slices

    const mid = (t0 + t1) / 2;
    // Find all raw windows covering the midpoint of this elementary slice
    const covering = rawWindows.filter(w => w.start <= mid && w.end >= mid);
    if (covering.length === 0) continue;

    // Mean FoG probability across all active windows covering this slice
    const meanConf = covering.reduce((sum, w) => sum + (w.confidence || 0), 0) / covering.length;

    let state = 'Normal';
    if (meanConf >= 0.60) {
      state = 'FoG';
    } else if (meanConf >= 0.40) {
      state = 'Borderline';
    }

    // Identify primary cue: best matching active window with highest confidence
    const bestWindow = covering.reduce((best, w) => {
      return (w.confidence || 0) > (best.confidence || 0) ? w : best;
    }, covering[0]);

    elementary.push({
      start: t0,
      end: t1,
      confidence: meanConf,
      type: state,
      primary_cue: bestWindow.primary_cue || 'None'
    });
  }

  // 3. Merge contiguous adjacent elementary intervals sharing the same state
  const merged = [];
  for (const slice of elementary) {
    if (merged.length === 0) {
      merged.push({ ...slice, maxConf: slice.confidence });
    } else {
      const last = merged[merged.length - 1];
      if (last.type === slice.type && Math.abs(last.end - slice.start) < 0.005) {
        const dLast = last.end - last.start;
        const dSlice = slice.end - slice.start;
        const totalD = dLast + dSlice;
        last.confidence = totalD > 0 ? (last.confidence * dLast + slice.confidence * dSlice) / totalD : last.confidence;
        last.end = slice.end;
        if (slice.confidence > (last.maxConf || 0)) {
          last.primary_cue = slice.primary_cue;
          last.maxConf = slice.confidence;
        }
      } else {
        merged.push({ ...slice, maxConf: slice.confidence });
      }
    }
  }

  // 4. Clean up precision and return canonical non-overlapping intervals
  return merged.map(m => ({
    start: Number(m.start.toFixed(2)),
    end: Number(m.end.toFixed(2)),
    confidence: Number(m.confidence.toFixed(4)),
    type: m.type,
    primary_cue: m.primary_cue || 'None'
  }));
}

/**
 * Computes deterministic summary metrics from the aggregated non-overlapping timeline.
 * @param {Array<{start: number, end: number, confidence: number, type: string, primary_cue: string}>} timeline
 */
export function computeAggregatedStats(timeline) {
  if (!timeline || timeline.length === 0) {
    return {
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
    };
  }

  const fogIntervals = timeline.filter(e => e.type === 'FoG');
  const borderlineIntervals = timeline.filter(e => e.type === 'Borderline');
  const normalIntervals = timeline.filter(e => e.type === 'Normal');

  // Dominant cue strictly derived from FoG intervals if any exist, else 'None'
  let dominantCue = 'None';
  if (fogIntervals.length > 0) {
    const cueCounts = {};
    for (const ep of fogIntervals) {
      if (ep.primary_cue && ep.primary_cue !== 'None') {
        cueCounts[ep.primary_cue] = (cueCounts[ep.primary_cue] || 0) + 1;
      }
    }
    let maxCount = 0;
    for (const [cue, count] of Object.entries(cueCounts)) {
      if (count > maxCount) {
        maxCount = count;
        dominantCue = cue;
      }
    }
  }

  const avgConfVal = timeline.reduce((sum, e) => sum + (e.confidence || 0), 0) / timeline.length;
  const totalDuration = timeline[timeline.length - 1].end - timeline[0].start;
  const fogDuration = fogIntervals.reduce((sum, e) => sum + Math.max(0, e.end - e.start), 0);
  const fogBurdenPct = totalDuration > 0 ? (fogDuration / totalDuration) * 100 : 0;
  const meanFogConf = fogIntervals.length > 0
    ? (fogIntervals.reduce((sum, e) => sum + (e.confidence || 0), 0) / fogIntervals.length)
    : 0;

  let longestFog = null;
  if (fogIntervals.length > 0) {
    longestFog = fogIntervals.reduce((longest, curr) => {
      const currDur = curr.end - curr.start;
      const longDur = longest.end - longest.start;
      return currDur > longDur ? curr : longest;
    }, fogIntervals[0]);
  }

  return {
    totalIntervals: timeline.length,
    fogCount: fogIntervals.length,
    borderlineCount: borderlineIntervals.length,
    normalCount: normalIntervals.length,
    avgConfidence: `${(avgConfVal * 100).toFixed(1)}%`,
    dominantCue,
    totalDuration: Number(totalDuration.toFixed(2)),
    fogDuration: Number(fogDuration.toFixed(2)),
    fogBurdenPct: Number(fogBurdenPct.toFixed(2)),
    meanFogConfidence: Number(meanFogConf.toFixed(4)),
    longestFog
  };
}

/**
 * Generates deterministic, model-grounded narrative explanation strictly derived
 * from the canonical aggregated non-overlapping timeline.
 * @param {Array<{start: number, end: number, confidence: number, type: string, primary_cue: string}>} timeline
 * @param {Object} stats Precomputed aggregated statistics
 * @returns {string} Model-grounded explanation narrative
 */
export function generateModelGroundedNarrative(timeline, stats) {
  if (!timeline || timeline.length === 0 || !stats) {
    return 'No non-overlapping gait intervals recorded in the input trial.';
  }

  const { totalIntervals, fogCount, borderlineCount, normalCount, dominantCue, fogDuration, fogBurdenPct, longestFog } = stats;
  const fogIntervals = timeline.filter(e => e.type === 'FoG');

  let p1 = '';
  if (fogCount === 0) {
    p1 = `The recording contained ${totalIntervals} non-overlapping classified intervals. The model classified 0 intervals as FoG, ${borderlineCount} as Borderline, and ${normalCount} as Normal. No FoG-classified intervals were detected in this recording.`;
  } else if (fogCount === 1) {
    const fogEp = fogIntervals[0];
    const confPct = ((fogEp.confidence || 0) * 100).toFixed(1);
    const cue = fogEp.primary_cue || dominantCue || 'None';
    p1 = `The recording contained ${totalIntervals} non-overlapping classified intervals. The model classified 1 interval as FoG, ${borderlineCount} as Borderline, and ${normalCount} as Normal. The FoG-classified interval occurred from ${fogEp.start.toFixed(2)}s to ${fogEp.end.toFixed(2)}s with a classification confidence of ${confPct}%. The dominant model-derived cue for the FoG interval was ${cue}.`;
  } else {
    const longestConfPct = longestFog ? ((longestFog.confidence || 0) * 100).toFixed(1) : '0.0';
    const longestDur = longestFog ? (longestFog.end - longestFog.start).toFixed(2) : '0.00';
    const longestStart = longestFog ? longestFog.start.toFixed(2) : '0.00';
    const longestEnd = longestFog ? longestFog.end.toFixed(2) : '0.00';
    p1 = `The recording contained ${totalIntervals} non-overlapping classified intervals. The model classified ${fogCount} intervals as FoG, ${borderlineCount} as Borderline, and ${normalCount} as Normal. Total FoG duration was ${fogDuration.toFixed(2)} seconds (${fogBurdenPct.toFixed(1)}% burden). The longest FoG interval spanned from ${longestStart}s to ${longestEnd}s (${longestDur}s duration, confidence ${longestConfPct}%). The dominant model-derived cue across FoG intervals was ${dominantCue}.`;
  }

  const safetyStatement = 'These model-derived feature cues represent statistical associations within the model output and do not imply clinical causation or diagnosis.';

  return `${p1}\n\n${safetyStatement}`;
}
