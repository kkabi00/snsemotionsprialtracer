import re
import pandas as pd
import time
import matplotlib.pyplot as plt
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from kiwipiepy import Kiwi
import os

# 누적 데이터 파일 경로
CUMULATIVE_DATA_FILE = 'cumulative_data.csv'

# 위험지수 사전 정의
risk_scores = {
    'admiration': 1.0, 'amusement': 1.0, 'approval': 1.2, 'caring': 1.2, 'curiosity': 1.2,
    'desire': 1.3, 'excitement': 1.4, 'gratitude': 1.2, 'joy': 1.5, 'love': 1.5,
    'optimism': 1.3, 'pride': 1.3, 'relief': 1.0, 'realization': 1.1, 'surprise': 1.0,
    'neutral': 1.0,
    'annoyance': 3.0, 'confusion': 3.2, 'disappointment': 3.5, 'disapproval': 3.8,
    'disgust': 4.0, 'embarrassment': 4.2, 'fear': 4.5, 'grief': 4.5, 'nervousness': 4.0,
    'remorse': 3.5, 'sadness': 4.0, 'anger' : 4.3
}

def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출."""
    if 'youtu.be' in url:
        match = re.search(r"youtu\.be/([^#\&\?]+)", url)
    else:
        match = re.search(r"v=([^#\&\?]+)", url)
    return match.group(1) if match else None

def fetch_youtube_script_with_time(video_id):
    """YouTube 비디오 ID로부터 자막 데이터 및 시간을 가져옵니다."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
        return [{'start': item['start'], 'text': item['text']} for item in transcript]
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def emotion_analysis(text):
    """주어진 텍스트에 대해 감정 분석을 수행."""
    model_name = "monologg/koelectra-base-v3-goemotions"  # 한국어 감정 분석 모델
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

    return nlp(text)

def split_into_sentences(text):
    """Kiwi를 사용하여 텍스트를 문장 단위로 분리."""
    kiwi = Kiwi()
    sentences = [sentence.text for sentence in kiwi.split_into_sents(text)]
    return sentences

def aggregate_emotion_scores(results):
    """감정 분석 결과를 문장 단위로 합산하고 0.5 이상인 감정의 over_half_score 필드를 추가."""
    emotion_scores = {}
    over_half_scores = {}

    # 감정 분석 결과를 순차적으로 처리
    for result in results:
        emotion = result['entity_group']
        score = result['score']

        # 감정 점수를 합산
        if emotion in emotion_scores:
            emotion_scores[emotion] += score
        else:
            emotion_scores[emotion] = score

    # 각 감정의 점수가 0.5 이상이면 1, 그렇지 않으면 0을 기록
    for emotion, score in emotion_scores.items():
        over_half_scores[emotion] = 1 if score >= 0.5 else 0

    return emotion_scores, over_half_scores

def load_cumulative_data():
    """이전 비디오의 누적 데이터를 불러옵니다."""
    if os.path.exists(CUMULATIVE_DATA_FILE):
        df = pd.read_csv(CUMULATIVE_DATA_FILE)
        last_sum_danger_score = df['sum_danger_score'].iloc[-1]
        last_elapsed_time = df['elapsed_time'].iloc[-1]
        return last_sum_danger_score, last_elapsed_time
    else:
        return 0, 0  # 초기값

def save_cumulative_data(sum_danger_score, elapsed_time, video_id, addiction_rate):
    """현재 비디오의 누적 데이터를 파일에 저장하며, 영상 ID와 중독율을 100분율로 추가."""
    # addiction_rate를 100분율로 변환
    addiction_rate_percentage = addiction_rate * 100
    
    # 이전 데이터 불러오기
    _, last_elapsed_time = load_cumulative_data()
    
    # 누적된 elapsed_time 계산
    total_elapsed_time = last_elapsed_time + elapsed_time
    
    data = pd.DataFrame([{
        'video_id': video_id,
        'sum_danger_score': sum_danger_score,
        'elapsed_time': total_elapsed_time,
        'addiction_rate': f"{addiction_rate_percentage:.2f}%"  # 100분율로 표현
    }])
    if os.path.exists(CUMULATIVE_DATA_FILE):
        data.to_csv(CUMULATIVE_DATA_FILE, mode='a', header=False, index=False)
    else:
        data.to_csv(CUMULATIVE_DATA_FILE, index=False)

def plot_sum_danger_score_over_time(df):
    """시간에 따른 sum_danger_score를 시각화하는 꺾은선 그래프를 그립니다."""
    plt.figure(figsize=(12, 6))
    
    # x축은 elapsed_time, y축은 sum_danger_score
    plt.plot(df['elapsed_time'].cumsum(), df['sum_danger_score'], marker='o', linestyle='-')
    
    plt.title('Sum Danger Score Over Elapsed Time')
    plt.xlabel('Elapsed Time (s)')
    plt.ylabel('Sum Danger Score')
    plt.grid(True)
    plt.tight_layout()  # 레이아웃 조정
    plt.show()

def save_to_excel(analysis_data, video_id):
    """문장별 감정 분석 결과를 엑셀 파일로 저장."""
    df_analysis = pd.DataFrame(analysis_data)

    # 'sum_danger_score' 열을 누적 합으로 계산
    df_analysis['sum_danger_score'] = df_analysis['sentence_danger_score'].cumsum()

    excel_filename = f"emotion_analysis_{video_id}.xlsx"
    df_analysis.to_excel(excel_filename, sheet_name="Sentence Analysis", index=False)

    print(f"\n엑셀 파일로 저장 완료: {excel_filename}")

def plot_cumulative_sum_danger_score():
    """누적된 전체 sum_danger_score를 시각화하는 꺾은선 그래프를 그립니다."""
    if os.path.exists(CUMULATIVE_DATA_FILE):
        df = pd.read_csv(CUMULATIVE_DATA_FILE)
        
        # 누적된 sum_danger_score를 계산하여 시각화
        df['cumulative_sum_danger_score'] = df['sum_danger_score'].cumsum()
        
        plt.figure(figsize=(12, 6))
        plt.plot(df['elapsed_time'].cumsum(), df['cumulative_sum_danger_score'], marker='o', linestyle='-')
        plt.title('Overall Cumulative Sum Danger Score Over Elapsed Time')
        plt.xlabel('Elapsed Time (s)')
        plt.ylabel('Cumulative Sum Danger Score')
        plt.grid(True)
        plt.tight_layout()  # 레이아웃 조정
        plt.show()
    else:
        print("누적 데이터를 찾을 수 없습니다. 분석된 데이터가 없습니다.")

def main():
    # 이전 비디오의 누적 데이터 로드
    cumulative_sum_danger_score, cumulative_elapsed_time = load_cumulative_data()

    while True:
        youtube_url = input("YouTube URL 입력 (종료하려면 'exit' 입력): ")
        if youtube_url.lower() == 'exit':
            print("프로그램을 종료하고 누적 데이터를 시각화합니다.")
            plot_cumulative_sum_danger_score()  # 종료 시 누적 데이터 시각화
            break

        video_id = extract_video_id(youtube_url)

        if video_id is None:
            print("잘못된 YouTube URL입니다.")
            continue

        transcript = fetch_youtube_script_with_time(video_id)
        if transcript:
            # 1. 자막 데이터를 문장 단위로 나누기
            sentences = split_into_sentences(' '.join([item['text'] for item in transcript]))
            total_video_time = sum(item['start'] for item in transcript)  # 총 영상 시간 계산

            # 2. 각 문장에 대해 감정 분석 수행
            analysis_data = []
            video_total_danger_score = 0  # 현재 비디오의 총 중독 지수
            for i, sentence in enumerate(sentences):
                print(f"\nAnalyzing sentence: {sentence}")

                # 감정 분석 시작 전 시간 측정
                start_time = transcript[i]['start'] + cumulative_elapsed_time
                start_time_in_seconds = round(start_time, 2)  # 초 단위로 변환

                # 감정 분석 수행
                start_time_analysis = time.time()  # 시작 시간 기록
                results = emotion_analysis(sentence)
                elapsed_time = time.time() - start_time_analysis  # 소요 시간 (초)

                # 감정 결과를 합산하여 문장 단위로 집계 및 over_half_score 계산
                aggregated_scores, over_half_scores = aggregate_emotion_scores(results)

                # sentence_danger_score 계산
                sentence_danger_score = sum(
                    risk_scores.get(emotion, 1.0) for emotion, score in aggregated_scores.items() if score >= 0.5
                )

                # 누적 합 계산
                cumulative_sum_danger_score += sentence_danger_score

                # 분석 결과 저장
                analysis_data.append({
                    'start_time': start_time_in_seconds,
                    'sentence': sentence,
                    'emotions': ', '.join(aggregated_scores.keys()),  # 감정 목록
                    'scores': ', '.join([f"{score:.2f}" for score in aggregated_scores.values()]),  # 점수 목록
                    'sentence_danger_score': round(sentence_danger_score, 2),  # 문장 단위 위험점수
                    'sum_danger_score': round(cumulative_sum_danger_score, 2),  # 누적 위험점수
                    'elapsed_time': round(elapsed_time, 2)  # 감정 분석에 소요된 시간 (초)
                })

            # 시각화
            df_analysis = pd.DataFrame(analysis_data)
            plot_sum_danger_score_over_time(df_analysis)

            # 누적 데이터 저장
            last_elapsed_time = df_analysis['start_time'].iloc[-1]
            save_cumulative_data(cumulative_sum_danger_score, last_elapsed_time, video_id, 0)  # 중독율은 필요 시 0으로 설정

            # 엑셀 파일 저장
            save_to_excel(analysis_data, video_id)

            # 콘솔에 누적 시청 시간 및 누적 위험 지수 출력
            print(f"\n누적 시청 시간: {round(last_elapsed_time / 60, 2)}분")
            print(f"누적 위험 지수: {cumulative_sum_danger_score}")
        else:
            print("이 비디오에는 자막이 없습니다.")

if __name__ == "__main__":
    main()
    