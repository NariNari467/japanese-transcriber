# Whisper 文字起こしツール

OpenAI Whisper API を使った日本語音声ファイルの文字起こしツール。CLIとGUIの2つのインターフェースを提供する。

## 背景

Python 3.14 は PyTorch 未対応のため、ローカル Whisper モデル (`openai-whisper` / `faster-whisper`) は動作しない。そのため OpenAI のクラウド API (`whisper-1`) を使用する。

## ファイル構成

```
Whisper/
├── .env                        # APIキー（git管理外）
├── .gitignore
├── requirements.txt
├── transcribe_api.py           # CLIツール（エンジニア向け）
├── transcribe_gui.py           # GUIアプリのソース（Tkinter）
├── build_exe.py                # Windows .exe ビルドスクリプト
├── 文字起こしツール.spec       # PyInstaller スペックファイル
├── dist/
│   └── 文字起こしツール.exe   # 配布用 .exe（git管理外、約104 MB）
└── whisper file/               # 文字起こし結果の出力フォルダ（git管理外）
```

## セットアップ

```bash
pip install -r requirements.txt
```

`.env` に OpenAI API キーを設定する：

```
OPENAI_API_KEY=sk-proj-...
```

## 使い方

### CLI（エンジニア向け）

```bash
# 基本（同じフォルダに結果を保存）
python transcribe_api.py audio.mp3

# 出力先を指定
python transcribe_api.py audio.mp3 -o result.txt
```

### GUI .exe（非エンジニア向け）

1. `dist/文字起こしツール.exe` をダブルクリックして起動
2. 「ファイルを選択」で音声ファイルを指定
3. 出力先フォルダを選択（デフォルト：デスクトップの `文字起こし結果/`）
4. 「▶ 文字起こし開始」をクリック
5. 処理完了後、`{ファイル名}_{YYYYMMDD_HHMMSS}.txt` が保存される

> GUIはバックグラウンドスレッドで処理するため、長い音声でも画面がフリーズしない。

## 出力フォーマット

セグメントごとに1行ずつテキストが出力される（タイムスタンプなし）：

```
まあ、そうやね
ああ、そっか
なるほど、それは面白いね
```

## .exe のビルド

APIキーを `.exe` に埋め込んでビルドする（配布用）：

```bash
pip install pyinstaller
python build_exe.py
```

ビルドの流れ：
1. `.env` から API キーを読み込む
2. `_config.py`（APIキー埋め込みモジュール）を自動生成
3. PyInstaller で `--onefile --windowed` モードでコンパイル
4. ビルド後に `_config.py` を自動削除（セキュリティ対策）
5. `dist/文字起こしツール.exe` が生成される（約104 MB）

> **注意**: APIキーを変更した場合は再ビルドして再配布が必要。

## 制約

| 項目 | 内容 |
|------|------|
| 対応言語 | 日本語固定（`language="ja"`） |
| ファイルサイズ上限 | 25 MB（OpenAI API 制限、≒ 20 分の音声） |
| 対応フォーマット | mp3, mp4, m4a, wav, webm, flac など |
| Python バージョン | 3.14.2 で動作確認（ローカルモデルは非対応） |
| GUI 動作環境 | Windows のみ（.exe） |
| API 依存 | インターネット接続と有効な OpenAI API キーが必要 |
