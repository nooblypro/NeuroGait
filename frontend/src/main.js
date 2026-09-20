/**
 * NEUROGAIT — 5-BEAT CINEMATIC INTERACTIVE ENGINE
 * Compact 480vh timeline, frame-accurate video scrubbing, high-contrast typography
 */

// Math Utility Helpers
const clamp = (val, min = 0, max = 1) => Math.min(Math.max(val, min), max);
const lerp = (start, end, amt) => (1 - amt) * start + amt * end;
const smoothstep = (min, max, value) => {
  const x = Math.max(0, Math.min(1, (value - min) / (max - min)));
  return x * x * (3 - 2 * x);
};

// DOM Cache
const dom = {
  video: document.getElementById('bg-video'),
  hudProgress: document.getElementById('hud-progress'),
  hudTimecode: document.getElementById('hud-timecode'),
  brandContainer: document.getElementById('brand-container'),
  blackout: document.getElementById('blackout-curtain'),

  // 5 Major Beats
  b1: document.getElementById('beat-1'),
  b2: document.getElementById('beat-2'),
  b3: document.getElementById('beat-3'),
  b4: document.getElementById('beat-4'),
  b5: document.getElementById('beat-5'),

  // Beat 2 Elements
  b2Modalities: document.getElementById('b2-modalities'),
  b2ModReveal: document.getElementById('b2-mod-reveal'),
  b2Features: document.getElementById('b2-features'),
  b2FeatCenter: document.getElementById('b2-feat-center'),
  b2Tags: [
    document.getElementById('tag-1'),
    document.getElementById('tag-2'),
    document.getElementById('tag-3'),
    document.getElementById('tag-4'),
    document.getElementById('tag-5'),
    document.getElementById('tag-6'),
    document.getElementById('tag-7'),
    document.getElementById('tag-8'),
  ],

  // Beat 3 Elements
  b3Sync: document.getElementById('b3-sync'),
  b3ImuPulse: document.getElementById('b3-imu-pulse'),
  b3SyncBadge: document.getElementById('b3-sync-badge'),
  b3Detect: document.getElementById('b3-detect'),
  b3Cursor: document.getElementById('b3-cursor'),
  b3Highlight: document.getElementById('b3-highlight'),
  b3CalloutPanel: document.getElementById('b3-callout-panel'),
  b3ConfPanel: document.getElementById('b3-conf-panel'),
  b3ConfNum: document.getElementById('b3-conf-num'),

  // Beat 4 Elements
  b4EvidencePanel: document.getElementById('b4-evidence-panel'),
  b4BedrockPanel: document.getElementById('b4-bedrock-panel'),
  b4Arrow: document.getElementById('b4-arrow'),

  // Beat 5 Elements
  b5Words: [
    document.getElementById('b5-word-1'),
    document.getElementById('b5-word-2'),
    document.getElementById('b5-word-3'),
  ],
  b5Credits: document.getElementById('b5-credits'),
};

// State Variables
let targetProgress = 0;
let currentProgress = 0;
let isSeeking = false;
let pendingSeekProgress = null;

// Video Scrubbing Engine (No Autoplay, 100% Scroll-Controlled)
function updateVideoTime(p) {
  if (!dom.video) return;
  const dur = dom.video.duration;
  if (!dur || isNaN(dur) || dur <= 0) return;

  const maxTime = Math.max(0, dur - 0.04);
  const targetTime = clamp(p * maxTime, 0, maxTime);

  if (dom.hudTimecode) {
    dom.hudTimecode.textContent = `${targetTime.toFixed(2)}s`;
  }

  if (Math.abs(dom.video.currentTime - targetTime) > 0.015) {
    if (!isSeeking) {
      isSeeking = true;
      if ('fastSeek' in dom.video) {
        try {
          dom.video.fastSeek(targetTime);
        } catch {
          dom.video.currentTime = targetTime;
        }
      } else {
        dom.video.currentTime = targetTime;
      }
    } else {
      pendingSeekProgress = p;
    }
  }
}

function setupScrollScrubbing() {
  if (!dom.video) return;

  dom.video.pause();
  dom.video.currentTime = 0;

  dom.video.addEventListener('play', () => {
    dom.video.pause();
  });

  dom.video.addEventListener('seeked', () => {
    isSeeking = false;
    if (pendingSeekProgress !== null) {
      const nextProgress = pendingSeekProgress;
      pendingSeekProgress = null;
      updateVideoTime(nextProgress);
    }
  });

  if (dom.video.readyState >= 1) {
    updateVideoTime(currentProgress);
  } else {
    dom.video.addEventListener('loadedmetadata', () => {
      updateVideoTime(currentProgress);
    });
    dom.video.addEventListener('canplay', () => {
      updateVideoTime(currentProgress);
    });
  }
}

// Scene Helper: Activate Beat Container
function setBeatVisibility(el, visible, opacity = 1, translateY = 0, scale = 1) {
  if (!el) return;
  if (visible && opacity > 0.005) {
    el.style.visibility = 'visible';
    el.style.opacity = opacity.toFixed(3);
    el.style.transform = `translate3d(0, ${translateY.toFixed(2)}px, 0) scale(${scale.toFixed(3)})`;
  } else {
    el.style.visibility = 'hidden';
    el.style.opacity = '0';
  }
}

// 5-Beat Unified Progression State Machine
function updateBeats(p) {
  // Update HUD Chapter Status
  if (dom.hudProgress) {
    if (p < 0.18) dom.hudProgress.textContent = '1 / 5 // HERO';
    else if (p < 0.42) dom.hudProgress.textContent = '2 / 5 // MODALITIES & FEATURES';
    else if (p < 0.68) dom.hudProgress.textContent = '3 / 5 // SYNC & DETECTION';
    else if (p < 0.88) dom.hudProgress.textContent = '4 / 5 // EVIDENCE & BEDROCK';
    else dom.hudProgress.textContent = '5 / 5 // SYNTHESIS';
  }

  // -------------------------------------------------------------
  // BEAT 1: HERO (0.000 — 0.180)
  // -------------------------------------------------------------
  if (p <= 0.190) {
    const fadeOut = 1 - smoothstep(0.110, 0.180, p);
    const shiftY = lerp(0, -30, smoothstep(0.040, 0.180, p));
    setBeatVisibility(dom.b1, true, fadeOut, shiftY);

    if (dom.brandContainer) {
      dom.brandContainer.style.opacity = (1 - fadeOut).toFixed(2);
    }
  } else {
    setBeatVisibility(dom.b1, false);
    if (dom.brandContainer) dom.brandContainer.style.opacity = '1';
  }

  // -------------------------------------------------------------
  // BEAT 2: TWO MODALITIES → 8 FEATURES (0.180 — 0.420)
  // -------------------------------------------------------------
  if (p >= 0.170 && p <= 0.430) {
    const enter = smoothstep(0.170, 0.200, p);
    const exit = 1 - smoothstep(0.400, 0.430, p);
    const beatAlpha = Math.min(enter, exit);
    setBeatVisibility(dom.b2, true, beatAlpha);

    // Sub-phase 2A: Modalities (0.180 - 0.290)
    const modFadeOut = 1 - smoothstep(0.270, 0.305, p);
    if (dom.b2Modalities) {
      dom.b2Modalities.style.opacity = modFadeOut.toFixed(2);
      dom.b2Modalities.style.transform = `translate(-50%, -50%) scale(${lerp(1, 0.94, 1 - modFadeOut)})`;
    }

    // Sub-phase 2B: 08 FUSED FEATURES + Floating Annotations (0.290 - 0.420)
    const featFadeIn = smoothstep(0.290, 0.325, p);
    if (dom.b2Features) {
      dom.b2Features.style.opacity = featFadeIn.toFixed(2);
    }

    // Stagger in the 8 feature tags
    dom.b2Tags.forEach((tag, idx) => {
      const tagStart = 0.300 + idx * 0.010;
      const tagAlpha = smoothstep(tagStart, tagStart + 0.015, p);
      if (tag) {
        tag.style.opacity = tagAlpha.toFixed(2);
        tag.style.transform = `translateY(${lerp(10, 0, tagAlpha)}px)`;
      }
    });
  } else {
    setBeatVisibility(dom.b2, false);
  }

  // -------------------------------------------------------------
  // BEAT 3: SYNCHRONIZE → DETECT (0.420 — 0.680)
  // -------------------------------------------------------------
  if (p >= 0.410 && p <= 0.690) {
    const enter = smoothstep(0.410, 0.440, p);
    const exit = 1 - smoothstep(0.660, 0.690, p);
    const beatAlpha = Math.min(enter, exit);
    setBeatVisibility(dom.b3, true, beatAlpha);

    // Sub-phase 3A: Synchronization dual tracks snapping into alignment (0.420 - 0.530)
    const syncFadeOut = 1 - smoothstep(0.510, 0.545, p);
    if (dom.b3Sync) {
      dom.b3Sync.style.opacity = syncFadeOut.toFixed(2);

      // Glide IMU pulse into lock with video pulse
      const alignP = smoothstep(0.420, 0.485, p);
      const shiftX = lerp(-40, 0, alignP);
      if (dom.b3ImuPulse) {
        dom.b3ImuPulse.style.transform = `translateX(${shiftX}px)`;
      }

      // Temporal alignment badge reveal
      const badgeAlpha = smoothstep(0.465, 0.495, p);
      if (dom.b3SyncBadge) {
        dom.b3SyncBadge.style.opacity = badgeAlpha.toFixed(2);
        dom.b3SyncBadge.style.transform = `translateY(${lerp(14, 0, badgeAlpha)}px)`;
      }
    }

    // Sub-phase 3B: Detection timeline & 92% confidence (0.530 - 0.680)
    const detectFadeIn = smoothstep(0.530, 0.565, p);
    if (dom.b3Detect) {
      dom.b3Detect.style.opacity = detectFadeIn.toFixed(2);

      // Move timeline cursor [12% -> 84%]
      const curP = smoothstep(0.535, 0.640, p);
      const curPos = lerp(12, 84, curP);
      if (dom.b3Cursor) {
        dom.b3Cursor.style.left = `${curPos}%`;
      }

      // Flagged interval highlight (05.2s - 06.8s) activates
      const inInterval = curPos >= 45 && curPos <= 72;
      const highlightAlpha = smoothstep(0.560, 0.590, p);
      if (dom.b3Highlight) {
        dom.b3Highlight.style.opacity = highlightAlpha.toFixed(2);
      }

      // Callout & Confidence panel reveals
      const panelAlpha = smoothstep(0.575, 0.615, p);
      if (dom.b3CalloutPanel) {
        dom.b3CalloutPanel.style.opacity = panelAlpha.toFixed(2);
        dom.b3CalloutPanel.style.transform = `translateY(${lerp(15, 0, panelAlpha)}px)`;
      }
      if (dom.b3ConfPanel) {
        dom.b3ConfPanel.style.opacity = panelAlpha.toFixed(2);
        dom.b3ConfPanel.style.transform = `translateY(${lerp(15, 0, panelAlpha)}px)`;
      }

      // Confidence count-up to 92%
      if (dom.b3ConfNum) {
        const val = Math.round(92 * smoothstep(0.580, 0.630, p));
        dom.b3ConfNum.textContent = `${val}%`;
      }
    }
  } else {
    setBeatVisibility(dom.b3, false);
  }

  // -------------------------------------------------------------
  // BEAT 4: EVIDENCE → EXPLANATION (0.680 — 0.880)
  // -------------------------------------------------------------
  if (p >= 0.670 && p <= 0.890) {
    const enter = smoothstep(0.670, 0.700, p);
    const exit = 1 - smoothstep(0.860, 0.890, p);
    const beatAlpha = Math.min(enter, exit);
    setBeatVisibility(dom.b4, true, beatAlpha);

    // Evidence panel enters
    const evAlpha = smoothstep(0.685, 0.730, p);
    if (dom.b4EvidencePanel) {
      dom.b4EvidencePanel.style.opacity = evAlpha.toFixed(2);
      dom.b4EvidencePanel.style.transform = `translateY(${lerp(18, 0, evAlpha)}px)`;
    }

    // Synthesis arrow
    const arrowAlpha = smoothstep(0.725, 0.760, p);
    if (dom.b4Arrow) {
      dom.b4Arrow.style.opacity = arrowAlpha.toFixed(2);
    }

    // Bedrock explanation card enters
    const bedAlpha = smoothstep(0.750, 0.800, p);
    if (dom.b4BedrockPanel) {
      dom.b4BedrockPanel.style.opacity = bedAlpha.toFixed(2);
      dom.b4BedrockPanel.style.transform = `translateY(${lerp(18, 0, bedAlpha)}px)`;
    }
  } else {
    setBeatVisibility(dom.b4, false);
  }

  // -------------------------------------------------------------
  // BEAT 5: ENDING (0.880 — 1.000)
  // -------------------------------------------------------------
  if (p >= 0.870) {
    setBeatVisibility(dom.b5, true, 1);

    // Kinetic words cascade
    const w1P = smoothstep(0.885, 0.915, p);
    const w2P = smoothstep(0.910, 0.940, p);
    const w3P = smoothstep(0.935, 0.965, p);

    if (dom.b5Words[0]) {
      dom.b5Words[0].style.opacity = w1P.toFixed(2);
      dom.b5Words[0].style.transform = `translateY(${lerp(20, 0, w1P)}px)`;
    }
    if (dom.b5Words[1]) {
      dom.b5Words[1].style.opacity = w2P.toFixed(2);
      dom.b5Words[1].style.transform = `translateY(${lerp(20, 0, w2P)}px)`;
    }
    if (dom.b5Words[2]) {
      dom.b5Words[2].style.opacity = w3P.toFixed(2);
      dom.b5Words[2].style.transform = `translateY(${lerp(20, 0, w3P)}px)`;
    }

    // Credits reveal
    const credP = smoothstep(0.960, 0.988, p);
    if (dom.b5Credits) {
      dom.b5Credits.style.opacity = credP.toFixed(2);
      dom.b5Credits.style.transform = `translateY(${lerp(18, 0, credP)}px)`;
    }

    // Fade to pure black at absolute end
    const blackAlpha = smoothstep(0.988, 1.000, p);
    if (dom.blackout) {
      dom.blackout.style.opacity = blackAlpha.toFixed(2);
    }
  } else {
    setBeatVisibility(dom.b5, false);
    if (dom.blackout) dom.blackout.style.opacity = '0';
  }
}

// RequestAnimationFrame Lerped Loop
function onFrame() {
  currentProgress = lerp(currentProgress, targetProgress, 0.095);

  if (Math.abs(targetProgress - currentProgress) < 0.0001) {
    currentProgress = targetProgress;
  }

  // Scrub background video directly with scroll progress
  updateVideoTime(currentProgress);

  // Update the 5-beat narrative state machine
  updateBeats(currentProgress);

  requestAnimationFrame(onFrame);
}

// Scroll Event Handler
function onScroll() {
  const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
  if (maxScroll > 0) {
    targetProgress = clamp(window.scrollY / maxScroll);
  }
}

// Keyboard Navigation support
function onKeyDown(e) {
  const step = 0.06 * (document.documentElement.scrollHeight - window.innerHeight);
  if (e.key === 'ArrowDown' || e.key === 'PageDown' || e.key === ' ') {
    window.scrollBy({ top: step, behavior: 'smooth' });
  } else if (e.key === 'ArrowUp' || e.key === 'PageUp') {
    window.scrollBy({ top: -step, behavior: 'smooth' });
  } else if (e.key === 'Home') {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } else if (e.key === 'End') {
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' });
  }
}

// Initialization
function init() {
  setupScrollScrubbing();

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('keydown', onKeyDown);
  window.addEventListener('resize', onScroll);

  onScroll();
  currentProgress = targetProgress;

  requestAnimationFrame(onFrame);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
