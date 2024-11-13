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
                try {
                    console.log("Detected new URL:", currentUrl);
                    chrome.runtime.sendMessage({ type: "URL_CHANGED", url: currentUrl });
                } catch (error) {
                    console.error("Failed to send message:", error);
                }
            }, 300);
        }
    });

    observer.observe(document, { subtree: true, childList: true });
    
    // Clean up observer and debounce on page unload
     window.addEventListener("beforeunload", () => {
        if (observer) observer.disconnect();
        clearTimeout(debounceTimeout);
    });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "IMAGE_URL") {
        const imageUrl = message.imageUrl;
        
        // 이미지를 추가할 컨테이너 요소
        let imgContainer = document.getElementById("emotionChart");
        if (!imgContainer) {
            imgContainer = document.createElement("div");
            imgContainer.id = "image-container";
            document.body.appendChild(imgContainer);
        }

        // 이미지 엘리먼트 생성
        const img = document.createElement("img");
        img.src = imageUrl;
        img.alt = "Image from Chrome Extension";
        imgContainer.appendChild(img);
    }
});

// 페이지가 로드될 때 URL 변경 감시 시작
startObserving();