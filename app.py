from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import re
import pandas as pd
#import time
import matplotlib 
matplotlib.use('Agg')  # 수정 부분 
import matplotlib.pyplot as plt 
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from kiwipiepy import Kiwi
import os
from datetime import datetime
import signal  # 수정 부분
import sys     # 수정 부분

app = Flask(__name__)
CORS(app)
# 누적 데이터 파일 경로
CUMULATIVE_DATA_FILE = 'cumulative_data.csv'
# 이미지 폴더 설정
OUTPUT_FOLDER = "test/generated_images"
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

# 위험지수 사전 정의
risk_scores = {
    'admiration': 1.0, 'amusement': 1.0, 'approval': 1.2, 'caring': 1.2, 'curiosity': 1.2,
    'desire': 1.3, 'excitement': 1.4, 'gratitude': 1.2, 'joy': 1.5, 'love': 1.5,
    'optimism': 1.3, 'pride': 1.3, 'relief': 1.0, 'realization': 1.1, 'surprise': 1.0,
    'neutral': 1.0,
    'annoyance': 3.0, 'confusion': 3.2, 'disappointment': 3.5, 'disapproval': 3.8,
    'disgust': 4.0, 'embarrassment': 4.2, 'fear': 4.5, 'grief': 4.5, 'nervousness': 4.0,
    'remorse': 3.5, 'sadness': 4.0, 'anger': 4.3
}

def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출."""
    if 'youtu.be' in url:
        match = re.search(r"youtu\.be/([^#\&\?]+)", url)
    else:
        match = re.search(r"v=([^#\&\?]+)", url)
    return match.group(1) if match else None

def fetch_youtube_script_with_time(video_id):
    """YouTube 비디오 ID로부터 자막 데이터 및 시간 조회."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
        return [{'start': item['start'], 'text': item['text']} for item in transcript]
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def emotion_analysis(text):
    """주어진 텍스트에 대해 감정 분석 수행."""
    model_name = "monologg/koelectra-base-v3-goemotions"  # 한국어 감정 분석 모델
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

    return nlp(text)

def split_into_sentences(text):
    """Kiwi 사용, 텍스트를 문장 단위로 분리"""
    kiwi = Kiwi()
    sentences = [sentence.text for sentence in kiwi.split_into_sents(text)] # type: ignore
    return sentences

def aggregate_emotion_scores(results):
    """감정 분석 결과 문장 단위로 합산, 0.5 이상인 감정의 over_half_score 필드 처리"""
    #최종 결과에 over_half_score 필드 더이상 불필요하므로 제거
    emotion_scores = {}
    over_half_scores = {}

    for result in results:
        emotion = result['entity_group']
        score = result['score']
        if emotion in emotion_scores:
            emotion_scores[emotion] += score
        else:
            emotion_scores[emotion] = score

    for emotion, score in emotion_scores.items():
        over_half_scores[emotion] = 1 if score >= 0.5 else 0

    return emotion_scores, over_half_scores

def get_output_folder(user_name):
    """사용자 이름과 현재 날짜 기준, 출력 폴더 생성"""
    today = datetime.now().strftime("%Y-%m-%d")
    output_folder = os.path.join("outputs", user_name, today)
    os.makedirs(output_folder, exist_ok=True)
    return output_folder

def load_cumulative_data():
    """이전 비디오의 누적 데이터 read"""
    if os.path.exists(CUMULATIVE_DATA_FILE):
        df = pd.read_csv(CUMULATIVE_DATA_FILE)
        last_sum_danger_score = df['sum_danger_score'].iloc[-1]
        last_elapsed_time = df['elapsed_time'].iloc[-1]
        return last_sum_danger_score, last_elapsed_time
    else:
        return 0, 0

def save_cumulative_data(sum_danger_score, elapsed_time, video_id, output_folder, addiction_rate=0):
    """현재 비디오의 누적 데이터 update"""
    addiction_rate_percentage = addiction_rate * 100
    _, last_elapsed_time = load_cumulative_data()
    total_elapsed_time = last_elapsed_time + elapsed_time

    data = pd.DataFrame([{
        'video_id': video_id,
        'sum_danger_score': sum_danger_score,
        'elapsed_time': total_elapsed_time,
        'addiction_rate': f"{addiction_rate_percentage:.2f}%"
    }])

    file_path = os.path.join(output_folder, 'cumulative_data.csv')
    if os.path.exists(file_path):
        data.to_csv(file_path, mode='a', header=False, index=False)
    else:
        data.to_csv(file_path, index=False)

def plot_sum_danger_score_over_time(df, output_folder):
    """시간에 따른 sum_danger_score를 시각화, 증가율이 1인 기준선 전경 추가"""
    plt.figure(figsize=(12, 6))
    
    # 누적된 sum_danger_score 그래프
    plt.plot(df['start_time'].cumsum(), df['sum_danger_score'], marker='o', linestyle='-', label='Sum Danger Score')
    
    # 기준선 (증가율이 1, 시작점은 첫 영상의 시작 sum danger score)
    start_score = df['sum_danger_score'].iloc[0]  # 첫 sum danger score 값을 기준으로 설정
    base_line = [start_score + i for i in range(len(df))]  # 증가율이 1인 선형 기준선
    plt.plot(df['start_time'].cumsum(), base_line, linestyle='--', color='red', label='Baseline (1 per step)')
    
    # 그래프 설정
    plt.title('Sum Danger Score Over Elapsed Time with Baseline')
    plt.xlabel('Elapsed Time (s)')
    plt.ylabel('Sum Danger Score')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    # 이미지 저장
    image_path = os.path.join(output_folder, 'sum_danger_score_plot_with_baseline.png')
    plt.savefig(image_path)
    plt.close()
    print(f"Plot saved to {image_path}")

def save_to_excel(analysis_data, video_id, output_folder):
    """문장별 감정 분석 결과: 엑셀화"""
    df_analysis = pd.DataFrame(analysis_data)
    df_analysis['sum_danger_score'] = df_analysis['sentence_danger_score'].cumsum()

    excel_filename = os.path.join(output_folder, f"emotion_analysis_{video_id}.xlsx")
    df_analysis.to_excel(excel_filename, sheet_name="Sentence Analysis", index=False)
    print(f"\n저장 완료: {excel_filename}")

def format_time_in_minutes_and_seconds(time_in_minutes):
    """시간 포맷팅."""
    minutes = int(time_in_minutes)
    seconds = int((time_in_minutes - minutes) * 60)
    return f"{minutes}분 {seconds}초"

@app.route('/', methods=['POST']) # type: ignore
def process_url():
    data = request.get_json()
    youtube_url = data.get("url")
    print("성공")
    # URL을 이용해 이미지 생성 로직 수행 
    # 여기 부분을 
    image_path = create_image_from_url(youtube_url)
    
    if image_path is None:
        print("process_url() 종료")
    else :
        # 이미지의 URL을 확장 프로그램에 반환
        return jsonify({"image_url": f"{image_path}"})

def create_image_from_url(url):
    image_filename = "sum_danger_score_plot_with_baseline.png"  # 예시 파일 이름
    image_path = os.path.join(OUTPUT_FOLDER, image_filename)
    #output_folder = get_output_folder("user_name")
    cumulative_sum_danger_score, cumulative_elapsed_time = load_cumulative_data()
    #youtube_url = input("YouTube URL 입력 (종료하려면 'exit' 입력): ")
    youtube_url = url
    if youtube_url.lower() == 'exit':
        print("누적 데이터를 시각화 및 프로그램 자동 종료")
        return None
    video_id = extract_video_id(youtube_url)
    if video_id is None:
        print("잘못된 YouTube URL입니다.")
        return None

    transcript = fetch_youtube_script_with_time(video_id)
    if not transcript:
        print("이 비디오는 자막이 없습니다.")
        return None
    else:
        sentences = split_into_sentences(' '.join([item['text'] for item in transcript]))

        analysis_data = []
        for i, sentence in enumerate(sentences):
            print(f"\nAnalyzing sentence: {sentence}")
            start_time = transcript[i]['start']  # 초 단위
            start_time_in_seconds = round(start_time, 2)

            # 감정 분석 수행
            results = emotion_analysis(sentence)

            aggregated_scores, over_half_scores = aggregate_emotion_scores(results)
            sentence_danger_score = sum(
                risk_scores.get(emotion, 1.0) for emotion, score in aggregated_scores.items() if score >= 0.5
            )
            cumulative_sum_danger_score += sentence_danger_score

            analysis_data.append({
                'start_time': start_time_in_seconds,
                'sentence': sentence,
                'emotions': ', '.join(aggregated_scores.keys()),
                'scores': ', '.join([f"{score:.2f}" for score in aggregated_scores.values()]),
                'sentence_danger_score': round(sentence_danger_score, 2),
                'sum_danger_score': round(cumulative_sum_danger_score, 2)
            })

        # 총 비디오 시청 시간은 마지막 문장의 start_time + 해당 문장의 길이
        last_sentence_start_time = transcript[-1]['start']  # 초 단위
        last_sentence_length_estimate = len(transcript[-1]['text']) / 100  # 문장의 길이를 시간으로 변환 (추정치)
        video_total_time = last_sentence_start_time + last_sentence_length_estimate  # 초 단위

        # 누적 시청 시간 업데이트 (분 단위로 변환)
        cumulative_elapsed_time += (cumulative_elapsed_time + video_total_time) / 60  # 초 -> 분

        df_analysis = pd.DataFrame(analysis_data)
        plot_sum_danger_score_over_time(df_analysis, OUTPUT_FOLDER)
        save_cumulative_data(cumulative_sum_danger_score, video_total_time, video_id, OUTPUT_FOLDER)
        #save_to_excel(analysis_data, video_id, OUTPUT_FOLDER)

        # 누적 시청 시간을 분 초 형태로 포맷팅하여 출력
        formatted_time = format_time_in_minutes_and_seconds(cumulative_elapsed_time)
        print(f"\n누적 시청 시간: {formatted_time}") #오류 다소 있음
        print(f"누적 위험 지수: {cumulative_sum_danger_score}")
        return f"{OUTPUT_FOLDER}/{image_filename}"

def signal_handler(sig, frame):  # 수정 부분
    print("프로그램 종료 중...")
    sys.exit(0)  
    
# 정적 파일 서빙을 위한 경로
@app.route('/generated_images/<filename>')
def serve_image(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), mimetype='image/png')
# 서버 실행
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)  # 수정 부분
    app.run(debug=True, use_reloader=False)  # 수정 부분

# DB_FILE = "emotion_analysis_results.db"
# # 감정 위험 점수 정의
# risk_scores = {
#     'Admiration': 1.0, 'Amusement': 1.0, 'Approval': 1.2, 'Caring': 1.2, 'Curiosity': 1.2,
#     'Desire': 1.3, 'Excitement': 1.4, 'Gratitude': 1.2, 'Joy': 1.5, 'Love': 1.5,
#     'Optimism': 1.3, 'Pride': 1.3, 'Relief': 1.0, 'Realization': 1.1, 'Surprise': 1.0,
#     'Neutral': 1.0,  # 대소문자 일치
#     'Annoyance': 3.0, 'Confusion': 3.2, 'Disappointment': 3.5, 'Disapproval': 3.8,
#     'Disgust': 4.0, 'Embarrassment': 4.2, 'Fear': 4.5, 'Grief': 4.5, 'Nervousness': 4.0,
#     'Remorse': 3.5, 'Sadness': 4.0
# }

# # 유튜브 URL에서 video ID 추출
# def extract_video_id(url):
#     try:
#         if 'youtu.be' in url:
#             match = re.search(r"youtu\.be/([^#\&\?]+)", url)
#         else:
#             match = re.search(r"v=([^#\&\?]+)", url)
#         return match.group(1) if match else None
#     except Exception as e:
#         return None

# # 유튜브 자막 가져오기
# def fetch_youtube_script(video_id):
#     try:
#         transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
#         return ' '.join([item['text'] for item in transcript])
#     except Exception as e:
#         print(e)
#         return None

# # 감정 분석 실행
# def emotion_analysis(text):
#     model_name = "monologg/koelectra-base-v3-goemotions"
#     tokenizer = AutoTokenizer.from_pretrained(model_name)
#     model = AutoModelForTokenClassification.from_pretrained(model_name)
#     nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
#     return nlp(text)

# # 텍스트를 문장으로 분할
# def split_into_sentences(text):
#     kiwi = Kiwi()
#     sentences = [sentence.text for sentence in kiwi.split_into_sents(text)]
#     return sentences

# # 감정 점수 집계
# def aggregate_emotion_scores(results):
#     emotion_scores = {}
#     over_half_scores = {}

#     for result in results:
#         emotion = result['entity_group']
#         score = result['score']
#         emotion_scores[emotion] = emotion_scores.get(emotion, 0) + score

#     for emotion, score in emotion_scores.items():
#         over_half_scores[emotion] = 1 if score >= 0.5 else 0

#     return emotion_scores, over_half_scores

# 분석 결과 저장
# 데이터베이스 연결 시간 제외
# def save_to_database(data, video_id):
#     conn = sqlite3.connect(DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS emotion_analysis (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             video_id TEXT,
#             sentence TEXT,
#             emotions TEXT,
#             scores TEXT,
#             emotion_risk_scores TEXT,
#             elapsed_time_ms REAL,
#             over_half_score TEXT,
#             risk_score_sum REAL
#         )
#     """)

#     for row in data:
#         cursor.execute("""
#             INSERT INTO emotion_analysis (video_id, sentence, emotions, scores, emotion_risk_scores, elapsed_time_ms, over_half_score, risk_score_sum)
#             VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#         """, (video_id, row['sentence'], row['emotions'], row['scores'], row['emotion_risk_scores'], row['elapsed_time_ms'], row['over_half_score'], row['risk_score_sum']))

#     conn.commit()
#     conn.close()