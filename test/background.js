// const FLASK_SERVER_URL = "http://localhost:5000/";  // Flask 서버 URL

// chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
//     if (message.type === "URL_CHANGED") {
//         const url = message.url;

//         fetch(FLASK_SERVER_URL, {
//             method: "POST",
//             headers: {
//                 "Content-Type": "application/json"
//             },
//             body: JSON.stringify({ url: url })
//         })
//         .then(response => response.json())
//         .then(data => {
//             // 서버로부터 이미지 URL을 받아 팝업에 전달
//             chrome.runtime.sendMessage({ type: "IMAGE_URL", imageUrl: data.image_url });
//         })
//         .catch(error => console.error("Error:", error));
//     }
// });

const FLASK_SERVER_URL = "http://localhost:5000/";
console.log("Background service worker loaded.");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.type === "URL_CHANGED") {
        const youtubeUrl = request.url;
        const imageUrl = chrome.runtime.getURL("generated_images/sum_danger_score_plot_with_baseline.png");
        console.log("Sending URL to server:", youtubeUrl);
        sendUrlToServer(youtubeUrl);
    }
});

async function sendUrlToServer(url) {
    try {
        const response = await fetch(`${FLASK_SERVER_URL}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url: url })
        });
        if (!response.ok) {
            throw new Error(`Server responded with status: ${response.status}`);
        }

        const data = await response.json();
        console.log("Image URL received from server:", data.image_url);
        // You can also send this back to content.js or handle it accordingly
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs && tabs.length > 0) {
                chrome.tabs.sendMessage(tabs[0].id, { type: "IMAGE_URL", imageUrl: data.image_url });
            } else {
                console.error("NO active tab found")
            }
            
        });
    } catch (error) {
        console.error("Error sending URL to server:", error);
    }
}
