(() => {
  let requestSize;
  let averageSize;
  let amplificationValue;
  let responseBar;
  let responseScale;
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
    const latencyMessage = document.createElement('span');
    latencyMessage.className = 'timeline-empty';
    latencyMessage.textContent = 'Waiting for the legitimate client';
    serviceTimeline.appendChild(latencyMessage);
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

  function showEmptyState() {
    averageSize.textContent = '0 B';
    amplificationValue.textContent = '0.0x';
    responseBar.style.width = '0%';
    responseScale.textContent = 'Waiting for amplified responses';
  }

  TrafficVisualizer.registerExtension({
    mount({root, config, formatBytes}) {
      root.innerHTML = `
        <div class="extension-grid ntp-details">
          <div class="extension-card">
            <div class="label">Fixed request IP packet</div>
            <span class="extension-value" id="ntp-request-size"></span>
            <span class="extension-note" id="ntp-request-payload"></span>
          </div>
          <div class="extension-card">
            <div class="label">Average response IP packet</div>
            <span class="extension-value" id="ntp-average-size">0 B</span>
          </div>
          <div class="extension-card amplification-card">
            <div class="label">IP-layer byte amplification</div>
            <span class="extension-value amplification-value" id="ntp-amplification">0.0x</span>
          </div>
          <div class="extension-card">
            <div class="label">Lab amplifiers</div>
            <span class="extension-value" id="ntp-amplifiers"></span>
          </div>
        </div>
        <div class="amplification-scale">
          <div class="scale-heading">
            <span>Request-to-response scale</span>
            <span id="ntp-response-scale">Waiting for amplified responses</span>
          </div>
          <div class="scale-row">
            <span class="scale-label">Request</span>
            <div class="scale-track"><span class="scale-bar request-bar"></span></div>
            <span class="scale-number">1x</span>
          </div>
          <div class="scale-row">
            <span class="scale-label">Response</span>
            <div class="scale-track"><span class="scale-bar response-bar" id="ntp-response-bar"></span></div>
            <span class="scale-number" id="ntp-response-number">0.0x</span>
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

      const requestIpBytes = Number(config.request_ip_bytes);
      const requestPayloadBytes = Number(config.request_payload_bytes);
      requestSize = requestIpBytes;
      root.querySelector('#ntp-request-size').textContent = formatBytes(requestIpBytes);
      root.querySelector('#ntp-request-payload').textContent =
        `${formatBytes(requestPayloadBytes)} UDP payload + ` +
        `${formatBytes(requestIpBytes - requestPayloadBytes)} headers`;
      root.querySelector('#ntp-amplifiers').textContent = config.amplifiers;
      averageSize = root.querySelector('#ntp-average-size');
      amplificationValue = root.querySelector('#ntp-amplification');
      responseBar = root.querySelector('#ntp-response-bar');
      responseScale = root.querySelector('#ntp-response-scale');
      const maximum = Number(config.gauge_max_amplification) || 20;
      responseBar.dataset.maximum = String(maximum);
      root.querySelector('.request-bar').style.width = `${100 / maximum}%`;
      impactConfig = {
        impact_latency_warning_ms: Number(config.impact_latency_warning_ms) || 150,
        impact_stale_seconds: Number(config.impact_stale_seconds) || 4,
        impact_chart_max_ms: Number(config.impact_chart_max_ms) || 500,
        impact_bandwidth_stale_seconds: Number(config.impact_bandwidth_stale_seconds) || 12,
      };
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
    update(stats, {formatBytes, root}) {
      updateImpact(stats.impact);
      if (!stats.total_packets) {
        showEmptyState();
        root.querySelector('#ntp-response-number').textContent = '0.0x';
        return;
      }

      const averageResponseBytes = stats.total_ip_bytes / stats.total_packets;
      const amplification = averageResponseBytes / requestSize;
      const formattedAmplification = `${amplification.toFixed(1)}x`;
      const maximum = Number(responseBar.dataset.maximum);

      averageSize.textContent = formatBytes(Math.round(averageResponseBytes));
      amplificationValue.textContent = formattedAmplification;
      responseScale.textContent = `Observed response is ${formattedAmplification} the request size`;
      responseBar.style.width = `${Math.min(amplification / maximum, 1) * 100}%`;
      root.querySelector('#ntp-response-number').textContent = formattedAmplification;
    },
    reset({root}) {
      showEmptyState();
      root.querySelector('#ntp-response-number').textContent = '0.0x';
      showWaiting();
    },
  });
})();
