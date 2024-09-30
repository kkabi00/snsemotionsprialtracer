#!/usr/bin/env python
# coding: utf-8

# <a href="https://colab.research.google.com/github/kkabi00/snsemotionsprialtracer/blob/main/youtube_script.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# In[1]:

# pip install 은 따로 터미널에서 실행할 것
#!pip install pytube3

# In[ ]:


#!pip install youtube_transcript_api

# In[ ]:


#!pip install kiwipiepy #문장분리를 위해 kiwipiepy 설치

# In[ ]:


from pytube import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from kiwipiepy import Kiwi

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
            'start_time': (start_min, start_sec),
            'end_time': (end_min, end_sec)
        })

        print(f"{start_min:02d}:{start_sec:02d} ~ {end_min:02d}:{end_sec:02d}: {separate[i].text}")

    return segments_with_durations

# 유튜브 링크 입력
youtube_url = input("유튜브 링크를 입력: ")
video_id = youtube_info(youtube_url)

if video_id:
    print(f"비디오 ID: {video_id}")
    print("스크립트 응답:")
    api_response = get_script_from_api(video_id)
else:
    print("에러 발생: 비디오 ID를 추출할 수 없습니다.")

