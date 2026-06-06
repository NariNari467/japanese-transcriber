"""
大容量音声ファイルの文字起こしコアロジック。
24MB 以下はそのまま API に送信、超える場合は ffmpeg で 15 分チャンクに分割して処理する。

GUIとCLIの両方から使用される共有モジュール。
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile

from openai import OpenAI

CHUNK_THRESHOLD = 24 * 1024 * 1024  # 24MB を超えたらチャンク処理
CHUNK_SECONDS = 900                  # 15分チャンク（192kbps でも 21.6MB 以内）


class TranscribeCancelled(Exception):
    """チャンク間でキャンセルされた。lines に途中まで完了した行が入っている。"""
    def __init__(self, lines: list):
        self.lines = lines


def _get_ffmpeg() -> str:
    """ffmpeg バイナリのパスを返す。

    検索順序:
    1. 実行中の .exe と同じフォルダ（配布時）
    2. このスクリプトと同じフォルダ（開発時）
    3. システム PATH
    """
    if getattr(sys, 'frozen', False):
        candidate = pathlib.Path(sys.executable).parent / 'ffmpeg.exe'
    else:
        candidate = pathlib.Path(__file__).parent / 'ffmpeg.exe'

    if candidate.exists():
        return str(candidate)

    found = shutil.which('ffmpeg')
    return found if found else 'ffmpeg'


def _split_audio(
    audio_path: pathlib.Path,
    tmp_dir: pathlib.Path,
    ffmpeg_cmd: str,
) -> list:
    """ffmpeg の stream copy で音声を CHUNK_SECONDS ごとに分割する。再エンコードなし。"""
    try:
        test = subprocess.run(
            [ffmpeg_cmd, '-version'],
            capture_output=True,
        )
        if test.returncode != 0:
            raise RuntimeError(
                'ffmpeg が起動できませんでした。\n'
                'ffmpeg.exe をこの .exe と同じフォルダに置いてください。\n'
                'ダウンロード: https://www.gyan.dev/ffmpeg/builds/'
            )
    except FileNotFoundError:
        raise RuntimeError(
            'ffmpeg が見つかりません。\n'
            'ffmpeg.exe をこの .exe と同じフォルダに置いてください。\n'
            'ダウンロード: https://www.gyan.dev/ffmpeg/builds/'
        )

    ext = audio_path.suffix.lower()
    pattern = str(tmp_dir / f'chunk_%03d{ext}')
    result = subprocess.run(
        [
            ffmpeg_cmd, '-y', '-i', str(audio_path),
            '-f', 'segment',
            '-segment_time', str(CHUNK_SECONDS),
            '-c', 'copy',
            pattern,
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    if result.returncode != 0:
        raise RuntimeError(
            f'ffmpeg による分割に失敗しました:\n{result.stderr[-500:]}'
        )

    chunks = sorted(tmp_dir.glob(f'chunk_*{ext}'))
    if not chunks:
        raise RuntimeError('ffmpeg による分割後にチャンクファイルが見つかりませんでした。')
    return chunks


def _transcribe_one(client: OpenAI, audio_path: pathlib.Path) -> list:
    """単一ファイルを Whisper API に送信してセグメントテキストのリストを返す。"""
    with open(audio_path, 'rb') as f:
        transcript = client.audio.transcriptions.create(
            model='whisper-1',
            file=f,
            language='ja',
            response_format='verbose_json',
        )
    return [seg.text.strip() for seg in (transcript.segments or [])]


def transcribe_file(
    audio_path,
    api_key: str,
    progress_cb=None,
    cancel_event=None,
) -> list:
    """音声ファイルを文字起こしする。24MB 超の場合は自動的にチャンク処理する。

    progress_cb(event: str, data: dict) が呼ばれるイベント:
      ('status', {'msg': str})   — ステータス文字列
      ('line',   {'text': str})  — 文字起こし済みの1セグメント
    """
    audio_path = pathlib.Path(audio_path)
    file_size = audio_path.stat().st_size
    client = OpenAI(api_key=api_key)

    def emit(event, data):
        if progress_cb:
            progress_cb(event, data)

    if file_size <= CHUNK_THRESHOLD:
        emit('status', {'msg': '文字起こし中...'})
        lines = []
        for line in _transcribe_one(client, audio_path):
            lines.append(line)
            emit('line', {'text': line})
        return lines

    # --- 大容量ファイル: チャンク処理 ---
    ffmpeg_cmd = _get_ffmpeg()
    tmp_dir = pathlib.Path(tempfile.mkdtemp(prefix='whisper_chunks_'))
    try:
        emit('status', {'msg': '音声ファイルを分割中...'})
        chunks = _split_audio(audio_path, tmp_dir, ffmpeg_cmd)
        total = len(chunks)
        all_lines = []

        for i, chunk_path in enumerate(chunks, 1):
            if cancel_event and cancel_event.is_set():
                raise TranscribeCancelled(all_lines)
            emit('status', {'msg': f'文字起こし中... ({i}/{total})'})
            for line in _transcribe_one(client, chunk_path):
                all_lines.append(line)
                emit('line', {'text': line})

        return all_lines
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
