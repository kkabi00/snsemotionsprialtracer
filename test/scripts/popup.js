chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    if (message.image) {
        document.getElementById('videoGraph').src = 'data:image/png;base64,' + message.image;
    }
});
