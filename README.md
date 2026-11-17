# CoreBall

一个球形的 AI 伴侣机器人。

球里住着人格和记忆，球可以插到不同的载体上——**一个灵魂，任意身体**。
灵感来自童年 IP「超能 NoNo」，但外观与设定完全原创。

---

## 现在是什么状态

**纸上已经闭合，手上还没开始。**

机构、尺寸、控制、行为都画完了，能跑出渲染图和一段动画。
**一个实体零件都还没做。**

- 全部是参数化模型，改一个数字重跑即可
- 全部是算出来的，不是凭感觉画的（张力、余量、可飞区域都有数字）
- 没有一行是给"可爱"服务的代码——可爱在渲染图和动作曲线里

---

## 目录

```
README.md                 你在这里
TODO.md                   待办与已知问题
docs/
  00-规格书.md             最初的项目规格（v0.1，未改动）
  01-设计决定.md           每一次取舍：决定 / 为什么 / 代价
  02-控制架构.md           五层结构、张力数学、禁区、路径、曲线
  03-参数表.md             所有尺寸和数字，一处可查
  archive/                已废弃的方向（最早的桌面盒、电磁板工位）
blender/
  build_ball.py           核心球 φ80
  build_hub.py            吊点总成（偏航 + 伸缩），可单独出图
  build_desk_rig.py       工位 + 四角绞盘 + 五线
  build_winch.py          绞盘总成 A/B 两种
  build_anim.py           8 秒运动动画 → mp4
  build_command.py        指挥场景：拖 CMD_TARGET，球与四线实时跟随
  cmd_runtime.py          面板、禁区、意图通道（由 指挥.bat 启动）
  actions.json            动作表与口令：用户可以自己改
  指挥.bat                双击进入指挥场景
  out/                    所有渲染产物
tools/
  tension.py              张力分配计算器
  zone_map.py             允许飞行区地图
  plan.py                 路径规划
  curves.py               速度曲线对比
  storyboard.py           「它的一天」分镜
```

---

## 怎么跑

```powershell
# Blender 在
set B=C:\Users\21165\Apps\blender-4.5.16\blender-4.5.16-windows-x64\blender.exe

# 模型
& $B --background --python blender\build_ball.py      -- --out blender\out\ball  --render
& $B --background --python blender\build_desk_rig.py  -- --out blender\out\rig   --render
& $B --background --python blender\build_winch.py     -- --out blender\out\winch --render
& $B --background --python blender\build_hub.py       -- --out blender\out\hub   --render

# 指挥场景（拖 CMD_TARGET，四线实时跟随）
& $B --background --python-exit-code 1 --python blender\build_command.py -- --out blender\out\cmd

# 动画（约 10 分钟）
& $B --background --python blender\build_anim.py      -- --out blender\out\anim

# 计算（纯 Python，不需要 Blender）
python tools\tension.py -380 520 1370
python tools\zone_map.py
python tools\plan.py
python tools\curves.py
python tools\storyboard.py
```

`blender\重建.bat` 和 `blender\打开场景.bat` 是给双击用的。

## 指挥它

双击 `blender\指挥.bat`，然后：

- 直接拖 `CMD_TARGET`（球、吊点、四根线一起走）
- 键盘 `1` 过来 · `2` 回去 · `3` 升 · `4` 降 · `5` 看我 · `0` 停
- 任何程序都可以发一条 UDP 指令：
  ```powershell
  $u = New-Object Net.Sockets.UdpClient
  $b = [Text.Encoding]::UTF8.GetBytes('{"intent":"come"}')
  $u.Send($b, $b.Length, '127.0.0.1', 4590)
  ```
- 动作、口令、快慢都在 `blender\actions.json` 里，改完重开 `指挥.bat` 生效

## 大脑（打字 → 球会动）

1. 复制 `brain.example.json` 为 `brain.json`，把 DeepSeek 的 key 填进 `providers.deepseek.api_key`（`brain.json` 已在 .gitignore 里，不会提交）
2. `python brain.py`，直接打字；回复里带动作时，球会通过 UDP 动
3. 性格写在 `persona.md`，记忆存在 `memory/`（只追加，攒够了自动压缩）
4. 想换 Kimi 做记忆：`roles.memory` 改成 `kimi`，再填 kimi 的 key
5. 自测：`python tools\test_brain.py`

## 让它说话

- 默认用 **Windows 离线语音**：0 成本、不用注册，`python voice.py "你好"` 就能听。
- 换 **火山引擎**：`brain.json` → `voice.volcengine` 填 `appid` 和 `token`，`provider` 保持 `auto` 就会自动切过去。
- 火山控制台：语音技术 → 语音合成 → 创建应用，拿 APPID 和 Access Token。

---

## 关键数字

| 项 | 值 |
|---|---|
| 球 | φ80，约 260 g，单手可握 |
| 吊点总成 | 约 200 g，偏航 360°，伸缩 90 mm |
| 工位 | 1640 × 1100 × 1900 mm |
| 线 | 4 根承力 + 1 根供电（双股） |
| 当前线长 | 530 / 1181 / 457 / 1043 mm |
| 最松张力 | 1.86 N（余量够） |
| 可飞区域 | 占工位 39–40% |
| 禁区 | 脖子为心 r210 硬，r305 软 |
| 默认位置 | (−380, 520, 1300)，距眼 640 mm，偏正前 30° |

---

## 三句话讲完这个项目

1. **它不是什么都能干。** 它只做一件事：在你旁边，用位置和姿态表示态度。
2. **悬浮不靠反重力，靠四根线。** 绳子是它的语法，不是它的缺陷。
3. **人格不在最短路里，在边界上。** 宽敞的地方谁走都一样，贴着禁区走才是性格。

---

## 接下来

见 `TODO.md`。当前建议的第一步是**把接口标准冻结**——它是唯一一个后面所有零件都挂在上面、而且越晚定越贵的东西。
