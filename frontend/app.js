const API_BASE = "/api/v1";
const SESSION_KEY = "industry-rag-session-id";

const elements = {
  sessionChip: document.getElementById("sessionChip"),
  copySessionBtn: document.getElementById("copySessionBtn"),
  newSessionBtn: document.getElementById("newSessionBtn"),
  healthBtn: document.getElementById("healthBtn"),
  metricsBtn: document.getElementById("metricsBtn"),
  modelsBtn: document.getElementById("modelsBtn"),
  healthOutput: document.getElementById("healthOutput"),
  metricsOutput: document.getElementById("metricsOutput"),
  modelsOutput: document.getElementById("modelsOutput"),
  ingestForm: document.getElementById("ingestForm"),
  pdfFile: document.getElementById("pdfFile"),
  ingestStatus: document.getElementById("ingestStatus"),
  ingestOutput: document.getElementById("ingestOutput"),
  queryModeBtn: document.getElementById("queryModeBtn"),
  streamModeBtn: document.getElementById("streamModeBtn"),
  chatMessages: document.getElementById("chatMessages"),
  chatForm: document.getElementById("chatForm"),
  chatInput: document.getElementById("chatInput"),
  sendBtn: document.getElementById("sendBtn"),
};

let chatMode = "query";
let currentSessionId = "";

function createSessionId() {
  if (crypto.randomUUID) {
    return `session-${crypto.randomUUID()}`;
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getSessionId() {
  if (!currentSessionId) {
    setSessionId(createSessionId());
  }

  return currentSessionId;
}

function initializeSession() {
  const saved = localStorage.getItem(SESSION_KEY);
  setSessionId(saved || createSessionId());
}

function setSessionId(sessionId) {
  currentSessionId = sessionId;
  localStorage.setItem(SESSION_KEY, currentSessionId);
  elements.sessionChip.textContent = compactSessionId(currentSessionId);
  elements.sessionChip.title = currentSessionId;
}

function compactSessionId(sessionId) {
  if (sessionId.length <= 24) {
    return sessionId;
  }

  return `${sessionId.slice(0, 16)}...${sessionId.slice(-8)}`;
}

function formatJson(value) {
  return JSON.stringify(value, null, 2);
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(options.headers || {}),
    },
  });

  const text = await response.text();
  let payload = text;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { raw: text };
  }

  if (!response.ok) {
    const message = typeof payload === "string" ? payload : payload.detail || payload.message || response.statusText;
    throw new Error(message);
  }

  return payload;
}

async function loadPanel(button, output, path) {
  button.disabled = true;
  output.textContent = "Loading...";
  try {
    const data = await requestJson(path);
    output.textContent = formatJson(data);
  } catch (error) {
    output.textContent = formatJson({ status: "error", message: error.message });
  } finally {
    button.disabled = false;
  }
}

function setStatus(message, type = "") {
  elements.ingestStatus.textContent = message;
  elements.ingestStatus.className = `status-line ${type}`.trim();
}

function addMessage(role, text) {
  const message = document.createElement("div");
  message.className = `message ${role}`;
  message.textContent = text;
  elements.chatMessages.appendChild(message);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  return message;
}

function addLoadingMessage() {
  const message = document.createElement("div");
  message.className = "message loading";

  const spinner = document.createElement("span");
  spinner.className = "spinner";

  const label = document.createElement("span");
  label.textContent = "Generating response...";

  message.append(spinner, label);
  elements.chatMessages.appendChild(message);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  return message;
}

function appendSources(messageElement, data) {
  const sources = Array.isArray(data.sources) ? data.sources : [];
  if (!sources.length) {
    return;
  }

  const sourceBlock = document.createElement("div");
  sourceBlock.className = "sources";
  sourceBlock.textContent = sources
    .map((source, index) => {
      const file = source.source_file || "unknown source";
      const score = typeof source.relevance_score === "number" ? ` (${source.relevance_score.toFixed(3)})` : "";
      return `${index + 1}. ${file}${score}`;
    })
    .join("\n");
  messageElement.appendChild(sourceBlock);
}

function appendMeta(messageElement, data) {
  const meta = document.createElement("span");
  meta.className = "message-meta";

  const parts = [];
  if (data.model_used) {
    parts.push(`model: ${data.model_used}`);
  }
  if (typeof data.latency_ms === "number") {
    parts.push(`latency: ${data.latency_ms.toFixed(0)} ms`);
  }
  if (typeof data.confidence_score === "number") {
    parts.push(`confidence: ${data.confidence_score.toFixed(3)}`);
  }

  if (parts.length) {
    meta.textContent = parts.join(" | ");
    messageElement.appendChild(meta);
  }
}

function setMode(mode) {
  chatMode = mode;
  elements.queryModeBtn.classList.toggle("active", mode === "query");
  elements.streamModeBtn.classList.toggle("active", mode === "stream");
}

function setChatBusy(isBusy) {
  elements.chatInput.disabled = isBusy;
  elements.sendBtn.disabled = isBusy;
  elements.queryModeBtn.disabled = isBusy;
  elements.streamModeBtn.disabled = isBusy;
  elements.chatInput.placeholder = isBusy ? "Waiting for response..." : "Ask a question about your documents...";
}

async function sendQuery(query, sessionId) {
  const data = await requestJson("/query", {
    method: "POST",
    body: JSON.stringify({ query, session_id: sessionId }),
  });

  const assistantMessage = addMessage("assistant", data.answer || formatJson(data));
  appendMeta(assistantMessage, data);
  appendSources(assistantMessage, data);
}

async function sendStream(query, sessionId, loadingMessage) {
  const response = await fetch(`${API_BASE}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId }),
  });

  if (!response.ok || !response.body) {
    throw new Error(await response.text());
  }

  loadingMessage.remove();
  const assistantMessage = addMessage("assistant", "");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    assistantMessage.textContent += decoder.decode(value, { stream: true });
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  }

  assistantMessage.textContent += decoder.decode();
}

elements.copySessionBtn.addEventListener("click", async () => {
  const sessionId = getSessionId();
  try {
    await navigator.clipboard.writeText(sessionId);
    elements.copySessionBtn.textContent = "Copied";
    setTimeout(() => {
      elements.copySessionBtn.textContent = "Copy";
    }, 1200);
  } catch {
    elements.copySessionBtn.textContent = "Copy failed";
    setTimeout(() => {
      elements.copySessionBtn.textContent = "Copy";
    }, 1200);
  }
});

elements.newSessionBtn.addEventListener("click", () => {
  setSessionId(createSessionId());
  elements.chatMessages.replaceChildren();
});

elements.healthBtn.addEventListener("click", () => {
  loadPanel(elements.healthBtn, elements.healthOutput, "/health");
});

elements.metricsBtn.addEventListener("click", () => {
  loadPanel(elements.metricsBtn, elements.metricsOutput, "/metrics");
});

elements.modelsBtn.addEventListener("click", () => {
  loadPanel(elements.modelsBtn, elements.modelsOutput, "/models");
});

elements.ingestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = elements.pdfFile.files[0];
  if (!file) {
    setStatus("Select a PDF file first.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  setStatus("Uploading and ingesting PDF...");
  elements.ingestOutput.textContent = "Loading...";

  try {
    const data = await requestJson("/ingest", {
      method: "POST",
      body: formData,
    });
    const ok = data.status === "success";
    setStatus(ok ? "PDF ingested successfully." : "PDF ingestion returned an error.", ok ? "success" : "error");
    elements.ingestOutput.textContent = formatJson(data);
  } catch (error) {
    setStatus("PDF ingestion failed.", "error");
    elements.ingestOutput.textContent = formatJson({ status: "error", message: error.message });
  }
});

elements.queryModeBtn.addEventListener("click", () => setMode("query"));
elements.streamModeBtn.addEventListener("click", () => setMode("stream"));

elements.chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = elements.chatInput.value.trim();
  if (!query) {
    return;
  }

  const sessionId = getSessionId();
  elements.chatInput.value = "";
  setChatBusy(true);
  addMessage("user", query);
  const loadingMessage = addLoadingMessage();

  try {
    if (chatMode === "stream") {
      await sendStream(query, sessionId, loadingMessage);
    } else {
      await sendQuery(query, sessionId);
      loadingMessage.remove();
    }
  } catch (error) {
    loadingMessage.remove();
    addMessage("error", error.message || "Request failed.");
  } finally {
    setChatBusy(false);
    elements.chatInput.focus();
  }
});

elements.chatInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.chatForm.requestSubmit();
  }
});

initializeSession();
setMode("query");
