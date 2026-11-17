"""实时摄像头预览 + 手势识别测试。

用法：
  .venv\\Scripts\\python.exe tools\\camera_view.py            # 只看画面
  .venv\\Scripts\\python.exe tools\\camera_view.py --test 15  # 3 秒倒计时后测 15 秒

按键：q / Esc 退出，s 存快照。
测试模式会显示倒计时与实时检出率，结束后打印统计并自动关闭。
"""
import argparse
import os
import sys
import time

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
SNAP = os.path.join(HERE, "..", "blender", "out", "cmd", "camera_view.png")

CONN = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
        (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15),
        (15, 16), (13, 17), (17, 18), (18, 19), (19, 20), (0, 17)]


def classify(lm):
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
    ap.add_argument("--test", type=float, default=0.0)
    ap.add_argument("--cam", type=int, default=0)
    a = ap.parse_args()

    if not os.path.exists(MODEL):
        print("NO_MODEL:", MODEL)
        return 4

    cap = cv2.VideoCapture(a.cam, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("NO_CAMERA")
        return 2
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    opts = vision.HandLandmarkerOptions(
        base_options=mpp.BaseOptions(model_asset_path=MODEL),
        num_hands=1, running_mode=vision.RunningMode.VIDEO,
        min_hand_detection_confidence=0.5, min_tracking_confidence=0.5)
    landmarker = vision.HandLandmarker.create_from_options(opts)

    t_start = time.time()
    countdown = 5.0
    frames = hits = 0
    labels = {}
    fps = 0.0
    last = time.time()
    hold_until = None
    summary = None
    print("OPEN 倒计时 %.0f 秒，然后测 %.0f 秒" % (countdown, a.test or 0), flush=True)

    while True:
        ok, frame = cap.read()
        if not ok:
            print("READ_FAIL", flush=True)
            break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(time.time() * 1000))

        hand = bool(res.hand_landmarks)
        if hand:
            pts = [(int(p.x * w), int(p.y * h)) for p in res.hand_landmarks[0]]
            for x, y in CONN:
                cv2.line(frame, pts[x], pts[y], (0, 200, 120), 2)
            for p in pts:
                cv2.circle(frame, p, 4, (0, 255, 160), -1)

        now = time.time()
        fps = 0.9 * fps + 0.1 / max(1e-3, now - last)
        last = now
        elapsed = now - t_start

        if a.test > 0 and summary is None:
            if elapsed < countdown:
                big = "READY  %.0f" % (countdown - elapsed + 1)
                cv2.putText(frame, big, (w // 2 - 150, h // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 220, 255), 4)
                cv2.putText(frame, "raise your hand after the countdown",
                            (w // 2 - 260, h // 2 + 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (230, 235, 240), 2)
            else:
                frames += 1
                if hand:
                    hits += 1
                    lab = classify(res.hand_landmarks[0])
                    labels[lab] = labels.get(lab, 0) + 1
                left = a.test - (elapsed - countdown)
                rate = 100.0 * hits / max(1, frames)
                cv2.putText(frame, "TEST %.0fs  hit %.0f%%" % (max(0.0, left), rate),
                            (14, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 120), 2)
                if left <= 0:
                    summary = (frames, hits, dict(labels))
                    hold_until = now + 5.0
                    print("RESULT frames=%d hits=%d rate=%.0f%% labels=%s"
                          % (frames, hits, 100.0 * hits / max(1, frames), labels), flush=True)
                    if hand:
                        os.makedirs(os.path.dirname(SNAP), exist_ok=True)
                        cv2.imwrite(SNAP, frame)
        else:
            cv2.putText(frame, "fps %.0f  q=quit  s=snapshot" % fps,
                        (14, h - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (210, 220, 230), 1)

        cv2.putText(frame, "HAND" if hand else "no hand", (14, h - 44),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 220, 120) if hand else (80, 80, 255), 2)
        cv2.imshow("CoreBall Camera", frame)

        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord('q')):
            print("QUIT at %.1fs frames=%d hits=%d" % (elapsed, frames, hits), flush=True)
            break
        if k == ord('s'):
            os.makedirs(os.path.dirname(SNAP), exist_ok=True)
            cv2.imwrite(SNAP, frame)
            print("快照:", os.path.abspath(SNAP))
        if hold_until is not None and now > hold_until:
            break

    cap.release()
    landmarker.close()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
