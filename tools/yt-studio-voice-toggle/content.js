// Adds the "New character voice" toggle to YouTube Studio, right under the
// section whose heading matches the label set in the extension's options
// ("Extras" by default). YouTube Studio is a single-page app that redraws
// itself, so this keeps watching the page and re-adds the toggle when needed.

(() => {
  const HOST_ID = "cv-voice-toggle-host";
  let sectionLabel = "Extras";
  let fallbackTimer = null;

  chrome.storage.sync.get({ sectionLabel: "Extras" }, (s) => {
    sectionLabel = (s.sectionLabel || "Extras").trim();
    place();
  });

  const send = (msg) =>
    new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(msg, (reply) => {
        if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
        if (!reply || !reply.ok) return reject(new Error((reply && reply.error) || "Something went wrong."));
        resolve(reply.result);
      });
    });

  // ---- Finding the section -------------------------------------------------

  function labelMatches(text) {
    const want = sectionLabel.toLowerCase().replace(/s$/, "");
    const got = text.trim().toLowerCase().replace(/s$/, "");
    return got === want;
  }

  function findHeading() {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || node.nodeValue.length > 40) return NodeFilter.FILTER_REJECT;
        if (node.parentElement && node.parentElement.closest(`#${HOST_ID}`)) return NodeFilter.FILTER_REJECT;
        return labelMatches(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      },
    });
    let node;
    while ((node = walker.nextNode())) {
      const el = node.parentElement;
      if (el && el.getClientRects().length > 0) return el; // visible only
    }
    return null;
  }

  // Walk up from the heading to the box that holds the whole section, so the
  // toggle lands under the section's contents rather than between the heading
  // and its first field.
  function sectionOf(heading) {
    const headingLen = heading.textContent.trim().length;
    let el = heading;
    for (let i = 0; i < 6 && el.parentElement && el.parentElement !== document.body; i++) {
      const parent = el.parentElement;
      if (parent.textContent.trim().length > headingLen + 15) {
        // parent holds more than the heading: if it also holds other sections,
        // el is the section itself; otherwise parent is the section.
        const siblingHeadings = [...parent.children].filter((c) => c !== el && c.querySelector("h1,h2,h3,h4,[role=heading]"));
        return siblingHeadings.length > 1 ? el : parent;
      }
      el = parent;
    }
    return heading;
  }

  function place() {
    const existing = document.getElementById(HOST_ID);
    const heading = findHeading();
    if (heading) {
      const section = sectionOf(heading);
      if (existing && existing.previousElementSibling === section && !existing.dataset.floating) return;
      const host = existing || build();
      delete host.dataset.floating;
      host.style.cssText = "display:block;margin:16px 0;";
      section.insertAdjacentElement("afterend", host);
      clearTimeout(fallbackTimer);
      fallbackTimer = null;
      return;
    }
    // No matching section on this screen: after a short wait, show the toggle
    // as a small floating button so it is still reachable.
    if (!existing && !fallbackTimer) {
      fallbackTimer = setTimeout(() => {
        fallbackTimer = null;
        if (document.getElementById(HOST_ID) || findHeading()) return place();
        const host = build();
        host.dataset.floating = "1";
        host.style.cssText = "position:fixed;right:20px;bottom:20px;z-index:2147483000;width:340px;max-width:calc(100vw - 40px);";
        document.body.appendChild(host);
      }, 4000);
    }
  }

  let scheduled = false;
  new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      place();
    });
  }).observe(document.documentElement, { childList: true, subtree: true });

  // ---- The toggle and its panel -------------------------------------------

  function build() {
    const host = document.createElement("div");
    host.id = HOST_ID;
    const root = host.attachShadow({ mode: "open" }); // keeps Studio's CSS out
    root.innerHTML = `
      <style>
        :host { all: initial; }
        [hidden] { display: none !important; }
        * { box-sizing: border-box; font-family: Roboto, "YouTube Sans", Arial, sans-serif; }
        .box { border: 1px solid var(--line); border-radius: 8px; padding: 12px 16px; background: var(--bg); color: var(--fg); }
        .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
        .title { font-size: 15px; font-weight: 500; }
        .sub { font-size: 12px; color: var(--muted); margin-top: 2px; }
        .switch { position: relative; width: 36px; height: 20px; flex: none; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .track { position: absolute; inset: 0; border-radius: 10px; background: var(--off); cursor: pointer; transition: background .15s; }
        .track::after { content: ""; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform .15s; box-shadow: 0 1px 2px rgba(0,0,0,.3); }
        input:checked + .track { background: var(--accent); }
        input:checked + .track::after { transform: translateX(16px); }
        input:focus-visible + .track { outline: 2px solid var(--accent); outline-offset: 2px; }
        .panel { margin-top: 12px; display: grid; gap: 10px; }
        .panel[hidden] { display: none; }
        label.f { display: grid; gap: 4px; font-size: 12px; color: var(--muted); }
        input[type=text], textarea, select { width: 100%; font-size: 14px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 4px; background: var(--field); color: var(--fg); }
        textarea { min-height: 60px; resize: vertical; }
        .tabs { display: flex; gap: 6px; }
        .tabs button { flex: 1; padding: 6px 8px; font-size: 13px; border: 1px solid var(--line); background: transparent; color: var(--fg); border-radius: 16px; cursor: pointer; }
        .tabs button[aria-pressed=true] { background: var(--accent); color: #fff; border-color: var(--accent); }
        .go { justify-self: start; padding: 8px 16px; font-size: 14px; font-weight: 500; border: 0; border-radius: 18px; background: var(--accent); color: #fff; cursor: pointer; }
        .go:disabled { opacity: .5; cursor: default; }
        .msg { font-size: 13px; line-height: 1.4; }
        .msg.err { color: var(--err); }
        .msg.ok { color: var(--ok); }
        .voices { font-size: 12px; color: var(--muted); }
        audio { width: 100%; height: 32px; }
        .box { --bg:#fff; --fg:#0f0f0f; --muted:#606060; --line:#d9d9d9; --field:#fff; --off:#c4c4c4; --accent:#065fd4; --err:#c00; --ok:#0b8043; }
        @media (prefers-color-scheme: dark) {
          .box { --bg:#282828; --fg:#f1f1f1; --muted:#aaa; --line:#3f3f3f; --field:#1f1f1f; --off:#717171; --accent:#3ea6ff; --err:#ff6b6b; --ok:#5fd38d; }
        }
      </style>
      <div class="box">
        <div class="row">
          <div>
            <div class="title">New character voice</div>
            <div class="sub">Turn a new sound into a voice for one of your characters</div>
          </div>
          <label class="switch" title="Add a new character voice">
            <input type="checkbox" id="toggle" aria-label="Add a new character voice">
            <span class="track"></span>
          </label>
        </div>
        <div class="panel" id="panel" hidden>
          <label class="f">Character name
            <input type="text" id="name" maxlength="80" placeholder="e.g. Captain Rex">
          </label>
          <div class="tabs" role="group" aria-label="How to make the voice">
            <button type="button" data-mode="describe" aria-pressed="true">Describe it</button>
            <button type="button" data-mode="upload" aria-pressed="false">Upload a sound</button>
          </div>
          <label class="f" id="describeField">What should it sound like?
            <textarea id="description" maxlength="2000" placeholder="e.g. deep, gravelly older man, slow, British accent"></textarea>
          </label>
          <div id="uploadField" hidden>
            <label class="f">Sound clip (5–20 seconds of clear speech works best)
              <input type="file" id="file" accept="audio/*,video/*">
            </label>
            <label class="f" style="margin-top:8px">Words spoken in the clip (optional)
              <input type="text" id="transcript" placeholder="Leave empty and VoiceStudio will listen for them">
            </label>
            <label class="f" style="margin-top:8px;flex-direction:row;display:flex;gap:8px;align-items:flex-start;color:inherit">
              <input type="checkbox" id="consent" style="margin-top:2px">
              <span>This is my own voice, or I have permission from the person whose voice it is.</span>
            </label>
          </div>
          <label class="f">Language
            <select id="language">
              <option value="Auto">Auto</option>
              <option>English</option><option>Spanish</option><option>French</option><option>German</option>
              <option>Portuguese</option><option>Italian</option><option>Japanese</option><option>Korean</option>
              <option>Chinese</option><option>Hindi</option><option>Arabic</option>
            </select>
          </label>
          <button type="button" class="go" id="go">Create voice</button>
          <div class="msg" id="msg" role="status" aria-live="polite"></div>
          <audio id="player" controls hidden></audio>
          <div class="voices" id="voices"></div>
        </div>
      </div>`;

    const $ = (id) => root.getElementById(id);
    let mode = "describe";

    const setMsg = (text, kind = "") => {
      $("msg").textContent = text;
      $("msg").className = `msg ${kind}`;
    };

    async function refreshVoices() {
      try {
        const voices = await send({ type: "listVoices" });
        $("voices").textContent = voices.length
          ? `Your character voices in VoiceStudio: ${voices.map((v) => v.name).join(", ")}`
          : "";
      } catch { /* shown when they try to create */ }
    }

    $("toggle").addEventListener("change", async (e) => {
      $("panel").hidden = !e.target.checked;
      if (!e.target.checked) return;
      setMsg("");
      try {
        await send({ type: "health" });
        refreshVoices();
      } catch (err) {
        setMsg(err.message, "err");
      }
    });

    root.querySelectorAll(".tabs button").forEach((b) =>
      b.addEventListener("click", () => {
        mode = b.dataset.mode;
        root.querySelectorAll(".tabs button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
        $("describeField").hidden = mode !== "describe";
        $("uploadField").hidden = mode !== "upload";
        setMsg("");
      })
    );

    // Keep typing in our fields from triggering YouTube Studio shortcuts.
    root.addEventListener("keydown", (e) => e.stopPropagation());

    $("go").addEventListener("click", async () => {
      const name = $("name").value.trim();
      const language = $("language").value;
      if (!name) return setMsg("Give the character a name first.", "err");

      let msg;
      if (mode === "describe") {
        const description = $("description").value.trim();
        if (!description) return setMsg("Describe how the voice should sound.", "err");
        msg = { type: "design", name, description, language };
      } else {
        const file = $("file").files[0];
        if (!file) return setMsg("Choose a sound clip.", "err");
        if (file.size > 50 * 1024 * 1024) return setMsg("That clip is over 50 MB. A short clip of 5–20 seconds is plenty.", "err");
        if (!$("consent").checked) return setMsg("Please confirm you have permission to use this voice.", "err");
        const fileDataUrl = await new Promise((res, rej) => {
          const r = new FileReader();
          r.onload = () => res(r.result);
          r.onerror = () => rej(r.error);
          r.readAsDataURL(file);
        });
        msg = { type: "clone", name, fileDataUrl, fileName: file.name, language, transcript: $("transcript").value.trim() };
      }

      $("go").disabled = true;
      $("player").hidden = true;
      setMsg("Creating the voice in VoiceStudio…");
      try {
        const { profile, unmatched } = await send(msg);
        let text = `Saved "${profile.name}". Pick it in VoiceStudio (or ask Claude) for your voiceovers.`;
        if (unmatched.length) text += ` Words VoiceStudio couldn't use: ${unmatched.join(", ")}.`;
        setMsg(text, "ok");
        refreshVoices();
        try {
          const { dataUrl } = await send({ type: "preview", id: profile.id });
          $("player").src = dataUrl;
          $("player").hidden = false;
        } catch {
          // Design voices render their sample the first time the voice model
          // is loaded, so a preview may not exist yet. Not an error.
        }
      } catch (err) {
        setMsg(err.message, "err");
      } finally {
        $("go").disabled = false;
      }
    });

    return host;
  }
})();
