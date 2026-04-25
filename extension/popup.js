const STEP_DEFINITIONS = [
  {
    key: "fetch_stock_data",
    title: "Price context",
    caption: "Fetch the move data before we try to explain it.",
  },
  {
    key: "fetch_news",
    title: "Catalyst scan",
    caption: "Pull the headlines most likely to explain the move.",
  },
  {
    key: "align_news_with_price",
    title: "Correlation map",
    caption: "Match timing and sentiment between headlines and price action.",
  },
  {
    key: "final_answer",
    title: "Narrative",
    caption: "Turn the aligned evidence into a clean explanation.",
  },
];

const PREVIEW_ARCHETYPES = [
  {
    key: "breakout",
    direction: "up",
    confidence: 84,
    movePercent: 4.3,
    stockBody: "The sample price view shows a patient opening range followed by a decisive breakout in the strongest window.",
    newsTheme: "upbeat guidance and product momentum",
    headlines: [
      "Preview catalyst: upbeat guidance tone",
      "Preview catalyst: product cycle enthusiasm",
      "Preview catalyst: analyst commentary firming",
    ],
    answerTemplate(symbol) {
      return `Preview explanation for ${symbol}: the strongest upside window in this sample run lines up with ${this.newsTheme}. Momentum then broadened as the second synthetic headline cluster arrived. Connect Live mode when you want real market evidence instead of preview data.`;
    },
  },
  {
    key: "pullback",
    direction: "down",
    confidence: 79,
    movePercent: -3.6,
    stockBody: "The sample price view shows a fragile open and an accelerating selloff as sentiment weakens into the second half of the session.",
    newsTheme: "margin pressure and demand cooling",
    headlines: [
      "Preview catalyst: margin pressure concern",
      "Preview catalyst: softer demand chatter",
      "Preview catalyst: cautious street tone",
    ],
    answerTemplate(symbol) {
      return `Preview explanation for ${symbol}: the sharpest downside window in this sample run aligns with ${this.newsTheme}. Later movement stays weak rather than rebounding, which makes the catalyst chain feel persistent instead of fleeting.`;
    },
  },
  {
    key: "whipsaw",
    direction: "flat",
    confidence: 72,
    movePercent: 1.2,
    stockBody: "The sample price view is choppy, with early strength fading and a late rebound that leaves the session mixed overall.",
    newsTheme: "mixed headlines with no single dominant catalyst",
    headlines: [
      "Preview catalyst: mixed commentary cluster",
      "Preview catalyst: competing macro signals",
      "Preview catalyst: wait-and-see analyst tone",
    ],
    answerTemplate(symbol) {
      return `Preview explanation for ${symbol}: the sample run looks mixed rather than one-directional. The aligned preview headlines suggest competing signals, so the final read is less about one clear catalyst and more about a noisy tug-of-war in sentiment.`;
    },
  },
];

const DEFAULTS = {
  mode: "live",
  apiBaseUrl: "https://marketmind-ai-api.vercel.app",
  symbol: "NVDA",
  range: "5d",
};

const state = {
  mode: DEFAULTS.mode,
  apiBaseUrl: DEFAULTS.apiBaseUrl,
  symbol: DEFAULTS.symbol,
  range: DEFAULTS.range,
  running: false,
  settingsOpen: false,
  historyCount: 0,
  latencyMs: null,
  phase: "idle",
  answer: null,
  evidence: [],
  toolLog: [],
  timeline: createTimeline(),
};

const dom = {};
let logId = 0;

document.addEventListener("DOMContentLoaded", initialize);

async function initialize() {
  cacheDom();
  bindEvents();
  await hydrateSettings();
  resetSurface();
  render();
  window.requestAnimationFrame(() => {
    document.body.classList.add("is-ready");
  });
}

function cacheDom() {
  dom.settingsToggle = document.querySelector("#settingsToggle");
  dom.settingsPanel = document.querySelector("#settingsPanel");
  dom.modeButtons = Array.from(document.querySelectorAll("[data-mode]"));
  dom.saveSettingsButton = document.querySelector("#saveSettingsButton");
  dom.apiBaseUrl = document.querySelector("#apiBaseUrl");
  dom.analysisForm = document.querySelector("#analysisForm");
  dom.symbolInput = document.querySelector("#symbolInput");
  dom.rangeButtons = Array.from(document.querySelectorAll("[data-range]"));
  dom.quickChips = Array.from(document.querySelectorAll("[data-symbol]"));
  dom.analyzeButton = document.querySelector("#analyzeButton");
  dom.analyzeButtonText = document.querySelector("#analyzeButtonText");
  dom.statusPill = document.querySelector("#statusPill");
  dom.modeBadge = document.querySelector("#modeBadge");
  dom.historyBadge = document.querySelector("#historyBadge");
  dom.timeline = document.querySelector("#timeline");
  dom.evidenceGrid = document.querySelector("#evidenceGrid");
  dom.evidenceCount = document.querySelector("#evidenceCount");
  dom.toolLog = document.querySelector("#toolLog");
  dom.resetButton = document.querySelector("#resetButton");
  dom.answerLead = document.querySelector("#answerLead");
  dom.answerBody = document.querySelector("#answerBody");
  dom.confidenceValue = document.querySelector("#confidenceValue");
  dom.confidenceRing = document.querySelector("#confidenceRing");
  dom.footerNote = document.querySelector("#footerNote");
}

function bindEvents() {
  dom.settingsToggle.addEventListener("click", toggleSettingsPanel);
  dom.saveSettingsButton.addEventListener("click", saveSettings);
  dom.analysisForm.addEventListener("submit", handleAnalyze);
  dom.resetButton.addEventListener("click", handleReset);
  dom.symbolInput.addEventListener("input", () => {
    dom.symbolInput.value = normalizeSymbol(dom.symbolInput.value);
  });

  dom.modeButtons.forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });

  dom.rangeButtons.forEach((button) => {
    button.addEventListener("click", () => setRange(button.dataset.range));
  });

  dom.quickChips.forEach((button) => {
    button.addEventListener("click", () => {
      const nextSymbol = normalizeSymbol(button.dataset.symbol || "");
      dom.symbolInput.value = nextSymbol;
      state.symbol = nextSymbol;
      setActiveQuickChip(nextSymbol);
      persistSettings();
      render();
    });
  });
}

async function hydrateSettings() {
  const stored = await storageGet(DEFAULTS);
  state.mode = stored.mode || DEFAULTS.mode;
  state.apiBaseUrl = stored.apiBaseUrl || DEFAULTS.apiBaseUrl;
  state.symbol = normalizeSymbol(stored.symbol || DEFAULTS.symbol);
  state.range = stored.range || DEFAULTS.range;
  dom.symbolInput.value = state.symbol;
  dom.apiBaseUrl.value = state.apiBaseUrl;
  syncModeButtons();
  syncRangeButtons();
  setActiveQuickChip(state.symbol);
}

async function saveSettings() {
  state.apiBaseUrl = sanitizeBaseUrl(dom.apiBaseUrl.value) || DEFAULTS.apiBaseUrl;
  dom.apiBaseUrl.value = state.apiBaseUrl;
  await persistSettings();
  pushLog({
    kind: "system",
    title: "Settings saved",
    body: `Mode is ${capitalize(state.mode)} and backend URL is ${state.apiBaseUrl}.`,
  });
  render();
}

function toggleSettingsPanel() {
  state.settingsOpen = !state.settingsOpen;
  dom.settingsPanel.hidden = !state.settingsOpen;
  dom.settingsToggle.setAttribute("aria-expanded", String(state.settingsOpen));
}

function setMode(mode) {
  state.mode = mode === "live" ? "live" : "preview";
  syncModeButtons();
  updateAnalyzeButtonLabel();
  persistSettings();
  render();
}

function setRange(range) {
  state.range = range;
  syncRangeButtons();
  persistSettings();
  render();
}

function syncModeButtons() {
  dom.modeButtons.forEach((button) => {
    const isActive = button.dataset.mode === state.mode;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
}

function syncRangeButtons() {
  dom.rangeButtons.forEach((button) => {
    const isActive = button.dataset.range === state.range;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-checked", String(isActive));
  });
}

function setActiveQuickChip(symbol) {
  dom.quickChips.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.symbol === symbol);
  });
}

async function handleAnalyze(event) {
  event.preventDefault();

  if (state.running) {
    return;
  }

  const symbol = normalizeSymbol(dom.symbolInput.value);
  if (!symbol) {
    enterErrorState("Enter a valid stock symbol before starting the analysis.");
    return;
  }

  state.symbol = symbol;
  state.apiBaseUrl = sanitizeBaseUrl(dom.apiBaseUrl.value) || DEFAULTS.apiBaseUrl;
  setActiveQuickChip(state.symbol);
  await persistSettings();

  resetSurface();
  state.running = true;
  state.phase = "running";
  render();

  const start = performance.now();

  try {
    if (state.mode === "live") {
      await runLiveAnalysis();
    } else {
      await runPreviewAnalysis();
    }

    state.phase = "success";
    state.latencyMs = Math.round(performance.now() - start);
  } catch (error) {
    state.phase = "error";
    state.latencyMs = Math.round(performance.now() - start);
    pushLog({
      kind: "error",
      title: "Analysis halted",
      body: error instanceof Error ? error.message : "Unknown error",
    });
    if (!state.answer) {
      state.answer = {
        lead: "The run needs attention",
        body: error instanceof Error ? error.message : "The extension could not finish this run.",
        confidence: "--",
      };
    }
  } finally {
    state.running = false;
    render();
  }
}

function handleReset() {
  resetSurface();
  state.phase = "idle";
  state.running = false;
  render();
}

async function runPreviewAnalysis() {
  const symbol = state.symbol;
  const range = state.range;
  const history = [];
  const preview = buildPreviewDataset(symbol, range);

  pushLog({
    kind: "system",
    title: "Preview mode started",
    body: "This run uses clearly labeled synthetic data so you can test the UI before the live backend is connected.",
  });

  await executePreviewStep({
    tool: "fetch_stock_data",
    input: { symbol, range },
    output: preview.stockOutput,
    history,
    evidenceCard: preview.stockEvidence,
  });

  await executePreviewStep({
    tool: "fetch_news",
    input: { query: `${symbol} stock`, range },
    output: preview.newsOutput,
    history,
    evidenceCard: preview.newsEvidence,
  });

  await executePreviewStep({
    tool: "align_news_with_price",
    input: {
      news: preview.newsOutput,
      prices: preview.stockOutput,
    },
    output: preview.alignmentOutput,
    history,
    evidenceCard: preview.alignmentEvidence,
  });

  setTimelineState("final_answer", "active");
  pushLog({
    kind: "final",
    title: "Preview explanation ready",
    body: preview.finalAnswer.body,
  });
  await wait(360);

  state.historyCount = history.length + 1;
  state.answer = preview.finalAnswer;
  setTimelineState("final_answer", "done");
}

async function executePreviewStep({ tool, input, output, history, evidenceCard }) {
  const thought = previewThought(tool);
  const toolCall = {
    type: "tool_call",
    thought,
    tool,
    input,
  };

  history.push(toolCall);
  state.historyCount = history.length;
  setTimelineState(tool, "active");
  pushLog({
    kind: "call",
    title: formatToolName(tool),
    body: thought,
  });
  render();
  await wait(420);

  const toolResult = {
    type: "tool_result",
    tool,
    output,
  };

  history.push(toolResult);
  state.historyCount = history.length;
  state.evidence = [evidenceCard, ...state.evidence].slice(0, 6);
  setTimelineState(tool, "done");
  pushLog({
    kind: "result",
    title: `${formatToolName(tool)} complete`,
    body: summarizeToolResult(tool, output, true),
  });
  render();
  await wait(260);
}

async function runLiveAnalysis() {
  const baseUrl = sanitizeBaseUrl(state.apiBaseUrl);
  if (!baseUrl) {
    throw new Error("Add a backend URL before switching to Live mode.");
  }

  const symbol = state.symbol;
  const range = state.range;
  const history = [];

  pushLog({
    kind: "system",
    title: "Live mode started",
    body: `Sending the first request to ${baseUrl}/analyze.`,
  });

  for (let turn = 0; turn < 8; turn += 1) {
    const response = await postJson(`${baseUrl}/analyze`, {
      symbol,
      range,
      history,
    });

    if (response.type === "tool_call") {
      history.push(response);
      state.historyCount = history.length;
      setTimelineState(response.tool, "active");
      pushLog({
        kind: "call",
        title: formatToolName(response.tool),
        body: response.thought || "The agent requested the next tool step.",
      });
      render();

      const output = await postJson(`${baseUrl}/tools/${response.tool}`, response.input || {});
      const result = {
        type: "tool_result",
        tool: response.tool,
        output,
      };

      history.push(result);
      state.historyCount = history.length;
      state.evidence = [buildLiveEvidenceCard(response.tool, output), ...state.evidence].slice(0, 6);
      setTimelineState(response.tool, "done");
      pushLog({
        kind: "result",
        title: `${formatToolName(response.tool)} complete`,
        body: summarizeToolResult(response.tool, output, false),
      });
      render();
      continue;
    }

    if (response.type === "final_answer") {
      setTimelineState("final_answer", "active");
      pushLog({
        kind: "final",
        title: "Live explanation ready",
        body: response.answer || "Final answer received.",
      });
      state.answer = {
        lead: "Live explanation ready",
        body: response.answer || "No answer text was returned.",
        confidence: response.confidence || "--",
      };
      setTimelineState("final_answer", "done");
      state.historyCount = history.length + 1;
      return;
    }

    throw new Error("The backend returned an unsupported response shape.");
  }

  throw new Error("The live workflow did not finish within the expected number of turns.");
}

function buildPreviewDataset(symbol, range) {
  const archetype = PREVIEW_ARCHETYPES[hashString(symbol) % PREVIEW_ARCHETYPES.length];
  const directionTone =
    archetype.direction === "up" ? "positive" : archetype.direction === "down" ? "negative" : "neutral";
  const percent = Math.abs(archetype.movePercent).toFixed(1);

  const articles = archetype.headlines.map((headline, index) => ({
    title: `${headline} for ${symbol}`,
    published_at: `Preview window ${index + 1}`,
    source: "Demo Feed",
    url: "#",
    summary: "Synthetic sample headline for testing the extension UI.",
  }));

  return {
    stockOutput: {
      symbol,
      range,
      prices: [
        { timestamp: "Preview window 1", open: 100, high: 103, low: 99, close: 102 },
        { timestamp: "Preview window 2", open: 102, high: 105, low: 101, close: 104 },
        { timestamp: "Preview window 3", open: 104, high: 106, low: 103, close: 105 },
      ],
    },
    newsOutput: {
      query: `${symbol} stock`,
      range,
      articles,
    },
    alignmentOutput: {
      symbol,
      range,
      aligned_moves: [
        {
          timestamp: "Preview window 2",
          direction: archetype.direction,
          price_change_percent: archetype.movePercent,
          price_context: "Synthetic move window used to preview the UI.",
          correlated_news: articles.slice(0, 2),
        },
      ],
    },
    stockEvidence: {
      tone: directionTone,
      label: "Preview price context",
      meta: `${range.toUpperCase()} sample move`,
      title: `${symbol} shows a ${archetype.direction === "up" ? "breakout-style" : archetype.direction === "down" ? "selloff-style" : "mixed"} preview pattern`,
      body: archetype.stockBody,
    },
    newsEvidence: {
      tone: "neutral",
      label: "Preview catalyst cluster",
      meta: `${articles.length} sample headlines`,
      title: `${symbol} headlines are grouped into one visible catalyst theme`,
      body: `This preview run uses synthetic headlines around ${archetype.newsTheme} so the popup can demonstrate article cards, sequencing, and alignment states without implying live news coverage.`,
    },
    alignmentEvidence: {
      tone: directionTone,
      label: "Preview alignment",
      meta: `${percent}% sample move`,
      title: `The strongest move window lines up with the headline cluster`,
      body: `The extension surfaces one clean explanation instead of a loose list. In this preview path, the move and the headlines are intentionally staged to show how the final UI should narrate causality.`,
    },
    finalAnswer: {
      lead:
        archetype.direction === "up"
          ? `${symbol} looks catalyst-led in this preview run`
          : archetype.direction === "down"
            ? `${symbol} looks sentiment-driven in this preview run`
            : `${symbol} looks mixed in this preview run`,
      body: archetype.answerTemplate(symbol),
      confidence: `${archetype.confidence}%`,
    },
  };
}

function buildLiveEvidenceCard(tool, output) {
  if (tool === "fetch_stock_data") {
    const prices = Array.isArray(output?.prices) ? output.prices.length : 0;
    return {
      tone: "neutral",
      label: "Live price result",
      meta: `${prices} data points`,
      title: "Price context loaded",
      body: prices > 0
        ? `The backend returned ${prices} price points. This card is ready to become a richer price snapshot when you connect real chart summaries.`
        : "The backend returned a stock payload, but it did not include a populated price array.",
    };
  }

  if (tool === "fetch_news") {
    const articles = Array.isArray(output?.articles) ? output.articles.length : 0;
    return {
      tone: "neutral",
      label: "Live news result",
      meta: `${articles} articles`,
      title: "News scan loaded",
      body: articles > 0
        ? `The backend returned ${articles} related articles. The popup is ready to turn them into evidence cards with timestamps and source labels.`
        : "The backend returned a news payload, but it did not include article entries.",
    };
  }

  const moves = Array.isArray(output?.aligned_moves) ? output.aligned_moves.length : 0;
  return {
    tone: "positive",
    label: "Live alignment result",
    meta: `${moves} aligned moves`,
    title: "Correlation view loaded",
    body: moves > 0
      ? `The backend returned ${moves} aligned move windows. This is the final evidence layer before the explanation is generated.`
      : "The backend returned an alignment payload, but it did not include aligned move windows.",
  };
}

function setTimelineState(targetKey, targetState) {
  state.timeline = state.timeline.map((step) => {
    if (step.key === targetKey) {
      return { ...step, state: targetState };
    }

    if (targetState === "active" && step.state === "active") {
      return { ...step, state: "pending" };
    }

    return step;
  });
}

function resetSurface() {
  state.historyCount = 0;
  state.latencyMs = null;
  state.answer = null;
  state.evidence = [];
  state.toolLog = [];
  state.timeline = createTimeline();
}

function render() {
  renderStatus();
  renderTimeline();
  renderEvidence();
  renderToolLog();
  renderAnswer();
  renderBadges();
  renderFooter();
  updateAnalyzeButtonLabel();
}

function renderStatus() {
  dom.statusPill.classList.remove("is-running", "is-success", "is-error");

  if (state.phase === "running") {
    dom.statusPill.textContent = state.mode === "live" ? "Running live loop" : "Walking preview loop";
    dom.statusPill.classList.add("is-running");
  } else if (state.phase === "success") {
    const modeLabel = capitalize(state.mode);
    dom.statusPill.textContent = state.latencyMs ? `${modeLabel} complete in ${state.latencyMs}ms` : `${modeLabel} complete`;
    dom.statusPill.classList.add("is-success");
  } else if (state.phase === "error") {
    dom.statusPill.textContent = "Run needs attention";
    dom.statusPill.classList.add("is-error");
  } else {
    dom.statusPill.textContent = state.mode === "live" ? "Live ready" : "Preview ready";
  }

  dom.analyzeButton.disabled = state.running;
}

function renderBadges() {
  dom.modeBadge.textContent = state.mode === "live" ? "Live Mode" : "Preview Mode";
  dom.historyBadge.textContent = `History ${state.historyCount}`;
}

function renderTimeline() {
  dom.timeline.innerHTML = "";

  state.timeline.forEach((step, index) => {
    const item = document.createElement("li");
    item.className = `timeline__item ${step.state === "active" ? "is-active" : ""} ${step.state === "done" ? "is-done" : ""}`.trim();

    const marker = document.createElement("div");
    marker.className = "timeline__marker";
    marker.textContent = step.state === "done" ? "✓" : String(index + 1);

    const body = document.createElement("div");
    body.className = "timeline__body";

    const title = document.createElement("p");
    title.className = "timeline__title";
    title.textContent = step.title;

    const caption = document.createElement("p");
    caption.className = "timeline__caption";
    caption.textContent = step.caption;

    body.append(title, caption);
    item.append(marker, body);
    dom.timeline.append(item);
  });
}

function renderEvidence() {
  dom.evidenceGrid.innerHTML = "";

  if (state.evidence.length === 0) {
    dom.evidenceGrid.innerHTML = `<div class="empty-state">Evidence cards will land here as each tool completes. The layout is designed to keep the move story readable even in a small popup.</div>`;
    dom.evidenceCount.textContent = "0 cards";
    return;
  }

  dom.evidenceCount.textContent = `${state.evidence.length} cards`;

  state.evidence.forEach((card) => {
    const article = document.createElement("article");
    article.className = `evidence-card evidence-card--${card.tone || "neutral"}`;

    const meta = document.createElement("div");
    meta.className = "evidence-card__meta";
    meta.innerHTML = `<span>${escapeHtml(card.label)}</span><span>${escapeHtml(card.meta)}</span>`;

    const title = document.createElement("h3");
    title.className = "evidence-card__title";
    title.textContent = card.title;

    const body = document.createElement("p");
    body.className = "evidence-card__body";
    body.textContent = card.body;

    article.append(meta, title, body);
    dom.evidenceGrid.append(article);
  });
}

function renderToolLog() {
  dom.toolLog.innerHTML = "";

  if (state.toolLog.length === 0) {
    dom.toolLog.innerHTML = `<div class="empty-state">Tool calls, tool results, and the final answer will appear here in the exact order the agent loop runs.</div>`;
    return;
  }

  state.toolLog.forEach((entry) => {
    const wrapper = document.createElement("article");
    wrapper.className = "log-entry";

    const top = document.createElement("div");
    top.className = "log-entry__top";

    const badge = document.createElement("span");
    badge.className = `log-entry__badge log-entry__badge--${entry.kind}`;
    badge.textContent = entry.kind;

    const time = document.createElement("span");
    time.className = "log-entry__time";
    time.textContent = entry.time;

    top.append(badge, time);

    const title = document.createElement("p");
    title.className = "log-entry__title";
    title.textContent = entry.title;

    const body = document.createElement("p");
    body.className = "log-entry__body";
    body.textContent = entry.body;

    wrapper.append(top, title, body);
    dom.toolLog.append(wrapper);
  });
}

function renderAnswer() {
  if (!state.answer) {
    dom.answerLead.textContent = "No explanation yet";
    dom.answerBody.textContent = "Run a symbol through the popup to see the timeline, tool log, and explanation build in order.";
    dom.confidenceValue.textContent = "--";
    dom.confidenceRing.style.setProperty("--confidence-angle", "0deg");
    return;
  }

  dom.answerLead.textContent = state.answer.lead;
  dom.answerBody.textContent = state.answer.body;
  dom.confidenceValue.textContent = state.answer.confidence;
  dom.confidenceRing.style.setProperty("--confidence-angle", `${confidenceToDegrees(state.answer.confidence)}deg`);
}

function renderFooter() {
  if (state.mode === "live") {
    dom.footerNote.textContent =
      "Live mode expects a backend that exposes POST /analyze and POST /tools/<tool_name>. Preview mode is still available for UI testing when the backend is offline.";
    return;
  }

  dom.footerNote.textContent =
    "Preview mode uses synthetic sample data only for demonstrating the UX. Switch to Live mode when your backend endpoints are ready.";
}

function updateAnalyzeButtonLabel() {
  if (state.running) {
    dom.analyzeButtonText.textContent = state.mode === "live" ? "Running Live Analysis" : "Building Preview Story";
    return;
  }

  dom.analyzeButtonText.textContent = state.mode === "live" ? "Run Live Analysis" : "Analyze With Preview";
}

function pushLog({ kind, title, body }) {
  logId += 1;
  state.toolLog = [
    ...state.toolLog,
    {
      id: logId,
      kind,
      title,
      body,
      time: timestamp(),
    },
  ].slice(-18);
}

function createTimeline() {
  return STEP_DEFINITIONS.map((step) => ({
    ...step,
    state: "pending",
  }));
}

function previewThought(tool) {
  if (tool === "fetch_stock_data") {
    return "Fetching stock data first so the move story starts from actual price context.";
  }

  if (tool === "fetch_news") {
    return "Price context is ready, so the next step is scanning headlines that may explain the move.";
  }

  return "Both datasets are ready, so the next step is aligning headlines with the move windows before producing an explanation.";
}

function summarizeToolResult(tool, output, previewMode) {
  if (tool === "fetch_stock_data") {
    const count = Array.isArray(output?.prices) ? output.prices.length : 0;
    return previewMode
      ? `Loaded ${count} sample price windows for the preview timeline.`
      : `Loaded ${count} price points from the live backend.`;
  }

  if (tool === "fetch_news") {
    const count = Array.isArray(output?.articles) ? output.articles.length : 0;
    return previewMode
      ? `Loaded ${count} synthetic headlines for the preview catalyst cluster.`
      : `Loaded ${count} articles from the live backend.`;
  }

  const count = Array.isArray(output?.aligned_moves) ? output.aligned_moves.length : 0;
  return previewMode
    ? `Built ${count} sample aligned move windows for the explanation stage.`
    : `Built ${count} aligned move windows from the live backend.`;
}

function enterErrorState(message) {
  state.phase = "error";
  state.answer = {
    lead: "The run needs attention",
    body: message,
    confidence: "--",
  };
  pushLog({
    kind: "error",
    title: "Input needed",
    body: message,
  });
  render();
}

function normalizeSymbol(value) {
  return value.toUpperCase().replace(/[^A-Z.-]/g, "").slice(0, 10);
}

function sanitizeBaseUrl(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function capitalize(value) {
  return value ? `${value[0].toUpperCase()}${value.slice(1)}` : "";
}

function formatToolName(tool) {
  return tool
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function hashString(value) {
  return Array.from(value).reduce((accumulator, character) => accumulator + character.charCodeAt(0), 0);
}

function confidenceToDegrees(confidence) {
  const numeric = Number.parseInt(String(confidence).replace("%", ""), 10);
  if (Number.isNaN(numeric)) {
    return 0;
  }

  return Math.max(0, Math.min(360, numeric * 3.6));
}

function timestamp() {
  return new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function wait(duration) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, duration);
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function storageGet(defaults) {
  return new Promise((resolve) => {
    if (!chrome?.storage?.local) {
      resolve(defaults);
      return;
    }

    chrome.storage.local.get(defaults, (stored) => {
      resolve(stored);
    });
  });
}

function storageSet(values) {
  return new Promise((resolve) => {
    if (!chrome?.storage?.local) {
      resolve();
      return;
    }

    chrome.storage.local.set(values, () => {
      resolve();
    });
  });
}

function persistSettings() {
  return storageSet({
    mode: state.mode,
    apiBaseUrl: state.apiBaseUrl,
    symbol: state.symbol,
    range: state.range,
  });
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Request failed for ${url} with status ${response.status}.`);
  }

  return response.json();
}
