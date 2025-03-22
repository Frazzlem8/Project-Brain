import whisper
import spacy
import subprocess
from moviepy import VideoFileClip
import os
import yt_dlp
import re
import argparse
import json
import ollama
import os

# ------------------ ARGUMENT PARSING ------------------
parser = argparse.ArgumentParser(description="YouTube Shorts Automation Script")
parser.add_argument("video_url", help="URL of the video to process")
parser.add_argument("--step", choices=[
    "download", "transcribe", "find_moments", "cut_clips", "resize", "label", "generate_metadata", "upload", "all"
], help="Run only a specific step of the process")

args = parser.parse_args()
video_url = args.video_url

# ------------------ FILE MANAGEMENT ------------------
def get_video_title(url):
    """Fetch the video title without downloading it."""
    try:
        ydl_opts = {'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'Unknown_Title')
    except Exception as e:
        print(f"❌ Error fetching video title: {e}")
        return None

def sanitize_filename(title):
    """Sanitize the title to be used as a filename."""
    return re.sub(r'[^\w\-_]', '', title).replace(" ", "_")

title = get_video_title(video_url)
safe_title = sanitize_filename(title)
folder_path = f"downloads/{safe_title}"
os.makedirs(folder_path, exist_ok=True)
file_path = f"{folder_path}/{safe_title}.mp4"

# ------------------ STEP 1: DOWNLOAD VIDEO ------------------
def download_video():
    """Download video from YouTube."""
    if os.path.exists(file_path):
        print(f"✅ Video already downloaded: {file_path}")
        return
    
    print(f"⬇️ Downloading video: {video_url}")
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': file_path,
        'noplaylist': True,
        'quiet': False,
        'merge_output_format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
    print(f"✅ Video downloaded: {file_path}")

if args.step == "download":
    download_video()
    exit()

# ------------------ STEP 2: TRANSCRIBE VIDEO ------------------
def transcribe_video():
    """Transcribe video audio to text using Whisper."""
    transcript_path = f"{folder_path}/transcript.txt"
    segments_path = f"{folder_path}/segments.json"

    if os.path.exists(transcript_path) and os.path.exists(segments_path):
        print(f"✅ Transcript & segments already exist: {transcript_path}, {segments_path}")
        return

    print("🔄 Transcribing video...")
    model = whisper.load_model("medium")
    global result
    result = model.transcribe(file_path)

    # Save full transcript
    with open(transcript_path, "w") as f:
        f.write(result["text"])

    # Save segment data as JSON
    with open(segments_path, "w") as f:
        json.dump(result["segments"], f, indent=4)

    print(f"✅ Transcription saved to '{transcript_path}' and '{segments_path}'")

if args.step == "transcribe":
    transcribe_video()
    exit()

# ------------------ STEP 3: FIND KEY MOMENTS ------------------
def find_key_moments():
    """Extract key moments based on keywords."""
    key_moments_path = f"{folder_path}/key_moments.txt"
    segments_path = f"{folder_path}/segments.json"

    if os.path.exists(key_moments_path):
        print(f"✅ Key moments already extracted: {key_moments_path}")
        return

    if not os.path.exists(segments_path):
        print(f"❌ Error: Segments file '{segments_path}' not found! Run transcription first.")
        return

    print("🔎 Finding key moments...")

    with open(segments_path, "r") as f:
        segments = json.load(f)

    keywords = ["crazy", "insane", "unbelievable", "hilarious", "shocking", "oh", "my", "laughter"]
    
    key_moments = [
        {"start": seg["start"], "end": seg["end"], "text": seg["text"]}
        for seg in segments if any(word in seg["text"].lower() for word in keywords)
    ]

    with open(key_moments_path, "w") as f:
        for moment in key_moments:
            f.write(f"{moment['start']} - {moment['end']}: {moment['text']}\n")

    print(f"✅ Key moments saved: {key_moments_path}")

if args.step == "find_moments":
    find_key_moments()
    exit()

# ------------------ STEP 4: CUT CLIPS ------------------

def cut_clips():
    print("✂️ Cutting clips from video...")
    print("FILE PATH: ", file_path)
    print("FOLDER PATH: ", folder_path)

    video = VideoFileClip(file_path)
    video_duration = video.duration

    MIN_CLIP_LENGTH = 60
    MAX_CLIP_LENGTH = 179

    with open(f"{folder_path}/key_moments.txt", "r") as f:
        key_moments = [line.strip().split(": ") for line in f.readlines()]

    for i, (times, text) in enumerate(key_moments):
        try:
            start_str, end_str = times.split(" - ")
            moment_start = float(start_str)
            moment_end = float(end_str)
        except ValueError:
            print(f"⚠️ Skipping invalid time format on line {i}: {times}")
            continue

        # Start a few seconds before moment
        start_time = max(0, moment_start - 3)
        end_time = moment_end + 5  # initial buffer after moment
        clip_length = end_time - start_time

        # If the clip is too short, extend it
        if clip_length < MIN_CLIP_LENGTH:
            end_time = start_time + MIN_CLIP_LENGTH
            if end_time > video_duration:
                end_time = video_duration
                start_time = max(0, end_time - MIN_CLIP_LENGTH)
            clip_length = end_time - start_time

        # If clip is too long, trim it
        if clip_length > MAX_CLIP_LENGTH:
            end_time = start_time + MAX_CLIP_LENGTH
            if end_time > video_duration:
                end_time = video_duration
            clip_length = end_time - start_time

        output_filename = f"{folder_path}/clip_{i}.mp4"
        ffmpeg_command = (
            f'ffmpeg -ss {start_time} -i "{file_path}" -t {clip_length} '
            f'-c:v copy -c:a copy "{output_filename}"'
        )

        print(f"📌 Cutting: {output_filename} (Start: {start_time:.2f}s, End: {end_time:.2f}s, Length: {clip_length:.2f}s)")
        subprocess.run(ffmpeg_command, shell=True)

    print("✅ Clips have been adjusted and saved!")

if args.step == "cut_clips":
    cut_clips()
    exit()

# ------------------ STEP 5: RESIZE CLIPS ------------------
def resize_clips():
    """Resize only clips that start with 'clip_' for Shorts format."""
    print("📏 Resizing clips for Shorts...")

    # Filter only files that start with "clip_" and end with ".mp4"
    clip_files = [f for f in os.listdir(folder_path) if f.startswith("clip_") and f.endswith(".mp4")]

    for clip_file in clip_files:
        input_clip = os.path.join(folder_path, clip_file)
        output_clip = os.path.join(folder_path, f"shorts_{clip_file}")

        print(f"🎬 Resizing {clip_file} -> {output_clip}")

        ffmpeg_resize = f'''
        ffmpeg -i "{input_clip}" -vf "scale='if(gt(iw/ih,9/16),1080,-1)':'if(gt(iw/ih,9/16),-1,1920)',pad=1080:1920:(ow-iw)/2:(oh-ih)/2" -c:a copy "{output_clip}"
        '''
        subprocess.run(ffmpeg_resize, shell=True)

    print("✅ Clips resized for Shorts!")

if args.step == "resize":
    resize_clips()
    exit()

# ------------------ STEP 6: ADD LABELS ------------------
def add_labels():
    """Overlay part numbers on clips that start with 'clip_'."""
    print("🎬 Adding part labels to clips...")

    font_path = "arial.ttf"  # Default font path

    # Filter only files that start with "clip_" and end with ".mp4"
    clip_files = [f for f in os.listdir(folder_path) if f.startswith("clip_") and f.endswith(".mp4")]

    for i, clip_file in enumerate(clip_files):
        input_clip = os.path.join(folder_path, f"shorts_{clip_file}")  # Resized version
        output_clip = os.path.join(folder_path, f"final_{clip_file}")

        print(f"📝 Labeling {clip_file} -> {output_clip}")

        ffmpeg_command = f'''
        ffmpeg -i "{input_clip}" -vf "drawtext=text='Part {i+1}':fontfile={font_path}:x=(w-text_w)/2:y=h-150:fontsize=60:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=10" -c:a copy "{output_clip}"
        '''
        subprocess.run(ffmpeg_command, shell=True)

    print("✅ Part labels added!")

if args.step == "label":
    add_labels()
    exit()



# ------------------ STEP 7: GENERATE TITLE & DESCRIPTION ------------------
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
    metadata_output = f"{folder_path}/shorts_metadata.txt"

    if not os.path.exists(captions_path):
        print(f"❌ Error: Key moments file '{captions_path}' not found!")
        return
    
    key_moments = []
    with open(captions_path, "r") as f:
        key_moments = [line.strip() for line in f.readlines() if "-" in line]

    with open(metadata_output, "w") as f:
        for i, moment in enumerate(key_moments):
            input_clip = f"{folder_path}/final_clip_{i}.mp4"
            
            if not os.path.exists(input_clip):
                print(f"⚠️ Skipping: {input_clip} not found.")
                continue
            
            print(f"🎤 Generating title & description for {input_clip}...")

            transcript_text = moment.split(":")[-1].strip()
            ai_output = generate_title_and_description(transcript_text, part_number=i+1)
            
            f.write(f"Clip: {input_clip}\n{ai_output}\n\n")

    print(f"✅ Titles & descriptions saved in '{metadata_output}'")

if args.step == "generate_metadata":
    process_clips_for_titles(folder_path)
    exit()

# ------------------ STEP 7: UPLOAD ------------------
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
    request = youtube.videos().insert(part="snippet,status", body=request_body, media_body=media)
    
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

def clean():
    print("🧹 Cleaning up temporary files...")
    # Remove original video file
    for file in os.listdir(folder_path):
        if file.startswith("shorts_clip_"):
            os.remove(f"{folder_path}/{file}")
        elif file.startswith("clip_"):
            os.remove(f"{folder_path}/{file}")


if args.step == "upload":
    batch_upload_videos(folder_path)
    # clean()
    exit()

# ------------------ RUN ALL STEPS ------------------
if args.step == "all":
    download_video()
    transcribe_video()
    find_key_moments()
    cut_clips()
    resize_clips()
    add_labels()
    process_clips_for_titles(folder_path)
    batch_upload_videos(folder_path)
    # clean()
    exit()