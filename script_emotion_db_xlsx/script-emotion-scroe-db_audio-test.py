import re
import sqlite3
import pandas as pd
import time
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from kiwipiepy import Kiwi
from pydub import AudioSegment
import speech_recognition as sr
import yt_dlp

DB_FILE = "emotion_analysis_results.db"

risk_scores = {
    'Admiration': 1.0, 'Amusement': 1.0, 'Approval': 1.2, 'Caring': 1.2, 'Curiosity': 1.2,
    'Desire': 1.3, 'Excitement': 1.4, 'Gratitude': 1.2, 'Joy': 1.5, 'Love': 1.5,
    'Optimism': 1.3, 'Pride': 1.3, 'Relief': 1.0, 'Realization': 1.1, 'Surprise': 1.0,
    'Neutral': 1.0,  # 대소문자 일치
    'Annoyance': 3.0, 'Confusion': 3.2, 'Disappointment': 3.5, 'Disapproval': 3.8,
    'Disgust': 4.0, 'Embarrassment': 4.2, 'Fear': 4.5, 'Grief': 4.5, 'Nervousness': 4.0,
    'Remorse': 3.5, 'Sadness': 4.0
}

def extract_video_id(url):
    if 'youtu.be' in url:
        match = re.search(r"youtu\.be/([^#\&\?]+)", url)
    else:
        match = re.search(r"v=([^#\&\?]+)", url)
    return match.group(1) if match else None

def download_video_audio(video_id):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': f"{video_id}.%(ext)s"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

    return f"{video_id}.mp3"

def convert_audio_to_text(audio_file):
    recognizer = sr.Recognizer()
    sound = AudioSegment.from_mp3(audio_file)
    sound.export("converted.wav", format="wav")  # wav 파일로 변환

    with sr.AudioFile("converted.wav") as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language='ko-KR')
            return text
        except sr.UnknownValueError:
            print("STT에서 텍스트를 추출할 수 없습니다.")
            return None

def fetch_youtube_script(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])
        return ' '.join([item['text'] for item in transcript])
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        print("자막을 찾을 수 없습니다. STT로 오디오를 텍스트로 변환합니다...")
        audio_file = download_video_audio(video_id)
        return convert_audio_to_text(audio_file)

def emotion_analysis(text):
    model_name = "monologg/koelectra-base-v3-goemotions"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForTokenClassification.from_pretrained(model_name)
    nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")

    return nlp(text)

def split_into_sentences(text):
    kiwi = Kiwi()
    sentences = [sentence.text for sentence in kiwi.split_into_sents(text)]
    return sentences

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

def save_to_excel(data, video_id):
    df = pd.DataFrame(data)
    excel_filename = f"emotion_analysis_{video_id}.xlsx"
    df.to_excel(excel_filename, index=False)
    print(f"\n엑셀 파일로 저장 완료: {excel_filename}")

def display_results(video_id):
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
        sentences = split_into_sentences(script)
        analysis_data = []
        for sentence in sentences:
            print(f"\nAnalyzing sentence: {sentence}")
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
        save_to_excel(analysis_data, video_id)
        display_results(video_id)
    else:
        print("이 비디오에는 자막이 없습니다.")

if __name__ == "__main__":
    main()
