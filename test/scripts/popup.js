chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    if (message.image) {
        document.getElementById('videoGraph') + message.image;
    }
});
