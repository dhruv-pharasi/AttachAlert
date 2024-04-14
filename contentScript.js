// contentScript.js
const checkForAttachments = () => {
  // This is a simplistic check for attachments in Gmail based on the UI's current structure
  // The class ".a1.aaA.aMZ" may change as Gmail updates its UI
  const attachmentContainer = document.querySelector('.a1.aaA.aMZ');
  return attachmentContainer !== null;
};

// Listen for messages from the background or popup script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "check_attachment") {
    const hasAttachment = checkForAttachments();
    sendResponse({ attachment: hasAttachment });
  }
});


