"""说话：火山引擎 TTS，没配 key 时退回 Windows 离线语音。

火山引擎需要：appid + access token（控制台 → 语音技术 → 语音合成）。
key 填在 brain.json 的 voice.volcengine 里。

用法（一般由 brain.py 调用）：
  python voice.py "你好"
"""
import base64
import json
import os
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
MEM = HERE / "memory"
VOLC_URL = "https://openspeech.bytedance.com/api/v1/tts"


def pick_provider(cfg):
    v = (cfg.get("voice") or {})
    prov = v.get("provider", "auto")
    if prov != "auto":
        return prov
    volc = v.get("volcengine") or {}
    if volc.get("appid") and volc.get("token"):
        return "volcengine"
    return "windows"


def volc_speak(text, v):
    """返回 wav 字节。出错抛 RuntimeError，里面带服务端返回。"""
    payload = {
        "app": {"appid": v["appid"], "token": v["token"],
                "cluster": v.get("cluster", "volcano_tts")},
        "user": {"uid": "coreball"},
        "audio": {"voice_type": v.get("voice_type", "BV700_streaming"),
                  "encoding": v.get("encoding", "wav"),
                  "speed_ratio": v.get("speed_ratio", 1.0)},
        "request": {"reqid": str(uuid.uuid4()), "text": text, "operation": "query"},
    }
    req = urllib.request.Request(
        VOLC_URL, data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer;" + v["token"],
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read().decode("utf-8"))
    if out.get("code") != 3000 or "data" not in out:
        raise RuntimeError("火山 TTS 返回：%s" % json.dumps(out, ensure_ascii=False)[:300])
    return base64.b64decode(out["data"])


def windows_speak(text):
    """用 Windows 自带语音，异步播，不阻塞对话。"""
    MEM.mkdir(parents=True, exist_ok=True)
    f = MEM / "tts_text.txt"
    f.write_text(text, encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Speech; "
          "$t = Get-Content -Raw -Encoding UTF8 '%s'; "
          "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
          "$s.Rate = 0; $s.Speak($t)" % f)
    subprocess.Popen(["powershell", "-NoProfile", "-Command", ps],
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def speak(text, cfg):
    """说一句话。返回用了哪个 provider。失败会抛异常，调用方自己决定要不要吞。"""
    text = (text or "").strip()
    if not text:
        return None
    v = (cfg.get("voice") or {})
    provider = pick_provider(cfg)
    if provider == "volcengine":
        data = volc_speak(text, v["volcengine"])
        MEM.mkdir(parents=True, exist_ok=True)
        out = MEM / "last_tts.wav"
        out.write_bytes(data)
        import winsound
        winsound.PlaySound(str(out), winsound.SND_FILENAME | winsound.SND_ASYNC)
        return "volcengine"
    windows_speak(text)
    return "windows"


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or "你好"
    cfg = json.loads((HERE / "brain.json").read_text(encoding="utf-8"))
    print("provider:", speak(text, cfg))
