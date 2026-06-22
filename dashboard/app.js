/* ============================================================
   SanctSim Dashboard — app.js
   ============================================================ */

'use strict';

// ── Global state ─────────────────────────────────────────────
const State = {
  rounds: [],       // parsed JSON array
  meta: {},         // derived simulation metadata
  agents: {},       // {id: {group, initialWealth, ...}}
  fileName: '',
  activeView: 'macro',
  activeAgent: null,
  networkRound: null,
  charts: {},       // ApexCharts instances keyed by id
  network: null,    // vis.js Network instance
};

// ── Colour helpers ─────────────────────────────────────────────
const COLORS = {
  blue:   '#3b82f6',
  teal:   '#14b8a6',
  amber:  '#f59e0b',
  red:    '#ef4444',
  green:  '#22c55e',
  purple: '#a855f7',
  cyan:   '#06b6d4',
  rose:   '#f43f5e',
  developed: '#60a5fa',
  developing:'#34d399',
  si:     '#818cf8',
  sfi:    '#94a3b8',
};

const APEX_BASE = {
  chart: { background: 'transparent', toolbar: { show: false }, animations: { enabled: true, speed: 600 } },
  theme: { mode: 'dark' },
  grid: { borderColor: 'rgba(99,179,237,0.1)', strokeDashArray: 4 },
  stroke: { curve: 'smooth', width: 2 },
  tooltip: { theme: 'dark', style: { fontFamily: 'Inter, sans-serif', fontSize: '12px' } },
  legend: { fontFamily: 'Inter, sans-serif', fontSize: '12px', labels: { colors: '#94a3b8' } },
  xaxis: { labels: { style: { colors: '#64748b', fontFamily: 'Inter, sans-serif', fontSize: '11px' } }, axisBorder: { show: false }, axisTicks: { show: false } },
  yaxis: { labels: { style: { colors: '#64748b', fontFamily: 'Inter, sans-serif', fontSize: '11px' } } },
  dataLabels: { enabled: false },
};

// ── Utility ────────────────────────────────────────────────────
function fmt(n, decimals = 0) {
  if (n == null || isNaN(n)) return '—';
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + 'B';
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return n.toFixed(decimals);
}

function pct(n) { return n == null ? '—' : (n * 100).toFixed(1) + '%'; }

function trustClass(level) {
  if (!level) return 'trust-default';
  const l = level.toLowerCase();
  if (l.includes('cooperative') || l.includes('similar')) return 'trust-cooperative';
  if (l.includes('free-rider') || l.includes('uncooperative') || l.includes('untrustworthy')) return 'trust-free-rider';
  if (l.includes('unreliable') || l.includes('inconsistent') || l.includes('cautious')) return 'trust-unreliable';
  if (l.includes('strategic') || l.includes('opportunistic') || l.includes('aggressive') || l.includes('ambitious')) return 'trust-strategic';
  return 'trust-default';
}

function destroyChart(id) {
  if (State.charts[id]) { try { State.charts[id].destroy(); } catch(e){} delete State.charts[id]; }
}

function el(id) { return document.getElementById(id); }

// ── File loading ───────────────────────────────────────────────
function initDropZone() {
  const zone = el('drop-zone');
  const fileInput = el('file-input');

  zone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', e => { if (e.target.files[0]) loadFile(e.target.files[0]); });

  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]);
  });
}

function loadFile(file) {
  showLoading(true);
  State.fileName = file.name;
  const reader = new FileReader();
  reader.onload = e => {
    try {
      State.rounds = JSON.parse(e.target.result);
      processData();
      renderAll();
    } catch(err) {
      alert('Failed to parse JSON: ' + err.message);
    } finally {
      showLoading(false);
    }
  };
  reader.readAsText(file);
}

function showLoading(on) {
  el('loading-overlay').classList.toggle('visible', on);
}

// ── Data Processing ────────────────────────────────────────────
function processData() {
  const rounds = State.rounds;
  const meta = {
    numRounds: rounds.length,
    numAgents: 0,
    isLDF: false,
    hasShocks: false,
    hasDemocracy: false,
    agentIds: [],
  };

  // Collect agent IDs from first round
  const firstRound = rounds[0];
  meta.agentIds = Object.keys(firstRound.agents).map(Number).sort((a,b) => a-b);
  meta.numAgents = meta.agentIds.length;

  // Detect LDF & shocks
  meta.isLDF  = rounds.some(r => r.ldf_contributions_total > 0);
  meta.hasShocks = rounds.some(r => r.shock_occurred);
  meta.hasDemocracy = rounds.some(r => r.constitutional_change != null);

  // Build agent registry from first round
  const agents = {};
  for (const [id, data] of Object.entries(firstRound.agents)) {
    agents[parseInt(id)] = {
      id: parseInt(id),
      group: data.agent_group,
      strategy: data.strategy,
      vulnerability: data.vulnerability,
      historicalEmissions: data.historical_emissions,
      contributionCapacity: data.contribution_capacity,
    };
  }

  State.meta = meta;
  State.agents = agents;
}

// ── Render all views ───────────────────────────────────────────
function renderAll() {
  // Show dashboard, hide drop zone
  el('drop-zone').style.display = 'none';
  el('dashboard-ui').style.display = 'block';

  // Update file badge
  const badge = el('file-badge');
  badge.textContent = State.fileName;
  badge.style.display = 'block';

  // Update nav tabs
  const ldfTab = el('tab-ldf');
  const democTab = el('tab-democracy');
  if (ldfTab) ldfTab.style.display = State.meta.isLDF ? '' : 'none';
  if (democTab) democTab.style.display = State.meta.hasDemocracy ? '' : 'none';

  renderKPIs();
  renderMacroCharts();
  renderAgentList();
  if (State.meta.isLDF) renderLDFView();
  if (State.meta.hasDemocracy) renderDemocracyView();

  // Default: select first agent
  selectAgent(State.meta.agentIds[0]);
  switchView('macro');
}

// ── KPI Cards ──────────────────────────────────────────────────
function renderKPIs() {
  const rounds = State.rounds;
  const last = rounds[rounds.length - 1];
  const first = rounds[0];

  const avgCoop = rounds.reduce((s, r) => s + (r.cooperation_rate || 0), 0) / rounds.length;
  const shockCount = rounds.filter(r => r.shock_occurred).length;

  // Wealth: pull all agents last round
  const lastAgents = Object.values(last.agents);
  const totalWealth = lastAgents.reduce((s, a) => s + (a.wealth || 0), 0);
  const avgGini = rounds.reduce((s,r) => s + (r.gini_wealth || 0), 0) / rounds.length;
  const finalPool = last.ldf_pool_end || 0;
  const totalPayouts = rounds.reduce((s,r) => s + (r.ldf_payouts_total || 0), 0);

  el('kpi-grid').innerHTML = `
    <div class="kpi-card kpi-blue">
      <div class="kpi-label">Total Rounds</div>
      <div class="kpi-value">${State.meta.numRounds}</div>
      <div class="kpi-sub">${State.meta.numAgents} agents</div>
    </div>
    <div class="kpi-card kpi-teal">
      <div class="kpi-label">Avg Cooperation</div>
      <div class="kpi-value">${pct(avgCoop)}</div>
      <div class="kpi-sub">across all rounds</div>
    </div>
    <div class="kpi-card kpi-purple">
      <div class="kpi-label">Final Total Wealth</div>
      <div class="kpi-value">${fmt(totalWealth)}</div>
      <div class="kpi-sub">all agents combined</div>
    </div>
    <div class="kpi-card kpi-amber">
      <div class="kpi-label">Avg Gini Index</div>
      <div class="kpi-value">${avgGini.toFixed(3)}</div>
      <div class="kpi-sub">wealth inequality</div>
    </div>
    ${shockCount > 0 ? `
    <div class="kpi-card kpi-red">
      <div class="kpi-label">Climate Shocks</div>
      <div class="kpi-value">${shockCount}</div>
      <div class="kpi-sub">shock rounds</div>
    </div>` : ''}
    ${State.meta.isLDF ? `
    <div class="kpi-card kpi-green">
      <div class="kpi-label">LDF Pool (Final)</div>
      <div class="kpi-value">${fmt(finalPool)}</div>
      <div class="kpi-sub">${fmt(totalPayouts)} paid out</div>
    </div>` : ''}
  `;
}

// ── Macro Charts ───────────────────────────────────────────────
function renderMacroCharts() {
  const rounds = State.rounds;
  const labels = rounds.map(r => `R${r.round_number}`);

  // 1. Cooperation Rate + Gini
  destroyChart('chart-coop');
  State.charts['chart-coop'] = new ApexCharts(el('chart-coop'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'line', height: 220 },
    series: [
      { name: 'Cooperation Rate', data: rounds.map(r => +(r.cooperation_rate * 100).toFixed(2)) },
      { name: 'Gini Index', data: rounds.map(r => +(r.gini_wealth || 0).toFixed(4)), type: 'line' },
    ],
    colors: [COLORS.teal, COLORS.amber],
    stroke: { width: [2.5, 2], curve: 'smooth', dashArray: [0, 5] },
    yaxis: [
      { title: { text: 'Coop %', style: { color: '#64748b', fontSize: '11px' } }, labels: { formatter: v => v.toFixed(0)+'%', style: { colors: '#64748b' } }, min: 0, max: 100 },
      { opposite: true, title: { text: 'Gini', style: { color: '#64748b', fontSize: '11px' } }, labels: { formatter: v => v.toFixed(3), style: { colors: '#64748b' } } },
    ],
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    annotations: buildShockAnnotations(rounds),
  });
  State.charts['chart-coop'].render();

  // 2. SI vs SFI membership
  destroyChart('chart-membership');
  State.charts['chart-membership'] = new ApexCharts(el('chart-membership'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'area', height: 220, stacked: true },
    series: [
      { name: 'SI Members', data: rounds.map(r => r.si_members.length) },
      { name: 'SFI Members', data: rounds.map(r => r.sfi_members.length) },
    ],
    colors: [COLORS.si, COLORS.sfi],
    fill: { type: 'gradient', gradient: { opacityFrom: 0.5, opacityTo: 0.1 } },
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    yaxis: { ...APEX_BASE.yaxis, title: { text: '# Agents', style: { color: '#64748b', fontSize: '11px' } } },
    annotations: buildShockAnnotations(rounds),
  });
  State.charts['chart-membership'].render();

  // 3. Contributions per round (total)
  destroyChart('chart-contrib');
  State.charts['chart-contrib'] = new ApexCharts(el('chart-contrib'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'bar', height: 220 },
    plotOptions: { bar: { columnWidth: '65%', borderRadius: 3 } },
    series: [
      { name: 'SI Contribution', data: rounds.map(r => r.si_total_contribution || 0) },
      { name: 'SFI Contribution', data: rounds.map(r => r.sfi_total_contribution || 0) },
    ],
    colors: [COLORS.si, COLORS.sfi],
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    yaxis: { ...APEX_BASE.yaxis, labels: { formatter: v => fmt(v), style: { colors: '#64748b' } } },
    annotations: buildShockAnnotations(rounds),
  });
  State.charts['chart-contrib'].render();

  // 4. Wealth Trajectory per agent (per group)
  renderWealthChart(labels);

  // 5. Reputation Trajectories
  renderReputationChart(labels);

  // 6. LDF charts if applicable
  if (State.meta.isLDF) {
    renderLDFPoolChart(labels);
  }
}

function buildShockAnnotations(rounds) {
  const shocks = rounds.filter(r => r.shock_occurred);
  return {
    xaxis: shocks.map(r => ({
      x: `R${r.round_number}`,
      borderColor: COLORS.amber,
      strokeDashArray: 0,
      borderWidth: 1.5,
      label: {
        text: `⚡ ${(r.shock_severity * 100).toFixed(0)}%`,
        style: { color: COLORS.amber, background: 'rgba(245,158,11,0.1)', fontSize: '10px', fontFamily: 'Inter, sans-serif' },
      },
    })),
  };
}

function renderWealthChart(labels) {
  const rounds = State.rounds;
  const agentIds = State.meta.agentIds;

  const developed = agentIds.filter(id => State.agents[id]?.group === 'developed');
  const developing = agentIds.filter(id => State.agents[id]?.group === 'developing');

  // Compute group average wealth per round
  const devAvg = rounds.map(r => {
    const vals = developed.map(id => r.agents[id]?.wealth || 0).filter(Boolean);
    return vals.length ? vals.reduce((a,b) => a+b, 0) / vals.length : 0;
  });
  const devgAvg = rounds.map(r => {
    const vals = developing.map(id => r.agents[id]?.wealth || 0).filter(Boolean);
    return vals.length ? vals.reduce((a,b) => a+b, 0) / vals.length : 0;
  });

  // Individual traces
  const series = [
    { name: 'Avg Developed', data: devAvg.map(v => +v.toFixed(2)) },
    { name: 'Avg Developing', data: devgAvg.map(v => +v.toFixed(2)) },
    ...agentIds.map(id => ({
      name: `A${id}`,
      data: rounds.map(r => +(r.agents[id]?.wealth || 0).toFixed(2)),
    })),
  ];

  destroyChart('chart-wealth');
  State.charts['chart-wealth'] = new ApexCharts(el('chart-wealth'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'line', height: 300 },
    series,
    colors: [COLORS.developed, COLORS.developing, ...agentIds.map(id =>
      State.agents[id]?.group === 'developed' ? 'rgba(96,165,250,0.3)' : 'rgba(52,211,153,0.3)'
    )],
    stroke: {
      width: [3, 3, ...agentIds.map(() => 1)],
      curve: 'smooth',
      dashArray: [0, 4, ...agentIds.map(() => 0)],
    },
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    yaxis: { ...APEX_BASE.yaxis, labels: { formatter: v => fmt(v), style: { colors: '#64748b' } } },
    legend: { ...APEX_BASE.legend, show: true },
    annotations: buildShockAnnotations(State.rounds),
  });
  State.charts['chart-wealth'].render();
}

function renderReputationChart(labels) {
  const rounds = State.rounds;
  const agentIds = State.meta.agentIds;

  destroyChart('chart-rep');
  State.charts['chart-rep'] = new ApexCharts(el('chart-rep'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'line', height: 260 },
    series: agentIds.map(id => ({
      name: `Agent ${id}`,
      data: rounds.map(r => +(r.agents[id]?.reputation || 5).toFixed(3)),
    })),
    colors: agentIds.map(id => State.agents[id]?.group === 'developed' ? COLORS.developed : COLORS.developing),
    stroke: { width: 1.5, curve: 'smooth' },
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    yaxis: { ...APEX_BASE.yaxis, labels: { formatter: v => v.toFixed(1), style: { colors: '#64748b' } } },
  });
  State.charts['chart-rep'].render();
}

function renderLDFPoolChart(labels) {
  const rounds = State.rounds;
  destroyChart('chart-ldf-pool');
  State.charts['chart-ldf-pool'] = new ApexCharts(el('chart-ldf-pool'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'line', height: 260 },
    series: [
      { name: 'Pool Balance', data: rounds.map(r => +(r.ldf_pool_end || 0).toFixed(2)) },
      { name: 'Contributions', data: rounds.map(r => +(r.ldf_contributions_total || 0).toFixed(2)) },
      { name: 'Payouts', data: rounds.map(r => +(r.ldf_payouts_total || 0).toFixed(2)) },
      { name: 'Gross Damage', data: rounds.map(r => +(r.gross_damage_total || 0).toFixed(2)) },
    ],
    colors: [COLORS.green, COLORS.blue, COLORS.teal, COLORS.red],
    stroke: { width: [3, 2, 2, 2], curve: 'smooth', dashArray: [0, 5, 5, 3] },
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    yaxis: { ...APEX_BASE.yaxis, labels: { formatter: v => fmt(v), style: { colors: '#64748b' } } },
    annotations: buildShockAnnotations(rounds),
  });
  State.charts['chart-ldf-pool'].render();

  // Per-agent LDF transfers (developed pay, developing receive)
  const agentIds = State.meta.agentIds;
  const developing = agentIds.filter(id => State.agents[id]?.group === 'developing');
  const developed  = agentIds.filter(id => State.agents[id]?.group === 'developed');

  const devgPayouts = developing.map(id => ({
    name: `A${id}`,
    data: rounds.map(r => +(r.agents[id]?.ldf_payout_round || 0).toFixed(2)),
  }));
  const devContribs = developed.map(id => ({
    name: `A${id}`,
    data: rounds.map(r => +(r.agents[id]?.ldf_contribution_round || 0).toFixed(2)),
  }));

  destroyChart('chart-ldf-payouts');
  State.charts['chart-ldf-payouts'] = new ApexCharts(el('chart-ldf-payouts'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'bar', height: 260 },
    plotOptions: { bar: { columnWidth: '70%', borderRadius: 2 } },
    series: devgPayouts,
    colors: developing.map(() => COLORS.developing),
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    yaxis: { ...APEX_BASE.yaxis, labels: { formatter: v => fmt(v), style: { colors: '#64748b' } } },
    title: { text: 'LDF Payouts per Developing Agent', style: { color: '#94a3b8', fontFamily: 'Inter', fontSize: '12px' } },
  });
  State.charts['chart-ldf-payouts'].render();

  destroyChart('chart-ldf-contribs');
  State.charts['chart-ldf-contribs'] = new ApexCharts(el('chart-ldf-contribs'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'bar', height: 260 },
    plotOptions: { bar: { columnWidth: '70%', borderRadius: 2 } },
    series: devContribs,
    colors: developed.map(() => COLORS.developed),
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    yaxis: { ...APEX_BASE.yaxis, labels: { formatter: v => fmt(v), style: { colors: '#64748b' } } },
    title: { text: 'LDF Contributions per Developed Agent', style: { color: '#94a3b8', fontFamily: 'Inter', fontSize: '12px' } },
  });
  State.charts['chart-ldf-contribs'].render();
}

// ── LDF Summary View ───────────────────────────────────────────
function renderLDFView() {
  const rounds = State.rounds;
  const agentIds = State.meta.agentIds;

  const shockRounds = rounds.filter(r => r.shock_occurred);
  const totalGrossDamage = rounds.reduce((s,r) => s + (r.gross_damage_total || 0), 0);
  const totalNetDamage   = rounds.reduce((s,r) => s + (r.net_damage_total   || 0), 0);
  const totalContribs    = rounds.reduce((s,r) => s + (r.ldf_contributions_total || 0), 0);
  const totalPayouts     = rounds.reduce((s,r) => s + (r.ldf_payouts_total   || 0), 0);
  const finalPool        = rounds[rounds.length-1].ldf_pool_end || 0;

  let shockHTML = shockRounds.map(r => `
    <div class="vote-card">
      <div class="vote-header">
        <span>Round ${r.round_number} — Climate Shock</span>
        <span class="shock-badge">⚡ ${(r.shock_severity*100).toFixed(1)}% severity</span>
      </div>
      <div class="stat-row"><span class="stat-label">Gross Damage</span><span class="stat-value mono">${fmt(r.gross_damage_total)}</span></div>
      <div class="stat-row"><span class="stat-label">Net Damage</span><span class="stat-value mono">${fmt(r.net_damage_total)}</span></div>
      <div class="stat-row"><span class="stat-label">LDF Payout</span><span class="stat-value mono text-green-400">${fmt(r.ldf_payouts_total)}</span></div>
      <div class="stat-row"><span class="stat-label">Pool After</span><span class="stat-value mono">${fmt(r.ldf_pool_end)}</span></div>
    </div>
  `).join('');

  // Net transfer table
  let rows = agentIds.map(id => {
    const group = State.agents[id]?.group;
    const totalContrib = rounds.reduce((s,r) => s + (r.agents[id]?.ldf_contribution_round || 0), 0);
    const totalPayout  = rounds.reduce((s,r) => s + (r.agents[id]?.ldf_payout_round      || 0), 0);
    const net = totalPayout - totalContrib;
    return { id, group, totalContrib, totalPayout, net };
  }).sort((a,b) => b.net - a.net);

  const tableRows = rows.map(r => `
    <tr>
      <td><span class="pill ${r.group==='developed'?'pill-blue':'pill-green'}">${r.group==='developed'?'DEV':'DVG'}</span> Agent ${r.id}</td>
      <td class="mono">${fmt(r.totalContrib)}</td>
      <td class="mono">${fmt(r.totalPayout)}</td>
      <td class="mono ${r.net >= 0 ? 'text-green-400' : 'text-red-400'}">${r.net >= 0 ? '+' : ''}${fmt(r.net)}</td>
    </tr>
  `).join('');

  el('ldf-view-content').innerHTML = `
    <div class="kpi-grid" style="grid-template-columns: repeat(auto-fill, minmax(180px,1fr))">
      <div class="kpi-card kpi-amber"><div class="kpi-label">Shock Rounds</div><div class="kpi-value">${shockRounds.length}</div><div class="kpi-sub">out of ${rounds.length} rounds</div></div>
      <div class="kpi-card kpi-red"><div class="kpi-label">Total Gross Damage</div><div class="kpi-value">${fmt(totalGrossDamage)}</div><div class="kpi-sub">${fmt(totalNetDamage)} net</div></div>
      <div class="kpi-card kpi-blue"><div class="kpi-label">Total Contributions</div><div class="kpi-value">${fmt(totalContribs)}</div><div class="kpi-sub">to LDF pool</div></div>
      <div class="kpi-card kpi-green"><div class="kpi-label">Total Payouts</div><div class="kpi-value">${fmt(totalPayouts)}</div><div class="kpi-sub">to affected agents</div></div>
      <div class="kpi-card kpi-teal"><div class="kpi-label">Coverage Ratio</div><div class="kpi-value">${totalGrossDamage > 0 ? pct(totalPayouts / totalGrossDamage) : '—'}</div><div class="kpi-sub">payouts / gross damage</div></div>
      <div class="kpi-card kpi-purple"><div class="kpi-label">Final Pool</div><div class="kpi-value">${fmt(finalPool)}</div><div class="kpi-sub">remaining balance</div></div>
    </div>

    <div class="chart-grid chart-grid-full" style="margin-bottom:1.5rem">
      <div class="chart-card">
        <div class="chart-title">📊 LDF Pool Dynamics</div>
        <div class="chart-subtitle">Pool balance, contributions, payouts, and gross damage over time</div>
        <div id="chart-ldf-pool"></div>
      </div>
    </div>

    <div class="chart-grid chart-grid-2" style="margin-bottom:1.5rem">
      <div class="chart-card"><div id="chart-ldf-contribs"></div></div>
      <div class="chart-card"><div id="chart-ldf-payouts"></div></div>
    </div>

    <div class="chart-grid chart-grid-2" style="margin-bottom:1.5rem">
      <div class="chart-card">
        <div class="chart-title">⚡ Shock Events</div>
        <div class="chart-subtitle">${shockRounds.length} shock round(s) with damage and payout detail</div>
        <div class="detail-card-body" style="padding-top:0.5rem">
          ${shockHTML || '<div class="empty-state"><span class="empty-icon">✅</span><p>No climate shocks occurred in this run.</p></div>'}
        </div>
      </div>
      <div class="chart-card">
        <div class="chart-title">🌍 Net Transfer per Agent</div>
        <div class="chart-subtitle">Positive = net recipient, Negative = net contributor</div>
        <div style="overflow-x:auto">
          <table class="sanction-table">
            <thead><tr><th>Agent</th><th>Contributed</th><th>Received</th><th>Net Transfer</th></tr></thead>
            <tbody>${tableRows}</tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  // Re-render LDF charts since they're now in the DOM
  renderLDFPoolChart(State.rounds.map(r => `R${r.round_number}`));
}

// ── Democracy View ─────────────────────────────────────────────
function renderDemocracyView() {
  const votes = State.rounds
    .filter(r => r.constitutional_change != null)
    .map(r => ({ round: r.round_number, ...r.constitutional_change }));

  if (!votes.length) {
    el('democracy-view-content').innerHTML = '<div class="empty-state"><span class="empty-icon">🗳️</span><p>No constitutional votes occurred in this simulation.</p></div>';
    return;
  }

  const html = votes.map(v => {
    const for_  = v.votes_for || v.for  || 0;
    const against = v.votes_against || v.against || 0;
    const total = for_ + against;
    const pctFor = total > 0 ? (for_ / total * 100).toFixed(0) : 50;
    const passed = v.passed != null ? v.passed : (for_ > against);
    return `
      <div class="vote-card">
        <div class="vote-header">
          <span>Round ${v.round} — Constitutional Vote</span>
          <span class="pill ${passed ? 'pill-green' : 'pill-red'}">${passed ? '✓ PASSED' : '✗ FAILED'}</span>
        </div>
        ${v.proposal ? `<div class="reasoning-block"><strong>Proposal:</strong> ${v.proposal}</div>` : ''}
        <div style="margin-top:0.75rem">
          <div style="display:flex; justify-content:space-between; font-size:0.72rem; margin-bottom:0.35rem">
            <span style="color:#4ade80">For: ${for_}</span>
            <span style="color:#f87171">Against: ${against}</span>
          </div>
          <div class="vote-bar-wrap"><div class="vote-bar-inner" style="width:${pctFor}%"></div></div>
        </div>
        ${v.changes ? `<div style="margin-top:0.75rem; font-size:0.72rem; color:#94a3b8">${Object.entries(v.changes).map(([k,v2]) => `<div class="stat-row"><span class="stat-label">${k}</span><span class="stat-value mono">${JSON.stringify(v2)}</span></div>`).join('')}</div>` : ''}
      </div>
    `;
  }).join('');

  el('democracy-view-content').innerHTML = `
    <div class="kpi-grid" style="grid-template-columns:repeat(3,1fr);margin-bottom:1.5rem">
      <div class="kpi-card kpi-purple"><div class="kpi-label">Total Votes</div><div class="kpi-value">${votes.length}</div></div>
      <div class="kpi-card kpi-green"><div class="kpi-label">Passed</div><div class="kpi-value">${votes.filter(v=>(v.passed!=null?v.passed:((v.votes_for||v.for||0)>(v.votes_against||v.against||0)))).length}</div></div>
      <div class="kpi-card kpi-red"><div class="kpi-label">Failed</div><div class="kpi-value">${votes.filter(v=>!(v.passed!=null?v.passed:((v.votes_for||v.for||0)>(v.votes_against||v.against||0)))).length}</div></div>
    </div>
    <div style="display:flex;flex-direction:column;gap:0">${html}</div>
  `;
}

// ── Agent List & Selection ─────────────────────────────────────
function renderAgentList() {
  const agentIds = State.meta.agentIds;
  const list = el('agent-list');
  list.innerHTML = agentIds.map(id => {
    const a = State.agents[id];
    const isDev = a?.group === 'developed';
    return `
      <div class="agent-list-item" id="agent-item-${id}" onclick="selectAgent(${id})">
        <div class="agent-avatar ${isDev ? 'avatar-developed' : 'avatar-developing'}">${id}</div>
        <div class="agent-list-info">
          <div class="agent-list-name">Agent ${id}</div>
          <div class="agent-list-meta">${isDev ? '🏭 Developed' : '🌿 Developing'} · ${a?.strategy || 'LLM'}</div>
        </div>
      </div>
    `;
  }).join('');

  // Search
  el('agent-search').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    agentIds.forEach(id => {
      const item = el(`agent-item-${id}`);
      const a = State.agents[id];
      const match = `${id} ${a?.group}`.toLowerCase().includes(q);
      item.style.display = match ? '' : 'none';
    });
  });
}

function selectAgent(id) {
  State.activeAgent = id;
  // highlight
  State.meta.agentIds.forEach(i => el(`agent-item-${i}`)?.classList.remove('active'));
  el(`agent-item-${id}`)?.classList.add('active');
  renderAgentDetail(id);
}

// ── Agent Deep Dive ─────────────────────────────────────────────
function renderAgentDetail(id) {
  const rounds = State.rounds;
  const agent = State.agents[id];
  const isDev = agent?.group === 'developed';

  // Profile card
  const lastRound = rounds[rounds.length - 1].agents[id];
  const firstRound = rounds[0].agents[id];
  const totalContrib = rounds.reduce((s,r) => s + (r.agents[id]?.ldf_contribution_round || r.agents[id]?.contribution || 0), 0);
  const totalPunGiven = rounds.reduce((s,r) => s + Object.values(r.agents[id]?.assigned_punishments || {}).reduce((a,b) => a+b, 0), 0);
  const totalPunReceived = rounds.reduce((s,r) => s + (r.agents[id]?.received_punishments || 0), 0);
  const totalRewGiven = rounds.reduce((s,r) => s + Object.values(r.agents[id]?.assigned_rewards || {}).reduce((a,b) => a+b, 0), 0);

  el('agent-profile-content').innerHTML = `
    <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem">
      <div class="agent-avatar ${isDev?'avatar-developed':'avatar-developing'}" style="width:56px;height:56px;font-size:1.25rem">${id}</div>
      <div>
        <div style="font-size:1.1rem;font-weight:700">Agent ${id}</div>
        <div style="font-size:0.75rem;color:#94a3b8">${isDev?'🏭 Developed Nation':'🌿 Developing Nation'} · ${agent?.strategy}</div>
      </div>
      <div style="margin-left:auto;text-align:right">
        <div style="font-size:0.65rem;color:#64748b">Final Wealth</div>
        <div style="font-size:1.3rem;font-weight:800;color:${isDev?COLORS.developed:COLORS.developing}">${fmt(lastRound?.wealth)}</div>
        <div style="font-size:0.65rem;color:#64748b">${lastRound?.rank || '—'}</div>
      </div>
    </div>
    <div class="chart-grid chart-grid-2" style="margin-bottom:0.75rem">
      <div>
        <div class="stat-row"><span class="stat-label">Vulnerability</span><span class="stat-value">${agent?.vulnerability}</span></div>
        <div class="stat-row"><span class="stat-label">Historical Emissions</span><span class="stat-value">${agent?.historicalEmissions}</span></div>
        <div class="stat-row"><span class="stat-label">Contribution Capacity</span><span class="stat-value">${agent?.contributionCapacity}</span></div>
        <div class="stat-row"><span class="stat-label">Final Reputation</span><span class="stat-value">${(lastRound?.reputation || 5).toFixed(2)}</span></div>
      </div>
      <div>
        <div class="stat-row"><span class="stat-label">Total Contribution</span><span class="stat-value mono">${fmt(totalContrib)}</span></div>
        <div class="stat-row"><span class="stat-label">Punishments Given</span><span class="stat-value">${totalPunGiven}</span></div>
        <div class="stat-row"><span class="stat-label">Punishments Received</span><span class="stat-value">${totalPunReceived}</span></div>
        <div class="stat-row"><span class="stat-label">Rewards Given</span><span class="stat-value">${totalRewGiven}</span></div>
      </div>
    </div>
  `;

  // Agent wealth + contribution dual chart
  const labels = rounds.map(r => `R${r.round_number}`);
  destroyChart('chart-agent-wealth');
  State.charts['chart-agent-wealth'] = new ApexCharts(el('chart-agent-wealth'), {
    ...APEX_BASE,
    chart: { ...APEX_BASE.chart, type: 'line', height: 220 },
    series: [
      { name: 'Wealth', data: rounds.map(r => +(r.agents[id]?.wealth || 0).toFixed(2)) },
      { name: 'Payoff', data: rounds.map(r => +(r.agents[id]?.payoff || 0).toFixed(2)) },
      { name: 'Contribution', data: rounds.map(r => +(r.agents[id]?.contribution || 0).toFixed(2)) },
    ],
    colors: [isDev ? COLORS.developed : COLORS.developing, COLORS.teal, COLORS.amber],
    stroke: { width: [2.5, 2, 1.5], curve: 'smooth', dashArray: [0, 5, 3] },
    xaxis: { ...APEX_BASE.xaxis, categories: labels },
    yaxis: { ...APEX_BASE.yaxis, labels: { formatter: v => fmt(v), style: { colors: '#64748b' } } },
    annotations: buildShockAnnotations(State.rounds),
  });
  State.charts['chart-agent-wealth'].render();

  // Sanctions heatmap: punishments given per target
  const sanctionTargets = {};
  rounds.forEach(r => {
    Object.entries(r.agents[id]?.assigned_punishments || {}).forEach(([target, val]) => {
      sanctionTargets[target] = (sanctionTargets[target] || 0) + val;
    });
  });
  const sanctionHTML = Object.keys(sanctionTargets).length > 0
    ? `<table class="sanction-table"><thead><tr><th>Target Agent</th><th>Total Punishments</th></tr></thead><tbody>
        ${Object.entries(sanctionTargets).sort((a,b) => b[1]-a[1]).map(([t,v]) => `<tr><td>Agent ${t}</td><td class="mono">${v}</td></tr>`).join('')}
        </tbody></table>`
    : '<div class="empty-state" style="padding:1.5rem"><span class="empty-icon">🕊️</span><p>No punishments assigned.</p></div>';

  el('agent-sanctions-content').innerHTML = sanctionHTML;

  // Round timeline
  renderAgentTimeline(id, rounds);
}

function renderAgentTimeline(id, rounds) {
  const container = el('agent-timeline');
  container.innerHTML = rounds.map(r => {
    const a = r.agents[id];
    if (!a) return '';

    const isShock = r.shock_occurred;
    const institution = a.institution_choice || '—';
    const contrib = a.contribution;
    const wealth = a.wealth;
    const rep = a.reputation;
    const payoff = a.payoff;
    const punGiven = Object.entries(a.assigned_punishments || {});
    const rewGiven = Object.entries(a.assigned_rewards || {});
    const trustEntries = Object.entries(a.belief_state?.trust_levels || {});
    const ldfContrib = a.ldf_contribution_round;
    const ldfPayout = a.ldf_payout_round;
    const climateDmg = a.climate_damage_taken_round;

    const trustTags = trustEntries.map(([pid, lv]) =>
      `<span class="trust-tag ${trustClass(lv)}" title="Agent ${pid}: ${lv}">A${pid}: ${lv}</span>`
    ).join('');

    const sanctionLines = [
      ...punGiven.map(([t,v]) => `<span class="pill pill-red">-${v} → A${t}</span>`),
      ...rewGiven.map(([t,v]) => `<span class="pill pill-green">+${v} → A${t}</span>`),
    ].join(' ');

    const ldfLine = State.meta.isLDF ? `
      <div style="display:flex;gap:0.5rem;margin-top:0.5rem;flex-wrap:wrap;font-size:0.7rem">
        ${ldfContrib > 0 ? `<span class="pill pill-blue">💸 Contributed ${fmt(ldfContrib)}</span>` : ''}
        ${ldfPayout  > 0 ? `<span class="pill pill-green">✅ Received ${fmt(ldfPayout)}</span>` : ''}
        ${climateDmg > 0 ? `<span class="pill pill-red">⚡ Damaged ${fmt(climateDmg)}</span>` : ''}
      </div>` : '';

    return `
      <div class="round-entry">
        <div class="round-marker">
          <div class="round-dot ${isShock ? 'shock-round' : ''}">${r.round_number}</div>
          <div class="round-line"></div>
        </div>
        <div class="round-content">
          <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.35rem;flex-wrap:wrap">
            <span class="pill ${institution==='SI'?'pill-purple':'pill-amber'}">${institution}</span>
            <span style="font-size:0.72rem;color:#94a3b8">Contributed <strong style="color:#e2e8f0">${fmt(contrib)}</strong></span>
            <span style="font-size:0.72rem;color:#94a3b8">Wealth <strong style="color:#e2e8f0">${fmt(wealth)}</strong></span>
            <span style="font-size:0.72rem;color:#94a3b8">Payoff <strong style="color:${payoff>=0?'#4ade80':'#f87171'}">${fmt(payoff)}</strong></span>
            <span style="font-size:0.72rem;color:#94a3b8">Rep <strong style="color:#e2e8f0">${rep?.toFixed(2)}</strong></span>
            ${isShock ? `<span class="shock-badge">⚡ Shock ${(r.shock_severity*100).toFixed(0)}%</span>` : ''}
          </div>

          ${a.contribution_reasoning ? `
            <div class="reasoning-block">
              <strong>💡 Contribution reasoning:</strong> ${a.contribution_reasoning}
            </div>` : ''}

          ${sanctionLines ? `<div style="display:flex;gap:0.35rem;margin-top:0.5rem;flex-wrap:wrap">${sanctionLines}</div>` : ''}

          ${a.punishment_reasoning && punGiven.length > 0 ? `
            <div class="reasoning-block" style="margin-top:0.4rem">
              <strong>⚖️ Sanction reasoning:</strong> ${a.punishment_reasoning}
            </div>` : ''}

          ${ldfLine}

          ${trustEntries.length > 0 ? `
            <details style="margin-top:0.5rem">
              <summary style="font-size:0.68rem;color:#64748b;cursor:pointer;user-select:none">
                🧠 Belief state & trust levels (${trustEntries.length} agents)
              </summary>
              <div class="trust-tags" style="margin-top:0.4rem">${trustTags}</div>
              ${a.belief_state?.observations ? `<div class="reasoning-block" style="margin-top:0.4rem"><strong>Observations:</strong> ${a.belief_state.observations}</div>` : ''}
              ${a.belief_state?.institutional_strategy ? `<div class="reasoning-block" style="margin-top:0.25rem"><strong>Strategy:</strong> ${a.belief_state.institutional_strategy}</div>` : ''}
            </details>` : ''}

          ${a.tom_scores && Object.keys(a.tom_scores).length > 0 ? `
            <details style="margin-top:0.35rem">
              <summary style="font-size:0.68rem;color:#64748b;cursor:pointer;user-select:none">
                🔍 ToM Scores (${Object.keys(a.tom_scores).length})
              </summary>
              <div class="trust-tags" style="margin-top:0.4rem">
                ${Object.entries(a.tom_scores).map(([t,s]) => `<span class="trust-tag trust-default">A${t}: ${typeof s === 'object' ? JSON.stringify(s) : s}</span>`).join('')}
              </div>
            </details>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

// ── Network Graph ──────────────────────────────────────────────
function renderNetworkGraph(roundNum) {
  const rounds = State.rounds;
  const round = roundNum ? rounds.find(r => r.round_number === roundNum) : rounds[rounds.length - 1];
  if (!round) return;

  State.networkRound = round.round_number;

  const nodes = new vis.DataSet();
  const edges = new vis.DataSet();

  // Create nodes
  State.meta.agentIds.forEach(id => {
    const agent = State.agents[id];
    const isDev = agent?.group === 'developed';
    const isSI = round.si_members.includes(id);
    nodes.add({
      id,
      label: `A${id}`,
      title: `Agent ${id}\n${agent?.group}\n${isSI ? 'SI' : 'SFI'}\nReputation: ${(round.agents[id]?.reputation || 5).toFixed(2)}`,
      color: {
        background: isDev ? 'rgba(96,165,250,0.3)' : 'rgba(52,211,153,0.3)',
        border: isDev ? '#60a5fa' : '#34d399',
        highlight: { background: isDev ? 'rgba(96,165,250,0.6)' : 'rgba(52,211,153,0.6)', border: isDev ? '#60a5fa' : '#34d399' },
      },
      font: { color: isDev ? '#93c5fd' : '#6ee7b7', size: 12, face: 'Inter' },
      borderWidth: isSI ? 2.5 : 1,
      borderDashes: isSI ? false : [4, 2],
      size: 20 + Math.min((round.agents[id]?.contribution || 0) / 1e6, 20),
    });
  });

  // Edges: punishments (red) and rewards (green)
  const edgeType = el('network-edge-type')?.value || 'punishments';
  let edgeId = 0;
  State.meta.agentIds.forEach(id => {
    const a = round.agents[id];
    if (!a) return;
    const targets = edgeType === 'punishments' ? a.assigned_punishments : a.assigned_rewards;
    Object.entries(targets || {}).forEach(([target, val]) => {
      if (!val) return;
      edges.add({
        id: edgeId++,
        from: id,
        to: parseInt(target),
        value: val,
        title: `${edgeType === 'punishments' ? '⚖️ Punish' : '🎁 Reward'}: ${val}`,
        color: { color: edgeType === 'punishments' ? 'rgba(239,68,68,0.7)' : 'rgba(34,197,94,0.7)', highlight: edgeType === 'punishments' ? '#ef4444' : '#22c55e' },
        arrows: { to: { enabled: true, scaleFactor: 0.6 } },
        width: Math.min(val / 2, 6),
        smooth: { type: 'curvedCW', roundness: 0.2 },
      });
    });
  });

  const container = el('network-canvas');
  if (State.network) { State.network.destroy(); State.network = null; }
  State.network = new vis.Network(container, { nodes, edges }, {
    physics: { stabilization: { iterations: 200 }, barnesHut: { gravitationalConstant: -3000, springLength: 150 } },
    interaction: { hover: true, tooltipDelay: 100 },
    nodes: { shape: 'dot' },
    edges: { smooth: { type: 'curvedCW', roundness: 0.2 } },
  });
}

function populateNetworkRoundSelector() {
  const sel = el('network-round-select');
  if (!sel) return;
  sel.innerHTML = State.rounds.map(r =>
    `<option value="${r.round_number}" ${r.shock_occurred ? '⚡' : ''}>Round ${r.round_number}${r.shock_occurred ? ' ⚡' : ''}</option>`
  ).join('');
  sel.value = State.rounds[State.rounds.length - 1].round_number;
  sel.addEventListener('change', () => renderNetworkGraph(parseInt(sel.value)));

  el('network-edge-type')?.addEventListener('change', () => renderNetworkGraph(parseInt(sel.value)));
}

// ── View Switching ─────────────────────────────────────────────
function switchView(name) {
  State.activeView = name;
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.view === name));
  document.querySelectorAll('.view-section').forEach(s => s.classList.toggle('active', s.id === `view-${name}`));

  if (name === 'network' && State.rounds.length) {
    populateNetworkRoundSelector();
    setTimeout(() => renderNetworkGraph(State.rounds[State.rounds.length - 1].round_number), 100);
  }
}

// ── Bootstrap ──────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initDropZone();
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      if (State.rounds.length) switchView(tab.dataset.view);
    });
  });
});
