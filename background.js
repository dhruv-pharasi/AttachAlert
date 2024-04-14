// background.js
chrome.action.onClicked.addListener((tab) => {
    // Injects the content script into the current page
    chrome.scripting.executeScript({
      target: {tabId: tab.id},
      function: checkForAttachments
    }, (results) => {
      // You could add more logic here based on the results
      console.log('Attachment status checked', results);
    });
  });
  