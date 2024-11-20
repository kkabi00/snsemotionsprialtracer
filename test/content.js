let lastUrl = location.href;
let observer;

function startObserving() {
    // 기존 observer가 있다면 중지
    if (observer) {
        observer.disconnect();
    }

    observer = new MutationObserver(() => {
        const currentUrl = location.href;
        if (currentUrl !== lastUrl && currentUrl.match(/youtube\.com\/watch\?v=/)) {
            lastUrl = currentUrl;
            try {
                console.log("Detected new URL:", currentUrl);
                chrome.runtime.sendMessage({ type: "URL_CHANGED", url: currentUrl });

                addDynamicStyles();
                addCustomDiv();

            } catch (error) {
                console.error("Failed to send message:", error);
            }
        }
    });

    observer.observe(document, { subtree: true, childList: true });
    
    // Clean up observer and debounce on page unload
     window.addEventListener("beforeunload", () => {
        if (observer) observer.disconnect();
    });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "IMAGE_URL") {
        console.log("Message received in content.js:", message);
        const imageUrl = message.imageUrl
        
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
function addDynamicStyles() {
    if (!document.getElementById('custom-style')) {
        const styleTag = document.createElement('style');
        styleTag.id = 'custom-style';
        styleTag.textContent = `
            #custom-div {
                display: flex;           /* Flexbox 사용 */
                justify-content: center; /* 가로 중앙 정렬 */
                align-items: center;     /* 세로 중앙 정렬 */
                background-color: lightblue; /* 배경색 */
                padding: 10px;          /* 내부 여백 */
                margin: 0px;            /* 외부 여백 */
                border: 2px solid blue; /* 테두리 */
                border-radius: 8px;     /* 모서리를 둥글게 */
                font-size: 16px;        /* 글꼴 크기 */
                text-align: center;     /* 텍스트 가운데 정렬 */
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2); /* 그림자 */
                flex-direction: column; /* 버튼과 컨테이너 수직 배치 */
                width: 300px;           /* 고정된 너비 */
                height: auto;           /* 높이 자동 조절 */
            }

            #custom-div button {
                padding: 10px 15px;
                font-size: 14px;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                display: flex;
                align-items: center;    /* 텍스트와 아이콘 정렬 */
                gap: 10px;              /* 텍스트와 화살표 간격 */
            }

            #custom-div button:hover {
                background-color: #0056b3;
            }

            #arrow {
                font-size: 16px;
                transition: transform 0.3s ease; /* 애니메이션 */
            }

            #additional-info {
                margin-top: 10px;          /* 버튼과의 간격 */
                padding: 10px;            /* 내부 여백 */
                background-color: white;  /* 배경색 */
                border: 1px solid #ccc;   /* 테두리 */
                border-radius: 8px;       /* 모서리를 둥글게 */
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* 그림자 */
                width: 80%;               /* custom-div보다 작게 */
                max-width: 250px;         /* 최대 너비 제한 */
                display: none;            /* 기본적으로 숨김 */
                text-align: left;         /* 텍스트 정렬 */
            }

            #additional-info img {
                width: 100%;             /* 이미지가 컨테이너에 맞도록 */
                border-radius: 5px;      /* 이미지 모서리를 둥글게 */
                margin-bottom: 10px;     /* 이미지와 버튼 간격 */
            }

            #additional-info button {
                width: 100%;             /* 버튼이 컨테이너 너비에 맞도록 */
                padding: 8px;
                font-size: 14px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }

            #additional-info button:hover {
                background-color: #218838;
            }
        `;
        document.head.appendChild(styleTag);
        console.log('Style dynamically added.');
    } else {
        console.log('Style already exists.');
    }
}

function addCustomDiv() {
    const secondaryDiv = document.querySelector('div#secondary.style-scope.ytd-watch-flexy');
    if (secondaryDiv) {
        if (!document.getElementById('custom-div')) {
            const newDiv = document.createElement('div');
            newDiv.id = 'custom-div';

            // 버튼 생성
            const analysisButton = document.createElement('button');
            analysisButton.textContent = 'SnS 감정 분석기';

            // 화살표 추가
            const arrow = document.createElement('span');
            arrow.id = 'arrow';
            arrow.textContent = '▼'; // 기본 화살표 아래 방향
            analysisButton.appendChild(arrow);

            // 추가 정보 영역 생성
            const additionalInfo = document.createElement('div');
            additionalInfo.id = 'additional-info';

            // 이미지 공간 추가
            const reportImage = document.createElement('img');
            reportImage.src = 'https://via.placeholder.com/250'; // 임시 이미지 URL
            reportImage.alt = '오늘의 보고서 미리보기';

            // "오늘의 보고서" 버튼 추가
            const reportButton = document.createElement('button');
            reportButton.textContent = '오늘의 보고서';

            // 버튼 클릭 이벤트
            analysisButton.addEventListener('click', () => {
                const isVisible = additionalInfo.style.display === 'block';

                // 토글 동작: 열고 닫기
                additionalInfo.style.display = isVisible ? 'none' : 'block';

                // 화살표 방향 변경
                arrow.textContent = isVisible ? '▼' : '▲';
            });

            // 추가 정보 영역에 이미지와 버튼 추가
            additionalInfo.appendChild(reportImage);
            additionalInfo.appendChild(reportButton);

            // 새로운 DIV에 버튼과 추가 정보 영역 추가
            newDiv.appendChild(analysisButton);
            newDiv.appendChild(additionalInfo);

            // Secondary div에 추가
            secondaryDiv.prepend(newDiv);
            console.log('Custom div successfully added.');
        } else {
            console.log('Custom div already exists.');
        }
    } else {
        console.log('Secondary div not found.');
    }
}




// alert 추가
// 페이지가 로드될 때 URL 변경 감시 시작
startObserving();