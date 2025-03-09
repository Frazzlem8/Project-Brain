import whisper
import spacy
import subprocess
from moviepy import VideoFileClip
import os
import yt_dlp
import re
import argparse

def get_video_title(url):
    """Fetches the video title without downloading it."""
    try:
        ydl_opts = {'quiet': True}  # Don't print unnecessary output
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)  # Get metadata only
            return info.get('title', 'Unknown_Title')  # Return title or fallback
    except Exception as e:
        print(f"❌ Error fetching video title: {e}")
        return None

def download_video(url, output_folder, filename):
    """Downloads a video from a given URL."""
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Get highest quality
        'outtmpl': f'{output_folder}/{filename}',  # Save with video title
        'noplaylist': True,  # Download only a single video
        'quiet': False,  # Show progress in terminal
        'merge_output_format': 'mp4'  # Ensure MP4 output
    }
    # Download video
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


parser = argparse.ArgumentParser(description="YouTube Shorts Automation Script")

parser.add_argument("video_url", help="URL of the video to process")

args = parser.parse_args()

video_url = args.video_url

print(f"🎥 Processing video: {video_url}")

title = get_video_title(video_url)
# Replace spaces with underscores & remove unsafe characters (like commas, slashes, etc.)
safe_title = re.sub(r'[^\w\-_]', '', title)  # Keeps letters, numbers, _, and -
folder_path = f"downloads/{safe_title}".replace(" ", "_")
os.makedirs(folder_path, exist_ok=True)

file_name = f"{safe_title}.mp4"  # Keep the filename clean
download_video(video_url, folder_path, file_name)


# 🔹 STEP 1: Transcribe the video
print("🔄 Transcribing video...")
model = whisper.load_model("medium")
file_path = f"{folder_path}/{file_name}"
result = model.transcribe(file_path)
full_text = result["text"]
print("\n📝 Full Transcript:\n", full_text)

# 🔹 Get Video Duration
video = VideoFileClip(file_path)
video_duration = video.duration
print(f"🎥 Video Duration: {video_duration:.2f} seconds")

# 🔹 STEP 2: Save the transcription as subtitles (SRT format)
print("💾 Saving subtitles...")
with open(f"{folder_path}/subtitles.srt", "w") as f:
    for i, segment in enumerate(result["segments"]):
        start_time = segment["start"]
        end_time = segment["end"]
        text = segment["text"]

        f.write(f"{i+1}\n")
        f.write(f"{start_time:.2f} --> {end_time:.2f}\n")
        f.write(f"{text}\n\n")

print(f"✅ Subtitles saved to '{folder_path}/subtitles.srt'")

#############################################
#  FIND KEY MOMENTS IN THE TRANSCRIPT       #
#############################################

print("🔎 Finding key moments...")
nlp = spacy.load("en_core_web_sm")
doc = nlp(full_text)

# Define "viral-worthy" words
keywords = ["crazy", "insane", "unbelievable", "hilarious", "shocking", "oh"]
key_moments = []

# Find sentences that contain keywords
for segment in result["segments"]:  
    if any(word in segment["text"].lower() for word in keywords):
        key_moments.append({
            "start": segment["start"],
            "end": segment["end"],
            "text": segment["text"]
        })

# Print extracted key moments
print("\n🔥 Viral-Worthy Clips Found:")
for moment in key_moments:
    print(f"[{moment['start']}s - {moment['end']}s] {moment['text']}")

# 🔹 STEP 4: Save key moments for further processing
with open(f"{folder_path}/key_moments.txt", "w") as f:
    for moment in key_moments:
        f.write(f"{moment['start']} - {moment['end']}: {moment['text']}\n")

print(f"✅ Key moments saved in '{folder_path}/key_moments.txt'")

#############################################
#  CUT KEY MOMENTS FROM THE VIDEO           #
#############################################

print("✂️ Cutting clips from video...")
print("FILE PATH: ", file_path)
print("FOLDER PATH: ", folder_path)

video = VideoFileClip(file_path)
video_duration = video.duration

# Define clip length constraints
MIN_CLIP_LENGTH = 60  # Minimum length = 60 seconds
MAX_CLIP_LENGTH = 179  # Maximum length = 3 mins

for i, moment in enumerate(key_moments):
    start_time = max(0, moment["start"] - 3)  # Start 3 seconds before key moment
    end_time = moment["end"] + 5  # Extend 5 seconds after key moment
    clip_length = end_time - start_time

    # Ensure the clip is at least MIN_CLIP_LENGTH seconds
    if clip_length < MIN_CLIP_LENGTH:
        end_time = start_time + MIN_CLIP_LENGTH
        clip_length = MIN_CLIP_LENGTH

    # Ensure the clip does not exceed MAX_CLIP_LENGTH
    if clip_length > MAX_CLIP_LENGTH:
        end_time = start_time + MAX_CLIP_LENGTH
        clip_length = MAX_CLIP_LENGTH  # Ensure length does not exceed max

    # Prevent cutting beyond video duration
    if end_time > video_duration:
        end_time = video_duration
        start_time = max(0, end_time - MAX_CLIP_LENGTH)  # Adjust start if necessary

    output_filename = f"{folder_path}/clip_{i}.mp4"
    
    # Use -t instead of -to for setting clip duration
    ffmpeg_command = f'ffmpeg -ss {start_time} -i {file_path} -t {clip_length} -c:v copy -c:a copy {output_filename}'
    
    print(f"📌 Cutting: {output_filename} (Start: {start_time}s, End: {end_time}s, Length: {clip_length}s)")
    subprocess.run(ffmpeg_command, shell=True)

print("✅ Clips have been adjusted and saved!")

############################################
#  RESIZE CLIPS FOR YOUTUBE SHORTS (9:16)   #
############################################

print("📏 Resizing clips for Shorts/TikTok (without stretching)...")
for i, moment in enumerate(key_moments):
    input_clip = f"{folder_path}/clip_{i}.mp4"
    output_clip = f"{folder_path}/shorts_clip_{i}.mp4"

    ffmpeg_resize = f'''
    ffmpeg -i {input_clip} -vf "scale='if(gt(iw/ih,9/16),1080,-1)':'if(gt(iw/ih,9/16),-1,1920)',pad=1080:1920:(ow-iw)/2:(oh-ih)/2" -c:a copy {output_clip}
    '''
    
    subprocess.run(ffmpeg_resize, shell=True)

print("✅ Clips resized correctly for Shorts!")


#############################################
#  ADD AUTO-GENERATED SUBTITLES TO CLIPS    #
#############################################

print("🎬 Adding part labels to clips...")

font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"  # macOS default
if not os.path.exists(font_path):
    font_path = "arial.ttf"  # Default fallback

for i, moment in enumerate(key_moments):
    input_clip = f"{folder_path}/shorts_clip_{i}.mp4"
    output_clip = f"{folder_path}/final_clip_{i}.mp4"
    part_text = f"Part {i+1}"

    ffmpeg_command = f'''
    ffmpeg -i {input_clip} -vf "drawtext=text='{part_text}':fontfile={font_path}:x=(w-text_w)/2:y=h-150:fontsize=60:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=10" -c:a copy {output_clip}
    '''
    
    print(f"🎞️ Running: {ffmpeg_command}")
    subprocess.run(ffmpeg_command, shell=True)

print("✅ Part labels added to all clips!")


##############################################
# Create youtube video title and description  #
##############################################

import ollama

def generate_title_and_description(transcript_text, part_number):
    """Generate a YouTube title and description using AI (Ollama Mistral)."""
    
    prompt = f"""
    You are generating YouTube metadata for a viral YouTube Shorts video.
    
    **Transcript snippet:** "{transcript_text}"

    Generate the following:
    - **Title** (max 60 characters, engaging, no clickbait abuse, include "Part {part_number}" if necessary)
    - **Description** (max 200 words, summarize the clip engagingly, include hashtags for reach)

    Return in this format:
    Title: [Generated Title]
    Description: [Generated Description]
    """

    response = ollama.chat(model="mistral", messages=[{"role": "user", "content": prompt}])
    
    return response['message']['content']

def process_clips_for_titles(folder_path):
    """Reads transcripts for each shorts clip and generates AI-powered titles & descriptions."""
    
    captions_path = f"{folder_path}/key_moments.txt"

    # Ensure key moments file exists
    if not os.path.exists(captions_path):
        print(f"❌ Error: Key moments file '{captions_path}' not found!")
        return
    
    # Read key moments to match clips with transcript
    key_moments = []
    with open(captions_path, "r") as f:
        key_moments = [line.strip() for line in f.readlines() if "-" in line]

    metadata_output = f"{folder_path}/shorts_metadata.txt"
    
    with open(metadata_output, "w") as f:
        for i, moment in enumerate(key_moments):
            input_clip = f"{folder_path}/final_clip_{i}.mp4"
            
            if not os.path.exists(input_clip):
                print(f"⚠️ Skipping: {input_clip} not found.")
                continue
            
            print(f"🎤 Generating title & description for {input_clip}...")

            # Extract transcript text from key moments
            transcript_text = moment.split(":")[-1].strip()

            # Get AI-generated title & description
            ai_output = generate_title_and_description(transcript_text, part_number=i+1)
            
            # Save the metadata
            f.write(f"Clip: {input_clip}\n{ai_output}\n\n")

    print(f"✅ Titles & descriptions saved in '{metadata_output}'")


process_clips_for_titles(folder_path)

##########################
#   Upload to Youtube    #
##########################


import json
import google.auth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# YouTube API Scope
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def authenticate_youtube():
    """Authenticate and return a YouTube API client."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secrets.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def upload_video(file_path, title, description, tags=["Shorts"], category="24", privacy_status="public"):
    """Uploads a video to YouTube with given metadata."""
    youtube = authenticate_youtube()

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category
        },
        "status": {
            "privacyStatus": privacy_status
        }
    }

    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = request.execute()
    print(f"✅ Uploaded: {title}")
    print(f"📹 Video ID: {response['id']}")

def load_titles_and_descriptions(metadata_file):
    """Reads the AI-generated metadata from file and maps it to corresponding clips."""
    metadata = {}
    if not os.path.exists(metadata_file):
        print(f"❌ Error: Metadata file '{metadata_file}' not found!")
        return metadata

    with open(metadata_file, "r") as f:
        current_clip = None
        for line in f.readlines():
            line = line.strip()
            if line.startswith("Clip:"):
                current_clip = line.split("Clip: ")[1]
                metadata[current_clip] = {"title": "", "description": ""}
            elif line.startswith("Title:"):
                metadata[current_clip]["title"] = line.replace("Title: ", "").strip()
            elif line.startswith("Description:"):
                metadata[current_clip]["description"] = line.replace("Description: ", "").strip()

    return metadata

def batch_upload_videos(folder_path):
    """Matches videos with AI-generated metadata and uploads them."""
    metadata_file = f"{folder_path}/shorts_metadata.txt"
    metadata = load_titles_and_descriptions(metadata_file)

    if not metadata:
        print("❌ No metadata found, skipping upload.")
        return

    video_files = [f for f in os.listdir(folder_path) if f.startswith("final_clip_") and f.endswith(".mp4")]

    for video in video_files:
        video_path = os.path.join(folder_path, video)
        if video_path in metadata:
            title = metadata[video_path]["title"]
            description = metadata[video_path]["description"]

            print(f"🚀 Uploading '{video_path}' with title: '{title}'")
            upload_video(video_path, title, description)
        else:
            print(f"⚠️ No metadata found for {video_path}, skipping.")

    print("🎉 All videos uploaded successfully!")


batch_upload_videos(folder_path)


##################
# Clean up files #
##################


print("🧹 Cleaning up temporary files...")
# Remove original video file
for file in os.listdir(folder_path):
    if file.startswith("shorts_clip_"):
        os.remove(f"{folder_path}/{file}")
    elif file.startswith("clip_"):
        os.remove(f"{folder_path}/{file}")
