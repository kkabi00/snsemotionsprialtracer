import re
import sqlite3
import pandas as pd
import time
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from kiwipiepy import Kiwi

# DB 설정: 감정 분석 결과를 저장할 데이터베이스 파일 이름
DB_FILE = "emotion_analysis_results.db"

# 위험지수 사전 정의
risk_scores = {
    'Admiration': 1.0, 'Amusement': 1.0, 'Approval': 1.2, 'Caring': 1.2, 'Curiosity': 1.2,
    'Desire': 1.3, 'Excitement': 1.4, 'Gratitude': 1.2, 'Joy': 1.5, 'Love': 1.5,
    'Optimism': 1.3, 'Pride': 1.3, 'Relief': 1.0, 'Realization': 1.1, 'Surprise': 1.0,
    'Neutral': 1.0,
    'Annoyance': 3.0, 'Confusion': 3.2, 'Disappointment': 3.5, 'Disapproval': 3.8,
    'Disgust': 4.0, 'Embarrassment': 4.2, 'Fear': 4.5, 'Grief': 4.5, 'Nervousness': 4.0,
    'Remorse': 3.5, 'Sadness': 4.0
}
def save_to_database(data, video_id):
    """문장별 감정 분석 결과를 SQLite DB에 저장."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 테이블 생성 (존재하지 않으면 생성)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emotion_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            sentence TEXT,
            emotions TEXT,
            scores TEXT,
            emotion_risk_scores TEXT,  # 감정별 위험지수 열 추가
            elapsed_time_ms REAL,
            over_half_score TEXT,
            risk_score_sum REAL
        )
    """)

    # 감정 분석 결과를 DB에 삽입
    for row in data:
        cursor.execute("""
            INSERT INTO emotion_analysis (video_id, sentence, emotions, scores, emotion_risk_scores, elapsed_time_ms, over_half_score, risk_score_sum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (video_id, row['sentence'], row['emotions'], row['scores'], row['emotion_risk_scores'], row['elapsed_time_ms'], row['over_half_score'], row['risk_score_sum']))

    # 변경 사항 저장 및 연결 종료
    conn.commit()
    conn.close()
def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출."""
    if 'youtu.be' in url:
        match = re.search(r"youtu\.be/([^#\&\?]+)", url)
    else:
        match = re.search(r"v=([^#\&\?]+)", url)
    return match.group(1) if match else None


def fetch_youtube_script(video_id):
    """YouTube 비디오 ID로부터 자막 데이터를 가져옵니다."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
        return ' '.join([item['text'] for item in transcript])
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


# aggregate_emotion_scores 함수 수정
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

def save_to_excel(data, video_id):
    """문장별 감정 분석 결과를 엑셀 파일로 저장."""
    # 데이터를 DataFrame으로 변환
    df = pd.DataFrame(data)

    # 엑셀 파일로 저장
    excel_filename = f"emotion_analysis_{video_id}.xlsx"
    df.to_excel(excel_filename, index=False)
    print(f"\n엑셀 파일로 저장 완료: {excel_filename}")

def display_results(video_id):
    """DB에 저장된 결과를 표 형식으로 출력."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM emotion_analysis WHERE video_id = '{video_id}'", conn)
    conn.close()
    if df.empty:
        print(f"No results found for video ID: {video_id}")
    else:
        print(f"\nEmotion Analysis Results for Video ID: {video_id}")
        print(df)


def main():
    youtube_url = input("YouTube URL 입력: ")
    video_id = extract_video_id(youtube_url)

    if video_id is None:
        print("잘못된 YouTube URL입니다.")
        return

    script = fetch_youtube_script(video_id)
    if script:
        # 1. 전체 스크립트를 문장 단위로 나누기
        sentences = split_into_sentences(script)

        # 2. 각 문장에 대해 감정 분석 수행
        analysis_data = []
        for sentence in sentences:
            print(f"\nAnalyzing sentence: {sentence}")

            # 감정 분석 시작 전 시간 측정
            start_time = time.time()

            # 감정 분석 수행
            results = emotion_analysis(sentence)

            # 감정 분석 종료 후 시간 측정
            elapsed_time = time.time() - start_time  # 소요 시간 (초)
            elapsed_time_ms = round(elapsed_time * 1000, 2)  # ms 단위로 변환

            # 감정 결과를 합산하여 문장 단위로 집계 및 over_half_score 계산
            aggregated_scores, over_half_scores = aggregate_emotion_scores(results)

            # 감정 점수와 over_half_score를 동일한 순서로 나열
            emotions_list = list(aggregated_scores.keys())
            scores_list = [f"{score:.2f}" for score in aggregated_scores.values()]
            over_half_scores_list = [str(over_half_scores[emotion]) for emotion in emotions_list]

            # 위험지수 합계 계산
            risk_score_sum = sum(risk_scores.get(emotion, 1.0) * over_half_scores[emotion] for emotion in emotions_list)

            # 각 감정의 위험지수 리스트 생성
            emotion_risk_scores_list = [f"{risk_scores.get(emotion, 1.0):.1f}" for emotion in emotions_list]

            # 합산된 감정 점수와 over_half_score를 저장할 형식으로 변환
            analysis_data.append({
                'sentence': sentence,
                'emotions': ', '.join(emotions_list),  # 감정 목록
                'scores': ', '.join(scores_list),  # 점수 목록
                'elapsed_time_ms': elapsed_time_ms,  # 감정 분석에 소요된 시간 (ms)
                'over_half_score': ', '.join(over_half_scores_list),  # 각 감정에 대한 over_half_score 목록
                'risk_score_sum': round(risk_score_sum, 2),  # 위험지수 합계
                'emotion_risk_scores': ', '.join(emotion_risk_scores_list)  # 감정별 위험지수 목록 추가
            })

        # 3. DB에 감정 분석 결과 저장
        save_to_database(analysis_data, video_id)

        # 4. 엑셀 파일로 저장
        save_to_excel(analysis_data, video_id)

        # 5. 저장된 결과를 표 형식으로 보기
        display_results(video_id)
    else:
        print("이 비디오에는 자막이 없습니다.")


if __name__ == "__main__":
    main()
