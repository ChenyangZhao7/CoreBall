"""手势识别可行性实验（一次性探针，不是产品代码）。

用法：
  .venv\\Scripts\\python.exe tools\\gesture_probe.py [--seconds 15] [--cam 0]

做的事：
  开摄像头 → MediaPipe HandLandmarker → 统计帧率与检出率 → 猜一个手势 → 存一张快照。

退出码：0 正常；2 打不开摄像头；3 没装依赖；4 模型下载失败。
"""
import argparse
import os
import sys
import time
import urllib.request

try:
    import cv2
    import mediapipe as mp
    from mediapipe.tasks import python as mpp
    from mediapipe.tasks.python import vision
except Exception as e:
    print("NO_DEPS:", e)
    sys.exit(3)

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL = os.path.join(HERE, "models", "hand_landmarker.task")
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
             "hand_landmarker/float16/1/hand_landmarker.task")
SNAP = os.path.join(HERE, "..", "blender", "out", "cmd", "gesture_probe.png")


def ensure_model():
    if os.path.exists(MODEL) and os.path.getsize(MODEL) > 100000:
        return True
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    print("下载模型 → %s" % MODEL)
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    except Exception as e:
        print("NO_MODEL:", e)
        return False
    return True


def classify(lm):
    """很粗的分类：数伸直的手指。只用于这次实验。"""
    fingers = 0
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        if lm[tip].y < lm[pip].y:
            fingers += 1
    if abs(lm[4].x - lm[3].x) > 0.04 and abs(lm[4].x - lm[2].x) > 0.06:
        fingers += 1
    if fingers == 0:
        return "fist"
    if fingers == 1:
        return "point"
    if fingers >= 4:
        return "palm"
    return "hand(%d)" % fingers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--no-hand", action="store_true", help="只测摄像头，不要求画面里有手")
    a = ap.parse_args()

    if not ensure_model():
        return 4

    cap = cv2.VideoCapture(a.cam, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("NO_CAMERA: 打不开摄像头 %d" % a.cam)
        return 2
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    base = mpp.BaseOptions(model_asset_path=MODEL)
    opts = vision.HandLandmarkerOptions(
        base_options=base, num_hands=1,
        running_mode=vision.RunningMode.VIDEO,
        min_hand_detection_confidence=0.6,
        min_tracking_confidence=0.5)
    landmarker = vision.HandLandmarker.create_from_options(opts)

    print("开始（%.0f 秒）：把手举到镜头前。" % a.seconds)
    t0 = time.time()
    frames = hits = 0
    labels = {}
    saved = False
    last_print = 0.0

    while time.time() - t0 < a.seconds:
        ok, frame = cap.read()
        if not ok:
            break
        frames += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = landmarker.detect_for_video(img, int((time.time() - t0) * 1000))
        if res.hand_landmarks:
            hits += 1
            lm = res.hand_landmarks[0]
            label = classify(lm)
            labels[label] = labels.get(label, 0) + 1
            if not saved:
                h, w = frame.shape[:2]
                for p in lm:
                    cv2.circle(frame, (int(p.x * w), int(p.y * h)), 4, (0, 255, 180), -1)
                os.makedirs(os.path.dirname(SNAP), exist_ok=True)
                cv2.imwrite(SNAP, frame)
                saved = True
        now = time.time() - t0
        if now - last_print > 3.0:
            print("  %.0fs  帧 %d  检出 %d" % (now, frames, hits))
            last_print = now

    dt = max(1e-6, time.time() - t0)
    cap.release()
    landmarker.close()
    print("---")
    print("帧数 %d  时长 %.1fs  帧率 %.1f fps" % (frames, dt, frames / dt))
    print("检出率 %.0f%%" % (100.0 * hits / max(1, frames)))
    print("手势计数 %s" % (labels or "无"))
    print("快照 %s" % (SNAP if saved else "没存（没检出过手）"))

    if a.no_hand:
        return 0 if frames > 10 else 2
    return 0 if hits > 0 else 5


if __name__ == "__main__":
    sys.exit(main())
