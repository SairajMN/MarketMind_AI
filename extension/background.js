const DEFAULT_SETTINGS = {
  mode: "live",
  apiBaseUrl: "https://marketmind-ai-api.vercel.app",
  symbol: "NVDA",
  range: "5d",
};

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.get(DEFAULT_SETTINGS, (stored) => {
    const nextValues = {};

    Object.entries(DEFAULT_SETTINGS).forEach(([key, value]) => {
      if (stored[key] === undefined) {
        nextValues[key] = value;
      }
    });

    if (Object.keys(nextValues).length > 0) {
      chrome.storage.local.set(nextValues);
    }
  });
});
