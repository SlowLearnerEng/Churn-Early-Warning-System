/* ============================================
   Churn Intelligence Platform — Views (Part 2)
   Seller 360, Cohorts, Interventions, Init
   (Rebuilt for real IndiaMART data)
   ============================================ */

/* ---- Seller 360 Picker ---- */
function renderSellerPicker(query) {
    const q = (query || '').toLowerCase();
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
    const container = document.getElementById('s360-list');
    container.innerHTML = list.slice(0, 100).map(s => {
        const riskColor = BAND_COLORS[s.risk_band] || '#6366f1';
        const aiIcon = s.ai_summary && !s.ai_summary.fallback ? '<span class="ai-badge" style="font-size:0.55rem;padding:1px 5px;vertical-align:middle;margin-left:4px">AI</span>' : '';
        return `<div class="s360-row" onclick="openSeller360('${s.seller_id}')">
            <span class="s360-cell s360-cell-name">
                <strong>${s.seller_id}</strong>
                <span class="s360-company">${s.company_name || s.seller_name}</span>
                ${aiIcon}
            </span>
            <span class="s360-cell">${s.package}</span>
            <span class="s360-cell">${s.city}</span>
            <span class="s360-cell">${bandChip(s.risk_band)} <span style="font-size:0.76rem;color:var(--text-secondary)">${s.risk_score.toFixed(0)}</span></span>
            <span class="s360-cell"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity:0.4"><polyline points="9 18 15 12 9 6"/></svg></span>
        </div>`;
    }).join('');
    if (list.length === 0) {
        container.innerHTML = '<div class="log-empty">No sellers match your search</div>';
    }
    if (list.length > 100) {
        container.innerHTML += `<div class="log-empty" style="padding:10px">${list.length - 100} more sellers — refine your search</div>`;
    }
}

function initSellerPicker() {
    const searchEl = document.getElementById('s360-search');
    searchEl.addEventListener('input', () => renderSellerPicker(searchEl.value));
    renderSellerPicker('');
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

        <div class="explanation-cards" id="explanation-cards"></div>

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
    initTabs(); renderKPIs(); renderDonut(); renderFunnel(); renderTopReasons(); renderHeatmap();
    initWatchlistFilters(); renderWatchlist(); initSellerPicker(); initCohortTabs(); renderCohorts(); renderInterventions();
}

document.addEventListener('DOMContentLoaded', init);
