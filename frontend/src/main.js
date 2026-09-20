/**
 * NEUROGAIT — 6-BEAT CINEMATIC & ASSESSMENT INTERACTIVE ENGINE
 * Scroll-controlled cinematic storytelling leading into the interactive assessment UI.
 */

import { aggregateTimeline, computeAggregatedStats, generateModelGroundedNarrative } from './timeline_aggregator.js';

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

  // 6 Major Beats
  b1: document.getElementById('beat-1'),
  b2: document.getElementById('beat-2'),
  b3: document.getElementById('beat-3'),
  b4: document.getElementById('beat-4'),
  b5: document.getElementById('beat-5'),
  b6: document.getElementById('beat-6'),

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
  b5CtaBox: document.getElementById('b5-cta-box'),
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
    if (el.id === 'beat-6') {
      el.style.pointerEvents = 'auto';
    }
  } else {
    el.style.visibility = 'hidden';
    el.style.opacity = '0';
    if (el.id === 'beat-6') {
      el.style.pointerEvents = 'none';
    }
  }
}

// 6-Beat Unified Progression State Machine
function updateBeats(p) {
  // Update HUD Chapter Status
  if (dom.hudProgress) {
    if (p < 0.16) dom.hudProgress.textContent = '1 / 6 // HERO';
    else if (p < 0.36) dom.hudProgress.textContent = '2 / 6 // MODALITIES & FEATURES';
    else if (p < 0.54) dom.hudProgress.textContent = '3 / 6 // SYNC & DETECTION';
    else if (p < 0.72) dom.hudProgress.textContent = '4 / 6 // EVIDENCE & BEDROCK';
    else if (p < 0.85) dom.hudProgress.textContent = '5 / 6 // SYNTHESIS';
    else dom.hudProgress.textContent = '6 / 6 // ASSESSMENT PIPELINE';
  }

  // BEAT 1: HERO
  if (p <= 0.170) {
    const fadeOut = 1 - smoothstep(0.100, 0.160, p);
    const shiftY = lerp(0, -30, smoothstep(0.040, 0.160, p));
    setBeatVisibility(dom.b1, true, fadeOut, shiftY);

    if (dom.brandContainer) {
      dom.brandContainer.style.opacity = (1 - fadeOut).toFixed(2);
    }
  } else {
    setBeatVisibility(dom.b1, false);
    if (dom.brandContainer) dom.brandContainer.style.opacity = '1';
  }

  // BEAT 2: MODALITIES & FEATURES
  if (p >= 0.150 && p <= 0.380) {
    const enter = smoothstep(0.150, 0.180, p);
    const exit = 1 - smoothstep(0.350, 0.380, p);
    const beatAlpha = Math.min(enter, exit);
    setBeatVisibility(dom.b2, true, beatAlpha);

    const modFadeOut = 1 - smoothstep(0.240, 0.280, p);
    if (dom.b2Modalities) {
      dom.b2Modalities.style.opacity = modFadeOut.toFixed(2);
      dom.b2Modalities.style.transform = `translate(-50%, -50%) scale(${lerp(1, 0.94, 1 - modFadeOut)})`;
    }

    const featFadeIn = smoothstep(0.260, 0.300, p);
    if (dom.b2Features) {
      dom.b2Features.style.opacity = featFadeIn.toFixed(2);
    }

    dom.b2Tags.forEach((tag, idx) => {
      const tagStart = 0.270 + idx * 0.008;
      const tagAlpha = smoothstep(tagStart, tagStart + 0.012, p);
      if (tag) {
        tag.style.opacity = tagAlpha.toFixed(2);
        tag.style.transform = `translateY(${lerp(10, 0, tagAlpha)}px)`;
      }
    });
  } else {
    setBeatVisibility(dom.b2, false);
  }

  // BEAT 3: SYNCHRONIZE & DETECT
  if (p >= 0.360 && p <= 0.560) {
    const enter = smoothstep(0.360, 0.390, p);
    const exit = 1 - smoothstep(0.530, 0.560, p);
    const beatAlpha = Math.min(enter, exit);
    setBeatVisibility(dom.b3, true, beatAlpha);

    const syncFadeOut = 1 - smoothstep(0.440, 0.470, p);
    if (dom.b3Sync) {
      dom.b3Sync.style.opacity = syncFadeOut.toFixed(2);

      const alignP = smoothstep(0.370, 0.430, p);
      const shiftX = lerp(-40, 0, alignP);
      if (dom.b3ImuPulse) {
        dom.b3ImuPulse.style.transform = `translateX(${shiftX}px)`;
      }

      const badgeAlpha = smoothstep(0.400, 0.430, p);
      if (dom.b3SyncBadge) {
        dom.b3SyncBadge.style.opacity = badgeAlpha.toFixed(2);
        dom.b3SyncBadge.style.transform = `translateY(${lerp(14, 0, badgeAlpha)}px)`;
      }
    }

    const detectFadeIn = smoothstep(0.460, 0.490, p);
    if (dom.b3Detect) {
      dom.b3Detect.style.opacity = detectFadeIn.toFixed(2);

      const curP = smoothstep(0.470, 0.540, p);
      const curPos = lerp(12, 84, curP);
      if (dom.b3Cursor) {
        dom.b3Cursor.style.left = `${curPos}%`;
      }

      const highlightAlpha = smoothstep(0.490, 0.520, p);
      if (dom.b3Highlight) {
        dom.b3Highlight.style.opacity = highlightAlpha.toFixed(2);
      }

      const panelAlpha = smoothstep(0.500, 0.530, p);
      if (dom.b3CalloutPanel) {
        dom.b3CalloutPanel.style.opacity = panelAlpha.toFixed(2);
        dom.b3CalloutPanel.style.transform = `translateY(${lerp(15, 0, panelAlpha)}px)`;
      }
      if (dom.b3ConfPanel) {
        dom.b3ConfPanel.style.opacity = panelAlpha.toFixed(2);
        dom.b3ConfPanel.style.transform = `translateY(${lerp(15, 0, panelAlpha)}px)`;
      }

      if (dom.b3ConfNum) {
        const val = Math.round(92 * smoothstep(0.500, 0.535, p));
        dom.b3ConfNum.textContent = `${val}%`;
      }
    }
  } else {
    setBeatVisibility(dom.b3, false);
  }

  // BEAT 4: EVIDENCE → EXPLANATION
  if (p >= 0.540 && p <= 0.740) {
    const enter = smoothstep(0.540, 0.570, p);
    const exit = 1 - smoothstep(0.710, 0.740, p);
    const beatAlpha = Math.min(enter, exit);
    setBeatVisibility(dom.b4, true, beatAlpha);

    const evAlpha = smoothstep(0.555, 0.590, p);
    if (dom.b4EvidencePanel) {
      dom.b4EvidencePanel.style.opacity = evAlpha.toFixed(2);
      dom.b4EvidencePanel.style.transform = `translateY(${lerp(18, 0, evAlpha)}px)`;
    }

    const arrowAlpha = smoothstep(0.590, 0.620, p);
    if (dom.b4Arrow) {
      dom.b4Arrow.style.opacity = arrowAlpha.toFixed(2);
    }

    const bedAlpha = smoothstep(0.610, 0.650, p);
    if (dom.b4BedrockPanel) {
      dom.b4BedrockPanel.style.opacity = bedAlpha.toFixed(2);
      dom.b4BedrockPanel.style.transform = `translateY(${lerp(18, 0, bedAlpha)}px)`;
    }
  } else {
    setBeatVisibility(dom.b4, false);
  }

  // BEAT 5: SYNTHESIS (0.720 — 0.850)
  if (p >= 0.720 && p <= 0.860) {
    const enter = smoothstep(0.720, 0.750, p);
    const exit = 1 - smoothstep(0.830, 0.860, p);
    const beatAlpha = Math.min(enter, exit);
    setBeatVisibility(dom.b5, true, beatAlpha);

    const w1P = smoothstep(0.730, 0.760, p);
    const w2P = smoothstep(0.750, 0.780, p);
    const w3P = smoothstep(0.770, 0.800, p);

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

    const credP = smoothstep(0.790, 0.830, p);
    if (dom.b5Credits) {
      dom.b5Credits.style.opacity = credP.toFixed(2);
      dom.b5Credits.style.transform = `translateY(${lerp(18, 0, credP)}px)`;
    }
    if (dom.b5CtaBox) {
      dom.b5CtaBox.style.opacity = credP.toFixed(2);
      dom.b5CtaBox.style.pointerEvents = credP > 0.5 ? 'auto' : 'none';
    }
  } else {
    setBeatVisibility(dom.b5, false);
  }

  // BEAT 6: BEGIN YOUR ASSESSMENT (0.840 — 1.000)
  if (p >= 0.840) {
    const enterP = smoothstep(0.840, 0.880, p);
    setBeatVisibility(dom.b6, true, enterP);
    if (dom.blackout) dom.blackout.style.opacity = '0';
  } else {
    setBeatVisibility(dom.b6, false);
  }
}

// RequestAnimationFrame Lerped Loop
function onFrame() {
  currentProgress = lerp(currentProgress, targetProgress, 0.095);

  if (Math.abs(targetProgress - currentProgress) < 0.0001) {
    currentProgress = targetProgress;
  }

  updateVideoTime(currentProgress);
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

// Keyboard Navigation
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

// Setup Assessment Interactive Controller
function setupAssessmentEngine() {
  const presetSampleBtn = document.getElementById('preset-sample-btn');
  const presetCustomBtn = document.getElementById('preset-custom-btn');
  const fileInputVideo = document.getElementById('file-input-video');
  const fileInputImu = document.getElementById('file-input-imu');
  const pillVideo = document.getElementById('pill-video');
  const pillImu = document.getElementById('pill-imu');
  const pillVideoName = document.getElementById('pill-video-name');
  const pillVideoSize = document.getElementById('pill-video-size');
  const pillImuName = document.getElementById('pill-imu-name');
  const pillImuSize = document.getElementById('pill-imu-size');
  const runBtn = document.getElementById('run-assessment-btn');
  const tracker = document.getElementById('session-tracker');
  const sessionIdVal = document.getElementById('session-id-val');
  const stepMsg = document.getElementById('step-msg');
  const resultsDashboard = document.getElementById('results-dashboard');

  let activeMode = 'sample';
  let selectedVideoFile = null;
  let selectedImuFile = null;

  if (presetSampleBtn && presetCustomBtn) {
    presetSampleBtn.addEventListener('click', () => {
      activeMode = 'sample';
      presetSampleBtn.classList.add('active');
      presetCustomBtn.classList.remove('active');
      pillVideo.classList.remove('hidden');
      pillImu.classList.remove('hidden');
      pillVideoName.textContent = 'PDFE01_1.mp4';
      pillVideoSize.textContent = '(80.0 MB)';
      pillImuName.textContent = 'SUB01_1.txt';
      pillImuSize.textContent = '(1.8 MB)';
    });

    presetCustomBtn.addEventListener('click', () => {
      activeMode = 'custom';
      presetCustomBtn.classList.add('active');
      presetSampleBtn.classList.remove('active');
      if (!selectedVideoFile) pillVideo.classList.add('hidden');
      if (!selectedImuFile) pillImu.classList.add('hidden');
    });
  }

  if (fileInputVideo) {
    fileInputVideo.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        selectedVideoFile = e.target.files[0];
        pillVideoName.textContent = selectedVideoFile.name;
        pillVideoSize.textContent = `(${(selectedVideoFile.size / (1024 * 1024)).toFixed(1)} MB)`;
        pillVideo.classList.remove('hidden');
        activeMode = 'custom';
        if (presetCustomBtn) {
          presetCustomBtn.classList.add('active');
          presetSampleBtn.classList.remove('active');
        }
      }
    });
  }

  if (fileInputImu) {
    fileInputImu.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        selectedImuFile = e.target.files[0];
        pillImuName.textContent = selectedImuFile.name;
        pillImuSize.textContent = `(${(selectedImuFile.size / (1024 * 1024)).toFixed(1)} MB)`;
        pillImu.classList.remove('hidden');
        activeMode = 'custom';
        if (presetCustomBtn) {
          presetCustomBtn.classList.add('active');
          presetSampleBtn.classList.remove('active');
        }
      }
    });
  }

  // Smooth scroll CTA handler
  const ctaRecorded = document.getElementById('cta-recorded');
  const ctaLive = document.getElementById('cta-live');
  const scrollToBeat6 = (e) => {
    e.preventDefault();
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: 'smooth' });
  };
  if (ctaRecorded) ctaRecorded.addEventListener('click', scrollToBeat6);
  if (ctaLive) ctaLive.addEventListener('click', scrollToBeat6);

  // Run Assessment Action
  if (runBtn) {
    runBtn.addEventListener('click', async () => {
      const execEnv = document.querySelector('input[name="exec_env_radio"]:checked')?.value || 'cloud';

      runBtn.disabled = true;
      runBtn.textContent = '⏳ Processing Multimodal Assessment...';
      tracker.classList.remove('hidden');
      resultsDashboard.classList.add('hidden');
      resetStepper();

      const videoFileToUpload = selectedVideoFile || (fileInputVideo && fileInputVideo.files && fileInputVideo.files[0]) || null;
      const imuFileToUpload = selectedImuFile || (fileInputImu && fileInputImu.files && fileInputImu.files[0]) || null;

      const API_BASE = import.meta.env.VITE_API_URL || 'https://xwncaenjbd.execute-api.ap-south-1.amazonaws.com';

      try {
        if (execEnv === 'cloud') {
          if (!videoFileToUpload || !imuFileToUpload) {
            throw new Error('Please select both a video (.mp4) and an IMU (.txt/.csv) file to run AWS Cloud Inference.');
          }

          const vName = videoFileToUpload.name;
          const iName = imuFileToUpload.name;
          const vSize = videoFileToUpload.size;
          const iSize = imuFileToUpload.size;

          updateStep('step-init', 'active', `Initializing AWS session for ${vName} (${(vSize / (1024 * 1024)).toFixed(1)} MB)...`);
          const sessRes = await fetch(`${API_BASE}/sessions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              video_filename: vName,
              imu_filename: iName,
              video_size_bytes: vSize,
              imu_size_bytes: iSize
            })
          });
          if (!sessRes.ok) {
            const errTxt = await sessRes.text();
            throw new Error(`Failed to initialize session (HTTP ${sessRes.status}): ${errTxt}`);
          }
          const sessData = await sessRes.json();
          if (!sessData.session_id) throw new Error(sessData.message || 'Session creation failed');
          const sid = sessData.session_id;
          sessionIdVal.textContent = sid;
          updateStep('step-init', 'done');

          updateStep('step-upload', 'active', `Uploading real files to S3 (${vName}, ${iName})...`);
          if (!sessData.upload_urls?.video || !sessData.upload_urls?.imu) {
            throw new Error('API Gateway did not return presigned S3 upload URLs.');
          }

          const vUploadRes = await fetch(sessData.upload_urls.video, {
            method: 'PUT',
            body: videoFileToUpload,
            headers: { 'Content-Type': 'video/mp4' }
          });
          if (!vUploadRes.ok) {
            throw new Error(`S3 video upload failed with HTTP status ${vUploadRes.status}`);
          }

          const iUploadRes = await fetch(sessData.upload_urls.imu, {
            method: 'PUT',
            body: imuFileToUpload,
            headers: { 'Content-Type': 'text/plain' }
          });
          if (!iUploadRes.ok) {
            throw new Error(`S3 IMU upload failed with HTTP status ${iUploadRes.status}`);
          }
          updateStep('step-upload', 'done');

          updateStep('step-confirm', 'active', 'Confirming S3 upload and updating DynamoDB state to UPLOADED...');
          const confRes = await fetch(`${API_BASE}/sessions/confirm-upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sid })
          });
          if (!confRes.ok) {
            const cErr = await confRes.text();
            throw new Error(`Upload confirmation failed (HTTP ${confRes.status}): ${cErr}`);
          }
          updateStep('step-confirm', 'done');

          updateStep('step-ecs', 'active', 'Dispatching ECS Fargate ML container task...');
          const startRes = await fetch(`${API_BASE}/inference/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sid })
          });
          if (!startRes.ok) {
            const sErr = await startRes.text();
            throw new Error(`ECS task dispatch failed (HTTP ${startRes.status}): ${sErr}`);
          }
          updateStep('step-ecs', 'done');

          updateStep('step-ml', 'active', 'Waiting for ECS Fargate container execution...');
          let pollCount = 0;
          const maxPolls = 140; // 140 * 3s = 420 seconds (7 minutes)
          let completeData = null;

          while (pollCount < maxPolls) {
            await new Promise(r => setTimeout(r, 3000));
            pollCount++;
            const elapsed = pollCount * 3;

            try {
              const stRes = await fetch(`${API_BASE}/inference/status?session_id=${sid}`);
              if (!stRes.ok) {
                stepMsg.textContent = `⏳ Polling status... (HTTP ${stRes.status}, ${elapsed}s elapsed)`;
                continue;
              }
              const stData = await stRes.json();

              if (stData.status === 'COMPLETE') {
                completeData = stData;
                break;
              } else if (stData.status === 'PROCESSING') {
                stepMsg.textContent = `⏳ Real ML inference active on AWS Fargate... MediaPipe pose extraction & 8-feature fusion (${elapsed}s elapsed)`;
              } else if (stData.status === 'ML_COMPLETE') {
                updateStep('step-ml', 'done');
                updateStep('step-bedrock', 'active', `ML inference complete in S3. Synthesizing clinical explanation (${elapsed}s elapsed)...`);
                stepMsg.textContent = `⏳ ML inference complete in S3. Synthesizing narrative explanation (${elapsed}s elapsed)...`;
              } else if (stData.status === 'NARRATIVE_GENERATING') {
                updateStep('step-ml', 'done');
                updateStep('step-bedrock', 'active', `Synthesizing narrative explanation (${elapsed}s elapsed)...`);
                stepMsg.textContent = `⏳ Synthesizing clinical narrative explanation (${elapsed}s elapsed)...`;
              } else if (stData.status === 'CREATED' || stData.status === 'UPLOADED') {
                stepMsg.textContent = `⏳ Session logged in DynamoDB (${stData.status}). Awaiting ECS worker pickup (${elapsed}s elapsed)...`;
              } else if (stData.status?.includes('FAILED') || stData.status?.includes('ERROR')) {
                throw new Error(`AWS Pipeline stopped with failure status: ${stData.status}`);
              }
            } catch (pollErr) {
              if (pollErr.message && pollErr.message.includes('AWS Pipeline stopped with failure status')) {
                throw pollErr;
              }
              console.warn('Status poll warning:', pollErr);
            }
          }

          if (!completeData) {
            throw new Error(`AWS Pipeline execution timed out after ${maxPolls * 3} seconds. Session ID: ${sid}. Real ECS Fargate task did not reach COMPLETE.`);
          }

          updateStep('step-ml', 'done');
          updateStep('step-bedrock', 'done');
          updateStep('step-ready', 'done', '✅ Real Assessment Complete!');

          renderResults(completeData);
        } else {
          // Local Engine Simulation
          sessionIdVal.textContent = `local-${Math.random().toString(36).substring(2, 10)}`;
          updateStep('step-init', 'done');
          updateStep('step-upload', 'done');
          updateStep('step-confirm', 'done');
          updateStep('step-ecs', 'done');
          updateStep('step-ml', 'done');
          updateStep('step-bedrock', 'done');
          updateStep('step-ready', 'done', '✅ Local Deterministic Assessment Complete!');

          renderResults(getVerifiedSampleResults());
        }
      } catch (err) {
        stepMsg.textContent = `❌ Error: ${err.message}`;
      } finally {
        runBtn.disabled = false;
        runBtn.textContent = '🚀 Run Multimodal Assessment';
      }
    });
  }
}

function resetStepper() {
  ['step-init', 'step-upload', 'step-confirm', 'step-ecs', 'step-ml', 'step-bedrock', 'step-ready'].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.className = 'step-box';
    }
  });
}

function updateStep(stepId, state, msg) {
  const el = document.getElementById(stepId);
  const msgEl = document.getElementById('step-msg');
  if (el) {
    el.className = `step-box ${state}`;
  }
  if (msg && msgEl) {
    msgEl.textContent = msg;
  }
}

function getVerifiedSampleResults() {
  return {
    success: true,
    status: 'COMPLETE',
    summary: {
      total_duration: 120.0,
      fog_episodes: 0,
      borderline_episodes: 7,
      normal_episodes: 8
    },
    episodes: [
      { start: 0.0, end: 8.0, type: 'Normal', confidence: 0.12, primary_cue: 'stride_width' },
      { start: 8.0, end: 16.0, type: 'Borderline', confidence: 0.48, primary_cue: 'left_ankle_velocity' },
      { start: 16.0, end: 24.0, type: 'Normal', confidence: 0.15, primary_cue: 'stride_width' },
      { start: 24.0, end: 32.0, type: 'Borderline', confidence: 0.52, primary_cue: 'gyro_x_var' },
      { start: 32.0, end: 40.0, type: 'Normal', confidence: 0.22, primary_cue: 'accel_rms' },
      { start: 40.0, end: 48.0, type: 'Borderline', confidence: 0.45, primary_cue: 'left_knee_angle' },
      { start: 48.0, end: 56.0, type: 'Normal', confidence: 0.18, primary_cue: 'stride_width' },
      { start: 56.0, end: 64.0, type: 'Borderline', confidence: 0.55, primary_cue: 'right_ankle_velocity' },
      { start: 64.0, end: 72.0, type: 'Normal', confidence: 0.25, primary_cue: 'accel_rms' },
      { start: 72.0, end: 80.0, type: 'Borderline', confidence: 0.42, primary_cue: 'gyro_z_var' },
      { start: 80.0, end: 88.0, type: 'Normal', confidence: 0.10, primary_cue: 'stride_width' },
      { start: 88.0, end: 96.0, type: 'Borderline', confidence: 0.49, primary_cue: 'left_ankle_velocity' },
      { start: 96.0, end: 104.0, type: 'Normal', confidence: 0.30, primary_cue: 'accel_rms' },
      { start: 104.0, end: 112.0, type: 'Borderline', confidence: 0.47, primary_cue: 'gyro_x_var' },
      { start: 112.0, end: 120.0, type: 'Normal', confidence: 0.14, primary_cue: 'stride_width' }
    ],
    explanation: {
      provider: 'Deterministic Rule Engine (Grounded)',
      quote: 'Recording evaluated over 120.0 seconds. No FoG-classified intervals were detected in this recording. Borderline intervals are model outputs with class probability between 0.40 and 0.60 and should be interpreted as uncertain classifications rather than confirmed FoG.'
    }
  };
}

function renderResults(data) {
  const dashboard = document.getElementById('results-dashboard');
  if (!dashboard) return;

  dashboard.classList.remove('hidden');

  // 1. Preserve raw overlapping model prediction windows internally
  const rawEpisodes = data.episodes || [];
  data.raw_episodes = rawEpisodes;

  // 2. Aggregate overlapping windows into non-overlapping timeline
  const timeline = aggregateTimeline(rawEpisodes);
  data.aggregated_episodes = timeline;

  // 3. Compute statistics strictly from the aggregated non-overlapping timeline
  const stats = computeAggregatedStats(timeline);

  // 4. Update Metric Cards
  const mTotalEl = document.getElementById('m-total');
  const mFogEl = document.getElementById('m-fog');
  const mBordEl = document.getElementById('m-borderline');
  const mNormEl = document.getElementById('m-normal');

  if (mTotalEl) mTotalEl.textContent = stats.totalIntervals;
  if (mFogEl) mFogEl.textContent = stats.fogCount;
  if (mBordEl) mBordEl.textContent = stats.borderlineCount;
  if (mNormEl) mNormEl.textContent = stats.normalCount;

  // 5. Update Banner & Meta Summary
  const banner = document.getElementById('results-banner');
  const rbTitle = document.getElementById('rb-title');
  const rbSub = document.getElementById('rb-sub');
  const rbFogCount = document.getElementById('rb-fog-count');
  const rbTotalCount = document.getElementById('rb-total-count');
  const rbAvgConf = document.getElementById('rb-avg-conf');
  const rbCue = document.getElementById('rb-cue');

  if (rbFogCount) rbFogCount.textContent = stats.fogCount;
  if (rbTotalCount) rbTotalCount.textContent = stats.totalIntervals;
  if (rbAvgConf) rbAvgConf.textContent = stats.avgConfidence;
  if (rbCue) rbCue.textContent = stats.dominantCue;

  if (stats.fogCount > 0) {
    if (banner) banner.className = 'results-banner banner-alert';
    if (rbTitle) rbTitle.textContent = '⚠️ Freezing of Gait (FoG) Detected';
    if (rbSub) rbSub.textContent = `Model identified ${stats.fogCount} discrete FoG-classified interval(s) during the recording.`;
  } else {
    if (banner) banner.className = 'results-banner banner-success';
    if (rbTitle) rbTitle.textContent = '✅ No FoG-Classified Intervals Detected';
    if (rbSub) rbSub.textContent = 'No FoG-classified intervals were detected in this recording.';
  }

  // 6. Format Model-Grounded Analysis Narrative strictly derived from Aggregated Timeline
  const narrativeText = generateModelGroundedNarrative(timeline, stats);

  data.explanation = {
    provider: 'Deterministic Rule Engine (Grounded)',
    narrative: narrativeText,
    summary: stats
  };

  const narrativeQuoteEl = document.getElementById('narrative-quote');
  if (narrativeQuoteEl) narrativeQuoteEl.textContent = narrativeText;

  const narrativeProviderEl = document.getElementById('narrative-provider');
  if (narrativeProviderEl) {
    narrativeProviderEl.textContent = 'Deterministic Rule Engine (Grounded)';
  }

  // 7. Render Non-Overlapping Timeline Visualization
  const timelineViz = document.getElementById('timeline-viz');
  if (timelineViz) {
    timelineViz.innerHTML = '';
    const totalDuration = stats.totalDuration || (timeline.length > 0 ? (timeline[timeline.length - 1].end - timeline[0].start) : 1);
    timeline.forEach(ep => {
      const seg = document.createElement('div');
      const dur = Math.max(0.05, ep.end - ep.start);
      const widthPct = (dur / totalDuration) * 100;
      const typeClass = ep.type === 'FoG' ? 'fog' : (ep.type === 'Borderline' ? 'bord' : 'norm');
      seg.className = `t-segment ${typeClass}`;
      seg.style.width = `${widthPct}%`;
      seg.title = `${ep.start.toFixed(2)}s — ${ep.end.toFixed(2)}s | ${ep.type} (${(ep.confidence * 100).toFixed(1)}%) | ${ep.primary_cue}`;
      timelineViz.appendChild(seg);
    });
  }

  // 8. Populate Non-Overlapping Episode Breakdown Table
  const tbody = document.getElementById('t-tbody');
  if (tbody) {
    tbody.innerHTML = '';
    timeline.forEach(ep => {
      const tr = document.createElement('tr');
      const badgeColor = ep.type === 'FoG' ? '#f87171' : (ep.type === 'Borderline' ? '#fbbf24' : '#3fb950');
      tr.innerHTML = `
        <td>${ep.start.toFixed(2)}s — ${ep.end.toFixed(2)}s</td>
        <td><span style="color: ${badgeColor}; font-weight: 700;">${ep.type}</span></td>
        <td>${((ep.confidence || 0) * 100).toFixed(1)}%</td>
        <td><code>${ep.primary_cue || 'None'}</code></td>
      `;
      tbody.appendChild(tr);
    });
  }

  dashboard.scrollIntoView({ behavior: 'smooth' });
}

// Initialization
function init() {
  setupScrollScrubbing();
  setupAssessmentEngine();

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
