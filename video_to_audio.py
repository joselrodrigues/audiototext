import os
import subprocess


def convert_video_to_audio(
    video_file_path, audio_file_path, ar=44100, ac=2, b_a="192k"
):
    if not os.path.isfile(video_file_path):
        print(f"The video file {video_file_path} does not exist.")
        return

    command = f'ffmpeg -i "{video_file_path}" -vn -ar {ar} -ac {ac} -b:a {b_a} "{audio_file_path}"'
    try:
        subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
        print(f"Successfully converted {video_file_path} to {audio_file_path}")
    except subprocess.CalledProcessError as e:
        print(
            f"An error occurred while converting {video_file_path} to {audio_file_path}"
        )
        print(f"Error message: {e.output.decode()}")
