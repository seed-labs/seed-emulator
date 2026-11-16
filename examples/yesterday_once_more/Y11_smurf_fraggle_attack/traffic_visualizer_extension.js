(() => {
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
    serviceTimeline.replaceChildren();
    bandwidthTimeline.replaceChildren();
    const message = document.createElement('span');
    message.className = 'timeline-empty';
    message.textContent = 'Waiting for the legitimate client';
    serviceTimeline.appendChild(message);
    const bandwidthMessage = document.createElement('span');
    bandwidthMessage.className = 'timeline-empty';
    bandwidthMessage.textContent = 'Waiting for the first bandwidth probe';
    bandwidthTimeline.appendChild(bandwidthMessage);
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

    const isStale = impact.last_probe_age_seconds > impactConfig.impact_stale_seconds;
    const latencyIsHigh = impact.latest_latency_ms >= impactConfig.impact_latency_warning_ms;
    const bandwidthIsStale = impact.bandwidth_sample_count
      && impact.last_bandwidth_age_seconds > impactConfig.impact_bandwidth_stale_seconds;
    if (isStale) {
      setStatus('UNREACHABLE', 'unreachable');
    } else if (impact.latest_success === false) {
      setStatus('FAILED', 'unreachable');
    } else if (
      impact.success_rate < 100
      || latencyIsHigh
      || impact.latest_bandwidth_success === false
      || bandwidthIsStale
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
      if (bandwidthIsStale) {
        serviceThroughput.textContent = 'Stale';
      } else if (impact.latest_bandwidth_success === false) {
        serviceThroughput.textContent = 'Failed';
      } else {
        serviceThroughput.textContent = `${impact.latest_throughput_mbps.toFixed(2)} Mbps`;
      }
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
    const bandwidthSamples = impact.samples
      .filter((sample) => sample.bandwidth_success !== null)
      .slice(-30);
    if (!bandwidthSamples.length) {
      const message = document.createElement('span');
      message.className = 'timeline-empty';
      message.textContent = 'Waiting for the first bandwidth probe';
      bandwidthTimeline.appendChild(message);
      return;
    }
    const maximumThroughput = Math.max(
      1,
      ...bandwidthSamples
        .filter((sample) => sample.bandwidth_success)
        .map((sample) => sample.throughput_mbps),
    );
    bandwidthSamples.forEach((sample) => {
      const bar = document.createElement('i');
      bar.className = sample.bandwidth_success
        ? 'probe-sample bandwidth-success'
        : 'probe-sample failure';
      const percent = sample.bandwidth_success
        ? Math.max(6, sample.throughput_mbps / maximumThroughput * 100)
        : 100;
      bar.style.height = `${percent}%`;
      bar.title = sample.bandwidth_success
        ? `${sample.throughput_mbps.toFixed(2)} Mbps`
        : 'Failed';
      bandwidthTimeline.appendChild(bar);
    });
  }

  TrafficVisualizer.registerExtension({
    mount({root, config}) {
      root.innerHTML = `
        <div class="extension-grid broadcast-details">
          <div class="extension-card">
            <div class="label">Smurf mode</div>
            <span class="extension-value">ICMP echo replies</span>
          </div>
          <div class="extension-card">
            <div class="label">Fraggle mode</div>
            <span class="extension-value">UDP chargen-like replies</span>
          </div>
          <div class="extension-card">
            <div class="label">Amplifier LAN</div>
            <span class="extension-value" id="broadcast-network"></span>
          </div>
          <div class="extension-card">
            <div class="label">Average observed IP packet</div>
            <span class="extension-value" id="broadcast-average-size">0 B</span>
          </div>
        </div>
        <section class="impact-panel" aria-label="Victim service impact">
          <div class="impact-heading">
            <div>
              <div class="label">Victim impact</div>
              <strong>Legitimate HTTP service</strong>
            </div>
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
      root.querySelector('#broadcast-network').textContent = config.amplifier_network;
      averageSize = root.querySelector('#broadcast-average-size');
      serviceStatus = root.querySelector('#impact-status');
      serviceLatency = root.querySelector('#impact-latency');
      serviceSuccessRate = root.querySelector('#impact-success-rate');
      serviceFailures = root.querySelector('#impact-failures');
      serviceThroughput = root.querySelector('#impact-throughput');
      serviceAverageThroughput = root.querySelector('#impact-average-throughput');
      serviceTimeline = root.querySelector('#impact-timeline');
      bandwidthTimeline = root.querySelector('#bandwidth-timeline');
      showWaiting();
    },
    update(stats, {formatBytes}) {
      averageSize.textContent = formatBytes(stats.average_ip_packet_size);
      updateImpact(stats.impact);
    },
    reset() {
      averageSize.textContent = '0 B';
      showWaiting();
    },
  });
})();
