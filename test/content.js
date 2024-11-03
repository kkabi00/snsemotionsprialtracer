let lastUrl = location.href;
let observer;
let debounceTimeout;

function startObserving() {
    // 기존 observer가 있다면 중지
    if (observer) {
        observer.disconnect();
    }

    observer = new MutationObserver(() => {
        const currentUrl = location.href;
        if (currentUrl !== lastUrl && currentUrl.includes("youtube.com/watch")) {
            lastUrl = currentUrl;
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                console.log("Detected new URL:", currentUrl);
                chrome.runtime.sendMessage({ type: "URL_CHANGED", url: currentUrl }, (response) => {
                    if (chrome.runtime.lastError) {
                        console.error("Error sending message:", chrome.runtime.lastError);
                    }
                });
            }, 300);
        }
    });

    observer.observe(document, { subtree: true, childList: true });
}

// 페이지가 로드될 때 URL 변경 감시 시작
startObserving();