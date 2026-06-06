"""
OpenAI Whisper API を使って日本語音声ファイルをテキストに書き起こす。
24MB を超えるファイルは自動的にチャンク分割して処理する。

Usage:
    python transcribe_api.py audio.mp3
    python transcribe_api.py audio.mp3 -o output.txt
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import transcribe_core

load_dotenv()


def transcribe(audio_path: Path, output_path: Path) -> None:
    print(f"文字起こし開始: {audio_path}")
    sys.stdout.flush()

    def on_progress(event, data):
        if event == 'status':
            print(data['msg'], flush=True)
        elif event == 'line':
            print(data['text'], flush=True)

    lines = transcribe_core.transcribe_file(
        audio_path, os.environ["OPENAI_API_KEY"], progress_cb=on_progress
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n完了: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="日本語音声ファイルを文字起こしする")
    parser.add_argument("audio", type=Path, help="入力音声ファイル (.mp3 など)")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="出力テキストファイルのパス (省略時: <音声ファイル名>.txt)"
    )
    args = parser.parse_args()

    output = args.output or args.audio.with_suffix(".txt")
    transcribe(args.audio, output)


if __name__ == "__main__":
    main()
