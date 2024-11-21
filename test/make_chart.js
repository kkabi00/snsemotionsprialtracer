// CSV 파일 경로
const csvFilePath = 'test/generated_images/current_data.csv';
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

// Chart.js를 설정하는 함수
function initializeChart(labels, dataPoints) {
    const ctx = document.getElementById('myChart').getContext('2d');

    // X축과 Y축 여유 공간 계산
    const xMax = Math.ceil(Math.max(...labels.map((x) => parseFloat(x))) / 100) * 100 + 300;
    const yMax = Math.ceil(Math.max(...dataPoints) / 100) * 100 + 300;

    // Base line 생성: start_score + i (i는 증가하는 인덱스)
    const baseLine = Array.from({ length: labels.length }, (_, i) => i);

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
          },
          {
            label: 'Baseline (1 per step)', // 선형 기준선
            data: baseLine, // Base line 데이터
            borderColor: 'rgba(255, 99, 132, 1)', // 빨간색
            backgroundColor: 'rgba(255, 99, 132, 0.2)', // 투명한 빨간색
            borderDash: [5, 5], // 점선
            tension: 0, // 직선
          }
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
    };
  
    new Chart(ctx, chartConfig);
}
