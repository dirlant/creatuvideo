"""Transcribe un video largo con faster-whisper (con tiempos por palabra) y guarda JSON.
Uso: python transcribir_largo.py <ffmpeg.exe> <video> <salida.json> [modelo]
"""
import json, subprocess, sys, time
import numpy as np
from faster_whisper import WhisperModel

ff, video, salida = sys.argv[1], sys.argv[2], sys.argv[3]
modelo = sys.argv[4] if len(sys.argv) > 4 else "small"
t0 = time.time()
raw = subprocess.run([ff, "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
audio = np.frombuffer(raw, dtype=np.float32)
print("audio: %.1f min" % (len(audio) / 16000 / 60), flush=True)
m = WhisperModel(modelo, device="cpu", compute_type="int8", cpu_threads=10)
segs, info = m.transcribe(audio, language="es", word_timestamps=True, vad_filter=True,
                          vad_parameters=dict(min_silence_duration_ms=300), beam_size=1, condition_on_previous_text=False)
out = []
for s in segs:
    out.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip(),
                "words": [{"w": w.word, "s": round(w.start, 2), "e": round(w.end, 2)} for w in (s.words or [])]})
    if len(out) % 25 == 0: print("%d segmentos, %.0f s procesados, %.1f min" % (len(out), s.end, (time.time() - t0) / 60), flush=True)
json.dump(out, open(salida, "w", encoding="utf-8"), ensure_ascii=False)
print("LISTO: %d segmentos en %.1f min" % (len(out), (time.time() - t0) / 60), flush=True)
