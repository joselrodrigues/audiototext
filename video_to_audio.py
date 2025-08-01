import os
import subprocess


def validate_file_path(path):
    """Validate that the file path is safe and exists."""
    if not os.path.exists(path):
        raise ValueError(f"File does not exist: {path}")
    
    if not os.path.isfile(path):
        raise ValueError(f"Path is not a file: {path}")
    
    # Verify allowed extensions
    allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
    if not any(path.lower().endswith(ext) for ext in allowed_extensions):
        raise ValueError(f"Unsupported file extension: {path}")
    
    return True


def validate_audio_params(ar, ac, bitrate):
    """Validate audio parameters for security."""
    # Validate sample rate
    if not isinstance(ar, int) or ar not in [8000, 16000, 22050, 44100, 48000]:
        raise ValueError(f"Invalid sample rate: {ar}")
    
    # Validate channels
    if not isinstance(ac, int) or ac not in [1, 2]:
        raise ValueError(f"Invalid channels: {ac}")
    
    # Validate bitrate
    valid_bitrates = ['64k', '128k', '192k', '256k', '320k']
    if bitrate not in valid_bitrates:
        raise ValueError(f"Invalid bitrate: {bitrate}")
    
    return True


def convert_video_to_audio(
    video_file_path, audio_file_path, ar=44100, ac=2, b_a="192k"
):
    """Securely convert video to audio using FFmpeg."""
    try:
        # Validate inputs
        validate_file_path(video_file_path)
        validate_audio_params(ar, ac, b_a)
        
        # Build secure command arguments
        args = [
            'ffmpeg',
            '-i', video_file_path,
            '-vn',  # no video
            '-ar', str(ar),
            '-ac', str(ac),
            '-b:a', b_a,
            '-y',  # overwrite output
            audio_file_path
        ]
        
        # Execute safely without shell=True
        result = subprocess.check_output(args, stderr=subprocess.STDOUT)
        print(f"Successfully converted {video_file_path} to {audio_file_path}")
        return result
        
    except ValueError as e:
        print(f"Validation error: {e}")
        return None
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while converting {video_file_path} to {audio_file_path}")
        print(f"Error message: {e.output.decode()}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None
