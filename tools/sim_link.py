"""Two-end serial simulation for the CoreBall interface v1.1.

No hardware: ball and carrier state machines exchange real encoded frames
through a byte link, so framing, CRC and power negotiation are exercised.

Usage:
  python tools/sim_link.py
"""
import protocol as P


class Link:
    def __init__(self):
        self.ab = b""      # ball -> carrier
        self.ba = b""      # carrier -> ball
        self.log = []

    def ball_send(self, ftype, payload=b""):
        raw = P.encode(ftype, payload)
        self.ab += raw
        self.log.append(("ball", ftype, raw.hex()))

    def carrier_send(self, ftype, payload=b""):
        raw = P.encode(ftype, payload)
        self.ba += raw
        self.log.append(("carrier", ftype, raw.hex()))

    def corrupt_next_ba(self):
        if self.ba:
            self.ba = self.ba[:-1] + bytes([self.ba[-1] ^ 0xFF])


class Ball:
    def __init__(self, supply_mA):
        self.supply = supply_mA
        self.state = "wait"
        self.last_who = -1.0
        self.last_hb = -1.0
        self.carrier = None
        self.status = None
        self.error = None
        self.crc_errors = 0

    def tick(self, t, link):
        if self.state == "wait":
            if t - self.last_who >= 0.1:
                link.ball_send(P.WHO)
                self.last_who = t
            if t > 1.0:
                self.state = "dumb"
        elif self.state == "ok":
            if t - self.last_hb >= 0.2:
                link.ball_send(P.HEARTBEAT)
                self.last_hb = t

    def receive(self, t, frame, link):
        if frame.type == P.WHO:
            w = P.parse_who(frame.payload)
            self.carrier = w
            if w["draw_mA"] > self.supply:
                self.state = "power"
                link.ball_send(P.ERROR, P.error_payload(P.ERR_POWER))
            else:
                self.state = "ok"
                link.ball_send(P.CMD, P.cmd_payload(0, 1000, 500, 1000))
        elif frame.type == P.STATUS:
            self.status = P.parse_status(frame.payload)
        elif frame.type == P.ERROR:
            self.error = P.parse_error(frame.payload)


class Carrier:
    def __init__(self, draw_mA, cls=3, axes=1, name="轮式底盘", silent=False,
                 corrupt_first=False):
        self.draw = draw_mA
        self.cls = cls
        self.axes = axes
        self.name = name
        self.silent = silent
        self.corrupt_first = corrupt_first
        self.first = True
        self.error = None
        self.cmds = []

    def receive(self, t, frame, link):
        if self.silent:
            return
        if frame.type == P.WHO:
            payload = P.who_payload(self.cls, self.axes, 0x03, self.draw,
                                    0, 1200, self.name)
            link.carrier_send(P.WHO, payload)
            if self.corrupt_first and self.first:
                link.corrupt_next_ba()
                self.first = False
        elif frame.type == P.CMD:
            c = P.parse_cmd(frame.payload)
            self.cmds.append(c)
            link.carrier_send(P.STATUS, P.status_payload(c["target"], 0, 0))
        elif frame.type == P.HEARTBEAT:
            link.carrier_send(P.HEARTBEAT)
        elif frame.type == P.ERROR:
            self.error = P.parse_error(frame.payload)


def pump(link, ball, carrier, t):
    buf = link.ab
    while True:
        f, rest, err = P.decode(buf)
        if f is None and err == "short":
            link.ab = rest
            break
        if f is not None:
            carrier.receive(t, f, link)
        buf = rest
        if not buf:
            link.ab = b""
            break
    buf = link.ba
    while True:
        f, rest, err = P.decode(buf)
        if f is None and err == "short":
            link.ba = rest
            break
        if f is not None:
            ball.receive(t, f, link)
        elif err == "crc":
            ball.crc_errors += 1
        buf = rest
        if not buf:
            link.ba = b""
            break


def run(supply, carrier, seconds=1.4, step=0.02):
    link = Link()
    ball = Ball(supply)
    t = 0.0
    while t <= seconds:
        ball.tick(t, link)
        pump(link, ball, carrier, t)
        t = round(t + step, 6)
    return ball, carrier, link


def expect(cond, msg):
    if not cond:
        raise SystemExit("FAIL: " + msg)


def scenario_top_ok():
    ball, car, _ = run(400, Carrier(350, name="吊点"))
    expect(ball.state == "ok", "顶井 350 mA 应握手成功")
    expect(ball.status == {"pos": 1000, "vel": 0, "fault": 0}, "STATUS 没回来")
    expect(car.cmds and car.cmds[0]["target"] == 1000, "载体没收到 CMD")
    print("PASS top 4-pin 350 mA -> CMD/STATUS")


def scenario_top_3a():
    ball, car, _ = run(400, Carrier(2500))
    expect(ball.state == "power", "3 A 载体插顶井应只供电")
    expect(not car.cmds, "功率不足时不应发 CMD")
    expect(car.error == P.ERR_POWER, "载体应收到 ERROR 功率不足")
    print("PASS top 3 A carrier -> ERROR power, no CMD")


def scenario_bottom_3a():
    ball, car, _ = run(3000, Carrier(2500))
    expect(ball.state == "ok", "底井 3 A 应握手成功")
    expect(ball.status is not None, "底井 STATUS 没回来")
    print("PASS bottom 3 A carrier -> handshake ok")


def scenario_silent():
    ball, _, _ = run(400, Carrier(0, silent=True), seconds=1.2)
    expect(ball.state == "dumb", "无应答 1 s 后应判哑载体")
    print("PASS silent carrier -> dumb after 1 s")


def scenario_crc():
    ball, car, _ = run(400, Carrier(350, corrupt_first=True), seconds=1.4)
    expect(ball.crc_errors >= 1, "应记录一次 CRC 错")
    expect(ball.state == "ok", "CRC 错后重试应成功")
    print("PASS bad CRC -> dropped, retry succeeds")


def main():
    scenario_top_ok()
    scenario_top_3a()
    scenario_bottom_3a()
    scenario_silent()
    scenario_crc()
    print("PASS all protocol scenarios")


if __name__ == "__main__":
    main()
