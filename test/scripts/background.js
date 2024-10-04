chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.videoUrl) {
        // Flask 서버로 URL을 전송
        sendUrlToServer(message.videoUrl);
    }
});

function sendUrlToServer(youtubeUrl) {
    fetch('http://localhost:5000/analyze', {  // Flask 서버의 엔드포인트로 URL 전송
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ youtube_url: youtubeUrl })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.analysis_data) {
            // 분석 데이터를 content script로 전송하여 차트를 그리게 함
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                chrome.tabs.sendMessage(tabs[0].id, { analysis_data: data.analysis_data });
            });
        } else {
            console.error('Error:', data.error);
            alert('Error occurred: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Request failed: ' + error);
    });
}
