"""
ビルドスクリプト: .env からAPIキーを読み込み、_config.py を生成し、
PyInstaller で .exe をビルドして、後で _config.py を削除します。

使い方:
    python build_exe.py
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

here = Path(__file__).parent

# .env から OPENAI_API_KEY を読み込む
env_path = here / ".env"
api_key = None
with open(env_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("OPENAI_API_KEY"):
            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            break

if not api_key:
    print("エラー: .env から OPENAI_API_KEY が見つかりませんでした")
    sys.exit(1)

print(f"APIキー確認: {api_key[:12]}...")

# ffmpeg の確認（24MB 超のファイル処理に必要）
ffmpeg_src = here / "ffmpeg.exe"
ffmpeg_on_path = shutil.which("ffmpeg")
if ffmpeg_src.exists():
    print(f"ffmpeg.exe 確認: {ffmpeg_src}")
elif ffmpeg_on_path:
    print(f"ffmpeg PATH 確認: {ffmpeg_on_path}")
    print("  ※配布時は ffmpeg.exe を .exe と同じフォルダに置いてください")
else:
    print("警告: ffmpeg が見つかりません")
    print("  24MB 超の音声ファイルを処理するには ffmpeg.exe が必要です")
    print("  https://www.gyan.dev/ffmpeg/builds/ からダウンロードして")
    print("  Whisper フォルダに ffmpeg.exe を置いてからビルドしてください")
    print("  （小さいファイルのみ使う場合は ffmpeg 不要です）")

# _config.py を作成（ビルド後に削除）
config_path = here / "_config.py"
config_path.write_text(f'API_KEY = "{api_key}"\n', encoding="utf-8")
print("_config.py を作成しました")

try:
    result = subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--onefile",
            "--windowed",
            "--name", "文字起こしツール",
            str(here / "transcribe_gui.py"),
        ],
        cwd=str(here),
        check=True,
    )
    dist_dir = here / "dist"
    ffmpeg_dst = dist_dir / "ffmpeg.exe"
    if ffmpeg_src.exists() and not ffmpeg_dst.exists():
        shutil.copy2(ffmpeg_src, ffmpeg_dst)
        print(f"ffmpeg.exe を dist/ にコピーしました: {ffmpeg_dst}")

    print("\n========================================")
    print("ビルド完了！")
    print(f"生成ファイル: {dist_dir / '文字起こしツール.exe'}")
    if ffmpeg_dst.exists():
        print(f"ffmpeg.exe:  {ffmpeg_dst}")
        print("【配布時】上記2ファイルを同じフォルダに入れて渡してください。")
    else:
        print("※大きいファイル(24MB超)を使う場合は ffmpeg.exe も同フォルダに置いてください")
        print("  ダウンロード: https://www.gyan.dev/ffmpeg/builds/")
    print("========================================")
finally:
    if config_path.exists():
        config_path.unlink()
        print("_config.py を削除しました（セキュリティ保護）")
