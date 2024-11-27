let lastUrl = location.href;
let observer;
let labels;
let sumDangerScores;
let warningFlag = false; // 플래그 활성화 여부 설정
let bgColor = 'lightblue';
const serverUrl = 'http://127.0.0.1:5000/get_csv';
const fileName = 'current_data.csv'; // 서버에 저장된 파일 이름

// 서버에서 CSV 데이터를 불러오는 함수
fetch(`${serverUrl}?file_name=${fileName}`)
  .then((response) => {
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return response.text(); // CSV 데이터를 텍스트로 변환
  })
  .then((csvData) => {
    // PapaParse로 CSV 데이터를 파싱
    const parsedData = Papa.parse(csvData, {
      header: true,
      skipEmptyLines: true,
    }).data;

    // start_time과 sum_danger_score 데이터를 추출
    labels = parsedData.map((row) => row.start_time);
    sumDangerScores = parsedData.map((row) =>
      parseFloat(row.sum_danger_score)
    );
  })
  .catch((error) => console.error('Error loading CSV data:', error));

// 이벤트 리스너 등록

// DOM이 로드된 후 실행 왜 작동이 안하지....................
/*
document.addEventListener("DOMContentLoaded", () => {
  // 모든 썸네일 링크를 선택
  const thumbnails = document.querySelectorAll('a#thumbnail');
  console.log("DOM Load Complete!!!!!!!!!!!!!!!!")

  thumbnails.forEach(thumbnail => {
    thumbnail.addEventListener("click", event => {
        console.log("event listen!!!!!!!!!!!!!")
      if (warningFlag) {
        event.preventDefault(); // 기본 이동 동작을 막음

        // 확인 창 표시
        const userConfirmed = confirm("위험 수치에 도달하였습니다. \n 정말 영상을 시청하시겠습니까?");

        if (userConfirmed) {
          // "확인" 클릭 시 영상 URL로 이동
          window.location.href = thumbnail.href;
        } else {
          // "취소" 클릭 시 아무 작업도 하지 않음
          console.log("사용자가 취소를 선택했습니다.");
        }
      } else {
        // warningFlag가 false일 경우, 기본 동작 수행
        console.log("경고창이 비활성화되어 바로 이동합니다.");
      }
    });
  });
});
*/

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

                const chartCanvas = initializeChart(labels, sumDangerScores);
                addCustomDiv(chartCanvas);

            } catch (error) {
                console.error("Failed to send message:", error);
            }
        }
    });

    observer.observe(document, { subtree: true, childList: true });

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
    if (document.getElementById('custom-style')) {
        document.getElementById('custom-style').remove();
    }
        const styleTag = document.createElement('style');
        styleTag.id = 'custom-style';
        styleTag.textContent = `
            #custom-div {
                display: flex;           /* Flexbox 사용 */
                justify-content: center; /* 가로 중앙 정렬 */
                align-items: center;     /* 세로 중앙 정렬 */
                background-color: ${bgColor}; /* 배경색 */
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
            #myChart {
            width: 100%;     /* 부모 요소 너비를 100% 사용 */
            height: 300px;   /* 고정된 높이 설정 */
            max-height: 400px; /* 최대 높이 제한 */
            }
        `;
        document.head.appendChild(styleTag);
        console.log('Style dynamically added.');

}

function addCustomDiv(chartCanvas) {
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

            //chart 추가
            additionalInfo.appendChild(chartCanvas);

            // "오늘의 보고서" 버튼 추가
            const reportButton = document.createElement('button');
            reportButton.textContent = '오늘의 보고서 다운로드';

            // 버튼 클릭 이벤트
            analysisButton.addEventListener('click', () => {
                const isVisible = additionalInfo.style.display === 'block';

                // 토글 동작: 열고 닫기
                additionalInfo.style.display = isVisible ? 'none' : 'block';

                // 화살표 방향 변경
                arrow.textContent = isVisible ? '▼' : '▲';
            });

            // 추가 정보 영역에 이미지와 버튼
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



// Chart.js를 설정하는 함수
function initializeChart(labels, dataPoints) {

    const canvas = document.createElement('canvas');
    canvas.id = 'myChart';
    const ctx = canvas.getContext('2d');

    // X축과 Y축 여유 공간 계산
    const xMax = Math.ceil(Math.max(...labels.map((x) => parseFloat(x))) / 100) * 100 + 300;
    const yMax = Math.ceil(Math.max(...dataPoints) / 100) * 100 + 500;


    // 기울기와 절편 설정 (Y = mx + c)
    // 고자극 선
    const slope1 = (7000 - 0) / 16000; // Y = 7000, X = 14400
    const intercept1 = 0; // Y절편 (c)
    // 저자극 선
    const slope2 = (5000 - 0) / 16000; // Y = 5000, X = 14400
    const intercept2 = 0; // Y절편 (c)

    // 직선 데이터 계산
    const line1 = labels.map((x) => slope1 * x + intercept1); // Y = slope1 * X + intercept1
    const line2 = labels.map((x) => slope2 * x + intercept2); // Y = slope2 * X + intercept2

    const chartConfig = {
      type: 'line',
      data: {
        labels: labels, // X축 레이블 (start_time)
        datasets: [
          {
            label: 'Sum Danger Score',
            data: dataPoints, // Y축 데이터 (sum_danger_score)
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            tension: 0.4, // 곡선 정도
            borderWidth: 2,
            pointRadius: 0,
            pointHoverTadius: 3, // 마우스 호버 시 점 크기 상승
          },
          {
            label: 'Danger_Line', // 고자극 직선
            data: line1, // 계산된 직선 데이터
            borderColor: 'rgba(255, 99, 132, 1)', // 파란색
            //borderDash: [10, 5], // 점선
            borderWidth: 3, // 선의 두께
            tension: 0, // 직선
            pointRadius: 0, // 점을 표시하지 않음
            fill: false,
          },
          {
            label: 'Safe_Line', // 저자극 직선
            data: line2, // 계산된 직선 데이터
            borderColor: 'rgba(0, 128, 0, 1)', // 초록색
            //borderDash: [10, 5], // 점선
            borderWidth: 3, // 선의 두께
            tension: 0, // 직선
            pointRadius: 0, // 점을 표시하지 않음
            fill: false,
          },
        ],
      },
      options: {
          responsive: true,
          maintainAspectRatio: false, // 차트 비율 조정 허용
        scales: {
          x: {
            type: 'linear',
            max: xMax, // X축 최대값
            ticks: {
              stepSize: 100, // X축 레이블 간격을 100 단위로 설정
            },
          },
          y: {
            max: yMax, // Y축 최대값
            ticks: {
              stepSize: 100, // Y축 레이블 간격을 100 단위로 설정
            },
          },
        },
      },
      plugins: [
        {
          id: 'backgroundColor',
          beforeDraw: (chart) => {
            const ctx = chart.ctx;
            const chartArea = chart.chartArea;
            const xScale = chart.scales.x;

            // x축 데이터
            const data = chart.data.datasets[0].data;
            const dangerLineData = chart.data.datasets[1].data;
            const safeLineData = chart.data.datasets[2].data;

            ctx.save();

            // 각 데이터 포인터 확인
            data.forEach((point, index) => {
              //const xValue = xScale.getPixelForValue(index); // x좌표
              //const yValue = yScale.getPixelForValue(point); // y좌표

              // 1시간이 지난 후
              if (labels[index] >= 3600) {
                const dangerValue = dangerLineData[index];
                const safeValue = safeLineData[index];
                // 중간값
                const midValue = (dangerValue + safeValue) / 2;

                // 배경 색상 선택
                 if (labels[index] >= 14400) { // 4시간 경과시
                  bgColor = 'red';// 빨간색
                  warningFlag = true;
                 } else if (point > midValue && point < dangerValue) {
                  bgColor = 'gold'; // 노란색
                     warningFlag = false;
                } else if (point >= dangerValue) {
                  bgColor = 'salmon'; // 빨간색
                  warningFlag = true;
                } else {
                  bgColor = 'lightblue';
                }
              }

            });

            console.log(bgColor,'in chart');
            addDynamicStyles();
            // 수직선 그리기
            const lastIndex = labels.length - 1;
            const lastXValue = xScale.getPixelForValue(labels[lastIndex]);

            ctx.strokeStyle = 'black';
            ctx.lineWidth = 2;
            ctx.setLineDash([5, 5]);

            ctx.beginPath();
            ctx.moveTo(lastXValue, chartArea.top);
            ctx.lineTo(lastXValue, chartArea.bottom);
            ctx.stroke();

            ctx.restore();
          }
        }
      ]
    };
    new Chart(ctx, chartConfig);

    return canvas;
}



// alert 추가
// 페이지가 로드될 때 URL 변경 감시 시작
startObserving();