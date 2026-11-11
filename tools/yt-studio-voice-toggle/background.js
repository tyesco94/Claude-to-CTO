// Talks to the VoiceStudio app running on this computer.
//
// All API calls happen here, not in the YouTube Studio page, so YouTube never
// sees or reaches VoiceStudio. rules.json strips the Origin header from this
// extension's own requests (and only those): VoiceStudio refuses requests that
// carry an origin it does not know, which is how it blocks other websites.

const DEFAULT_API = "http://127.0.0.1:3900";

async function apiBase() {
  const { apiBase } = await chrome.storage.sync.get({ apiBase: DEFAULT_API });
  return apiBase.replace(/\/+$/, "");
}

async function call(path, init = {}) {
  const base = await apiBase();
  let res;
  try {
    res = await fetch(base + path, init);
  } catch {
    throw new Error("Can't reach VoiceStudio. Open the VoiceStudio app on this computer and try again.");
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body && body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* not JSON */ }
    throw new Error(`VoiceStudio said: ${detail}`);
  }
  return res;
}

function dataUrlToBlob(dataUrl) {
  const [head, b64] = dataUrl.split(",");
  const mime = (head.match(/data:([^;]+)/) || [])[1] || "application/octet-stream";
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

async function blobToDataUrl(blob) {
  const buf = new Uint8Array(await blob.arrayBuffer());
  let bin = "";
  for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode(...buf.subarray(i, i + 0x8000));
  return `data:${blob.type || "audio/wav"};base64,${btoa(bin)}`;
}

const handlers = {
  async health() {
    const res = await call("/health");
    return res.json();
  },

  async listVoices() {
    const res = await call("/profiles");
    const rows = await res.json();
    return rows.map((p) => ({ id: p.id, name: p.name, kind: p.kind }));
  },

  // Describe a voice in words ("gravelly old pirate") and save it.
  async design({ name, description, language }) {
    const parsed = await (await call("/design/describe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description }),
    })).json();

    const form = new FormData();
    form.set("name", name);
    form.set("kind", "design");
    form.set("vd_states", JSON.stringify(parsed.attrs || {}));
    form.set("instruct", parsed.instruct || "");
    form.set("language", language || "Auto");
    form.set("personality", description);
    const profile = await (await call("/profiles", { method: "POST", body: form })).json();
    return { profile, unmatched: parsed.unmatched || [] };
  },

  // Turn an uploaded sound (a recording of the character's voice) into a voice.
  async clone({ name, fileDataUrl, fileName, language, transcript }) {
    const form = new FormData();
    form.set("name", name);
    form.set("kind", "clone");
    form.set("language", language || "Auto");
    if (transcript) form.set("ref_text", transcript);
    form.set("ref_audio", dataUrlToBlob(fileDataUrl), fileName || "sound.wav");
    const profile = await (await call("/profiles", { method: "POST", body: form })).json();
    return { profile, unmatched: [] };
  },

  async preview({ id }) {
    const res = await call(`/profiles/${encodeURIComponent(id)}/audio`);
    return { dataUrl: await blobToDataUrl(await res.blob()) };
  },
};

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  const handler = handlers[msg && msg.type];
  if (!handler) return false;
  handler(msg)
    .then((result) => sendResponse({ ok: true, result }))
    .catch((err) => sendResponse({ ok: false, error: String(err.message || err) }));
  return true; // keep the channel open for the async reply
});
