document.addEventListener("DOMContentLoaded", function() {
    // 백그라운드 스크립트에서 메시지를 받음
    chrome.runtime.onMessage.addListener((message) => {
        if (message.type === "IMAGE_URL") {
            const imgElement = document.getElementById("emotionChart");
            if (imgElement) {
                imgElement.src = message.imageUrl;
            } else {
                console.error("Image element not found");
            }
        }
    });
});