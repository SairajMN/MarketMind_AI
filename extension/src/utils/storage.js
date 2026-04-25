async function saveSession(sessionId, data) {
  await chrome.storage.local.set({ [sessionId]: data });
}

async function loadSession(sessionId) {
  const result = await chrome.storage.local.get([sessionId]);
  return result[sessionId] || null;
}

async function clearSession(sessionId) {
  await chrome.storage.local.remove([sessionId]);
}

export { saveSession, loadSession, clearSession };
