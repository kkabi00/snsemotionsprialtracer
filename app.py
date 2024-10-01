from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
import time
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from kiwipiepy import Kiwi
from pydub import AudioSegment
import speech_recognition as sr
import yt_dlp
import re

app = Flask(__name__)
CORS(app) # 모든 출처에 대해 CORS 허용 (보안 문제가 생길지도... 나중에 빼기)
DB_FILE = "emotion_analysis_results.db"

# 감정 위험 점수 정의
risk_scores = {
    'Admiration': 1.0, 'Amusement': 1.0, 'Approval': 1.2, 'Caring': 1.2, 'Curiosity': 1.2,
    'Desire': 1.3, 'Excitement': 1.4, 'Gratitude': 1.2, 'Joy': 1.5, 'Love': 1.5,
    'Optimism': 1.3, 'Pride': 1.3, 'Relief': 1.0, 'Realization': 1.1, 'Surprise': 1.0,
    'Neutral': 1.0,  # 대소문자 일치
    'Annoyance': 3.0, 'Confusion': 3.2, 'Disappointment': 3.5, 'Disapproval': 3.8,
    'Disgust': 4.0, 'Embarrassment': 4.2, 'Fear': 4.5, 'Grief': 4.5, 'Nervousness': 4.0,
    'Remorse': 3.5, 'Sadness': 4.0
}

# 유튜브 URL에서 video ID 추출
def extract_video_id(url):
    if 'youtu.be' in url:
        match = re.search(r"youtu\.be/([^#\&\?]+)", url)
    else:
        match = re.search(r"v=([^#\&\?]+)", url)
    return match.group(1) if match else None

# 유튜브 자막 가져오기
def fetch_youtube_script(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
        return ' '.join([item['text'] for item in transcript])
    except Exception as e:
        return None

# 감정 분석 실행
def emotion_analysis(text):
    model_name = "monologg/koelectra-base-v3-goemotions"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
    return nlp(text)

# 텍스트를 문장으로 분할
def split_into_sentences(text):
    kiwi = Kiwi()
    sentences = [sentence.text for sentence in kiwi.split_into_sents(text)]
    return sentences

# 감정 점수 집계
def aggregate_emotion_scores(results):
    emotion_scores = {}
    over_half_scores = {}

    for result in results:
        emotion = result['entity_group']
        score = result['score']
        emotion_scores[emotion] = emotion_scores.get(emotion, 0) + score

    for emotion, score in emotion_scores.items():
        over_half_scores[emotion] = 1 if score >= 0.5 else 0

    return emotion_scores, over_half_scores

# 분석 결과 저장
def save_to_database(data, video_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emotion_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            sentence TEXT,
            emotions TEXT,
            scores TEXT,
            emotion_risk_scores TEXT,
            elapsed_time_ms REAL,
            over_half_score TEXT,
            risk_score_sum REAL
        )
    """)

    for row in data:
        cursor.execute("""
            INSERT INTO emotion_analysis (video_id, sentence, emotions, scores, emotion_risk_scores, elapsed_time_ms, over_half_score, risk_score_sum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (video_id, row['sentence'], row['emotions'], row['scores'], row['emotion_risk_scores'], row['elapsed_time_ms'], row['over_half_score'], row['risk_score_sum']))

    conn.commit()
    conn.close()

# API 엔드포인트
@app.route('/analyze', methods=['POST'])
def analyze():
    youtube_url = request.json.get('youtube_url')
    video_id = extract_video_id(youtube_url)

    if video_id is None:
        return jsonify({'error': 'Invalid YouTube URL'}), 400

    script = fetch_youtube_script(video_id)
    if not script:
        return jsonify({'error': 'Could not fetch transcript'}), 500

    sentences = split_into_sentences(script)
    analysis_data = []
    for sentence in sentences:
        start_time = time.time()
        results = emotion_analysis(sentence)
        elapsed_time = time.time() - start_time
        elapsed_time_ms = round(elapsed_time * 1000, 2)

        aggregated_scores, over_half_scores = aggregate_emotion_scores(results)
        emotions_list = list(aggregated_scores.keys())
        scores_list = [f"{score:.2f}" for score in aggregated_scores.values()]
        over_half_scores_list = [str(over_half_scores[emotion]) for emotion in emotions_list]
        risk_score_sum = sum(risk_scores.get(emotion, 1.0) * over_half_scores[emotion] for emotion in emotions_list)
        emotion_risk_scores_list = [f"{risk_scores.get(emotion, 1.0):.1f}" for emotion in emotions_list]

        analysis_data.append({
            'sentence': sentence,
            'emotions': ', '.join(emotions_list),
            'scores': ', '.join(scores_list),
            'elapsed_time_ms': elapsed_time_ms,
            'over_half_score': ', '.join(over_half_scores_list),
            'risk_score_sum': round(risk_score_sum, 2),
            'emotion_risk_scores': ', '.join(emotion_risk_scores_list)
        })

    save_to_database(analysis_data, video_id)
    return jsonify({'video_id': video_id, 'analysis_data': analysis_data}), 200

# 서버 실행
if __name__ == '__main__':
    app.run(debug=True)