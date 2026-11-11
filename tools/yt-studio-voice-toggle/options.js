const defaults = { sectionLabel: "Extras", apiBase: "http://127.0.0.1:3900" };
const $ = (id) => document.getElementById(id);
const status = (t) => ($("status").textContent = t);

chrome.storage.sync.get(defaults, (s) => {
  $("sectionLabel").value = s.sectionLabel;
  $("apiBase").value = s.apiBase;
});

$("save").addEventListener("click", () => {
  chrome.storage.sync.set(
    {
      sectionLabel: $("sectionLabel").value.trim() || defaults.sectionLabel,
      apiBase: $("apiBase").value.trim() || defaults.apiBase,
    },
    () => status("Saved. Reload YouTube Studio to see the change.")
  );
});

$("test").addEventListener("click", () => {
  status("Checking…");
  chrome.runtime.sendMessage({ type: "health" }, (r) => {
    status(r && r.ok ? "Connected to VoiceStudio." : (r && r.error) || "No reply.");
  });
});
