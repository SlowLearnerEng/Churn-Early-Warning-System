/* ============================================
   Churn Intelligence Platform — Views (Part 2)
   Seller 360, Cohorts, Interventions, Init
   (Rebuilt for real IndiaMART data)
   ============================================ */

/* ---- Seller 360 Picker ---- */
function renderSellerPicker(query) {
    const dropdown = document.getElementById('s360-dropdown');
    const q = (query || '').toLowerCase().trim();
    let list = DATA.sellers.slice().sort((a, b) => b.risk_score - a.risk_score);
    if (q) {
        list = list.filter(s =>
            s.seller_id.toLowerCase().includes(q) ||
            (s.seller_name || '').toLowerCase().includes(q) ||
            (s.company_name || '').toLowerCase().includes(q) ||
            (s.city || '').toLowerCase().includes(q) ||
            (s.package || '').toLowerCase().includes(q)
        );
    }
    const shown = list.slice(0, 12);
    const header = q ? `${list.length} result${list.length !== 1 ? 's' : ''}` : 'Top risk sellers';
    if (shown.length === 0) {
        dropdown.innerHTML = '<div class="log-empty" style="padding:20px">No sellers match your search</div>';
    } else {
        dropdown.innerHTML = `
            <div class="s360-dropdown-header">${header}</div>
            ${shown.map(s => `
                <div class="s360-row" onmousedown="selectSeller360('${s.seller_id}')">
                    <span class="s360-cell s360-cell-name">
                        <strong>${s.seller_id}</strong>
                        <span class="s360-company">${s.company_name || s.seller_name}</span>
                    </span>
                    <span class="s360-cell">${s.package}</span>
                    <span class="s360-cell">${s.city}</span>
                    <span class="s360-cell">${bandChip(s.risk_band)} <span style="font-size:0.76rem;color:var(--text-secondary)">${s.risk_score.toFixed(0)}</span></span>
                    <span class="s360-cell"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity:0.4"><polyline points="9 18 15 12 9 6"/></svg></span>
                </div>
            `).join('')}
            ${list.length > 12 ? `<div class="log-empty" style="padding:10px;font-size:0.74rem">${list.length - 12} more — type to narrow results</div>` : ''}
        `;
    }
    dropdown.classList.add('open');
}

function selectSeller360(sellerId) {
    const dropdown = document.getElementById('s360-dropdown');
    const searchEl = document.getElementById('s360-search');
    dropdown.classList.remove('open');
    const s = DATA.sellers.find(x => x.seller_id === sellerId);
    if (s) searchEl.value = `${s.seller_id} — ${s.company_name || s.seller_name}`;
    openSeller360(sellerId);
}

function initSellerPicker() {
    const searchEl = document.getElementById('s360-search');
    const dropdown = document.getElementById('s360-dropdown');
    const wrap = document.getElementById('s360-search-wrap');
    searchEl.addEventListener('focus', () => renderSellerPicker(searchEl.value));
    searchEl.addEventListener('input', () => renderSellerPicker(searchEl.value));
    document.addEventListener('click', (e) => {
        if (!wrap.contains(e.target)) dropdown.classList.remove('open');
    }, true);
}

/* ============================================
   Alert Tab Helpers
   ============================================ */

function hashStr(str) {
    let h = 0;
    for (let i = 0; i < str.length; i++) h = (Math.imul(31, h) + str.charCodeAt(i)) | 0;
    return Math.abs(h);
}

function seededRand(seed) {
    let s = (seed % 2147483647) || 1;
    return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}

function generateWeeklyData(s) {
    const rnd = seededRand(hashStr(s.seller_id));
    const trend = s.health_trend || [];
    const m2 = trend[trend.length - 1] || {};
    const m1 = trend[trend.length - 2] || m2;
    const isAtRisk = ['high', 'critical'].includes(s.risk_band);

    const enqSlope = ((m2.enquiries || 0) - (m1.enquiries || 0)) / 8;
    const blSlope  = ((m2.buyleads || 0) - (m1.buyleads || 0)) / 8;
    const pkpSlope = ((m2.call_pickup_pct || 0) - (m1.call_pickup_pct || 0)) / 8;
    const actSlope = ((m2.lms_active_days || 0) - (m1.lms_active_days || 0)) / 8;

    const baseEnq = ((m2.enquiries || s.total_enquiries_30d || 20)) / 4;
    const baseBL  = ((m2.buyleads || Math.round((s.total_enquiries_30d || 20) * 0.4))) / 4;
    const basePkp = (m2.call_pickup_pct || s.call_pickup_pct_30d || 0.55) * 100;
    const baseAct = (m2.lms_active_days || 20) / 4;

    return Array.from({ length: 8 }, (_, i) => {
        const offset = i - 7;
        const noise = 0.88 + rnd() * 0.24;
        // accelerate visible decline in most recent 2 weeks for at-risk sellers
        const recMul = isAtRisk && i >= 6 ? (i === 7 ? 0.68 : 0.82) : 1;
        return {
            label: i === 7 ? 'This Wk' : i === 6 ? 'Last Wk' : `W-${7 - i}`,
            enq:    Math.max(0, Math.round((baseEnq + enqSlope * offset) * noise * recMul)),
            bl:     Math.max(0, Math.round((baseBL  + blSlope  * offset) * noise * recMul)),
            pickup: Math.min(100, Math.max(0, Math.round((basePkp + pkpSlope * offset * 100) * (0.92 + rnd() * 0.16) * recMul))),
            active: Math.max(0, Math.round((baseAct + actSlope * offset) * noise * recMul)),
        };
    });
}

function generateAlerts(s) {
    const alerts = [];
    const trend = s.health_trend || [];
    const last = trend[trend.length - 1] || {};
    const prev = trend[trend.length - 2] || last;

    // 1. Enquiry volume drop
    if (prev.enquiries > 0) {
        const drop = (prev.enquiries - last.enquiries) / prev.enquiries;
        if (drop > 0.1) alerts.push({
            type: 'activity_decline', icon: '📉',
            severity: drop > 0.35 ? 'critical' : drop > 0.2 ? 'high' : 'medium',
            title: 'Buyer Engagement Drop',
            message: `Enquiry volume dropped ${(drop*100).toFixed(0)}% this month vs last month.`,
            detail: `${prev.enquiries} enq last month → ${last.enquiries} this month. Buyers may be sourcing elsewhere.`,
            metric: `−${(drop*100).toFixed(0)}%`
        });
    }

    // 2. Call pickup decline
    if (prev.call_pickup_pct > 0 && last.call_pickup_pct < prev.call_pickup_pct - 0.07) {
        const pd = prev.call_pickup_pct - last.call_pickup_pct;
        alerts.push({
            type: 'activity_decline', icon: '📞',
            severity: pd > 0.2 ? 'high' : 'medium',
            title: 'Call Pickup Rate Declining',
            message: `Pickup fell ${(prev.call_pickup_pct*100).toFixed(0)}% → ${(last.call_pickup_pct*100).toFixed(0)}% — ${(pd*100).toFixed(0)}pp drop.`,
            detail: 'Missed calls signal disengagement. Buyers who cannot reach sellers approach competitors next.',
            metric: `−${(pd*100).toFixed(0)}pp`
        });
    }

    // 3. Missed opportunities — untouched leads
    const missed = Math.round((s.total_enquiries_30d || 0) * (s.untouched_pct || 0));
    if (missed > 2) alerts.push({
        type: 'missed_opportunities', icon: '⚡',
        severity: missed > 15 ? 'critical' : missed > 7 ? 'high' : 'medium',
        title: 'Missed Lead Responses',
        message: `${missed} buyers did not receive a response this month.`,
        detail: `${((s.untouched_pct||0)*100).toFixed(0)}% of leads are untouched. Each unresponded lead is a potential order lost to a competitor.`,
        metric: `${missed} leads`
    });

    // 4. Visibility drop — low catalogue rank
    const lowRank = (s.catalogue || []).filter(c => parseInt(c.rank) > 50).length;
    if (lowRank > 0) alerts.push({
        type: 'visibility_drop', icon: '👁',
        severity: lowRank >= 3 ? 'high' : 'medium',
        title: 'Product Visibility Declining',
        message: `Ranking below page 1 in ${lowRank} product categor${lowRank === 1 ? 'y' : 'ies'}.`,
        detail: 'Products not on first-page results reduce organic buyer discovery and enquiry volume significantly.',
        metric: `${lowRank} categories`
    });

    // 5. Catalog staleness signal from reason codes
    if ((s.reason_codes || []).some(r => r.code === 'catalog_staleness')) alerts.push({
        type: 'visibility_drop', icon: '📦',
        severity: 'medium',
        title: 'Catalog Not Updated Recently',
        message: 'Product listings have not been refreshed in over 120 days.',
        detail: 'Stale catalogs lose search ranking and buyer trust. Fresh listings improve visibility by up to 40%.',
        metric: '120+ days'
    });

    // 6. Conversion risk — slow response / low pickup
    if ((s.call_pickup_pct_30d || 0) < 0.6 || (s.untouched_pct || 0) > 0.2) {
        const lost = Math.round((s.total_enquiries_30d || 0) * (1 - (s.call_pickup_pct_30d || 0.5)) * 0.18);
        alerts.push({
            type: 'conversion_risk', icon: '🔄',
            severity: (s.call_pickup_pct_30d || 0) < 0.4 ? 'critical' : 'high',
            title: 'Response Delay Impacting Conversion',
            message: `~${lost} leads estimated lost to slow response. Pickup at ${((s.call_pickup_pct_30d||0)*100).toFixed(0)}%.`,
            detail: 'Sellers who respond within 1 hour convert 3× more leads. Industry benchmark: respond within 30 minutes.',
            metric: `${((s.call_pickup_pct_30d||0)*100).toFixed(0)}% pickup`
        });
    }

    // 7. Renewal risk — negative intent
    if ((s.negative_intent_pct || 0) > 0.15) alerts.push({
        type: 'renewal_risk', icon: '🔔',
        severity: (s.negative_intent_pct || 0) > 0.35 ? 'critical' : 'high',
        title: 'Renewal Risk Signal Detected',
        message: `${((s.negative_intent_pct||0)*100).toFixed(0)}% of recent calls show disengagement or cancellation intent.`,
        detail: 'Sellers with similar patterns reduce renewal rates by 35%. Proactive ROI-focused outreach recommended now.',
        metric: `${((s.negative_intent_pct||0)*100).toFixed(0)}% neg.`
    });

    // 8. Low rating
    if ((s.overall_rating || 0) > 0 && s.overall_rating < 3.8) alerts.push({
        type: 'conversion_risk', icon: '⭐',
        severity: s.overall_rating < 3.0 ? 'critical' : 'medium',
        title: 'Low Rating Reducing Buyer Trust',
        message: `Rating ${s.overall_rating.toFixed(1)}★ is below platform average (4.2★).`,
        detail: 'Buyers filter by rating. Low-rated sellers receive 30% fewer organic enquiries. Respond to all negative reviews.',
        metric: `${s.overall_rating.toFixed(1)}★`
    });

    // 9. Open tickets
    if ((s.open_tickets || 0) >= 2) alerts.push({
        type: 'conversion_risk', icon: '🎫',
        severity: s.open_tickets >= 4 ? 'high' : 'medium',
        title: 'Unresolved Support Tickets',
        message: `${s.open_tickets} open tickets may be blocking account performance.`,
        detail: 'Unresolved issues affect listing visibility and account health score on the platform.',
        metric: `${s.open_tickets} tickets`
    });

    const order = { critical: 0, high: 1, medium: 2 };
    return alerts.sort((a, b) => order[a.severity] - order[b.severity]);
}

function generateRecoveryOpportunities(s) {
    const rnd = seededRand(hashStr(s.seller_id + 'opp'));
    const opps = [];

    const waiting = Math.round((s.total_enquiries_30d || 0) * (s.untouched_pct || 0));
    if (waiting > 0) opps.push({
        icon: '💬', title: 'Buyers Awaiting Quotation', count: waiting,
        value: 'Time-critical', action: 'Respond Now', urgency: 'critical',
        detail: `${waiting} buyers sent enquiries with no response — likely comparing quotes from competitors right now.`
    });

    const reopen = Math.max(2, Math.round(3 + rnd() * 5));
    opps.push({
        icon: '🔄', title: 'Conversations Worth Reopening', count: reopen,
        value: 'Medium LTV', action: 'Follow Up', urgency: 'medium',
        detail: `${reopen} buyers interacted 30–60 days ago with no recent activity — a follow-up message often re-ignites interest.`
    });

    const inactiveRepeat = Math.max(2, Math.round(3 + rnd() * 8));
    opps.push({
        icon: '🔁', title: 'Inactive Repeat Buyers', count: inactiveRepeat,
        value: 'High LTV', action: 'Re-engage', urgency: 'high',
        detail: `${inactiveRepeat} repeat buyers haven't placed an enquiry in 45+ days. Repeat buyers convert at 4× the first-time buyer rate.`
    });

    opps.push({
        icon: '📈', title: 'Seasonal Demand Spike Ahead', count: Math.round(2 + rnd() * 3),
        value: 'High opportunity', action: 'Update Catalog', urgency: 'medium',
        detail: 'Category demand is projected to rise in the next 3–4 weeks. Refreshing catalog now positions you to capture this uplift.'
    });

    const staleProds = Math.round((s.catalogue || []).reduce((a, c) => a + (c.products || 0), 0) * 0.3);
    if (staleProds > 2) opps.push({
        icon: '🖼', title: 'Products Need Image Refresh', count: staleProds,
        value: 'Visibility boost', action: 'Update Images', urgency: 'medium',
        detail: `~${staleProds} products have not had image updates in 90+ days. Fresh images improve click-through rate by up to 25%.`
    });

    return opps;
}

function generateAINarrative(s, alerts) {
    const top = alerts.slice(0, 3);
    const phraseMap = {
        activity_decline: 'response follow-ups and call pickup have declined',
        missed_opportunities: 'incoming leads are going unresponded, losing orders to competitors',
        visibility_drop: 'product rankings have slipped, reducing organic buyer discovery',
        conversion_risk: 'slow response times are converting fewer enquiries into orders',
        renewal_risk: 'recent call patterns signal disengagement from the platform',
    };
    const phrases = top.map(a => phraseMap[a.type] || a.title.toLowerCase()).filter(Boolean);

    const narrative = phrases.length
        ? `Activity declined mainly because: ${phrases.join('; and ')}.`
        : 'Activity metrics are within acceptable range, but proactive monitoring is recommended.';

    const actions = [];
    const missedAlert = alerts.find(a => a.type === 'missed_opportunities');
    if (missedAlert) {
        const n = Math.round((s.total_enquiries_30d || 0) * (s.untouched_pct || 0));
        actions.push(`Reply to ${n} pending buyers — respond within 30 minutes for maximum conversion`);
    }
    if (alerts.find(a => a.type === 'visibility_drop' || (a.title || '').includes('Catalog')))
        actions.push('Add 5 new product listings with high-quality images and detailed descriptions');
    if (alerts.find(a => a.type === 'activity_decline')) {
        const n = Math.max(5, Math.round((s.total_enquiries_30d || 20) * 0.15));
        actions.push(`Follow up with ${n} buyers who showed interest in the last 30 days`);
    }
    if ((s.reviews || []).some(r => r.responded === 'No'))
        actions.push('Respond to all unanswered negative reviews to improve your trust score');
    if (alerts.find(a => a.type === 'conversion_risk'))
        actions.push('Enable call forwarding or assign a backup contact to reduce missed pickup rate');
    if (!actions.some(a => a.includes('product')))
        actions.push('Update catalog images for your top 3 categories to improve search ranking');

    return { narrative, actions: actions.slice(0, 5) };
}

/* ============================================
   Peer Benchmarking
   ============================================ */

function generateBenchmarks(s) {
    const peers = DATA.sellers.filter(p => p.category === s.category && p.seller_id !== s.seller_id);
    if (peers.length < 4) return null;

    const vals = (fn) => peers.map(fn).filter(v => v > 0).sort((a, b) => a - b);
    const pct = (arr, p) => arr[Math.max(0, Math.floor(arr.length * p) - 1)] || 0;

    const pickup  = vals(p => p.call_pickup_pct_30d || 0);
    const enq     = vals(p => p.total_enquiries_30d || 0);
    const rating  = vals(p => p.overall_rating || 0);
    const untch   = vals(p => p.untouched_pct || 0);

    return {
        peers: peers.length,
        category: s.category,
        metrics: [
            { label: 'Call Pickup Rate', mine: (s.call_pickup_pct_30d||0)*100, avg: pct(pickup,0.5)*100, top: pct(pickup,0.8)*100, unit: '%', higher: true },
            { label: 'Monthly Enquiries', mine: s.total_enquiries_30d||0, avg: pct(enq,0.5), top: pct(enq,0.8), unit: '', higher: true },
            { label: 'Overall Rating', mine: s.overall_rating||0, avg: pct(rating,0.5), top: pct(rating,0.8), unit: '★', higher: true, decimals: 1 },
            { label: 'Untouched Leads', mine: (s.untouched_pct||0)*100, avg: pct(untch,0.5)*100, top: pct(untch,0.2)*100, unit: '%', higher: false },
        ]
    };
}

function renderBenchmarkSection(s) {
    const bm = generateBenchmarks(s);
    const el = document.getElementById('benchmark-section');
    if (!el) return;
    if (!bm) { el.innerHTML = ''; return; }

    el.innerHTML = `
        <div class="benchmark-block">
            <div class="bm-block-header">
                Category Benchmarking
                <span class="section-sub">${bm.peers} peers in <strong>${bm.category}</strong></span>
            </div>
            <div class="benchmark-grid">
                ${bm.metrics.map(m => {
                    const fmt = (v) => m.decimals ? v.toFixed(m.decimals) : Math.round(v);
                    const topRef = Math.max(m.top, m.mine, 0.1);
                    const myW  = Math.min(100, (m.mine / topRef) * 95);
                    const avgW = Math.min(100, (m.avg  / topRef) * 95);
                    const beating_avg = m.higher ? m.mine >= m.avg : m.mine <= m.avg;
                    const beating_top = m.higher ? m.mine >= m.top : m.mine <= m.top;
                    const statusCls = beating_top ? 'bm-top' : beating_avg ? 'bm-avg' : 'bm-low';
                    const statusLabel = beating_top ? '🏆 Top 20%' : beating_avg ? '✓ Above avg' : '⚠ Below avg';
                    return `
                        <div class="benchmark-card">
                            <div class="bmc-header">
                                <span class="bmc-label">${m.label}</span>
                                <span class="bmc-status ${statusCls}">${statusLabel}</span>
                            </div>
                            <div class="bmc-value-row">
                                <span class="bmc-mine ${statusCls}">${fmt(m.mine)}${m.unit}</span>
                                <span class="bmc-compare">Avg ${fmt(m.avg)}${m.unit} · Top 20% ${fmt(m.top)}${m.unit}</span>
                            </div>
                            <div class="bmc-bar-track">
                                <div class="bmc-bar-fill ${statusCls}" style="width:${myW.toFixed(1)}%"></div>
                                <div class="bmc-avg-marker" style="left:${avgW.toFixed(1)}%" title="Category avg"></div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

/* ---- Seller 360 Detail ---- */
function openSeller360(sellerId) {
    const s = DATA.sellers.find(x => x.seller_id === sellerId);
    if (!s) return;

    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('nav-seller360').classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('panel-seller360').classList.add('active');

    const riskColor = BAND_COLORS[s.risk_band] || '#6366f1';
    const alerts = generateAlerts(s);
    const badgeCls = alerts.some(a => a.severity === 'critical') ? 'critical' : alerts.some(a => a.severity === 'high') ? 'high' : 'medium';
    const dtr = s.days_to_renewal;
    const showRenewalBanner = dtr != null && dtr <= 90 && ['high', 'critical'].includes(s.risk_band);

    const container = document.getElementById('seller360-content');
    container.innerHTML = `
        <div class="seller360-header">
            <div>
                <div class="seller360-title">${s.company_name || s.seller_name}</div>
                <div class="seller360-meta">
                    <div class="seller360-meta-item">ID: <span>${s.seller_id}</span></div>
                    <div class="seller360-meta-item">Owner: <span>${s.seller_name}</span></div>
                    <div class="seller360-meta-item">City: <span>${s.city}, ${s.state}</span></div>
                    <div class="seller360-meta-item">Package: <span>${s.package}</span></div>
                    <div class="seller360-meta-item">Tenure: <span>${s.member_since_years}y member</span></div>
                    <div class="seller360-meta-item">Renewal: <span>${s.subscription_end_date || '—'}</span></div>
                    <div class="seller360-meta-item">Turnover: <span>${s.turnover_range || '—'}</span></div>
                    <div class="seller360-meta-item">GST: <span>${s.gst_verified ? '✓' : '✗'}</span></div>
                </div>
            </div>
            <div style="text-align:center">
                <div style="width:90px;height:90px;position:relative;">
                    <canvas id="score-ring-canvas" width="90" height="90"></canvas>
                    <div class="seller360-score-center" style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">
                        <div style="font-size:1.3rem;font-weight:800;color:${riskColor}">${s.risk_score.toFixed(0)}</div>
                        <div class="seller360-score-label">Risk Score</div>
                    </div>
                </div>
                <div style="margin-top:6px">${bandChip(s.risk_band)}</div>
                <div style="font-size:0.7rem;color:var(--text-secondary);margin-top:4px">Conf: ${(s.confidence*100).toFixed(0)}%</div>
            </div>
        </div>

        ${showRenewalBanner ? `
        <div class="renewal-warning-banner">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
            <strong>Renewal in ${dtr <= 0 ? 'overdue' : dtr + ' days'}</strong>
            — ${s.risk_band.charAt(0).toUpperCase() + s.risk_band.slice(1)} risk of non-renewal detected.
            ${s.revenue_at_risk ? `<span class="renewal-rev-stake">${formatINR(s.revenue_at_risk)} at stake</span>` : ''}
            <button class="btn-view" style="margin-left:auto;font-size:0.72rem" onclick="document.querySelector('[data-tab=renewal]').click()">View Renewal Dashboard →</button>
        </div>
        ` : ''}

        <div class="s360-detail-tabs">
            <button class="s360-detail-tab active" data-s360tab="overview">Overview</button>
            <button class="s360-detail-tab" data-s360tab="alerts">
                Seller Alerts
                ${alerts.length > 0 ? `<span class="s360-alert-badge badge-${badgeCls}">${alerts.length}</span>` : ''}
            </button>
        </div>

        <div class="s360-tab-panel active" id="s360-panel-overview">
            <div class="explanation-cards" id="explanation-cards"></div>
            <div id="benchmark-section"></div>
            <div class="charts-row">
                <div class="chart-card" style="flex:1"><h3>Monthly Trends: BuyLeads & Enquiries</h3><div class="chart-wrap"><canvas id="chart-s360-trends"></canvas></div></div>
                <div class="chart-card" style="flex:1"><h3>Call Pickup Rate Trend</h3><div class="chart-wrap"><canvas id="chart-s360-pickup"></canvas></div></div>
            </div>
            <div class="charts-row">
                <div class="chart-card" style="flex:1">
                    <h3>📞 Recent Calls (${(s.calls||[]).length})</h3>
                    <div class="call-log" id="call-log"></div>
                </div>
                <div class="chart-card" style="flex:1">
                    <h3>⭐ Recent Reviews (${(s.reviews||[]).length})</h3>
                    <div class="review-log" id="review-log"></div>
                </div>
            </div>
            <div class="charts-row">
                <div class="chart-card" style="flex:1">
                    <h3>🎫 Tickets (${(s.tickets||[]).length})</h3>
                    <div class="ticket-log" id="ticket-log"></div>
                </div>
                <div class="chart-card" style="flex:1">
                    <h3>📦 Catalogue</h3>
                    <div class="catalogue-log" id="catalogue-log"></div>
                </div>
            </div>
            <div class="seller360-ai-panel" id="ai-panel"></div>
        </div>

        <div class="s360-tab-panel" id="s360-panel-alerts"></div>
    `;

    // Explanation cards
    const cards = [
        { label: 'Call Pickup (30d)', value: `${(s.call_pickup_pct_30d*100).toFixed(0)}%`, detail: s.call_pickup_pct_30d<0.5?'⚠️ Below threshold':'✓ Acceptable' },
        { label: 'Enquiries (30d)', value: s.total_enquiries_30d, detail: 'Monthly enquiry volume' },
        { label: 'Negative Intent', value: `${(s.negative_intent_pct*100).toFixed(0)}%`, detail: s.negative_intent_pct>0.2?'🔴 High churn signal':'Normal' },
        { label: 'Cancellation Rate', value: `${(s.cancellation_rate*100).toFixed(0)}%`, detail: `${s.cancelled_transactions||0} service cancellations` },
        { label: 'Overall Rating', value: s.overall_rating.toFixed(1), detail: 'Out of 5.0' },
        { label: 'Untouched Leads', value: `${(s.untouched_pct*100).toFixed(0)}%`, detail: s.untouched_pct>0.25?'⚠️ Missing opportunities':'OK' },
        { label: 'Review Response', value: `${(s.low_review_response_rate*100).toFixed(0)}%`, detail: 'Of negative reviews addressed' },
        { label: 'Open Tickets', value: s.open_tickets, detail: s.open_tickets>=2?'⚠️ Unresolved issues':'OK' },
    ];
    document.getElementById('explanation-cards').innerHTML = cards.map(c => `<div class="explanation-card"><div class="ec-label">${c.label}</div><div class="ec-value">${c.value}</div><div class="ec-detail">${c.detail}</div></div>`).join('');
    renderBenchmarkSection(s);

    drawScoreRing('score-ring-canvas', s.risk_score, riskColor);

    // Trend charts
    const trend = s.health_trend || [];
    if (trend.length > 1) {
        const labels = trend.map(t => t.period);
        makeChart('chart-s360-trends', {
            type: 'line', data: { labels,
                datasets: [
                    { label: 'BuyLeads', data: trend.map(t=>t.buyleads), borderColor: '#6366f1', backgroundColor: 'rgba(99,102,241,0.1)', fill: true, tension: 0.4, pointRadius: 3, borderWidth: 2 },
                    { label: 'Enquiries', data: trend.map(t=>t.enquiries), borderColor: '#10b981', tension: 0.4, pointRadius: 3, borderWidth: 2 },
                ] },
            options: trendChartOpts('Volume')
        });
        makeChart('chart-s360-pickup', {
            type: 'line', data: { labels,
                datasets: [{ label: 'Pickup %', data: trend.map(t=>(t.call_pickup_pct*100).toFixed(1)), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.1)', fill: true, tension: 0.4, pointRadius: 3, borderWidth: 2 }] },
            options: trendChartOpts('Pickup %')
        });
    }

    // Call log
    const callLog = document.getElementById('call-log');
    const callArr = s.calls || [];
    if (callArr.length) {
        callLog.innerHTML = callArr.map(c => {
            const intentColor = c.seller_intent === 'High Interest' || c.seller_intent === 'Interested in Renewal' ? 'var(--success)' :
                               c.seller_intent === 'Considering Cancellation' || c.seller_intent === 'Disengaged' ? 'var(--critical)' : 'var(--text-secondary)';
            return `<div class="log-entry">
                <div class="log-header"><span class="log-date">${c.date}</span> <span style="color:${intentColor};font-weight:600;font-size:0.72rem">${c.seller_intent}</span></div>
                <div class="log-meta">${c.buyer} · ${c.product} · ${c.duration}min</div>
                <div class="log-body">${c.summary}</div>
            </div>`;
        }).join('');
    } else { callLog.innerHTML = '<div class="log-empty">No calls recorded</div>'; }

    // Review log
    const reviewLog = document.getElementById('review-log');
    const revArr = s.reviews || [];
    if (revArr.length) {
        reviewLog.innerHTML = `<div style="padding:8px 0 4px;font-size:0.78rem;color:var(--text-secondary)">Overall Rating: <strong style="color:var(--text-primary);font-size:1rem">${s.overall_rating.toFixed(1)}</strong>/5.0</div>` +
            revArr.map(r => `<div class="log-entry">
            <div class="log-header"><span class="log-date">${r.date}</span> <span style="font-size:0.72rem;color:var(--warning);font-weight:600">${r.rating}★</span> <span class="chip chip-reason" style="margin-left:4px">${r.responded==='Yes'?'✓ Responded':'✗ No Response'}</span></div>
            <div class="log-meta">${r.product}</div>
            <div class="log-body">${r.text}</div>
        </div>`).join('');
    } else { reviewLog.innerHTML = '<div class="log-empty">No low-rating reviews</div>'; }

    // Ticket log
    const ticketLog = document.getElementById('ticket-log');
    const tktArr = s.tickets || [];
    if (tktArr.length) {
        ticketLog.innerHTML = '<table class="data-table" style="font-size:0.78rem"><thead><tr><th>Type</th><th>Status</th><th>Risk</th><th>Created</th></tr></thead><tbody>' +
            tktArr.map(t => `<tr><td>${t.type}</td><td>${statusChip(t.status.toLowerCase())}</td><td>${bandChip(t.risk_level.toLowerCase())}</td><td>${t.created}</td></tr>`).join('') +
            '</tbody></table>';
    } else { ticketLog.innerHTML = '<div class="log-empty">No tickets</div>'; }

    // Catalogue
    const catLog = document.getElementById('catalogue-log');
    const catArr = s.catalogue || [];
    if (catArr.length) {
        catLog.innerHTML = '<table class="data-table" style="font-size:0.78rem"><thead><tr><th>Category</th><th>Products</th><th>Rank</th><th>BuyLeads 6M</th></tr></thead><tbody>' +
            catArr.map(c => `<tr><td>${c.category}</td><td>${c.products}</td><td>${c.rank}</td><td>${c.bl_6m}</td></tr>`).join('') +
            '</tbody></table>';
    } else { catLog.innerHTML = '<div class="log-empty">No catalogue data</div>'; }

    // AI Panel
    renderAIPanel(s);

    // Internal tab switching
    let alertsRendered = false;
    container.querySelectorAll('.s360-detail-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            container.querySelectorAll('.s360-detail-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            container.querySelectorAll('.s360-tab-panel').forEach(p => p.classList.remove('active'));
            document.getElementById('s360-panel-' + btn.dataset.s360tab).classList.add('active');
            if (btn.dataset.s360tab === 'alerts' && !alertsRendered) {
                renderAlertTab(s);
                alertsRendered = true;
            }
        });
    });
}

function renderAIPanel(s) {
    const panel = document.getElementById('ai-panel');
    const ai = s.ai_summary;

    if (ai && !ai.fallback && !ai.parse_error) {
        panel.innerHTML = `
            <h3><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 014 4c0 1.95-1.4 3.58-3.25 3.93L12 22"/><path d="M8.56 9.44A4 4 0 1112 6"/></svg> AI Retention Agent <span class="ai-badge">AI</span></h3>
            <div class="ai-section"><div class="ai-section-title">Risk Explanation</div><p>${ai.risk_explanation || ''}</p></div>
            <div class="ai-section"><div class="ai-section-title">Reasons to Stay</div><ul>${(ai.reasons_to_stay||[]).map(r=>`<li>${r}</li>`).join('')}</ul></div>
            <div class="ai-section"><div class="ai-section-title">Recommended Action</div><p>${ai.next_best_action || ''}</p></div>
            <div class="ai-section"><div class="ai-section-title">Sales Opening Line</div><p style="font-style:italic;color:var(--accent)">"${ai.sales_opening_line || ''}"</p></div>
        `;
    } else {
        // Deterministic fallback
        const reasons = (s.reason_codes||[]).map(r=>r.evidence||r.code.replace(/_/g,' ')).join('; ');
        panel.innerHTML = `
            <h3><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 014 4c0 1.95-1.4 3.58-3.25 3.93L12 22"/><path d="M8.56 9.44A4 4 0 1112 6"/></svg> Retention Intelligence <span class="ai-badge" style="background:var(--text-muted)">RULE</span></h3>
            <div class="ai-section"><div class="ai-section-title">Risk Explanation</div>
                <p>Risk is ${s.risk_band} (score ${s.risk_score.toFixed(0)}) because: ${reasons || 'insufficient signal data'}.</p></div>
            <div class="ai-section"><div class="ai-section-title">Recommended Action</div>
                <p>${actionLabel(s.recommended_action)}. Focus on addressing the top risk drivers to improve renewal probability.</p></div>
        `;
    }
}

function drawScoreRing(canvasId, score, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d'), w = canvas.width, h = canvas.height, cx = w/2, cy = h/2, r = 38;
    ctx.clearRect(0,0,w,h);
    ctx.beginPath(); ctx.arc(cx,cy,r,0,Math.PI*2); ctx.strokeStyle='rgba(255,255,255,0.06)'; ctx.lineWidth=6; ctx.stroke();
    ctx.beginPath(); ctx.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+(Math.PI*2*score/100)); ctx.strokeStyle=color; ctx.lineWidth=6; ctx.lineCap='round'; ctx.stroke();
}

function trendChartOpts(yLabel) {
    return {
        responsive: true, maintainAspectRatio: false,
        scales: {
            x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font: { family: 'Inter', size: 10 } } },
            y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font: { family: 'Inter' } }, title: { display: true, text: yLabel, color: '#8b949e', font: { family: 'Inter', size: 11 } } }
        },
        plugins: { legend: { labels: { color: '#8b949e', font: { family: 'Inter', size: 11 }, usePointStyle: true, pointStyleWidth: 8 } } }
    };
}

/* ---- Cohorts ---- */
let currentCohort = 'by_package';

function renderCohorts() {
    const cohort = DATA.cohorts[currentCohort] || {};
    const keys = Object.keys(cohort).sort((a,b) => (cohort[b].avg_risk||0) - (cohort[a].avg_risk||0));
    const titles = { by_package: 'Risk by Package', by_state: 'Risk by State', by_business_type: 'Risk by Business Type', by_turnover: 'Risk by Turnover' };
    document.getElementById('cohort-chart-title').textContent = titles[currentCohort] || 'Cohort';

    const datasets = BAND_ORDER.map(band => ({
        label: band.charAt(0).toUpperCase()+band.slice(1),
        data: keys.map(k => (cohort[k].bands||{})[band]||0),
        backgroundColor: BAND_COLORS[band], borderRadius: 3
    }));

    makeChart('chart-cohort-bars', {
        type: 'bar', data: { labels: keys, datasets },
        options: { responsive: true, maintainAspectRatio: false,
            scales: { x: { stacked: true, grid: { display: false }, ticks: { color: '#8b949e', font: { family: 'Inter', size: 10 }, maxRotation: 45 } },
                      y: { stacked: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font: { family: 'Inter' } } } },
            plugins: { legend: { position: 'bottom', labels: { color: '#8b949e', font: { family: 'Inter', size: 11 }, usePointStyle: true, pointStyleWidth: 8, padding: 12 } } } }
    });

    makeChart('chart-cohort-revenue', {
        type: 'bar', data: { labels: keys, datasets: [{ data: keys.map(k => cohort[k].revenue_at_risk||0), backgroundColor: '#6366f1', borderRadius: 4, borderSkipped: false }] },
        options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            scales: { x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font: { family: 'Inter' }, callback: v => formatINR(v) } },
                      y: { grid: { display: false }, ticks: { color: '#8b949e', font: { family: 'Inter', size: 10 } } } },
            plugins: { legend: { display: false } } }
    });
}

function initCohortTabs() {
    document.querySelectorAll('.cohort-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.cohort-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentCohort = btn.dataset.cohort;
            renderCohorts();
        });
    });
}

/* ---- Interventions ---- */
function renderInterventions() {
    const sellers = DATA.sellers.filter(s => s.action_code);
    const actionCounts = {}, statusCounts = {};
    sellers.forEach(s => {
        actionCounts[s.action_code] = (actionCounts[s.action_code]||0)+1;
        const st = s.action_status||'unknown';
        statusCounts[st] = (statusCounts[st]||0)+1;
    });

    const total = sellers.length, scheduled = statusCounts['scheduled']||0, completed = statusCounts['completed']||0, recommended = statusCounts['recommended']||0;
    const totalRevenue = sellers.reduce((s,x) => s+(x.revenue_at_risk||0), 0);

    document.getElementById('intervention-kpis').innerHTML = [
        { label: 'Total Actions', value: total, sub: 'Across all sellers', cls: 'accent' },
        { label: 'Scheduled', value: scheduled, sub: 'Awaiting execution', cls: 'warning' },
        { label: 'Completed', value: completed, sub: 'Successfully executed', cls: 'success' },
        { label: 'Recommended', value: recommended, sub: 'Pending review', cls: 'accent' },
        { label: 'Revenue Covered', value: formatINR(totalRevenue), sub: 'Under intervention', cls: 'danger' },
    ].map(k => `<div class="kpi-card ${k.cls}"><div class="kpi-label">${k.label}</div><div class="kpi-value">${k.value}</div><div class="kpi-sub">${k.sub}</div></div>`).join('');

    const actionKeys = Object.keys(actionCounts).sort((a,b) => actionCounts[b]-actionCounts[a]);
    makeChart('chart-action-types', {
        type: 'doughnut', data: { labels: actionKeys.map(k => actionLabel(k)),
            datasets: [{ data: actionKeys.map(k => actionCounts[k]), backgroundColor: ['#6366f1','#818cf8','#a5b4fc','#c7d2fe','#e0e7ff','#312e81'], borderWidth: 0, borderRadius: 4 }] },
        options: { cutout: '62%', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#8b949e', font: { family: 'Inter', size: 10 }, padding: 10, usePointStyle: true, pointStyleWidth: 8 } } } }
    });

    const stKeys = Object.keys(statusCounts);
    const stColors = { scheduled: '#f59e0b', completed: '#10b981', recommended: '#6366f1', unknown: '#484f58' };
    makeChart('chart-action-status', {
        type: 'doughnut', data: { labels: stKeys.map(k => k.charAt(0).toUpperCase()+k.slice(1)),
            datasets: [{ data: stKeys.map(k => statusCounts[k]), backgroundColor: stKeys.map(k => stColors[k]||'#484f58'), borderWidth: 0, borderRadius: 4 }] },
        options: { cutout: '62%', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { color: '#8b949e', font: { family: 'Inter', size: 10 }, padding: 10, usePointStyle: true, pointStyleWidth: 8 } } } }
    });

    const sorted = sellers.sort((a,b) => (b.priority_score||0)-(a.priority_score||0));
    document.getElementById('action-body').innerHTML = sorted.slice(0,50).map(s => `
        <tr><td><strong>${s.seller_id}</strong></td><td>${bandChip(s.risk_band)}</td><td><span class="chip chip-action">${actionLabel(s.action_code)}</span></td><td>${s.owner_id||'—'}</td><td>${statusChip(s.action_status)}</td><td>${s.priority_score.toFixed(1)}</td></tr>
    `).join('');
}

/* ---- Seller Alerts Tab ---- */
function renderAlertTab(s) {
    const weeks   = generateWeeklyData(s);
    const alerts  = generateAlerts(s);
    const opps    = generateRecoveryOpportunities(s);
    const ai      = generateAINarrative(s, alerts);

    const thisWk  = weeks[7], lastWk = weeks[6];
    const pctDelta = (curr, prev) => prev > 0 ? ((curr - prev) / prev * 100) : 0;
    const enqD    = pctDelta(thisWk.enq,    lastWk.enq);
    const blD     = pctDelta(thisWk.bl,     lastWk.bl);
    const pkpD    = thisWk.pickup - lastWk.pickup;
    const actD    = thisWk.active - lastWk.active;

    const deltaChip = (v, unit) => {
        const pos = v >= 0;
        return `<span class="delta-chip ${pos ? 'delta-up' : 'delta-down'}">${pos ? '▲' : '▼'} ${Math.abs(v).toFixed(1)}${unit}</span>`;
    };

    const trendCards = [
        { label: 'ENQ Weekly Trend',     curr: thisWk.enq,    prev: lastWk.enq,    dv: enqD,  du: '%',   cid: 'chart-wk-enq',    data: weeks.map(w => w.enq),    color: '#6366f1', unit: '' },
        { label: 'BL Weekly Trend',      curr: thisWk.bl,     prev: lastWk.bl,     dv: blD,   du: '%',   cid: 'chart-wk-bl',     data: weeks.map(w => w.bl),     color: '#10b981', unit: '' },
        { label: 'Pickup % Weekly',      curr: thisWk.pickup, prev: lastWk.pickup, dv: pkpD,  du: 'pp',  cid: 'chart-wk-pickup', data: weeks.map(w => w.pickup), color: '#f59e0b', unit: '%' },
        { label: 'Active Days Weekly',   curr: thisWk.active, prev: lastWk.active, dv: actD,  du: 'days',cid: 'chart-wk-active', data: weeks.map(w => w.active), color: '#a78bfa', unit: '' },
    ];
    const wkLabels = weeks.map(w => w.label);
    const topSev   = alerts.some(a => a.severity === 'critical') ? 'critical' : alerts.some(a => a.severity === 'high') ? 'high' : 'medium';

    document.getElementById('s360-panel-alerts').innerHTML = `
        <div class="alert-section-title">
            Weekly Activity Trends
            <span class="section-sub">Last 8 weeks · week-over-week comparison</span>
        </div>
        <div class="weekly-trends-grid">
            ${trendCards.map(tc => `
                <div class="weekly-trend-card">
                    <div class="wtc-header">
                        <span class="wtc-label">${tc.label}</span>
                        ${deltaChip(tc.dv, tc.du)}
                    </div>
                    <div class="wtc-values">
                        <span class="wtc-current">${tc.curr}${tc.unit}</span>
                        <span class="wtc-vs">vs ${tc.prev}${tc.unit} last wk</span>
                    </div>
                    <div class="wtc-chart-wrap"><canvas id="${tc.cid}"></canvas></div>
                </div>
            `).join('')}
        </div>

        <div class="alert-section-title" style="margin-top:28px">
            Early Warning Alerts
            <span class="alert-count-pill alert-pill-${topSev}">${alerts.length} active</span>
        </div>
        <div class="alert-cards-grid">
            ${alerts.length ? alerts.map(a => `
                <div class="alert-card alert-card-${a.severity}">
                    <div class="alert-card-header">
                        <span class="alert-icon">${a.icon}</span>
                        <span class="alert-title">${a.title}</span>
                        <span class="alert-metric">${a.metric || ''}</span>
                    </div>
                    <div class="alert-message">${a.message}</div>
                    <div class="alert-detail">${a.detail}</div>
                </div>
            `).join('') : '<div class="log-empty" style="padding:24px">No active alerts — seller health looks stable</div>'}
        </div>

        <div class="alert-section-title" style="margin-top:28px">
            AI-Powered Insights
            <span class="ai-badge" style="margin-left:8px;vertical-align:middle">AI</span>
        </div>
        <div class="ai-narrative-block">
            <div class="ai-narrative-text">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2" style="flex-shrink:0;margin-top:2px"><circle cx="12" cy="12" r="10"/><path d="M12 8v4m0 4h.01"/></svg>
                <p>${ai.narrative}</p>
            </div>
            <div class="ai-actions-title">Recommended Actions</div>
            <div class="ai-actions-list">
                ${ai.actions.map((a, i) => `
                    <div class="ai-action-item">
                        <span class="ai-action-num">${i + 1}</span>
                        <span>${a}</span>
                    </div>
                `).join('')}
            </div>
        </div>

        <div class="alert-section-title" style="margin-top:28px">
            Opportunity Recovery
            <span class="section-sub" style="color:var(--success)">Recoverable opportunities detected</span>
        </div>
        <div class="recovery-opps-grid">
            ${opps.map(o => `
                <div class="recovery-opp-card recovery-${o.urgency}">
                    <div class="roc-top">
                        <span class="roc-icon">${o.icon}</span>
                        <div class="roc-content">
                            <div class="roc-title">${o.title}</div>
                            <div class="roc-count">${o.count} <span class="roc-value">${o.value}</span></div>
                        </div>
                    </div>
                    <div class="roc-detail">${o.detail}</div>
                    <button class="roc-btn">${o.action} →</button>
                </div>
            `).join('')}
        </div>
    `;

    // Sparkline charts
    trendCards.forEach(tc => {
        makeChart(tc.cid, {
            type: 'line',
            data: {
                labels: wkLabels,
                datasets: [{ data: tc.data, borderColor: tc.color, backgroundColor: tc.color + '22',
                    fill: true, tension: 0.4, pointRadius: 2, pointHoverRadius: 4, borderWidth: 2 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: { x: { display: false }, y: { display: false } },
                plugins: { legend: { display: false },
                    tooltip: { callbacks: { label: ctx => `${ctx.parsed.y}${tc.unit}` } } }
            }
        });
    });
}

/* ============================================
   Upsell Signal Detection
   ============================================ */

function computeUpsellScore(s) {
    let score = 0;
    const trend = s.health_trend || [];
    const last = trend[trend.length - 1] || {};
    const prev = trend[trend.length - 2] || last;

    // Positive momentum (30 pts)
    if ((last.enquiries || 0) > (prev.enquiries || 0)) score += 15;
    if ((last.buyleads  || 0) > (prev.buyleads  || 0)) score += 15;

    // Low churn risk (25 pts)
    if (s.risk_band === 'low')    score += 25;
    else if (s.risk_band === 'medium') score += 10;

    // Above-average engagement (20 pts)
    const allEnq = DATA.sellers.map(x => x.total_enquiries_30d || 0);
    const medEnq = allEnq.sort((a,b)=>a-b)[Math.floor(allEnq.length/2)] || 1;
    if ((s.total_enquiries_30d || 0) > medEnq * 1.5) score += 20;
    else if ((s.total_enquiries_30d || 0) > medEnq) score += 10;

    // High rating (15 pts)
    if ((s.overall_rating || 0) >= 4.5)      score += 15;
    else if ((s.overall_rating || 0) >= 4.0) score += 8;

    // Strong call pickup (10 pts)
    if ((s.call_pickup_pct_30d || 0) >= 0.75)      score += 10;
    else if ((s.call_pickup_pct_30d || 0) >= 0.6) score += 5;

    return Math.min(100, score);
}

function renderUpsellSignals() {
    const TIER_ORDER = ['star', 'prime', 'star-maxi', 'prime-maxi'];
    const tierRank = (pkg) => {
        const idx = TIER_ORDER.indexOf((pkg || '').toLowerCase());
        return idx === -1 ? 1 : idx; // lower index = lower tier = more upsell potential
    };

    const candidates = DATA.sellers
        .filter(s => s.risk_band !== 'critical')
        .map(s => ({ ...s, upsellScore: computeUpsellScore(s), tierRank: tierRank(s.package) }))
        .filter(s => s.upsellScore >= 35)
        .sort((a, b) => b.upsellScore - a.upsellScore);

    const totalARR = candidates.slice(0, 50).reduce((sum, s) => sum + (s.revenue_at_risk || 0) * 0.4, 0);
    const highScore = candidates.filter(s => s.upsellScore >= 65).length;
    const avgScore  = candidates.length ? Math.round(candidates.reduce((a,s)=>a+s.upsellScore,0)/candidates.length) : 0;

    document.getElementById('upsell-kpis').innerHTML = [
        { label: 'Upsell Candidates',    value: candidates.length,        sub: 'Score ≥ 35',          cls: 'accent' },
        { label: 'High-Score Leads',     value: highScore,                sub: 'Score ≥ 65',          cls: 'success' },
        { label: 'Potential ARR Uplift', value: formatINR(totalARR),      sub: 'Top 50 candidates',   cls: 'success' },
        { label: 'Avg Upsell Score',     value: avgScore,                 sub: 'Out of 100',          cls: 'accent' },
    ].map(k=>`<div class="kpi-card ${k.cls}"><div class="kpi-label">${k.label}</div><div class="kpi-value">${k.value}</div><div class="kpi-sub">${k.sub}</div></div>`).join('');

    // Chart: by package tier
    const byPkg = {};
    candidates.forEach(s => { byPkg[s.package] = (byPkg[s.package]||0)+1; });
    const pkgKeys = Object.entries(byPkg).sort((a,b)=>b[1]-a[1]).slice(0,8);
    makeChart('chart-upsell-tiers', {
        type: 'bar',
        data: { labels: pkgKeys.map(([k])=>k), datasets: [{ data: pkgKeys.map(([,v])=>v), backgroundColor: '#10b981', borderRadius: 4, borderSkipped: false }] },
        options: { responsive: true, maintainAspectRatio: false,
            scales: { x: { grid:{display:false}, ticks:{color:'#8b949e',font:{family:'Inter',size:10},maxRotation:30} },
                      y: { grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#8b949e',font:{family:'Inter'}} } },
            plugins: { legend:{display:false} } }
    });

    // Score distribution histogram
    const bins = [0,0,0,0,0]; // 35-45, 45-55, 55-65, 65-75, 75-100
    candidates.forEach(s => {
        if (s.upsellScore < 45)      bins[0]++;
        else if (s.upsellScore < 55) bins[1]++;
        else if (s.upsellScore < 65) bins[2]++;
        else if (s.upsellScore < 75) bins[3]++;
        else                         bins[4]++;
    });
    makeChart('chart-upsell-scores', {
        type: 'bar',
        data: { labels: ['35–44','45–54','55–64','65–74','75+'], datasets: [{ data: bins,
            backgroundColor: ['#a78bfa','#818cf8','#6366f1','#10b981','#059669'], borderRadius: 4, borderSkipped: false }] },
        options: { responsive: true, maintainAspectRatio: false,
            scales: { x: { grid:{display:false}, ticks:{color:'#8b949e',font:{family:'Inter'}} },
                      y: { grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#8b949e',font:{family:'Inter'}} } },
            plugins: { legend:{display:false} } }
    });

    // Table
    document.getElementById('upsell-body').innerHTML = candidates.slice(0, 60).map(s => {
        const scoreCls = s.upsellScore >= 65 ? 'success' : s.upsellScore >= 50 ? 'accent' : '';
        const trend = s.health_trend || [];
        const rising = trend.length >= 2 && (trend[trend.length-1].enquiries||0) > (trend[trend.length-2].enquiries||0);
        const signal = rising ? '<span class="chip chip-low">Rising ENQ</span>' : (s.risk_band==='low'?'<span class="chip chip-low">Low Risk</span>':'<span class="chip chip-medium">Active</span>');
        return `<tr>
            <td><strong>${s.seller_id}</strong><br><span style="color:var(--text-secondary);font-size:0.74rem">${s.company_name||s.seller_name}</span></td>
            <td>${s.package}</td>
            <td><div class="upsell-score-bar"><div class="usb-fill" style="width:${s.upsellScore}%"></div><span class="usb-val ${scoreCls}">${s.upsellScore}</span></div></td>
            <td>${s.total_enquiries_30d||0}</td>
            <td>${((s.call_pickup_pct_30d||0)*100).toFixed(0)}%</td>
            <td>${(s.overall_rating||0).toFixed(1)}★</td>
            <td>${signal}</td>
            <td><button class="btn-view" onclick="openSeller360('${s.seller_id}')">View</button></td>
        </tr>`;
    }).join('');
}

/* ============================================
   Early Activation Health
   ============================================ */

function computeActivationScore(s) {
    let score = 0;

    // Profile completeness (30 pts)
    if (s.gst_verified)         score += 10;
    if (s.trustseal_active)     score += 10;
    score += Math.min(10, (s.verification_score || 0) / 100 * 10);

    // Activity momentum (35 pts)
    if ((s.call_pickup_pct_30d||0) >= 0.5)  score += 15;
    if ((s.total_enquiries_30d||0) >= 10)   score += 10;
    const trend = s.health_trend || [];
    if (trend.length >= 2 && (trend[trend.length-1].enquiries||0) > (trend[trend.length-2].enquiries||0)) score += 10;

    // Catalog (20 pts)
    if ((s.catalogue||[]).length > 0)    score += 10;
    if ((s.total_products||0) >= 10)     score += 10;

    // Response quality (15 pts)
    if ((s.untouched_pct||1) < 0.2)              score += 10;
    if ((s.low_review_response_rate||0) > 0.5)   score += 5;

    return Math.min(100, Math.round(score));
}

function renderActivation() {
    const newSellers = DATA.sellers
        .filter(s => (s.member_since_years || 0) <= 1)
        .map(s => ({ ...s, activationScore: computeActivationScore(s) }))
        .sort((a, b) => a.activationScore - b.activationScore); // worst first

    const atRisk    = newSellers.filter(s => s.activationScore < 40).length;
    const strong    = newSellers.filter(s => s.activationScore >= 70).length;
    const avgScore  = newSellers.length ? Math.round(newSellers.reduce((a,s)=>a+s.activationScore,0)/newSellers.length) : 0;

    document.getElementById('activation-kpis').innerHTML = [
        { label: 'New Sellers (<1 yr)', value: newSellers.length,    sub: 'In activation window',     cls: 'accent' },
        { label: 'At-Risk Activation',  value: atRisk,               sub: 'Score < 40 — needs help',  cls: 'danger' },
        { label: 'Strong Activation',   value: strong,               sub: 'Score ≥ 70 — on track',    cls: 'success' },
        { label: 'Avg Activation Score',value: avgScore,             sub: 'Out of 100',               cls: 'accent' },
    ].map(k=>`<div class="kpi-card ${k.cls}"><div class="kpi-label">${k.label}</div><div class="kpi-value">${k.value}</div><div class="kpi-sub">${k.sub}</div></div>`).join('');

    // Score distribution
    const bins = { '0–24':0, '25–39':0, '40–59':0, '60–74':0, '75–100':0 };
    newSellers.forEach(s => {
        if (s.activationScore < 25)      bins['0–24']++;
        else if (s.activationScore < 40) bins['25–39']++;
        else if (s.activationScore < 60) bins['40–59']++;
        else if (s.activationScore < 75) bins['60–74']++;
        else                             bins['75–100']++;
    });
    makeChart('chart-activation-dist', {
        type: 'bar',
        data: { labels: Object.keys(bins), datasets: [{ data: Object.values(bins),
            backgroundColor: ['#ef4444','#f97316','#f59e0b','#10b981','#059669'], borderRadius: 4, borderSkipped: false }] },
        options: { responsive: true, maintainAspectRatio: false,
            scales: { x: { grid:{display:false}, ticks:{color:'#8b949e',font:{family:'Inter'}} },
                      y: { grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#8b949e',font:{family:'Inter'}} } },
            plugins: { legend:{display:false} } }
    });

    // Score vs tenure bubble
    makeChart('chart-activation-tenure', {
        type: 'scatter',
        data: { datasets: [{
            data: newSellers.slice(0, 80).map(s => ({
                x: Math.round((s.member_since_years || 0) * 12), // months
                y: s.activationScore,
            })),
            backgroundColor: newSellers.slice(0,80).map(s => s.activationScore < 40 ? 'rgba(239,68,68,0.6)' : s.activationScore >= 70 ? 'rgba(16,185,129,0.6)' : 'rgba(245,158,11,0.6)'),
            borderWidth: 0, pointRadius: 5,
        }] },
        options: { responsive: true, maintainAspectRatio: false,
            scales: {
                x: { title:{display:true,text:'Tenure (months)',color:'#8b949e',font:{family:'Inter',size:11}}, grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#8b949e',font:{family:'Inter'}} },
                y: { title:{display:true,text:'Activation Score',color:'#8b949e',font:{family:'Inter',size:11}}, grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#8b949e',font:{family:'Inter'}}, min:0, max:100 }
            },
            plugins: { legend:{display:false} } }
    });

    // Activation gaps per seller
    const getGap = (s) => {
        if (!s.gst_verified) return 'Complete GST verification';
        if ((s.untouched_pct||1) >= 0.2) return 'Respond to untouched leads';
        if ((s.catalogue||[]).length === 0) return 'Upload product catalog';
        if ((s.call_pickup_pct_30d||0) < 0.5) return 'Improve call pickup rate';
        if ((s.total_products||0) < 10) return 'Add more product listings';
        return 'Maintain current activity';
    };

    document.getElementById('activation-body').innerHTML = newSellers.slice(0, 60).map(s => {
        const scoreCls = s.activationScore < 40 ? 'critical' : s.activationScore < 60 ? 'high' : s.activationScore < 75 ? 'medium' : 'low';
        return `<tr>
            <td><strong>${s.seller_id}</strong><br><span style="color:var(--text-secondary);font-size:0.74rem">${s.company_name||s.seller_name}</span></td>
            <td>${s.package}</td>
            <td>${s.member_since_years <= 0 ? '<6 months' : '~1 year'}</td>
            <td>
                <div class="activation-score-bar">
                    <div class="asb-fill asb-${scoreCls}" style="width:${s.activationScore}%"></div>
                    <span class="asb-val">${s.activationScore}</span>
                </div>
            </td>
            <td style="font-size:0.78rem;color:var(--text-secondary)">${getGap(s)}</td>
            <td>${bandChip(s.risk_band)}</td>
            <td><button class="btn-view" onclick="openSeller360('${s.seller_id}')">View</button></td>
        </tr>`;
    }).join('');
}

/* ---- Renewal Risk Page ---- */
function renderRenewalRisk() {
    const sellers = DATA.sellers
        .filter(s => s.risk_band !== 'low')
        .map(s => ({ ...s, dtr: s.days_to_renewal != null ? s.days_to_renewal : 999 }))
        .sort((a, b) => {
            const urgA = a.risk_score * Math.max(0.05, 1 - Math.min(Math.max(a.dtr, 0), 180) / 180);
            const urgB = b.risk_score * Math.max(0.05, 1 - Math.min(Math.max(b.dtr, 0), 180) / 180);
            return urgB - urgA;
        });

    const within90  = sellers.filter(s => s.dtr >= 0 && s.dtr <= 90).length;
    const overdue   = sellers.filter(s => s.dtr < 0).length;
    const imm       = sellers.filter(s => s.dtr <= 30).length + overdue;
    const rev90     = sellers.filter(s => s.dtr <= 90).reduce((sum, s) => sum + (s.revenue_at_risk || 0), 0);
    const avgDtr    = within90 > 0
        ? Math.round(sellers.filter(s => s.dtr >= 0 && s.dtr <= 90).reduce((acc, s) => acc + s.dtr, 0) / within90)
        : '—';

    // Update nav badge
    const badge = document.getElementById('renewal-nav-count');
    if (badge) {
        const total = within90 + overdue;
        badge.textContent = total;
        badge.style.display = total > 0 ? 'inline-flex' : 'none';
    }

    document.getElementById('renewal-kpis').innerHTML = [
        { label: 'High-Risk in 90 Days', value: within90, sub: `${overdue} already overdue`, cls: 'danger' },
        { label: 'Revenue at Stake',     value: formatINR(rev90 || 0), sub: 'Within 90-day window', cls: 'danger' },
        { label: 'Avg Days to Renewal',  value: avgDtr, sub: 'Within renewal window', cls: 'warning' },
        { label: 'Immediate Action',     value: imm,    sub: 'Overdue + 0–30 days left', cls: 'critical' },
    ].map(k => `<div class="kpi-card ${k.cls}"><div class="kpi-label">${k.label}</div><div class="kpi-value">${k.value}</div><div class="kpi-sub">${k.sub}</div></div>`).join('');

    // Timeline bar chart
    const buckets = [
        { label: 'Overdue',     count: overdue,                                                       color: '#ef4444' },
        { label: '0–30 days',   count: sellers.filter(s => s.dtr >= 0 && s.dtr <= 30).length,        color: '#f97316' },
        { label: '31–60 days',  count: sellers.filter(s => s.dtr > 30 && s.dtr <= 60).length,        color: '#f59e0b' },
        { label: '61–90 days',  count: sellers.filter(s => s.dtr > 60 && s.dtr <= 90).length,        color: '#facc15' },
        { label: '90+ days',    count: sellers.filter(s => s.dtr > 90 && s.dtr < 999).length,        color: '#10b981' },
    ];
    makeChart('chart-renewal-timeline', {
        type: 'bar',
        data: { labels: buckets.map(b => b.label),
            datasets: [{ data: buckets.map(b => b.count), backgroundColor: buckets.map(b => b.color), borderRadius: 6, borderSkipped: false }] },
        options: { responsive: true, maintainAspectRatio: false,
            scales: { x: { grid: { display: false }, ticks: { color: '#8b949e', font: { family: 'Inter' } } },
                      y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font: { family: 'Inter' } } } },
            plugins: { legend: { display: false } } }
    });

    // Bubble chart — risk vs days to renewal
    const bubbleSellers = sellers.filter(s => s.dtr < 999).slice(0, 80);
    makeChart('chart-renewal-bubble', {
        type: 'bubble',
        data: { datasets: [{
            label: 'Sellers',
            data: bubbleSellers.map(s => ({
                x: Math.max(-30, Math.min(180, s.dtr)),
                y: s.risk_score,
                r: Math.max(4, Math.sqrt(s.revenue_at_risk || 500) / 14),
            })),
            backgroundColor: bubbleSellers.map(s => (BAND_COLORS[s.risk_band] || '#6366f1') + '88'),
            borderColor: bubbleSellers.map(s => BAND_COLORS[s.risk_band] || '#6366f1'),
            borderWidth: 1,
        }] },
        options: { responsive: true, maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: 'Days to Renewal', color: '#8b949e', font: { family: 'Inter', size: 11 } },
                     grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font: { family: 'Inter' } } },
                y: { title: { display: true, text: 'Churn Risk Score', color: '#8b949e', font: { family: 'Inter', size: 11 } },
                     grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#8b949e', font: { family: 'Inter' } }, min: 0, max: 100 }
            },
            plugins: { legend: { display: false },
                tooltip: { callbacks: { label: ctx => {
                    const sel = bubbleSellers[ctx.dataIndex];
                    return sel ? `${sel.company_name || sel.seller_id} | Risk: ${sel.risk_score.toFixed(0)} | ${sel.dtr < 0 ? 'Overdue' : sel.dtr + 'd left'}` : '';
                }}}}
        }
    });

    // Priority table
    document.getElementById('renewal-body').innerHTML = sellers.slice(0, 60).map(s => {
        let urgCls = 'low', urgLabel = '';
        if (s.dtr < 0)           { urgCls = 'critical'; urgLabel = `Overdue ${Math.abs(s.dtr)}d`; }
        else if (s.dtr <= 30)    { urgCls = 'critical'; urgLabel = `${s.dtr}d left`; }
        else if (s.dtr <= 60)    { urgCls = 'high';     urgLabel = `${s.dtr}d left`; }
        else if (s.dtr <= 90)    { urgCls = 'medium';   urgLabel = `${s.dtr}d left`; }
        else if (s.dtr < 999)    { urgCls = 'low';      urgLabel = `${s.dtr}d left`; }
        else                     { urgCls = 'low';      urgLabel = 'No date'; }

        const topAlert = generateAlerts(s)[0];
        return `<tr>
            <td><strong>${s.seller_id}</strong><br><span style="color:var(--text-secondary);font-size:0.74rem">${s.company_name || s.seller_name}</span></td>
            <td>${s.package}</td>
            <td>${bandChip(s.risk_band)} <span style="font-size:0.76rem">${s.risk_score.toFixed(0)}</span></td>
            <td>
                <span class="chip chip-${urgCls}" style="font-size:0.72rem">${urgLabel}</span>
                <div style="font-size:0.7rem;color:var(--text-muted);margin-top:2px">${s.subscription_end_date || '—'}</div>
            </td>
            <td>${s.revenue_at_risk ? formatINR(s.revenue_at_risk) : '—'}</td>
            <td>${topAlert ? `<span style="font-size:0.78rem">${topAlert.icon} ${topAlert.title}</span>` : '—'}</td>
            <td><span class="chip chip-action">${actionLabel(s.recommended_action)}</span></td>
            <td><button class="btn-view" onclick="openSeller360('${s.seller_id}')">View</button></td>
        </tr>`;
    }).join('');
}


/* ============================================
   Intervention ROI Tracker
   ============================================ */

function renderInterventionROI() {
    const ACTION_ROI = {
        roi: 3.2, renewal: 3.0, sales: 2.8, call: 2.6,
        catalog: 2.1, response: 1.8, feature: 1.5, email: 1.3, nudge: 1.3,
    };
    const getROI = (code) => {
        const k = (code||'').toLowerCase();
        for (const [key, val] of Object.entries(ACTION_ROI)) { if (k.includes(key)) return val; }
        return 1.5;
    };

    const actioned = DATA.sellers.filter(s => s.action_code);
    const completed = actioned.filter(s => s.action_status === 'completed');

    const retainedRev = completed.reduce((sum, s) => {
        const roi = getROI(s.action_code);
        return sum + (s.revenue_at_risk || 0) * (1 - 1 / roi);
    }, 0);
    const expectedRev = actioned.filter(s=>s.action_status==='scheduled').reduce((sum,s)=>{
        return sum + (s.revenue_at_risk||0) * (1 - 1/getROI(s.action_code)) * 0.7;
    }, 0);
    const avgROI = actioned.length ? (actioned.reduce((sum,s)=>sum+getROI(s.action_code),0)/actioned.length) : 1;

    document.getElementById('roi-kpis').innerHTML = [
        { label: 'Revenue Retained',   value: formatINR(retainedRev), sub: 'From completed actions',   cls: 'success' },
        { label: 'Expected Recovery',  value: formatINR(expectedRev), sub: 'From scheduled actions',   cls: 'accent' },
        { label: 'Avg ROI Multiple',   value: avgROI.toFixed(1) + '×', sub: 'Across all action types', cls: 'accent' },
        { label: 'Actions Tracked',    value: actioned.length,        sub: 'With revenue context',     cls: 'warning' },
    ].map(k=>`<div class="kpi-card ${k.cls}"><div class="kpi-label">${k.label}</div><div class="kpi-value">${k.value}</div><div class="kpi-sub">${k.sub}</div></div>`).join('');

    // Aggregate by type
    const byType = {};
    actioned.forEach(s => {
        const t = s.action_code;
        if (!byType[t]) byType[t] = { count:0, completed:0, revenue:0, roi: getROI(t) };
        byType[t].count++;
        if (s.action_status === 'completed') byType[t].completed++;
        byType[t].revenue += s.revenue_at_risk || 0;
    });
    const types = Object.entries(byType).sort((a,b)=>b[1].revenue-a[1].revenue).slice(0,7);

    makeChart('chart-roi-effectiveness', {
        type: 'bar',
        data: { labels: types.map(([k])=>actionLabel(k)),
            datasets: [
                { label: 'Est. ROI Multiple', data: types.map(([,v])=>v.roi), backgroundColor: '#6366f1', borderRadius: 4, borderSkipped: false },
                { label: 'Success Rate %',    data: types.map(([,v])=>v.completed/v.count*100), backgroundColor: '#10b981', borderRadius: 4, borderSkipped: false, yAxisID: 'y2' },
            ]},
        options: { responsive: true, maintainAspectRatio: false,
            scales: {
                x: { grid:{display:false}, ticks:{color:'#8b949e',font:{family:'Inter',size:10},maxRotation:30} },
                y:  { grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#8b949e',font:{family:'Inter'},callback:v=>v+'×'}, title:{display:true,text:'ROI Multiple',color:'#8b949e',font:{family:'Inter',size:10}} },
                y2: { position:'right', grid:{display:false}, ticks:{color:'#10b981',font:{family:'Inter'},callback:v=>v+'%'}, title:{display:true,text:'Success %',color:'#10b981',font:{family:'Inter',size:10}} },
            },
            plugins: { legend:{labels:{color:'#8b949e',font:{family:'Inter',size:11},usePointStyle:true,pointStyleWidth:8}} } }
    });

    // Recovery scenarios chart
    const totalRev = actioned.reduce((sum,s)=>sum+(s.revenue_at_risk||0),0);
    makeChart('chart-roi-recovery', {
        type: 'bar',
        data: { labels: ['20% Success','40% Success','65% Success'],
            datasets: [{ data: [0.2,0.4,0.65].map(r=>Math.round(totalRev*r*(avgROI-1)/avgROI)),
                backgroundColor:['#f59e0b','#6366f1','#10b981'], borderRadius:6, borderSkipped:false }] },
        options: { responsive:true, maintainAspectRatio:false,
            scales: { x:{grid:{display:false},ticks:{color:'#8b949e',font:{family:'Inter',size:10}}},
                      y:{grid:{color:'rgba(255,255,255,0.04)'},ticks:{color:'#8b949e',font:{family:'Inter'},callback:v=>formatINR(v)}} },
            plugins:{legend:{display:false}} }
    });

    // Playbook table
    document.getElementById('roi-playbook-body').innerHTML = types.map(([type, d]) => {
        const successRate = d.count > 0 ? (d.completed/d.count*100).toFixed(0) : '—';
        const retained = d.revenue * (1 - 1/d.roi) * (d.completed/Math.max(d.count,1));
        return `<tr>
            <td><span class="chip chip-action">${actionLabel(type)}</span></td>
            <td>${d.count}</td>
            <td>${d.completed}</td>
            <td>${successRate}%</td>
            <td><strong>${d.roi.toFixed(1)}×</strong></td>
            <td>${formatINR(retained)}</td>
        </tr>`;
    }).join('');
}

/* ---- Init ---- */
async function init() {
    try {
        const resp = await fetch('data/dashboard_data.json');
        DATA = await resp.json();
    } catch(e) {
        document.getElementById('loading-overlay').innerHTML = `<p style="color:#ef4444">Failed to load data. Run: python scripts/export_real_dashboard.py</p>`;
        return;
    }
    document.getElementById('loading-overlay').classList.add('hidden');
    initTabs();
    renderKPIs(); renderDonut(); renderFunnel(); renderTopReasons();
}

document.addEventListener('DOMContentLoaded', init);
