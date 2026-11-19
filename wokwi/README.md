# Wokwi 双端串口模拟

一个 ESP32 同时跑球端和载体端，两个 UART 交叉相连；字节是真的走 UART，所以帧头、CRC、WHO 握手、功率协商都能验证。

## 打开

1. 打开 <https://wokwi.com/projects/new/micropython-esp32>（或 Wokwi 的 MicroPython ESP32 模板）；
2. 把本目录的 `main.py` 和 `protocol.py` 贴进文件面板（`diagram.json` 用编辑器里的 Diagram 视图直接替换）；
3. 点绿旗运行，串口监视器会依次打印 5 个场景；
4. 跑完后按 GPIO4 的按钮重放。

## 接线（diagram.json 已包含）

| 连接 | 说明 |
|---|---|
| GPIO17 → GPIO26 | UART1 TX → UART2 RX |
| GPIO25 → GPIO16 | UART2 TX → UART1 RX |
| GPIO2 → 220 Ω → LED | 场景 PASS 时亮 |
| GPIO4 → 按钮 → GND | 重放 |

`UART1` 是球端，`UART2` 是载体端；`main.py` 里两个状态机各自独立。

## 场景

1. **顶井 + 4 针 350 mA**：握手成功，球发 CMD，载体回 STATUS；
2. **顶井 + 3 A 载体**：球回 ERROR 功率不足，不下发 CMD；
3. **底井 + 3 A 载体**：握手成功；
4. **无应答**：1 s 后判哑载体；
5. **CRC 错**：丢帧后重试成功。

## 注意

- 这是**一个 MCU 跑两端**的便利做法；真实产品是两颗 MCU，但协议字节完全相同。
- Wokwi 没有 RK3566 模型；球端在真实产品里是 RK3566 + ESP32-S3 协处理，这里用 ESP32 验证协议，不验证算力。
- `protocol.py` 与 `tools/protocol.py` 必须同步；改协议先改 `tools/protocol.py`，再同步到 `wokwi/`。
- 本目录不能直接双击运行；需要 Wokwi 账号（免费档够用）。
