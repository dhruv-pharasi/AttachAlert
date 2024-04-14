// popup.js
document.getElementById('checkBtn').addEventListener('click', () => {
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, {action: "checkForAttachments"}, response => {
        alert("Attachment Present: " + response.attachment);
      });
    });
  });
  