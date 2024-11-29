#non-kiwi ver
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import numpy as np
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import re
import pandas as pd
import matplotlib 
matplotlib.use('Agg')  # 수정 부분  
import matplotlib.pyplot as plt  # 수정 부분
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
# from kiwipiepy import Kiwi
import os
from datetime import datetime
import signal  
import sys     
import csv #csv 업로드

app = Flask(__name__)
CORS(app)
# 누적 데이터 파일 경로
CUMULATIVE_DATA_FILE = 'test/generated_images/cumulative_data.csv'  
CUMULATIVE_DATA_FILE2 = 'test/generated_images/current_data.csv'
# 이미지 폴더 설정
OUTPUT_FOLDER = "test/generated_images"
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
@app.route("/")
def index():
    return f"Current working directory: {os.getcwd()}"
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
        return [{'start': item['start'], 'duration': item['duration'], 'text': item['text']} for item in transcript]
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
    # kiwi = Kiwi()
    # sentences = [sentence.text for sentence in kiwi.split_into_sents(text)] # type: ignore
    sentences = text.split(',')
    return sentences

def aggregate_emotion_scores(results): 
    """감정 분석 결과 문장 단위로 합산, 0.5 이상인 감정의 over_half_score 필드 처리"""
    #최종 결과에 over_half_score 필드 더이상 불필요하므로 제거
    emotion_scores = {}
    # over_half_scores = {} # 수정 부분

    for result in results:
        emotion = result['entity_group']
        score = result['score']
        if emotion in emotion_scores:
            emotion_scores[emotion] += score
        else:
            emotion_scores[emotion] = score

    # for emotion, score in emotion_scores.items(): # 수정 부분
    #     over_half_scores[emotion] = 1 if score >= 0.5 else 0  # 수정 부분

    return emotion_scores

def get_output_folder(user_name):
    """사용자 이름과 현재 날짜 기준, 출력 폴더 생성"""
    today = datetime.now().strftime("%Y-%m-%d")
    output_folder = os.path.join("outputs", user_name, today)
    os.makedirs(output_folder, exist_ok=True)
    return output_folder

def load_cumulative_data():
    """이전 비디오의 누적 데이터 read"""
    if os.path.exists(CUMULATIVE_DATA_FILE):
        print("데이터 파일 있음")
        df = pd.read_csv(CUMULATIVE_DATA_FILE)
        last_sum_danger_score = df['sum_danger_score'].iloc[-1]
        last_elapsed_time = df['elapsed_time'].iloc[-1]
        return last_sum_danger_score, last_elapsed_time
    else:
        print("데이터 파일 없음")
        return 0, 0
    
def save_current_data(df):
    file_path = os.path.join(OUTPUT_FOLDER, 'current_data.csv')
    if os.path.exists(file_path):
        df.to_csv(file_path, mode='a', header=False, index=False)
    else:
        df.to_csv(file_path, index=False)

def save_cumulative_data(sum_danger_score, elapsed_time, video_id, output_folder, addiction_rate = 0):
    """현재 비디오의 누적 데이터 update"""
    addiction_rate_percentage = addiction_rate * 100
    _, last_elapsed_time = load_cumulative_data()
    total_elapsed_time = last_elapsed_time + elapsed_time

    data = pd.DataFrame([{
        'video_id': video_id,
        'sum_danger_score': round(sum_danger_score, 2),  
        'elapsed_time': round(total_elapsed_time, 2),    
        'addiction_rate': f"{addiction_rate_percentage:.2f}%"
    }])

    file_path = os.path.join(output_folder, 'cumulative_data.csv')
    if os.path.exists(file_path):
        data.to_csv(file_path, mode='a', header=False, index=False)
    else:
        data.to_csv(file_path, index=False)

model = None
scaler_X = None
scaler_Y = None

def regression_results():
    global model, scaler_X, scaler_Y
    df1 = pd.read_csv(CUMULATIVE_DATA_FILE2)
    df2 = pd.read_csv('test/generated_images/dataset.csv')  #딥러닝 시킬 데이터 경로 직접 따로 추가
    
    X = np.array(df2['start_time']) 
    Y = np.array(df2['sum_danger_score'])

    # 데이터 정규화
    scaler_X = StandardScaler()
    X_scaled = scaler_X.fit_transform(X.reshape(-1, 1)) 

    scaler_Y = StandardScaler()
    Y_scaled = scaler_Y.fit_transform(Y.reshape(-1, 1)) 

    # 데이터 분할 
    X_train, X_val, Y_train, Y_val = train_test_split(X_scaled, Y_scaled, test_size=0.2, random_state=42)

    # 모델 정의
    model = Sequential([
        Dense(128, input_dim=1, activation='relu'), 
        Dense(64, activation='relu'),
        Dense(64, activation='relu'),
        Dense(1) 
    ])

    # 모델 컴파일
    model.compile(optimizer='adam', loss='mse')

    # 모델 학습
    model.fit(X_train, Y_train, epochs=50, batch_size=32, validation_data=(X_val, Y_val)) 

def plot_sum_danger_score_over_time(output_folder): 
    global model, scaler_X, scaler_Y

    df = pd.read_csv(CUMULATIVE_DATA_FILE)
    df1 = pd.read_csv(CUMULATIVE_DATA_FILE2)

    # 예측값 생성
    x1 = np.array(df1['start_time']) 
    x1_scaled = scaler_X.transform(x1.reshape(-1, 1))

    predicted_scores = model.predict(x1_scaled)
    
    # 예측된 값을 원래의 scale로 변환
    predicted_scores_original = scaler_Y.inverse_transform(predicted_scores)

    # 새로운 베이스라인 생성
    new_base_line = predicted_scores_original.flatten() 
    data = pd.DataFrame([{
    'start_time': x1[i],
    'sum_danger_score': new_base_line[i]
    } for i in range(len(x1))])

    file_path = os.path.join(OUTPUT_FOLDER, 'mlp_data.csv')
    if os.path.exists(file_path):
        data.to_csv(file_path, mode='a', header=False, index=False, float_format='%.2f')
    else:
        data.to_csv(file_path, index=False, float_format='%.2f')

    # 기존 그래프에 새로운 베이스라인 추가
    plt.plot(df1['start_time'], df1['sum_danger_score'], marker='o', linestyle='-', label='Sum Danger Score')
    plt.plot(df1['start_time'], new_base_line, linestyle='--', color='red', label='Predicted Baseline')

    # x축과 y축의 동적 할당
    plt.xlim(left=0, right=df['elapsed_time'].iloc[-1]+200) 
    plt.ylim(bottom=0, top=df['sum_danger_score'].iloc[-1]+200)

    plt.title('Sum Danger Score Over Elapsed Time with Baseline')
    plt.xlabel('Elapsed Time (s)')
    plt.ylabel('Sum Danger Score')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    image_path = os.path.join(OUTPUT_FOLDER, 'test.png')
    plt.savefig(image_path)
    plt.close()
    print(f"Plot saved to {image_path}")

    # loss = model.evaluate(x1_scaled, y1_scaled)
    # print(f'Model Loss: {loss}')

# def save_to_excel(analysis_data, video_id, output_folder):
#     """문장별 감정 분석 결과: 엑셀화"""
#     df_analysis = pd.DataFrame(analysis_data)
#     df_analysis['sum_danger_score'] = df_analysis['sentence_danger_score'].cumsum()

#     excel_filename = os.path.join(output_folder, f"emotion_analysis_{video_id}.xlsx")
#     df_analysis.to_excel(excel_filename, sheet_name="Sentence Analysis", index=False)
#     print(f"\n저장 완료: {excel_filename}")

def format_time_in_minutes_and_seconds(time_in_minutes):
    """시간 포맷팅."""
    minutes = int(time_in_minutes)
    seconds = int((time_in_minutes - minutes) * 60)
    return f"{minutes}분 {seconds}초"

@app.route('/', methods=['POST'])
def process_url():
    data = request.get_json()
    youtube_url = data.get("url")
    print("성공")
    # URL을 이용해 이미지 생성 로직 수행
    image_path = create_image_from_url(youtube_url)
    
    # 이미지의 URL을 확장 프로그램에 반환
    # return jsonify({"image_url": f"{image_path}"})

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
    if transcript:
        sentences = ([item['text'] for item in transcript])

        if os.path.exists(CUMULATIVE_DATA_FILE2): 
            df2 = pd.read_csv(CUMULATIVE_DATA_FILE2) 
            last_start_time = df2['start_time'].iloc[-1]
        else:
            last_start_time = 0
    
        analysis_data = []
        for i, sentence in enumerate(sentences):
            
            print(f"\nAnalyzing text: {sentence}")
            
            start_time_in_seconds = last_start_time + transcript[i]['start'] 

            # 감정 분석 수행
            results = emotion_analysis(sentence)

            aggregated_scores = aggregate_emotion_scores(results) 
            sentence_danger_score = sum(
                risk_scores.get(emotion, 1.0) for emotion, score in aggregated_scores.items() if score >= 0.5
            )
            cumulative_sum_danger_score += sentence_danger_score

            analysis_data.append({ 
                'start_time': round(start_time_in_seconds, 2),
                #'sentences': sentence, # 준영수정 아래 필요없는 부분 처리함
                #'emotions': ', '.join(aggregated_scores.keys()),
                #'scores': ', '.join([f"{score:.2f}" for score in aggregated_scores.values()]),
                #'sentence_danger_score': round(sentence_danger_score, 2),
                'sum_danger_score': round(cumulative_sum_danger_score, 2)
            })

        # 총 비디오 시청 시간은 마지막 문장의 start_time + 해당 문장의 길이
        last_sentence_start_time = transcript[-1]['start']  # 초 단위
        last_sentence_length_estimate = len(transcript[-1]['text']) / 100  # 문장의 길이를 시간으로 변환 (추정치) 
        video_total_time = last_sentence_start_time + last_sentence_length_estimate  # 초 단위 
        
        # 추가
        # total_sentences = len(transcript)
        # for i, sentence in enumerate(analysis_data):
        # # 각 문장의 시작 시간을 비디오 시간에 맞게 균등 분배
        # start_time_in_seconds = (video_total_time / total_sentences) * (i + 1)
        # sentence['start_time'] = round(start_time_in_seconds, 2)
        
        df_analysis = pd.DataFrame(analysis_data)
        save_current_data(df_analysis) # 수정 부분
        save_cumulative_data(cumulative_sum_danger_score, video_total_time, video_id, OUTPUT_FOLDER)
        plot_sum_danger_score_over_time(OUTPUT_FOLDER)
        #save_to_excel(analysis_data, video_id, OUTPUT_FOLDER)

        # 누적 시청 시간 업데이트 (분 단위로 변환)
        cumulative_elapsed_time = (cumulative_elapsed_time + video_total_time) / 60  # 초 -> 분

        # 누적 시청 시간을 분 초 형태로 포맷팅하여 출력
        formatted_time = format_time_in_minutes_and_seconds(cumulative_elapsed_time)
        print(f"\n누적 시청 시간: {formatted_time}") 
        print(f"누적 위험 지수: {round(cumulative_sum_danger_score, 2)}")
        return f"{OUTPUT_FOLDER}/{image_filename}"
    else:
        print("이 비디오에는 자막이 없습니다.")
        return None
    
def signal_handler(sig, frame):  
    print("프로그램 종료 중...")
    sys.exit(0)    
    
# 정적 파일 서빙을 위한 경로
# @app.route('/generated_images/<filename>')
# def serve_image(filename):
#     return send_file(os.path.join(OUTPUT_FOLDER, filename), mimetype='image/png')

#csv data 서버 업로드용
@app.route('/get_csv', methods=['GET'])
def get_csv():
    file_name = request.args.get('file_name')
    if not file_name:
        return jsonify({"error": "File name not provided"}), 400

    file_path = os.path.join(OUTPUT_FOLDER, file_name)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    try:
        # CSV 파일을 텍스트로 반환
        return send_file(file_path, mimetype='text/csv')
    except Exception as e:
        return jsonify({"error": f"Failed to read the CSV file: {e}"}), 500


# 서버 실행
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    print("모델 학습 시작...")
    regression_results() 
    print("모델 학습 완료.") 
    app.run(debug=True, use_reloader=False)  