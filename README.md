# Virtual Piano (Hand‑Gesture Controlled)

A lightweight virtual piano you can play with hand gestures via a webcam. It uses MediaPipe Hands to track your thumb tip as the on‑screen pointer and a thumb–index pinch gesture as the "click" to press keys and UI buttons. The UI is rendered with Pygame; the camera feed is mirrored for intuitive control. Chinese fonts are auto‑loaded to avoid square glyphs.

- Tested on Windows with Python 3.12
- Libraries: OpenCV, MediaPipe, Pygame, NumPy (see `requirements.txt`)
- Features: mirrored camera, top‑layer pointer, black‑key priority hit‑testing, smoothing and hysteresis for stable clicks, sheet selection popup

## Quick Start (Windows, PowerShell)

```powershell
# Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run
python .\virtual_piano.py
```

Tip: If MediaPipe fails to install on Python 3.13+, use Python 3.12.

## Basic Controls

- Pointing: move your thumb tip in front of the camera.
- Click/Press: pinch thumb and index finger (with hysteresis to avoid jitter).

---

# 手势控制虚拟钢琴（中文说明）

这是一个通过摄像头手势来演奏的虚拟钢琴。项目使用 MediaPipe Hands 追踪拇指指尖作为屏幕指针，拇指与食指的捏合手势作为“点击”，用于按下琴键与操作界面按钮。界面由 Pygame 绘制，摄像头画面为镜像显示；内置中文字体自动加载，避免中文显示为方块。

- 已在 Windows + Python 3.12 下测试
- 依赖：OpenCV、MediaPipe、Pygame、NumPy（见 `requirements.txt`）
- 功能：镜像画面、指针置顶绘制、黑键判定优先、平滑与迟滞抖动抑制、乐谱选择弹窗

## 快速开始（Windows，PowerShell）

```powershell
# 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

# 运行
python .\virtual_piano.py
```

提示：若在 Python 3.13+ 安装 MediaPipe 失败，请改用 Python 3.12。

## 基本操作

- 指向：将拇指指尖移动到摄像头前作为指针。
- 点击/按键：拇指与食指捏合触发（带迟滞避免抖动）。
