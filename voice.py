"""说话（TTS）。默认用 Windows 自带中文语音，零成本、离线。

用法：
  python voice.py "你好，我是 CoreBall。"
  python brain.py --once "你好" --speak

配置：voice.json（本地，不提交）
  backend: "windows" | "cloud"
  voice:   Windows 音色名，例如 "Microsoft Huihui Desktop"
  rate:    -10..10，0 是正常语速
  auto_speak: true 时 brain.py 回复完自动念

接国产云（讯飞 / 火山 / 阿里）时把 backend 改成 "cloud"，
在 cloud 段填 provider / app_id / api_key / api_secret。
它们都是「POST 文字 + 签名 → 返回音频字节 → 写临时文件 → 播放」，
只是签名算法不同；填好之后在这里加对应的请求函数即可。
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
VOICE = HERE / "voice.json"

DEFAULTS = {
    "backend": "windows",
    "voice": "Microsoft Huihui Desktop",
    "rate": 0,
    "auto_speak": True,
    "cloud": {"provider": "", "app_id": "", "api_key": "", "api_secret": ""},
}


def load_config(path=VOICE):
    cfg = dict(DEFAULTS)
    p = Path(path)
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def auto_speak():
    return bool(load_config().get("auto_speak", True))


def speak(text, cfg=None):
    text = (text or "").strip()
    if not text:
        return False
    v = load_config()
    if cfg:
        # brain.py 会把整份 brain.json 传进来；只认语音相关的键，其余忽略
        for k in ("backend", "voice", "rate", "cloud"):
            if k in cfg:
                v[k] = cfg[k]
    backend = v.get("backend", "windows")
    if backend == "windows":
        return speak_windows(text, v)
    if backend == "cloud":
        raise RuntimeError("voice.json 的 cloud 段还没填（provider / app_id / api_key / api_secret）")
    raise RuntimeError("不认识的 backend: %r" % backend)


def speak_windows(text, cfg):
    voice = str(cfg.get("voice", "Microsoft Huihui Desktop")).replace("'", "")
    rate = int(cfg.get("rate", 0))
    tmp = Path(tempfile.gettempdir()) / "coreball_say.txt"
    tmp.write_text(text, encoding="utf-8")
    path = str(tmp).replace("'", "''")
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "try { $s.SelectVoice('%s') } catch {}; "
        "$s.Rate = %d; "
        "$s.Speak([IO.File]::ReadAllText('%s', [Text.Encoding]::UTF8))"
    ) % (voice, rate, path)
    subprocess.run(["powershell", "-NoProfile", "-Command", script],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True


def main():
    if len(sys.argv) > 1:
        speak(" ".join(sys.argv[1:]))
        return 0
    print(json.dumps(load_config(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
