# flask 웹서버 -> 실행 후 확장프로그램 실행

from flask import Flask, request, jsonify
from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from kiwipiepy import Kiwi

app = Flask(__name__)

def youtube_info(youtube_url):
    try:
        yt = YouTube(youtube_url)
        video_id = yt.video_id
        return video_id
    except Exception as e:
        return None, str(e)

def get_script_from_api(video_id):
    transcription = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko'])

    segments_with_durations = []
    text = ''  # 빈 문자열로 초기화

    for segment in transcription:
        text += segment['text'] + ' '

    text_ = text.replace('\n', ' ')

    kiwi = Kiwi()
    separate = kiwi.split_into_sents(text_)

    for i, segment in enumerate(transcription):
        start_time = segment['start']
        end_time = start_time + segment['duration']

        start_min = int(start_time // 60)
        start_sec = int(start_time % 60)
        end_min = int(end_time // 60)
        end_sec = int(end_time % 60)

        segments_with_durations.append({
            'text': separate[i].text,
            'start_time': f"{start_min:02d}:{start_sec:02d}",
            'end_time': f"{end_min:02d}:{end_sec:02d}"
        })

    return segments_with_durations

@app.route('/process_video', methods=['POST'])
def process_video():
    data = request.json
    youtube_url = data.get('youtube_url')
    
    if not youtube_url:
        return jsonify({'error': 'YouTube URL is missing'}), 400

    video_id = youtube_info(youtube_url)
    
    if not video_id:
        return jsonify({'error': 'Invalid YouTube URL or unable to extract video ID'}), 400

    try:
        transcription = get_script_from_api(video_id)
        return jsonify({'transcription': transcription})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
