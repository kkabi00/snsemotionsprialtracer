chrome.runtime.onMessage.addListener(function(message, sender, sendResponse) {
    // 받은 메시지를 서버로 전달
    fetch('http://localhost:5000/process_video_info', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(message),
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        sendResponse(data);
    })
    .catch((error) => {
        console.error('Error:', error);
    });
    return true; // 비동기 응답을 위해 true 반환
});
