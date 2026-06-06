import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import datetime
import pathlib

import _config  # APIキーはビルド時に埋め込まれる
import transcribe_core

DEFAULT_OUTPUT = pathlib.Path.home() / "Desktop" / "文字起こし結果"


class TranscribeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("文字起こしツール")
        self.geometry("620x540")
        self.resizable(False, False)
        self._cancel_event = threading.Event()
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="文字起こしツール",
                 font=("Yu Gothic UI", 16, "bold"), fg="#1a1a2e").pack(pady=(15, 2))
        tk.Label(self, text="日本語MP3ファイルをテキストに変換します",
                 font=("Yu Gothic UI", 10), fg="#555").pack(pady=(0, 12))

        # ファイル選択
        file_frame = tk.LabelFrame(self, text="音声ファイル",
                                    font=("Yu Gothic UI", 10), padx=8, pady=8)
        file_frame.pack(fill="x", padx=20, pady=4)
        self._file_var = tk.StringVar(value="ファイルが選択されていません")
        tk.Entry(file_frame, textvariable=self._file_var, state="readonly",
                 font=("Yu Gothic UI", 9), width=54).pack(side="left", padx=(0, 8))
        tk.Button(file_frame, text="ファイルを選ぶ",
                  command=self._pick_file, width=14).pack(side="left")

        # 保存先フォルダ
        out_frame = tk.LabelFrame(self, text="保存先フォルダ",
                                   font=("Yu Gothic UI", 10), padx=8, pady=8)
        out_frame.pack(fill="x", padx=20, pady=4)
        self._out_var = tk.StringVar(value=str(DEFAULT_OUTPUT))
        tk.Entry(out_frame, textvariable=self._out_var, state="readonly",
                 font=("Yu Gothic UI", 9), width=54).pack(side="left", padx=(0, 8))
        tk.Button(out_frame, text="フォルダを選ぶ",
                  command=self._pick_output, width=14).pack(side="left")

        # 実行 / 中断ボタン
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=14)
        self._run_btn = tk.Button(
            btn_frame, text="▶  文字起こし開始",
            font=("Yu Gothic UI", 13, "bold"),
            bg="#2e7d32", fg="white",
            activebackground="#1b5e20", activeforeground="white",
            width=18, height=2, command=self._run_transcription
        )
        self._run_btn.pack(side="left", padx=(0, 8))
        self._cancel_btn = tk.Button(
            btn_frame, text="■  中断",
            font=("Yu Gothic UI", 13, "bold"),
            bg="#c62828", fg="white",
            activebackground="#b71c1c", activeforeground="white",
            width=8, height=2, state="disabled",
            command=self._cancel_transcription
        )
        self._cancel_btn.pack(side="left")

        # ステータス
        self._status_var = tk.StringVar(value="ファイルを選択してください")
        self._status_label = tk.Label(
            self, textvariable=self._status_var,
            font=("Yu Gothic UI", 10), fg="#555"
        )
        self._status_label.pack()

        # ログエリア
        self._log = scrolledtext.ScrolledText(
            self, width=72, height=12, state="disabled",
            font=("Yu Gothic UI", 9), wrap="word"
        )
        self._log.pack(padx=20, pady=8)

        tk.Label(self, text="Powered by OpenAI Whisper API",
                 font=("Yu Gothic UI", 8), fg="#aaa").pack(pady=(0, 6))

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="音声ファイルを選択",
            filetypes=[("音声ファイル", "*.mp3 *.m4a *.wav *.webm *.mp4"), ("すべてのファイル", "*.*")]
        )
        if path:
            self._file_var.set(path)
            self._status_var.set("ファイルが選択されました。「文字起こし開始」を押してください。")
            self._status_label.config(fg="#555")

    def _pick_output(self):
        path = filedialog.askdirectory(title="保存先フォルダを選択")
        if path:
            self._out_var.set(path)

    def _run_transcription(self):
        audio_path = self._file_var.get()
        if audio_path == "ファイルが選択されていません":
            messagebox.showwarning("確認", "ファイルを先に選択してください。")
            return

        self._cancel_event.clear()
        self._run_btn.config(state="disabled")
        self._cancel_btn.config(state="normal")
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")
        self._status_var.set("処理中... しばらくお待ちください")
        self._status_label.config(fg="#e65100")

        threading.Thread(target=self._worker, args=(audio_path,), daemon=True).start()

    def _worker(self, audio_path):
        try:
            def on_progress(event, data):
                if event == 'status':
                    self.after(0, self._status_var.set, data['msg'])
                elif event == 'line':
                    self.after(0, self._append_log, data['text'] + '\n')

            lines = transcribe_core.transcribe_file(
                audio_path, _config.API_KEY,
                progress_cb=on_progress,
                cancel_event=self._cancel_event,
            )

            output_dir = pathlib.Path(self._out_var.get())
            output_dir.mkdir(parents=True, exist_ok=True)
            stem = pathlib.Path(audio_path).stem
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"{stem}_{ts}.txt"
            output_path.write_text("\n".join(lines), encoding="utf-8")

            self.after(0, self._on_done, str(output_path))

        except transcribe_core.TranscribeCancelled as e:
            if e.lines:
                output_dir = pathlib.Path(self._out_var.get())
                output_dir.mkdir(parents=True, exist_ok=True)
                stem = pathlib.Path(audio_path).stem
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = output_dir / f"{stem}_{ts}_途中まで.txt"
                output_path.write_text("\n".join(e.lines), encoding="utf-8")
                self.after(0, self._on_cancelled, str(output_path))
            else:
                self.after(0, self._on_cancelled, None)

        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _append_log(self, text):
        self._log.config(state="normal")
        self._log.insert("end", text)
        self._log.see("end")
        self._log.config(state="disabled")

    def _cancel_transcription(self):
        if messagebox.askyesno("中断の確認", "文字起こしを中断しますか？\n途中までの結果は保存されます。"):
            self._cancel_event.set()
            self._cancel_btn.config(state="disabled")
            self._status_var.set("中断中... 現在のチャンク完了後に停止します")
            self._status_label.config(fg="#e65100")

    def _on_done(self, path):
        self._run_btn.config(state="normal")
        self._cancel_btn.config(state="disabled")
        self._status_var.set("完了！ テキストファイルを保存しました")
        self._status_label.config(fg="#2e7d32")
        messagebox.showinfo("文字起こし完了", f"ファイルを保存しました:\n\n{path}")

    def _on_cancelled(self, path):
        self._run_btn.config(state="normal")
        self._cancel_btn.config(state="disabled")
        self._status_var.set("中断しました")
        self._status_label.config(fg="#555")
        if path:
            messagebox.showinfo("中断完了", f"途中までの文字起こし結果を保存しました:\n\n{path}")
        else:
            messagebox.showinfo("中断完了", "中断しました（保存データなし）")

    def _on_error(self, msg):
        self._run_btn.config(state="normal")
        self._cancel_btn.config(state="disabled")
        self._status_var.set("エラーが発生しました")
        self._status_label.config(fg="#c62828")
        messagebox.showerror("エラー", f"処理中にエラーが発生しました:\n\n{msg}")


if __name__ == "__main__":
    TranscribeApp().mainloop()
