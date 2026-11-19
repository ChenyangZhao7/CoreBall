"""CoreBall interface v1.1: ball + carrier on one ESP32, UART loopback.

Wiring (see diagram.json):
  UART1 TX 17 -> UART2 RX 26
  UART2 TX 25 -> UART1 RX 16
  GND common

The ESP32 runs both state machines. The bytes are real UART traffic, so
framing, CRC and power negotiation are exercised. Scenarios run once, then
press the GPIO4 button to replay.
"""
import time

import protocol as P
from machine import Pin, UART

U1 = UART(1, baudrate=115200, tx=17, rx=16)
U2 = UART(2, baudrate=115200, tx=25, rx=26)

LED = Pin(2, Pin.OUT)
BTN = Pin(4, Pin.IN, Pin.PULL_UP)

ab = b""      # ball -> carrier bytes
ba = b""      # carrier -> ball bytes
ball = None
carrier = None


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

    def tick(self, t):
        if self.state == "wait":
            if t - self.last_who >= 0.1:
                U1.write(P.encode(P.WHO))
                self.last_who = t
            if t > 1.0:
                self.state = "dumb"
        elif self.state == "ok":
            if t - self.last_hb >= 0.2:
                U1.write(P.encode(P.HEARTBEAT))
                self.last_hb = t

    def receive(self, frame):
        if frame.type == P.WHO:
            w = P.parse_who(frame.payload)
            self.carrier = w
            if w["draw_mA"] > self.supply:
                self.state = "power"
                U1.write(P.encode(P.ERROR, P.error_payload(P.ERR_POWER)))
            else:
                self.state = "ok"
                U1.write(P.encode(P.CMD, P.cmd_payload(0, 1000, 500, 1000)))
        elif frame.type == P.STATUS:
            self.status = P.parse_status(frame.payload)
        elif frame.type == P.ERROR:
            self.error = P.parse_error(frame.payload)


class Carrier:
    def __init__(self, draw_mA, name="轮式", silent=False, corrupt=False):
        self.draw = draw_mA
        self.name = name
        self.silent = silent
        self.corrupt = corrupt
        self.first = True
        self.cmds = []
        self.error = None

    def send(self, ftype, payload=b""):
        U2.write(P.encode(ftype, payload))

    def receive(self, frame):
        if self.silent:
            return
        if frame.type == P.WHO:
            payload = P.who_payload(3, 1, 0x03, self.draw, 0, 1200, self.name)
            raw = P.encode(P.WHO, payload)
            if self.corrupt and self.first:
                # 故意破坏最后一字节，制造 CRC 错
                raw = raw[:-1] + bytes([raw[-1] ^ 0xFF])
                self.first = False
            U2.write(raw)
        elif frame.type == P.CMD:
            c = P.parse_cmd(frame.payload)
            self.cmds.append(c)
            self.send(P.STATUS, P.status_payload(c["target"], 0, 0))
        elif frame.type == P.HEARTBEAT:
            self.send(P.HEARTBEAT)
        elif frame.type == P.ERROR:
            self.error = P.parse_error(frame.payload)


def pump():
    global ab, ba
    if U2.any():
        ab += U2.read(U2.any())
    if U1.any():
        ba += U1.read(U1.any())
    while True:
        f, rest, err = P.decode(ab)
        if f is None and err == "short":
            ab = rest
            break
        if f:
            carrier.receive(f)
        ab = rest
        if not ab:
            break
    while True:
        f, rest, err = P.decode(ba)
        if f is None and err == "short":
            ba = rest
            break
        if f:
            ball.receive(f)
        elif err == "crc":
            ball.crc_errors += 1
        ba = rest
        if not ba:
            break


def run(name, supply, draw, seconds, silent=False, corrupt=False):
    global ab, ba, ball, carrier
    ab, ba = b"", b""
    U1.read()
    U2.read()
    ball = Ball(supply)
    carrier = Carrier(draw, silent=silent, corrupt=corrupt)
    print("")
    print("== %s ==" % name)
    t0 = time.ticks_ms()
    last = -1
    while True:
        ms = time.ticks_diff(time.ticks_ms(), t0)
        if ms >= seconds * 1000:
            break
        t = ms / 1000.0
        ball.tick(t)
        pump()
        if int(t) != last:
            last = int(t)
            print("t=%d s  ball=%s carrier_cmd=%d err=%d crc=%d" % (
                last, ball.state, len(carrier.cmds),
                carrier.error if carrier.error is not None else 0,
                ball.crc_errors))
        time.sleep_ms(5)

    if name.startswith("top 4"):
        ok = ball.state == "ok" and ball.status is not None and carrier.cmds
    elif name.startswith("top 3"):
        ok = ball.state == "power" and not carrier.cmds and \
            carrier.error == P.ERR_POWER
    elif name.startswith("bottom"):
        ok = ball.state == "ok" and ball.status is not None
    elif name.startswith("silent"):
        ok = ball.state == "dumb"
    else:
        ok = ball.state == "ok" and ball.crc_errors >= 1
    print("RESULT:", "PASS" if ok else "FAIL")
    LED.value(1 if ok else 0)
    time.sleep_ms(300)


def main():
    print("CoreBall interface v1.1 - one ESP32, two UART ends")
    while True:
        run("top 4-pin 350 mA", 400, 350, 1.4)
        run("top 3 A carrier", 400, 2500, 1.4)
        run("bottom 3 A carrier", 3000, 2500, 1.4)
        run("silent carrier", 400, 0, 1.3, silent=True)
        run("bad CRC then retry", 400, 350, 1.5, corrupt=True)
        print("")
        print("All scenarios done. Press GPIO4 to replay.")
        LED.value(0)
        while BTN.value():
            time.sleep_ms(20)
        while not BTN.value():
            time.sleep_ms(20)


main()
