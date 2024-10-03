chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.videoUrl) {
        // Flask 서버로 URL을 전송
        sendUrlToServer(message.videoUrl);
    }
});
// 유튜브 영상 클릭을 감지하는 함수
function detectVideoClick() {
    const videoPlayer = document.querySelector('video');

    if (videoPlayer) {
        videoPlayer.addEventListener('click', function() {
            const videoId = getVideoId();
            if (videoId) {
                sendVideoIdToServer(videoId);
            }
        });
    }
}

// URL에서 영상 ID 추출하는 함수
function getVideoId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('v');  // 유튜브 영상 ID는 'v'라는 쿼리 파라미터에 있음
}

// Flask 서버로 영상 ID를 보내는 함수
function sendVideoIdToServer(videoId) {
    fetch('http://localhost:5000/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ video_id: videoId })
    })
    .then(response => response.json())
    .then(data => {
        console.log('서버로부터 응답:', data);
    })
    .catch(error => {
        console.error('영상 ID 전송 중 오류 발생:', error);
    });
}

// 페이지가 로드되면 영상 클릭 감지 함수 호출
window.addEventListener('load', () => {
    detectVideoClick();
});

// 유튜브 영상 페이지 변경 감지 함수
function detectVideoPause() {
    const videoPlayer = document.querySelector('video');

    if (videoPlayer) {

        // 유튜브 페이지에서 나가는 것을 감지 (탭 닫기, 페이지 변경 등)
        window.addEventListener('beforeunload', function() {
            console.log('페이지가 닫히거나 이동됨');
            sendStopSignalToServer();
        });
    }
}

// 서버에 영상 중지 신호 보내는 함수
function sendStopSignalToServer() {
    const videoId = getVideoId();  // 현재 URL에서 video_id를 다시 가져옴
    fetch('http://localhost:5000/stop_analysis', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: 'stop', video_id: videoId })  // video_id를 JSON으로 함께 보냄
    })
    .then(response => response.json())
    .then(data => {
        console.log('서버로부터 중지 신호 응답:', data);
    })
    .catch(error => {
        console.error('중지 신호 전송 중 오류 발생:', error);
    });
}

window.addEventListener('load', () => {
    detectVideoClick();
    detectVideoPause();  // 영상 일시 중지 및 페이지 이동 감지
});

/*
function getVideoInfo() {
    const videoUrl = window.location.href;
    return { videoUrl: videoUrl };
}

// URL이 변경될 때마다 메시지를 확장 프로그램에 보내기
function monitorUrlChange() {
    let lastUrl = window.location.href;

    const observer = new MutationObserver(() => {
        const currentUrl = window.location.href;
        if (currentUrl !== lastUrl) {
            lastUrl = currentUrl;
            if (currentUrl.includes('watch?v=')) {
                const videoInfo = getVideoInfo();  // getVideoInfo 호출
                chrome.runtime.sendMessage(videoInfo);  // URL 정보 전송
            }
        }
    });

    // DOM 변화를 감지하기 위한 옵저버 설정
    observer.observe(document.body, { childList: true, subtree: true });
}

// 처음 로드될 때 URL 체크
if (window.location.href.includes('watch?v=')) {
    const videoInfo = getVideoInfo();  // getVideoInfo 호출
    chrome.runtime.sendMessage(videoInfo);  // URL 정보 전송
}

// URL 변경 모니터링 시작
monitorUrlChange();

function sendUrlToServer(youtubeUrl) {
    fetch('http://localhost:5000/analyze', {  // Flask 서버의 엔드포인트로 URL 전송
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ youtube_url: youtubeUrl })
    })
    .then(response => response.json())
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
}*/

// 서버로부터 분석 데이터를 받아 차트를 그리는 함수
function drawChart(analysisData) {
    const ctx = document.getElementById('emotionChart').getContext('2d');

    // X축: elapsed_time_ms, Y축: scores
    const labels = analysisData.map(item => item.elapsed_time_ms);  // X축: 분석 시간
    const scores = analysisData.map(item => parseFloat(item.scores.split(',')[0]));  // Y축: 첫 번째 감정의 score 사용

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Emotion Score Over Time (ms)',
                data: scores,
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 2,
                fill: false
            }]
        },
        options: {
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Elapsed Time (ms)'  // X축: 시간
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Emotion Score'  // Y축: 감정 점수
                    },
                    beginAtZero: true
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(tooltipItem) {
                            return `Score: ${tooltipItem.raw}`;
                        }
                    }
                }
            }
        }
    });
}

// 차트 캔버스를 추가하는 함수
function addChartCanvas() {
    const existingCanvas = document.getElementById('emotionChart');
    if (!existingCanvas) {
        const canvas = document.createElement('canvas');
        canvas.id = 'emotionChart';
        canvas.style.position = 'fixed';
        canvas.style.bottom = '10px';
        canvas.style.right = '10px';
        canvas.style.width = '400px';
        canvas.style.height = '300px';
        document.body.appendChild(canvas);
    }
}

// 메시지를 받을 때 차트 그리기
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.analysis_data) {
        addChartCanvas();  // 차트 캔버스 추가
        drawChart(message.analysis_data);  // 차트 그리기
    }
});