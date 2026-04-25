chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'analyze') {
    chrome.tabs.create({ url: chrome.runtime.getURL('src/popup/index.html') });
    sendResponse({ status: 'opened' });
  }
});

chrome.alarms.create('stockCheck', { periodInMinutes: 60 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'stockCheck') {
    // Could fetch watchlist and notify; not implemented in MVP
  }
});

chrome.runtime.onInstalled.addListener(() => {
  console.log('MarketMind AI installed');
});