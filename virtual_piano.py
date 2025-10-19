import cv2
import mediapipe as mp
import pygame
import numpy as np
import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

# 初始化pygame
pygame.init()
pygame.mixer.init()

# 屏幕设置
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("虚拟钢琴")

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (80, 80, 80)
BLUE = (100, 150, 255)
GREEN = (100, 255, 150)
RED = (255, 100, 100)
YELLOW = (255, 255, 100)

class UIState(Enum):
    NORMAL = 1
    HOVER = 2
    ACTIVE = 3

class GameMode(Enum):
    NORMAL = 1
    SHEET_SELECT = 2
    SHEET_PLAY = 3
    COMPLETE = 4

@dataclass
class PianoKey:
    """钢琴键数据类"""
    note: str
    frequency: float
    rect: pygame.Rect
    is_black: bool
    state: UIState = UIState.NORMAL

@dataclass
class Button:
    """按钮数据类"""
    text: str
    rect: pygame.Rect
    state: UIState = UIState.NORMAL
    callback: callable = None

@dataclass
class Sheet:
    """乐谱数据类"""
    name: str
    notes: List[str]

class VirtualPiano:
    def __init__(self):
        self.running = True
        self.clock = pygame.time.Clock()
        self.mode = GameMode.NORMAL
        
        # MediaPipe手部检测
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils
        
        # 摄像头
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 手指位置和状态
        self.finger_pos = None
        self.is_finger_bent = False
        self.prev_finger_bent = False
        
        # 创建钢琴键
        self.piano_keys = self.create_piano_keys()
        
        # 创建按钮
        self.buttons = []
        self.create_buttons()
        
        # 乐谱
        self.sheets = self.create_sheets()
        self.current_sheet = None
        self.current_note_index = 0
        
        # 弹窗
        self.sheet_select_popup = None
        self.complete_popup_timer = 0
        
        # 生成音效
        self.generate_sounds()
        
        # 字体
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
    
    def create_piano_keys(self) -> List[PianoKey]:
        """创建钢琴键（一个八度）"""
        keys = []
        # 音符频率（C4到C5）
        notes_data = [
            ("C4", 261.63, False),
            ("C#4", 277.18, True),
            ("D4", 293.66, False),
            ("D#4", 311.13, True),
            ("E4", 329.63, False),
            ("F4", 349.23, False),
            ("F#4", 369.99, True),
            ("G4", 392.00, False),
            ("G#4", 415.30, True),
            ("A4", 440.00, False),
            ("A#4", 466.16, True),
            ("B4", 493.88, False),
            ("C5", 523.25, False),
        ]
        
        # 钢琴键区域（屏幕下方1/3）
        piano_y = int(SCREEN_HEIGHT * 2/3)
        piano_height = SCREEN_HEIGHT - piano_y
        white_key_width = 80
        white_key_height = piano_height - 20
        black_key_width = 50
        black_key_height = int(white_key_height * 0.6)
        
        # 先创建白键
        white_keys_count = sum(1 for _, _, is_black in notes_data if not is_black)
        start_x = (SCREEN_WIDTH - white_keys_count * white_key_width) // 2
        
        white_index = 0
        for note, freq, is_black in notes_data:
            if not is_black:
                x = start_x + white_index * white_key_width
                rect = pygame.Rect(x, piano_y + 10, white_key_width, white_key_height)
                keys.append(PianoKey(note, freq, rect, False))
                white_index += 1
        
        # 创建黑键（在白键上方）
        black_positions = [0, 1, 3, 4, 5]  # C#, D#, F#, G#, A#的相对位置
        black_index = 0
        for note, freq, is_black in notes_data:
            if is_black:
                white_pos = black_positions[black_index]
                x = start_x + white_pos * white_key_width + white_key_width - black_key_width // 2
                rect = pygame.Rect(x, piano_y + 10, black_key_width, black_key_height)
                keys.append(PianoKey(note, freq, rect, True))
                black_index += 1
        
        return keys
    
    def create_buttons(self):
        """创建功能按钮"""
        button_width = 150
        button_height = 40
        margin = 20
        
        # 退出游戏按钮
        exit_btn = Button(
            "退出游戏",
            pygame.Rect(margin, margin, button_width, button_height),
            callback=self.exit_game
        )
        
        # 乐谱选择按钮
        sheet_btn = Button(
            "乐谱选择",
            pygame.Rect(margin * 2 + button_width, margin, button_width, button_height),
            callback=self.open_sheet_select
        )
        
        self.buttons = [exit_btn, sheet_btn]
        self.normal_buttons = self.buttons.copy()
        
        # 乐谱模式按钮
        exit_sheet_btn = Button(
            "退出乐谱弹奏",
            pygame.Rect(margin, margin, button_width + 50, button_height),
            callback=self.exit_sheet_mode
        )
        
        reselect_btn = Button(
            "重新选择乐谱",
            pygame.Rect(margin * 2 + button_width + 50, margin, button_width + 50, button_height),
            callback=self.open_sheet_select
        )
        
        self.sheet_mode_buttons = [exit_sheet_btn, reselect_btn]
    
    def create_sheets(self) -> List[Sheet]:
        """创建乐谱"""
        return [
            Sheet("小星星", ["C4", "C4", "G4", "G4", "A4", "A4", "G4", 
                          "F4", "F4", "E4", "E4", "D4", "D4", "C4"]),
            Sheet("欢乐颂", ["E4", "E4", "F4", "G4", "G4", "F4", "E4", "D4",
                          "C4", "C4", "D4", "E4", "E4", "D4", "D4"]),
            Sheet("简单练习", ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]),
        ]
    
    def generate_sounds(self):
        """生成钢琴音效"""
        self.sounds = {}
        sample_rate = 22050
        duration = 0.5
        
        for key in self.piano_keys:
            samples = np.sin(2 * np.pi * np.arange(sample_rate * duration) * key.frequency / sample_rate)
            # 添加衰减效果
            envelope = np.exp(-np.arange(sample_rate * duration) / (sample_rate * 0.3))
            samples = samples * envelope * 0.3
            samples = (samples * 32767).astype(np.int16)
            
            # 创建立体声
            stereo_samples = np.column_stack((samples, samples))
            sound = pygame.sndarray.make_sound(stereo_samples)
            self.sounds[key.note] = sound
    
    def detect_hand(self, frame):
        """检测手部并获取手指位置"""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        
        self.finger_pos = None
        self.is_finger_bent = False
        
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            
            # 绘制手部关键点
            self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
            
            # 获取食指指尖位置（landmark 8）
            h, w, _ = frame.shape
            index_tip = hand_landmarks.landmark[8]
            x = int(index_tip.x * SCREEN_WIDTH)
            y = int(index_tip.y * SCREEN_HEIGHT * 2/3)  # 映射到摄像头显示区域
            self.finger_pos = (x, y)
            
            # 检测手指是否弯曲（比较食指指尖和第二关节的y坐标）
            index_pip = hand_landmarks.landmark[6]
            if index_tip.y > index_pip.y:  # 指尖在下方表示弯曲
                self.is_finger_bent = True
        
        return frame
    
    def check_click(self):
        """检测点击动作（手指从伸直到弯曲）"""
        clicked = False
        if self.is_finger_bent and not self.prev_finger_bent:
            clicked = True
        self.prev_finger_bent = self.is_finger_bent
        return clicked
    
    def update_ui_states(self):
        """更新UI元素状态"""
        clicked = self.check_click()
        
        # 根据模式选择活动按钮
        if self.mode == GameMode.NORMAL:
            active_buttons = self.normal_buttons
        elif self.mode == GameMode.SHEET_PLAY:
            active_buttons = self.sheet_mode_buttons
        elif self.mode == GameMode.SHEET_SELECT:
            active_buttons = []
        else:
            active_buttons = []
        
        # 更新按钮状态
        for btn in active_buttons:
            if self.finger_pos and btn.rect.collidepoint(self.finger_pos):
                if clicked:
                    btn.state = UIState.ACTIVE
                    if btn.callback:
                        btn.callback()
                else:
                    btn.state = UIState.HOVER
            else:
                btn.state = UIState.NORMAL
        
        # 更新钢琴键状态
        if self.mode in [GameMode.NORMAL, GameMode.SHEET_PLAY]:
            for key in self.piano_keys:
                if self.finger_pos and key.rect.collidepoint(self.finger_pos):
                    if clicked:
                        key.state = UIState.ACTIVE
                        self.play_note(key.note)
                    else:
                        key.state = UIState.HOVER
                else:
                    key.state = UIState.NORMAL
    
    def play_note(self, note: str):
        """播放音符"""
        if note in self.sounds:
            self.sounds[note].play()
            
            # 乐谱模式下检查是否正确
            if self.mode == GameMode.SHEET_PLAY and self.current_sheet:
                if self.current_note_index < len(self.current_sheet.notes):
                    if note == self.current_sheet.notes[self.current_note_index]:
                        self.current_note_index += 1
                        
                        # 检查是否完成
                        if self.current_note_index >= len(self.current_sheet.notes):
                            self.mode = GameMode.COMPLETE
                            self.complete_popup_timer = pygame.time.get_ticks()
    
    def draw_piano_keys(self):
        """绘制钢琴键"""
        # 先绘制白键
        for key in self.piano_keys:
            if not key.is_black:
                self.draw_key(key)
        
        # 再绘制黑键（在上层）
        for key in self.piano_keys:
            if key.is_black:
                self.draw_key(key)
    
    def draw_key(self, key: PianoKey):
        """绘制单个钢琴键"""
        # 根据状态选择颜色
        if key.is_black:
            colors = {
                UIState.NORMAL: BLACK,
                UIState.HOVER: DARK_GRAY,
                UIState.ACTIVE: GRAY
            }
        else:
            colors = {
                UIState.NORMAL: WHITE,
                UIState.HOVER: LIGHT_GRAY,
                UIState.ACTIVE: GRAY
            }
        
        color = colors[key.state]
        pygame.draw.rect(screen, color, key.rect)
        pygame.draw.rect(screen, BLACK, key.rect, 2)
        
        # 乐谱模式下高亮当前应该按的键
        if self.mode == GameMode.SHEET_PLAY and self.current_sheet:
            if self.current_note_index < len(self.current_sheet.notes):
                if key.note == self.current_sheet.notes[self.current_note_index]:
                    pygame.draw.rect(screen, YELLOW, key.rect, 5)
        
        # 绘制音符名称
        text_color = WHITE if key.is_black else BLACK
        text = self.small_font.render(key.note, True, text_color)
        text_rect = text.get_rect(center=(key.rect.centerx, key.rect.bottom - 20))
        screen.blit(text, text_rect)
    
    def draw_button(self, btn: Button):
        """绘制按钮"""
        colors = {
            UIState.NORMAL: BLUE,
            UIState.HOVER: GREEN,
            UIState.ACTIVE: RED
        }
        
        color = colors[btn.state]
        pygame.draw.rect(screen, color, btn.rect, border_radius=5)
        pygame.draw.rect(screen, WHITE, btn.rect, 2, border_radius=5)
        
        text = self.small_font.render(btn.text, True, WHITE)
        text_rect = text.get_rect(center=btn.rect.center)
        screen.blit(text, text_rect)
    
    def draw_camera_feed(self, frame):
        """绘制摄像头画面"""
        camera_height = int(SCREEN_HEIGHT * 2/3) - 80
        frame = cv2.resize(frame, (int(camera_height * 4/3), camera_height))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = np.rot90(frame)
        frame = pygame.surfarray.make_surface(frame)
        
        x = (SCREEN_WIDTH - frame.get_width()) // 2
        screen.blit(frame, (x, 80))
        
        # 绘制手指指针
        if self.finger_pos:
            color = RED if self.is_finger_bent else GREEN
            pygame.draw.circle(screen, color, self.finger_pos, 10)
            pygame.draw.circle(screen, WHITE, self.finger_pos, 10, 2)
    
    def draw_sheet_select_popup(self):
        """绘制乐谱选择弹窗"""
        # 半透明背景
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        # 弹窗背景
        popup_width = 400
        popup_height = 300
        popup_rect = pygame.Rect(
            (SCREEN_WIDTH - popup_width) // 2,
            (SCREEN_HEIGHT - popup_height) // 2,
            popup_width,
            popup_height
        )
        pygame.draw.rect(screen, WHITE, popup_rect, border_radius=10)
        pygame.draw.rect(screen, BLUE, popup_rect, 3, border_radius=10)
        
        # 标题
        title = self.font.render("选择乐谱", True, BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, popup_rect.top + 40))
        screen.blit(title, title_rect)
        
        # 乐谱选项
        item_height = 50
        start_y = popup_rect.top + 80
        
        clicked = self.check_click()
        
        for i, sheet in enumerate(self.sheets):
            item_rect = pygame.Rect(
                popup_rect.left + 20,
                start_y + i * (item_height + 10),
                popup_width - 40,
                item_height
            )
            
            # 检测悬停和点击
            state = UIState.NORMAL
            if self.finger_pos and item_rect.collidepoint(self.finger_pos):
                if clicked:
                    state = UIState.ACTIVE
                    self.select_sheet(sheet)
                else:
                    state = UIState.HOVER
            
            # 绘制选项
            colors = {
                UIState.NORMAL: LIGHT_GRAY,
                UIState.HOVER: GREEN,
                UIState.ACTIVE: RED
            }
            pygame.draw.rect(screen, colors[state], item_rect, border_radius=5)
            pygame.draw.rect(screen, BLACK, item_rect, 2, border_radius=5)
            
            text = self.small_font.render(sheet.name, True, BLACK)
            text_rect = text.get_rect(center=item_rect.center)
            screen.blit(text, text_rect)
    
    def draw_complete_popup(self):
        """绘制完成弹窗"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        screen.blit(overlay, (0, 0))
        
        popup_width = 400
        popup_height = 200
        popup_rect = pygame.Rect(
            (SCREEN_WIDTH - popup_width) // 2,
            (SCREEN_HEIGHT - popup_height) // 2,
            popup_width,
            popup_height
        )
        pygame.draw.rect(screen, WHITE, popup_rect, border_radius=10)
        pygame.draw.rect(screen, GREEN, popup_rect, 3, border_radius=10)
        
        title = self.font.render("恭喜！", True, GREEN)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, popup_rect.centery - 30))
        screen.blit(title, title_rect)
        
        msg = self.small_font.render("弹奏完成！", True, BLACK)
        msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, popup_rect.centery + 20))
        screen.blit(msg, msg_rect)
    
    # 回调函数
    def exit_game(self):
        """退出游戏"""
        self.running = False
    
    def open_sheet_select(self):
        """打开乐谱选择"""
        self.mode = GameMode.SHEET_SELECT
    
    def select_sheet(self, sheet: Sheet):
        """选择乐谱"""
        self.current_sheet = sheet
        self.current_note_index = 0
        self.mode = GameMode.SHEET_PLAY
    
    def exit_sheet_mode(self):
        """退出乐谱模式"""
        self.mode = GameMode.NORMAL
        self.current_sheet = None
        self.current_note_index = 0
    
    def run(self):
        """主循环"""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
            
            # 读取摄像头
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.flip(frame, 1)
                frame = self.detect_hand(frame)
                
                # 更新UI状态
                self.update_ui_states()
                
                # 绘制
                screen.fill(BLACK)
                
                # 绘制摄像头画面
                self.draw_camera_feed(frame)
                
                # 绘制按钮
                if self.mode == GameMode.NORMAL:
                    for btn in self.normal_buttons:
                        self.draw_button(btn)
                elif self.mode == GameMode.SHEET_PLAY:
                    for btn in self.sheet_mode_buttons:
                        self.draw_button(btn)
                    
                    # 显示进度
                    if self.current_sheet:
                        progress_text = f"{self.current_sheet.name}: {self.current_note_index}/{len(self.current_sheet.notes)}"
                        text = self.small_font.render(progress_text, True, WHITE)
                        screen.blit(text, (SCREEN_WIDTH // 2 - 100, 40))
                
                # 绘制钢琴键
                self.draw_piano_keys()
                
                # 绘制弹窗
                if self.mode == GameMode.SHEET_SELECT:
                    self.draw_sheet_select_popup()
                elif self.mode == GameMode.COMPLETE:
                    self.draw_complete_popup()
                    
                    # 5秒后自动关闭
                    if pygame.time.get_ticks() - self.complete_popup_timer > 5000:
                        self.exit_sheet_mode()
                
                pygame.display.flip()
                self.clock.tick(30)
        
        # 清理
        self.cap.release()
        self.hands.close()
        pygame.quit()

if __name__ == "__main__":
    game = VirtualPiano()
    game.run()