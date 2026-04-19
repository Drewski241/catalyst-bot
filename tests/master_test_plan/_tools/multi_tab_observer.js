// Multi-tab observer — paste into DevTools Console
// ==================================================
// Snapshots the state visible on every Dashboard / Offers / PnL / Intel /
// Logs / Settings tab in one pass, without the operator having to click
// through them manually. Produces a single JSON blob that can be diffed
// before/after a trigger action (e.g. for Layer 6 live-fire checks).
//
// Usage in a Layer 6 slice:
//   1. Load http://127.0.0.1:5000 in Chrome, open DevTools → Console.
//   2. Paste the whole contents of this file, then press Enter.
//   3. Run:   mtoSnapshot('before')
//   4. Perform the trigger (take-offer, TibetSwap swap, etc.).
//   5. Wait the slice's observation window.
//   6. Run:   mtoSnapshot('after')
//   7. Run:   mtoDiff()  → prints every field that changed + timing.
//
// The snapshot includes: key stats from every tab, the liquidity block,
// any visible toast/banner, and a SSE event capture. Nothing is modified
// on the page — all calls are read-only.
//
// NO DEPENDENCIES — plain vanilla browser JS. Only reads DOM + window
// globals the bot's GUI already exposes (bot_state, currentCAT, etc.)

(function () {
    'use strict';

    // Snapshots live on window so they survive navigation across tabs
    // (we can't use let/const at top level if we want reassignment to
    // persist through paste-reloads).
    window._mtoSnapshots = window._mtoSnapshots || {};
    window._mtoSseBuffer = window._mtoSseBuffer || [];
    window._mtoSseTap    = window._mtoSseTap    || null;

    // ---- SSE event tap ----------------------------------------------
    // When first loaded, wire a passive listener that records every
    // event emitted over /api/events into a ring buffer so we can
    // correlate what the server told us vs what the UI rendered.
    function _startSseTap() {
        if (window._mtoSseTap) return; // already running
        try {
            const es = new EventSource('/api/events');
            es.onmessage = (e) => {
                try {
                    const parsed = JSON.parse(e.data);
                    window._mtoSseBuffer.push({ t: Date.now(), msg: parsed });
                    if (window._mtoSseBuffer.length > 500) {
                        window._mtoSseBuffer.shift();
                    }
                } catch (err) { /* non-JSON payload, ignore */ }
            };
            es.onerror = () => { /* Transparent reconnect — don't spam */ };
            window._mtoSseTap = es;
            console.log('[MTO] SSE tap started on /api/events');
        } catch (err) {
            console.warn('[MTO] SSE tap failed:', err);
        }
    }

    // ---- Safe readers -----------------------------------------------
    // Every getter has a fallback so a missing / renamed element never
    // throws and kills the whole snapshot.
    const g = (id) => document.getElementById(id);
    const txt = (id) => { const e = g(id); return e ? (e.textContent || '').trim() : null; };
    const val = (id) => { const e = g(id); return e ? e.value : null; };
    const cnt = (sel) => document.querySelectorAll(sel).length;
    const cssDisplay = (id) => {
        const e = g(id); if (!e) return 'missing';
        return window.getComputedStyle(e).display;
    };

    // ---- Snapshotters per tab ---------------------------------------
    function _dashboardState() {
        return {
            startupGuideVisible: cssDisplay('startupGuide') !== 'none',
            totalFills: txt('statsTotalFills') || txt('dashFills') || null,
            lastFillAgo: txt('lastFillAgoDashboard') || null,
            ladderActiveCount: txt('ladderActiveCount') || null,
            ladderTargetCount: txt('ladderTargetCount') || null,
            liquidityStripVisible: cssDisplay('liquidityModeStrip') !== 'none',
            liquidityBadgeText: txt('liquidityModeBadgeText'),
            liquidityParkedVisible: cssDisplay('liquidityModeParkedBanner') !== 'none',
            liquidityParkedTitle: txt('liquidityModeParkedTitle'),
            statusBadge: txt('statusBadge') || txt('botStatusBadge') || null,
        };
    }

    function _offersState() {
        // Row count in each sub-tab
        const active = document.querySelectorAll('#activeTab tbody tr').length;
        const history = document.querySelectorAll('#historyTab tbody tr').length;
        const topActive = document.querySelector('#activeTab tbody tr');
        return {
            activeCount: active,
            historyCount: history,
            topActiveTradeId: topActive ? (topActive.dataset.tradeId || null) : null,
            topActiveText: topActive ? topActive.textContent.trim().slice(0, 200) : null,
        };
    }

    function _pnlState() {
        return {
            realised: txt('pnlRealised'),
            roundTrips: txt('pnlRoundTrips'),
            winRate: txt('pnlWinRate'),
            totalFills: txt('pnlTotalFills'),
            fillRate: txt('pnlFillRate'),
            buySellSplit: txt('pnlBuySellSplit'),
            volumeXch: txt('pnlVolumeXch'),
            volumeCat: txt('pnlVolumeCat'),
            buyVolumeXch: txt('pnlBuyVolumeXch'),
            buyVolumeCat: txt('pnlBuyVolumeCat'),
            sellVolumeXch: txt('pnlSellVolumeXch'),
            sellVolumeCat: txt('pnlSellVolumeCat'),
            netXchFlow: txt('pnlNetXchFlow'),
            netCatFlow: txt('pnlNetCatFlow'),
            avgFillSize: txt('pnlAvgFillSize'),
            avgTripPnl: txt('pnlAvgTripPnl'),
            avgTripTime: txt('pnlAvgTripTime'),
            netPosition: txt('invNetPosition'),
            maxPosition: txt('invMaxPosition'),
            positionFillWidth: (() => { const e = g('invPositionFill'); return e ? e.style.width : null; })(),
            modeBannerVisible: cssDisplay('pnlModeBanner') !== 'none',
            modeBannerTitle: txt('pnlModeBannerTitle'),
            sniperTotal: txt('sniperTotal'),
            sniperGapProbes: txt('sniperGapProbes'),
            sniperSkipped: txt('sniperSkipped'),
            circuitBreakerVisible: cssDisplay('circuitBreakerPanel') !== 'none',
            circuitBreakerReason: txt('circuitBreakerReason'),
        };
    }

    function _intelState() {
        return {
            activeViewId: document.querySelector('.v4-view.active')?.id || null,
            // Pick up major intel cards if they exist; generic read since
            // the Intel tab structure evolves.
            cardTexts: Array.from(document.querySelectorAll('#v4View-intel .v4-hero-value'))
                .map(e => (e.textContent || '').trim())
                .slice(0, 20),
        };
    }

    function _logsState() {
        const feed = document.querySelector('#logsFeed, .log-feed, #v4View-logs');
        if (!feed) return { available: false };
        const rows = feed.querySelectorAll('.log-row, .log-entry, li');
        const lastRow = rows[rows.length - 1];
        return {
            available: true,
            rowCount: rows.length,
            lastRowText: lastRow ? lastRow.textContent.trim().slice(0, 200) : null,
            lastRowTime: lastRow ? (lastRow.dataset.timestamp || null) : null,
        };
    }

    function _settingsState() {
        return {
            liquidityMode: (typeof getLiquidityMode === 'function') ? getLiquidityMode() : null,
            bodyLiquidityClass: document.body.className.split(' ')
                .find(c => c.startsWith('liquidity-mode-')) || null,
            reverseBuyReversedChecked: g('configBuyLadderReversed')?.checked ?? null,
            sniperEnabledChecked: g('configSniperEnabled')?.checked ?? null,
            smartDefaultsTitle: txt('smartDefaultsTitle'),
            pendingChangesBannerVisible: cssDisplay('settingsPendingBanner') !== 'none',
            lockedBannerVisible: cssDisplay('settingsLockedBanner') !== 'none',
        };
    }

    function _apiSnapshot() {
        // Fire off /api/status and /api/pnl in parallel; return promises.
        // These are included in the full snapshot via a separate async
        // capture path (see mtoSnapshot below).
        return Promise.all([
            fetch('/api/status', { cache: 'no-store' }).then(r => r.json()).catch(() => ({ error: 'fetch_failed' })),
            fetch('/api/pnl',    { cache: 'no-store' }).then(r => r.json()).catch(() => ({ error: 'fetch_failed' })),
            fetch('/api/offers', { cache: 'no-store' }).then(r => r.json()).catch(() => ({ error: 'fetch_failed' })),
        ]).then(([status, pnl, offers]) => ({ status, pnl, offers }));
    }

    // ---- Public API -------------------------------------------------
    // mtoSnapshot('label')  — capture everything, stash under label
    // mtoDiff()             — diff 'before' vs 'after'
    // mtoSseTap()           — explicit start (auto on first snapshot)
    // mtoSse()              — dump recent SSE events since last snapshot

    window.mtoSnapshot = async function mtoSnapshot(label) {
        _startSseTap();
        const t = Date.now();
        const apiBlob = await _apiSnapshot();
        const snapshot = {
            label,
            captured_at_ms: t,
            captured_at_iso: new Date(t).toISOString(),
            dashboard: _dashboardState(),
            offers: _offersState(),
            pnl: _pnlState(),
            intel: _intelState(),
            logs: _logsState(),
            settings: _settingsState(),
            api: apiBlob,
            sse_buffer_size: window._mtoSseBuffer.length,
        };
        window._mtoSnapshots[label] = snapshot;
        console.log(`[MTO] snapshot "${label}" captured at ${snapshot.captured_at_iso}`);
        console.log(snapshot);
        return snapshot;
    };

    window.mtoDiff = function mtoDiff(a, b) {
        a = a || 'before';
        b = b || 'after';
        const sa = window._mtoSnapshots[a];
        const sb = window._mtoSnapshots[b];
        if (!sa || !sb) {
            console.error(`[MTO] missing snapshot(s): need both "${a}" and "${b}" before diff`);
            return null;
        }
        const diff = {};
        const walk = (pa, pb, path) => {
            if (pa === pb) return;
            if (typeof pa !== 'object' || pa === null || typeof pb !== 'object' || pb === null) {
                diff[path] = { before: pa, after: pb };
                return;
            }
            const keys = new Set([...Object.keys(pa || {}), ...Object.keys(pb || {})]);
            for (const k of keys) {
                walk(pa?.[k], pb?.[k], path ? `${path}.${k}` : k);
            }
        };
        walk(sa, sb, '');
        const elapsed = sb.captured_at_ms - sa.captured_at_ms;
        console.log(`[MTO] ${a} → ${b} — ${elapsed} ms elapsed, ${Object.keys(diff).length} fields changed`);
        console.log(diff);
        return { elapsed_ms: elapsed, changed: diff };
    };

    window.mtoSse = function mtoSse(sinceMs) {
        const buf = window._mtoSseBuffer;
        const cutoff = sinceMs || (window._mtoSnapshots.before?.captured_at_ms || 0);
        const recent = buf.filter(e => e.t >= cutoff);
        const byType = {};
        for (const e of recent) {
            const t = (e.msg && e.msg.type) || 'unknown';
            byType[t] = (byType[t] || 0) + 1;
        }
        console.log(`[MTO] ${recent.length} SSE events since ${new Date(cutoff).toISOString()}:`, byType);
        return recent;
    };

    // Start the SSE tap immediately so events are captured from paste time
    _startSseTap();

    console.log('[MTO] ready. Usage: mtoSnapshot("before") → trigger → mtoSnapshot("after") → mtoDiff()');
})();
