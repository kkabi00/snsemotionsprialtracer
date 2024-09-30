// 유튜브 영상 정보 가져오기 (예: 제목, 조회수 등)
function getVideoInfo() {
    const title = document.querySelector('h1.title').innerText;
    const views = document.querySelector('.view-count').innerText;
    const videoId = window.location.search.split('v=')[1];
    
    return {
        title: title,
        views: views,
        videoId: videoId
    };
}

// 영상 클릭 시 정보 보내기
document.addEventListener('click', function() {
    const videoInfo = getVideoInfo();
    chrome.runtime.sendMessage(videoInfo);
});
