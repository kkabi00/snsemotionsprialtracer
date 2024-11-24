//const csvFilePath = 'generated_images/current_data.csv';
const csvFilePAth = 'test/generated_images/current_data.csv';
// CSV 데이터를 가져오고 차트를 초기화
fetch(csvFilePath)
  .then((response) => response.text())
  .then((csvData) => {
    // PapaParse로 CSV 데이터를 파싱
    const parsedData = Papa.parse(csvData, {
      header: true,
      skipEmptyLines: true,
    }).data;

    // start_time과 sum_danger_score 데이터를 추출
    const labels = parsedData.map((row) => row.start_time);
    const sumDangerScores = parsedData.map((row) =>
      parseFloat(row.sum_danger_score)
    );

    // 차트를 생성
    initializeChart(labels, sumDangerScores);
  })
  .catch((error) => console.error('Error loading CSV data:', error));

// main.html로 들어갈 배경색
let bgColor = 'white';
// Chart.js를 설정하는 함수
function initializeChart(labels, dataPoints) {
    const ctx = document.getElementById('myChart').getContext('2d');

    // X축과 Y축 여유 공간 계산
    const xMax = Math.ceil(Math.max(...labels.map((x) => parseFloat(x))) / 100) * 100 + 300;
    const yMax = Math.ceil(Math.max(...dataPoints) / 100) * 100 + 500;

    // Base line 생성: start_score + i (i는 증가하는 인덱스)
    // const baseLine = Array.from({ length: labels.length }, (_, i) => i);

    // 기울기와 절편 설정 (Y = mx + c)
    // 고자극 선
    const slope1 = (7000 - 0) / 14400; // Y = 7000, X = 14400
    const intercept1 = 0; // Y절편 (c)
    // 저자극 선
    const slope2 = (5000 - 0) / 14400; // Y = 5000, X = 14400
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
          // {
          //   label: 'Baseline (1 per step)', // 선형 기준선
          //   data: baseLine, // Base line 데이터
          //   borderColor: 'rgba(255, 99, 132, 1)', // 빨간색
          //   backgroundColor: 'rgba(255, 99, 132, 0.2)', // 투명한 빨간색
          //   borderDash: [5, 5], // 점선
          //   tension: 0, // 직선
          // }
          {
            label: 'Danger_Line', // 고자극 직선
            data: line1, // 계산된 직선 데이터
            borderColor: 'rgba(255, 99, 132, 1)', // 파란색
            //borderDash: [10, 5], // 점선
            borderWidth: 3, // 선의 두께
            tension: 0, // 직선
            pointRadius: 0, // 점을 표시하지 않음
            fill: false,
              pointRadius: 0, // 점 제거
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
              pointRadius: 0, // 점 제거
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          title: {
            display: true,
            text: 'Emotion tracer',
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Start Time',
            },
            type: 'linear',
            max: xMax, // X축 최대값
            ticks: {
              stepSize: 100, // X축 레이블 간격을 100 단위로 설정
            },
          },
          y: {
            title: {
              display: true,
              text: 'Sum Danger Score',
            },
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
            const yScale = chart.scales.y;

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
                if (point > midValue && point < dangerValue) {
                  bgColor = 'rgba(255, 255, 0, 0.2)'; // 노란색
                } else if (point >= dangerValue) {
                  bgColor = 'rgba(255, 0, 0, 0.2)'; // 빨간색
                } else if (labels[index] >= 14400) { // 4시간 경과시
                  bgColor = 'rgba(255, 0, 0, 0.5)';// 빨간색
                } else {
                  bgColor = 'rgba(0, 255, 0, 0.2)'; // 초록색
                }
                // HTML에 배경색 전달
                document.body.style.backgroundColor = bgColor;
                // 배경 색상 적용
                ctx.fillStyle = bgColor;
                ctx.fillRect(
                  xScale.getPixelForValue(labels[index - 1]),
                  chartArea.top,
                  xScale.getPixelForValue(labels[index - 1]) - xScale.getPixelForValue(labels[index - 1]),
                  chartArea.bottom - chartArea.top
                );
              }
            });
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
}
