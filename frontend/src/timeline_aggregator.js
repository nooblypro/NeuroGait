/**
 * NeuroGait Presentation Layer: Canonical Timeline Processor
 *
 * Treats backend canonical prediction episodes as authoritative and preserves
 * exact episode boundaries, confidences, classifications, and primary cues.
 *
 * Guarantees:
 * - Faithful representation of canonical backend prediction JSON.
 * - Does not recompute, re-average, or reinterpret model probabilities.
 * - Does not invent new ML classifications or convert FoG <-> Borderline.
 * - Chronologically sorts and formats display intervals.
 */

/**
 * Validates and chronologically sorts canonical prediction episodes from the backend.
 * @param {Array<{start: number, end: number, confidence: number, type: string, primary_cue?: string, data_mode?: string}>} canonicalEpisodes
 * @returns {Array<{start: number, end: number, confidence: number, type: 'Normal'|'Borderline'|'FoG', primary_cue: string, data_mode: string}>}
 */
export function aggregateTimeline(canonicalEpisodes) {
  if (!canonicalEpisodes || !Array.isArray(canonicalEpisodes) || canonicalEpisodes.length === 0) {
    return [];
  }

  const validated = [];
  for (const ep of canonicalEpisodes) {
    if (typeof ep.start === 'number' && typeof ep.end === 'number' && ep.end >= ep.start) {
      validated.push({
        start: Number(ep.start.toFixed(3)),
        end: Number(ep.end.toFixed(3)),
        confidence: typeof ep.confidence === 'number' ? Number(ep.confidence.toFixed(4)) : 0.0,
        type: ep.type || 'Normal',
        primary_cue: ep.primary_cue || 'None',
        data_mode: ep.data_mode || 'real'
      });
    }
  }

  // Ensure deterministic chronological ordering
  validated.sort((a, b) => a.start - b.start || a.end - b.end);
  return validated;
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
