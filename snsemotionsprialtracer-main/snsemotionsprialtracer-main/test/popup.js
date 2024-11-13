document.getElementById("load-image").addEventListener("click", () => {
    // `generated_images` 폴더 안의 PNG 파일을 불러옵니다.
    const imageUrl = chrome.runtime.getURL("generated_images/sum_danger_score_plot_with_baseline.png"); // 예시 파일 경로
    const imageContainer = document.getElementById("emotionChart");

    // 기존 이미지 제거
    imageContainer.innerHTML = "";

    // 새로운 이미지 엘리먼트 추가
    const img = document.createElement("img");
    img.src = imageUrl;
    img.alt = "Image from generated_images folder";
    
    imageContainer.appendChild(img);
});
