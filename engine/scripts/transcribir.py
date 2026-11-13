import sys, json, subprocess, numpy as np
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
out = {}
for f in sys.argv[3:]:
    raw = subprocess.run([sys.argv[2],"-v","error","-i",f,"-vn","-ac","1","-ar","16000","-f","f32le","-"],capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    segs, info = m.transcribe(a, language="es")
    out[f] = " ".join(s.text.strip() for s in segs)
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
