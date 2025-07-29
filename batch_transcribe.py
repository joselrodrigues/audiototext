from openai import OpenAI
from video_to_audio import convert_video_to_audio
import os
from tqdm import tqdm
import time
from pydub import AudioSegment
import requests
import json
import re
from pathlib import Path
import glob
import srt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment variables
BASE_URL = os.getenv('BASE_URL')
API_KEY = os.getenv('API_KEY')
INPUT_FOLDER = os.getenv('INPUT_FOLDER', 'input_videos')
OUTPUT_FOLDER = os.getenv('OUTPUT_FOLDER', 'output_audio')
TRANSCRIPTS_FOLDER = os.getenv('TRANSCRIPTS_FOLDER', 'transcripts')
MAX_CHUNK_SIZE_MB = float(os.getenv('MAX_CHUNK_SIZE_MB', '0.95'))
SUPPORTED_VIDEO_FORMATS = os.getenv('SUPPORTED_VIDEO_FORMATS', '.mp4,.avi,.mov,.mkv,.webm,.flv,.wmv').split(',')

if not BASE_URL or not API_KEY:
    print("Error: Please set BASE_URL and API_KEY in your .env file")
    exit(1)

def sanitize_filename(filename):
    """Replace spaces and special characters with hyphens, convert to lowercase"""
    # Remove file extension for folder name
    name = os.path.splitext(filename)[0]
    # Convert to lowercase
    name = name.lower()
    # Replace spaces and special characters with hyphens
    # Keep only alphanumeric, hyphens, and underscores
    sanitized = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with hyphens
    sanitized = re.sub(r'[\s]+', '-', sanitized)
    # Remove multiple consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    return sanitized


def find_srt_file(video_path):
    """Find corresponding SRT file for a video"""
    video_dir = os.path.dirname(video_path)
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    
    # Buscar cualquier archivo que empiece con el nombre del video y termine en .srt
    try:
        for file in os.listdir(video_dir):
            if file.lower().startswith(video_name.lower()) and file.lower().endswith('.srt'):
                return os.path.join(video_dir, file)
    except OSError:
        pass
    
    return None


def extract_text_from_srt(srt_file_path):
    """Extract plain text from SRT file"""
    try:
        with open(srt_file_path, 'r', encoding='utf-8') as f:
            subtitle_generator = srt.parse(f)
            
            text_lines = []
            for subtitle in subtitle_generator:
                # Remove HTML tags and clean up text
                clean_text = subtitle.content.replace('<br>', ' ').replace('\n', ' ')
                clean_text = re.sub(r'<[^>]+>', '', clean_text)  # Remove any HTML tags
                text_lines.append(clean_text.strip())
        
        return ' '.join(text_lines)
    except Exception as e:
        print(f"    Error reading SRT file: {e}")
        return None


def create_folder_structure():
    """Create necessary folders if they don't exist"""
    folders = [INPUT_FOLDER, OUTPUT_FOLDER, TRANSCRIPTS_FOLDER]
    for folder in folders:
        Path(folder).mkdir(exist_ok=True)
    print(f"✓ Folder structure ready: {', '.join(folders)}")


def get_video_files():
    """Get all video files from input folder, maintaining directory structure"""
    video_files = []
    
    # Walk through all subdirectories
    for root, dirs, files in os.walk(INPUT_FOLDER):
        for file in files:
            # Check if file has supported video extension
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in [ext.lower() for ext in SUPPORTED_VIDEO_FORMATS]:
                full_path = os.path.join(root, file)
                # Get relative path from input folder
                rel_path = os.path.relpath(full_path, INPUT_FOLDER)
                video_files.append(full_path)
    
    return sorted(video_files)


def chunk_audio(audio_file, output_dir, max_size_mb=MAX_CHUNK_SIZE_MB):
    """Split audio into chunks and save to output directory"""
    print("  Loading audio file...")
    audio = AudioSegment.from_wav(audio_file)
    total_duration = len(audio)
    
    print(f"  Total audio duration: {total_duration / 1000 / 60:.2f} minutes")
    
    # Calculate chunk duration based on file size
    file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
    minutes_per_chunk = max_size_mb / (file_size_mb / (total_duration / 1000 / 60))
    chunk_length_ms = int(minutes_per_chunk * 60 * 1000)
    
    print(f"  Splitting into chunks of {minutes_per_chunk:.2f} minutes each")
    
    chunks = []
    for i in range(0, total_duration, chunk_length_ms):
        chunk = audio[i:i + chunk_length_ms]
        chunk_num = i // chunk_length_ms
        chunk_filename = os.path.join(output_dir, f"chunk_{chunk_num:03d}.wav")
        chunk.export(chunk_filename, format="wav")
        chunk_size = os.path.getsize(chunk_filename) / (1024 * 1024)
        chunks.append(chunk_filename)
        print(f"  Created chunk {chunk_num + 1}: {len(chunk) / 1000:.2f} seconds, {chunk_size:.2f} MB")
    
    return chunks


def transcribe_chunk_with_requests(chunk_file):
    """Transcribe a single chunk using requests library with whisper model"""
    url = f"{BASE_URL}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    with open(chunk_file, "rb") as audio:
        files = {"file": (os.path.basename(chunk_file), audio, "audio/wav")}
        data = {"model": "whisper", "response_format": "text"}
        
        response = requests.post(url, headers=headers, files=files, data=data)
        
    if response.status_code == 200:
        result = response.json()
        if isinstance(result, dict):
            return {
                'text': result.get('text', ''),
                'language': result.get('language', 'unknown')
            }
        return {'text': str(result), 'language': 'unknown'}
    else:
        raise Exception(f"API error {response.status_code}: {response.text}")


def transcribe_chunks(chunks, video_name):
    """Transcribe each chunk and combine results"""
    transcriptions = []
    detected_languages = []
    partial_file = os.path.join(TRANSCRIPTS_FOLDER, f"{video_name}_partial.md")
    
    # Save progress every N chunks
    save_frequency = 10
    
    for i, chunk_file in enumerate(tqdm(chunks, desc=f"  Transcribing {video_name}")):
        try:
            result = transcribe_chunk_with_requests(chunk_file)
            transcriptions.append(result['text'])
            if result['language'] != 'unknown':
                detected_languages.append(result['language'])
            
            # Save partial results periodically
            if (i + 1) % save_frequency == 0 or (i + 1) == len(chunks):
                with open(partial_file, "w", encoding="utf-8") as f:
                    f.write(f"# Transcription (Partial - {i+1}/{len(chunks)} chunks)\n\n")
                    f.write(" ".join(transcriptions))
                
        except Exception as e:
            print(f"\n  Error transcribing chunk {chunk_file}: {e}")
            # Save what we have so far
            if transcriptions:
                with open(partial_file, "w", encoding="utf-8") as f:
                    f.write(f"# Transcription (Partial - {i}/{len(chunks)} chunks)\n\n")
                    f.write(" ".join(transcriptions))
            raise
    
    # Determine most common language
    if detected_languages:
        most_common_language = max(set(detected_languages), key=detected_languages.count)
    else:
        most_common_language = "unknown"
    
    # Remove partial file after successful completion
    if os.path.exists(partial_file):
        os.remove(partial_file)
    
    return " ".join(transcriptions), most_common_language


def process_video(video_path):
    """Process a single video file, maintaining directory structure"""
    video_name = os.path.basename(video_path)
    sanitized_name = sanitize_filename(video_name)
    
    # Get relative path from input folder to maintain directory structure
    rel_path = os.path.relpath(video_path, INPUT_FOLDER)
    rel_dir = os.path.dirname(rel_path)
    
    print(f"\nProcessing: {rel_path}")
    print(f"  Sanitized name: {sanitized_name}")
    
    # Check for SRT file
    srt_file = find_srt_file(video_path)
    if srt_file:
        print(f"  Found SRT file: {os.path.basename(srt_file)}")
    
    # Create output directory maintaining the same structure
    if rel_dir and rel_dir != '.':
        # Sanitize directory path as well
        sanitized_dir_parts = []
        for part in rel_dir.split(os.sep):
            sanitized_dir_parts.append(sanitize_filename(part + '.tmp').replace('.tmp', ''))
        sanitized_rel_dir = os.path.join(*sanitized_dir_parts)
        
        audio_output_base = os.path.join(OUTPUT_FOLDER, sanitized_rel_dir)
        transcript_output_base = os.path.join(TRANSCRIPTS_FOLDER, sanitized_rel_dir)
    else:
        audio_output_base = OUTPUT_FOLDER
        transcript_output_base = TRANSCRIPTS_FOLDER
    
    # Create directories
    audio_output_dir = os.path.join(audio_output_base, sanitized_name)
    Path(audio_output_dir).mkdir(parents=True, exist_ok=True)
    Path(transcript_output_base).mkdir(parents=True, exist_ok=True)
    
    # Convert video to audio
    audio_file = os.path.join(audio_output_dir, f"{sanitized_name}.wav")
    
    if not os.path.exists(audio_file):
        print("  Converting video to audio...")
        convert_video_to_audio(video_path, audio_file)
    else:
        print("  Audio file already exists, skipping conversion")
    
    # Check if audio file was created
    if not os.path.exists(audio_file):
        print("  Failed to create audio file")
        return False
    
    # Get audio file size
    audio_size = os.path.getsize(audio_file)
    print(f"  Audio file size: {audio_size / (1024 * 1024):.2f} MB")
    
    # Check if we need to chunk the audio
    if audio_size > 25 * 1024 * 1024:  # 25MB limit (though our gateway is more restrictive)
        print(f"  Audio file is larger than 25MB, splitting into chunks...")
        chunks = chunk_audio(audio_file, audio_output_dir)
        print(f"  Created {len(chunks)} chunks")
        
        # Transcribe chunks
        start_time = time.time()
        transcription, detected_language = transcribe_chunks(chunks, sanitized_name)
        elapsed = time.time() - start_time
        print(f"  Transcription completed in {elapsed:.2f} seconds")
        print(f"  Detected language: {detected_language}")
    else:
        # Transcribe the whole file
        print("  Transcribing audio...")
        start_time = time.time()
        result = transcribe_chunk_with_requests(audio_file)
        transcription = result['text']
        detected_language = result['language']
        elapsed = time.time() - start_time
        print(f"  Transcription completed in {elapsed:.2f} seconds")
        print(f"  Detected language: {detected_language}")
    
    # Save transcription maintaining directory structure
    transcript_file = os.path.join(transcript_output_base, f"{sanitized_name}.md")
    with open(transcript_file, "w", encoding="utf-8") as f:
        f.write(f"# Transcription: {video_name}\n\n")
        f.write(f"**Original file**: {video_name}\n")
        f.write(f"**Detected language**: {detected_language}\n")
        f.write(f"**Processing time**: {elapsed:.2f} seconds\n")
        f.write(f"**Date**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        f.write(transcription)
    
    print(f"  Transcription saved to: {transcript_file}")
    
    # Process SRT file if it exists
    if srt_file:
        print("  Processing SRT file...")
        srt_text = extract_text_from_srt(srt_file)
        
        if srt_text:
            # Save SRT text as separate file
            srt_transcript_file = os.path.join(transcript_output_base, f"{sanitized_name}-subtitles.md")
            with open(srt_transcript_file, "w", encoding="utf-8") as f:
                f.write(f"# Subtitles: {video_name}\n\n")
                f.write(f"**Original file**: {video_name}\n")
                f.write(f"**SRT file**: {os.path.basename(srt_file)}\n")
                f.write(f"**Extracted**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                f.write(srt_text)
            
            print(f"  SRT text saved to: {srt_transcript_file}")
        else:
            print("  Failed to extract text from SRT file")
    
    # Clean up audio chunks (but keep the main audio file)
    chunk_files = glob.glob(os.path.join(audio_output_dir, "chunk_*.wav"))
    for chunk in chunk_files:
        os.remove(chunk)
    
    return True


def main():
    print("=== Batch Video Transcription Tool ===\n")
    
    # Create folder structure
    create_folder_structure()
    
    # Get video files
    video_files = get_video_files()
    
    if not video_files:
        print(f"\nNo video files found in '{INPUT_FOLDER}' folder.")
        print(f"Supported formats: {', '.join(SUPPORTED_VIDEO_FORMATS)}")
        return
    
    print(f"\nFound {len(video_files)} video file(s) to process:")
    for video in video_files:
        print(f"  - {os.path.basename(video)}")
    
    # Process each video
    successful = 0
    failed = 0
    
    for video_path in video_files:
        try:
            if process_video(video_path):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\nError processing {os.path.basename(video_path)}: {e}")
            failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total videos: {len(video_files)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"\nTranscriptions saved in: {TRANSCRIPTS_FOLDER}/")
    print(f"Audio files saved in: {OUTPUT_FOLDER}/")


if __name__ == "__main__":
    main()