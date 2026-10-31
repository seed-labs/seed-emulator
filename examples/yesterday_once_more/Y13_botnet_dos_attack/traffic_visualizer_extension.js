(() => {
  let botField;
  let observedRate;
  let averageSize;
  let serviceStatus;
  let serviceLatency;
  let serviceSuccessRate;
  let serviceFailures;
  let serviceThroughput;
  let serviceAverageThroughput;
  let serviceTimeline;
  let bandwidthTimeline;
  let impactConfig;
  let configuredBotCount;
  let connectedBots;
  let runningBots;
  let commandProgress;
  let botnetApiUrl;
  let botnetFetchPending = false;

  function setStatus(label, className) {
    serviceStatus.textContent = label;
    serviceStatus.className = `impact-status ${className}`;
  }

  function showWaiting() {
    setStatus('WAITING', 'waiting');
    serviceLatency.textContent = '--';
    serviceSuccessRate.textContent = '--';
    serviceFailures.textContent = '0';
    serviceThroughput.textContent = '--';
    serviceAverageThroughput.textContent = '--';
    serviceTimeline.innerHTML = '<span class="timeline-empty">Waiting for the legitimate client</span>';
    bandwidthTimeline.innerHTML = '<span class="timeline-empty">Waiting for the first bandwidth probe</span>';
  }

  function updateImpact(impact) {
    if (impact?.probe_api_error) {
      showWaiting();
      setStatus('PROBE OFFLINE', 'unreachable');
      return;
    }
    if (!impact || !impact.sample_count) {
      showWaiting();
      return;
    }

    const stale = impact.last_probe_age_seconds > impactConfig.impact_stale_seconds;
    const highLatency = impact.latest_latency_ms >= impactConfig.impact_latency_warning_ms;
    const staleBandwidth = impact.bandwidth_sample_count
      && impact.last_bandwidth_age_seconds > impactConfig.impact_bandwidth_stale_seconds;
    if (stale) {
      setStatus('UNREACHABLE', 'unreachable');
    } else if (impact.latest_success === false) {
      setStatus('FAILED', 'unreachable');
    } else if (
      impact.success_rate < 100
      || highLatency
      || impact.latest_bandwidth_success === false
      || staleBandwidth
    ) {
      setStatus('DEGRADED', 'degraded');
    } else {
      setStatus('HEALTHY', 'healthy');
    }

    serviceLatency.textContent = impact.latest_latency_ms === null
      ? 'Timeout'
      : `${impact.latest_latency_ms.toFixed(1)} ms`;
    serviceSuccessRate.textContent = `${impact.success_rate.toFixed(1)}%`;
    serviceFailures.textContent = String(impact.failure_count);
    if (!impact.bandwidth_sample_count) {
      serviceThroughput.textContent = '--';
      serviceAverageThroughput.textContent = '--';
    } else {
      serviceAverageThroughput.textContent = impact.average_throughput_mbps === null
        ? '--'
        : `${impact.average_throughput_mbps.toFixed(2)} Mbps`;
      serviceThroughput.textContent = staleBandwidth
        ? 'Stale'
        : impact.latest_bandwidth_success === false
          ? 'Failed'
          : `${impact.latest_throughput_mbps.toFixed(2)} Mbps`;
    }

    serviceTimeline.replaceChildren();
    impact.samples.slice(-30).forEach((sample) => {
      const bar = document.createElement('i');
      bar.className = sample.success ? 'probe-sample success' : 'probe-sample failure';
      const percent = sample.success
        ? Math.max(6, Math.min(sample.latency_ms / impactConfig.impact_chart_max_ms, 1) * 100)
        : 100;
      bar.style.height = `${percent}%`;
      bar.title = sample.success ? `${sample.latency_ms.toFixed(1)} ms` : 'Failed';
      serviceTimeline.appendChild(bar);
    });

    bandwidthTimeline.replaceChildren();
    const samples = impact.samples
      .filter((sample) => sample.bandwidth_success !== null)
      .slice(-30);
    if (!samples.length) {
      bandwidthTimeline.innerHTML = '<span class="timeline-empty">Waiting for the first bandwidth probe</span>';
      return;
    }
    const maximum = Math.max(
      1,
      ...samples.filter((sample) => sample.bandwidth_success).map((sample) => sample.throughput_mbps),
    );
    samples.forEach((sample) => {
      const bar = document.createElement('i');
      bar.className = sample.bandwidth_success
        ? 'probe-sample bandwidth-success'
        : 'probe-sample failure';
      bar.style.height = sample.bandwidth_success
        ? `${Math.max(6, sample.throughput_mbps / maximum * 100)}%`
        : '100%';
      bar.title = sample.bandwidth_success
        ? `${sample.throughput_mbps.toFixed(2)} Mbps`
        : 'Failed';
      bandwidthTimeline.appendChild(bar);
    });
  }

  function renderBots(bots) {
    const visibleCount = Math.min(Math.max(configuredBotCount, bots.length), 24);
    botField.replaceChildren();
    for (let index = 0; index < visibleCount; index += 1) {
      const status = bots[index];
      const bot = document.createElement('span');
      const state = status?.online ? status.agent_state : 'offline';
      bot.className = `bot-node ${state === 'running' ? 'running' : state === 'offline' ? 'offline' : 'online'}`;
      bot.title = status
        ? `${status.bot_id}: ${state} (AS${status.asn || '?'})`
        : `Configured bot ${index + 1}: not registered`;
      bot.style.setProperty('--delay', `${(index % 8) * -0.11}s`);
      bot.innerHTML = '<span class="bot-head"></span><span class="bot-body"></span>';
      botField.appendChild(bot);
    }
    const total = Math.max(configuredBotCount, bots.length);
    if (total > visibleCount) {
      const remainder = document.createElement('span');
      remainder.className = 'bot-remainder';
      remainder.textContent = `+${total - visibleCount}`;
      botField.appendChild(remainder);
    }
  }

  function renderBotnetStatus(botSnapshot, commandSnapshot, root) {
    const bots = botSnapshot.bots || [];
    const online = bots.filter((bot) => bot.online);
    const running = online.filter((bot) => bot.agent_state === 'running');
    const latest = commandSnapshot.commands?.[0];
    connectedBots.textContent = `${botSnapshot.online_count}/${configuredBotCount}`;
    runningBots.textContent = String(running.length);
    commandProgress.textContent = latest
      ? `${latest.state} (${latest.assignment_count} bots)`
      : 'No command';
    renderBots(bots);

    const state = root.querySelector('#attack-state');
    if (running.length) {
      state.textContent = 'COMMAND ACTIVE';
      state.className = 'attack-state active';
    } else {
      state.textContent = 'C2 READY';
      state.className = 'attack-state idle';
    }
  }

  async function fetchBotnetStatus(root) {
    if (!botnetApiUrl || botnetFetchPending) return;
    botnetFetchPending = true;
    try {
      const [botsResponse, commandsResponse] = await Promise.all([
        fetch(`${botnetApiUrl}/api/bots`, {cache: 'no-store'}),
        fetch(`${botnetApiUrl}/api/commands`, {cache: 'no-store'}),
      ]);
      if (!botsResponse.ok || !commandsResponse.ok) throw new Error('BotnetLab API unavailable');
      renderBotnetStatus(await botsResponse.json(), await commandsResponse.json(), root);
    } catch (_error) {
      const state = root.querySelector('#attack-state');
      state.textContent = 'C2 OFFLINE';
      state.className = 'attack-state offline';
      connectedBots.textContent = '--';
      runningBots.textContent = '--';
      commandProgress.textContent = 'Unavailable';
    } finally {
      botnetFetchPending = false;
    }
  }

  TrafficVisualizer.registerExtension({
    mount({root, config}) {
      configuredBotCount = Number(config.bot_count) || 0;
      const botPps = Number(config.bot_pps) || 0;
      const payloadBytes = Number(config.udp_payload_bytes) || 0;
      const offeredLoad = Number(config.offered_load_mbps) || 0;
      root.innerHTML = `
        <section class="botnet-panel" aria-label="Botnet activity">
          <div class="botnet-heading">
            <div><div class="label">Command-and-control</div><strong>Distributed bot activity</strong></div>
            <span class="attack-state idle" id="attack-state">CONNECTING</span>
          </div>
          <div class="bot-field" id="bot-field"></div>
          <div class="extension-grid botnet-details">
            <div class="extension-card"><div class="label">Configured bots</div><span class="extension-value">${configuredBotCount}</span></div>
            <div class="extension-card"><div class="label">Connected bots</div><span class="extension-value" id="connected-bots">--</span></div>
            <div class="extension-card"><div class="label">Running bots</div><span class="extension-value" id="running-bots">--</span></div>
            <div class="extension-card"><div class="label">Latest command</div><span class="extension-value" id="command-progress">Waiting</span></div>
            <div class="extension-card"><div class="label">Default rate per bot</div><span class="extension-value">${botPps} pps</span></div>
            <div class="extension-card"><div class="label">Default UDP payload</div><span class="extension-value">${payloadBytes} B</span></div>
            <div class="extension-card"><div class="label">Default offered load</div><span class="extension-value">${offeredLoad.toFixed(2)} Mbps</span></div>
            <div class="extension-card"><div class="label">Observed attack rate</div><span class="extension-value" id="observed-rate">0.00 Mbps</span></div>
            <div class="extension-card"><div class="label">Average observed IP packet</div><span class="extension-value" id="average-size">0 B</span></div>
          </div>
          <div class="target-line">Fixed lab target: <strong>${config.victim_address}</strong></div>
        </section>
        <section class="impact-panel" aria-label="Victim service impact">
          <div class="impact-heading">
            <div><div class="label">Victim impact</div><strong>Legitimate HTTP service</strong></div>
            <span class="impact-status waiting" id="impact-status">WAITING</span>
          </div>
          <div class="impact-metrics">
            <div><span class="label">Current latency</span><strong id="impact-latency">--</strong></div>
            <div><span class="label">Recent success</span><strong id="impact-success-rate">--</strong></div>
            <div><span class="label">Failures</span><strong id="impact-failures">0</strong></div>
            <div><span class="label">Current goodput</span><strong id="impact-throughput">--</strong></div>
            <div><span class="label">Average goodput</span><strong id="impact-average-throughput">--</strong></div>
          </div>
          <div class="label timeline-label">Latency probes (higher is slower; red is failed)</div>
          <div class="probe-timeline" id="impact-timeline"></div>
          <div class="label timeline-label bandwidth-label">Goodput probes (higher is better; red is failed)</div>
          <div class="probe-timeline" id="bandwidth-timeline"></div>
        </section>`;

      impactConfig = {
        impact_latency_warning_ms: Number(config.impact_latency_warning_ms) || 150,
        impact_stale_seconds: Number(config.impact_stale_seconds) || 4,
        impact_chart_max_ms: Number(config.impact_chart_max_ms) || 500,
        impact_bandwidth_stale_seconds: Number(config.impact_bandwidth_stale_seconds) || 12,
      };
      botField = root.querySelector('#bot-field');
      connectedBots = root.querySelector('#connected-bots');
      runningBots = root.querySelector('#running-bots');
      commandProgress = root.querySelector('#command-progress');
      observedRate = root.querySelector('#observed-rate');
      averageSize = root.querySelector('#average-size');
      serviceStatus = root.querySelector('#impact-status');
      serviceLatency = root.querySelector('#impact-latency');
      serviceSuccessRate = root.querySelector('#impact-success-rate');
      serviceFailures = root.querySelector('#impact-failures');
      serviceThroughput = root.querySelector('#impact-throughput');
      serviceAverageThroughput = root.querySelector('#impact-average-throughput');
      serviceTimeline = root.querySelector('#impact-timeline');
      bandwidthTimeline = root.querySelector('#bandwidth-timeline');
      const botnetApiPort = Number(config.botnet_api_port);
      botnetApiUrl = config.botnet_api_url || (
        botnetApiPort
          ? `${window.location.protocol}//${window.location.hostname}:${botnetApiPort}`
          : ''
      );
      renderBots([]);
      fetchBotnetStatus(root);
      showWaiting();
    },
    update(stats, {root, formatBytes}) {
      observedRate.textContent = `${(stats.ip_bytes_last_second * 8 / 1_000_000).toFixed(2)} Mbps`;
      averageSize.textContent = formatBytes(stats.average_ip_packet_size);
      fetchBotnetStatus(root);
      updateImpact(stats.impact);
    },
    reset({root}) {
      observedRate.textContent = '0.00 Mbps';
      averageSize.textContent = '0 B';
      fetchBotnetStatus(root);
      showWaiting();
    },
  });
})();
