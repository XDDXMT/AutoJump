import pygame
import sys
import math
import pyautogui
import time
import random
from PIL import ImageGrab

# 初始化pygame
pygame.init()

# 跳一跳窗口区域参数
LEFT, TOP, WIDTH, HEIGHT = 980, 137, 599, 1109
GAME_REGION = (LEFT, TOP, LEFT + WIDTH, TOP + HEIGHT)  # (left, top, right, bottom)
SCREEN_WIDTH, SCREEN_HEIGHT = WIDTH, HEIGHT  # 使用游戏区域大小作为窗口大小

# 可调整参数 - 在代码顶部定义方便修改
JUMP_FACTOR = 1.35  # 初始距离-时间系数
JUMP_FACTOR_INCREMENT = 0.01  # 每次调整的增量
MIN_JUMP_FACTOR = 1.0  # 最小系数
MAX_JUMP_FACTOR = 2.0  # 最大系数
PRESS_DURATION = 0.2  # 鼠标移动时间
RANDOM_DELAY_MIN = 0.5  # 最小随机延迟
RANDOM_DELAY_MAX = 1.5  # 最大随机延迟

# 配置参数
POINT_RADIUS = 10
POINT_COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]  # 红:棋子, 绿:目标, 蓝:按压点

# 创建窗口
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption(f"WeChat Jump Helper - Region: {LEFT},{TOP},{WIDTH}x{HEIGHT}")

# 字体
font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 28)
medium_font = pygame.font.SysFont(None, 32)

class Point:
    def __init__(self, x, y, color, name):
        self.x = x
        self.y = y
        self.color = color
        self.name = name
        self.dragging = False
        self.offset_x = 0
        self.offset_y = 0

    def draw(self, surface):
        # 绘制点
        pygame.draw.circle(surface, self.color, (self.x, self.y), POINT_RADIUS)
        pygame.draw.circle(surface, (255, 255, 255), (self.x, self.y), POINT_RADIUS, 2)

        # 绘制标签
        text = small_font.render(self.name, True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.x, self.y - POINT_RADIUS - 15))
        pygame.draw.rect(surface, (0, 0, 0, 180),
                         (text_rect.x-5, text_rect.y-2, text_rect.width+10, text_rect.height+4))
        surface.blit(text, text_rect)

    def is_over(self, pos):
        return math.sqrt((self.x - pos[0])**2 + (self.y - pos[1])**2) <= POINT_RADIUS

    def start_drag(self, pos):
        self.dragging = True
        self.offset_x = self.x - pos[0]
        self.offset_y = self.y - pos[1]

    def drag(self, pos):
        if self.dragging:
            self.x = pos[0] + self.offset_x
            self.y = pos[1] + self.offset_y

    def stop_drag(self):
        self.dragging = False

def capture_game_region():
    """Capture specified game region as background"""
    try:
        screenshot = ImageGrab.grab(bbox=GAME_REGION)
        screenshot.save("game_region.png")
        return pygame.image.load("game_region.png")
    except Exception as e:
        print(f"Capture failed: {str(e)}")
        # Create blank background
        background = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        background.fill((50, 50, 50))
        return background

def find_piece_position(image):
    """在截图中找出棋子的中心位置（红点应移动的位置）"""
    img = image.convert('RGB')
    width, height = img.size

    target_color_range = {
        'r_min': 40, 'r_max': 70,
        'g_min': 40, 'g_max': 70,
        'b_min': 80, 'b_max': 130
    }

    count = 0
    sum_x = 0
    sum_y = 0

    for y in range(height // 3, height * 2 // 3):  # 限制扫描区域，提高效率
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            if (target_color_range['r_min'] <= r <= target_color_range['r_max'] and
                target_color_range['g_min'] <= g <= target_color_range['g_max'] and
                target_color_range['b_min'] <= b <= target_color_range['b_max']):
                sum_x += x
                sum_y += y
                count += 1

    if count > 0:
        center_x = sum_x // count
        center_y = sum_y // count
        return center_x, center_y
    else:
        return None

def find_block_target(image):
    """识别跳跃目标方块（上方优先），返回中心坐标"""
    img = image.convert("RGB")
    width, height = img.size

    candidates = []
    for y in range(height // 4, height * 3 // 4):
        for x in range(20, width - 20):
            r, g, b = img.getpixel((x, y))
            r_next, g_next, b_next = img.getpixel((x + 1, y))
            diff = abs(r - r_next) + abs(g - g_next) + abs(b - b_next)

            if diff > 30:  # 明显边缘
                brightness = (r + g + b) / 3
                if brightness > 50 and brightness < 240:
                    weight = (height - y) * 1.0  # 越靠上权重越大
                    candidates.append((x, y, weight))

    if not candidates:
        return None

    # 聚合候选点的加权平均中心
    total_weight = sum([c[2] for c in candidates])
    avg_x = int(sum([c[0] * c[2] for c in candidates]) / total_weight)
    avg_y = int(sum([c[1] * c[2] for c in candidates]) / total_weight)

    return avg_x, avg_y




def calculate_distance(p1, p2):
    """Calculate distance between two points"""
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)

def simulate_jump(press_point, distance, factor):
    """Simulate long press action"""
    # Calculate press time
    base = distance * factor / 1000
    press_time = base + 0.80 * (1 - math.exp(-base))  # 补偿值：短距离趋近于 0.1，长距离接近 0.1

    # Convert to seconds

    # Convert game region coordinates to screen coordinates
    screen_x = LEFT + press_point.x
    screen_y = TOP + press_point.y

    # Move mouse to press point
    pyautogui.moveTo(screen_x, screen_y, duration=PRESS_DURATION)
    time.sleep(0.1)

    # Simulate long press
    pyautogui.mouseDown()
    time.sleep(press_time)
    pyautogui.mouseUp()

    print(f"Jump executed: Dist={distance:.1f}px, Press={press_time*1000:.0f}ms, Factor={factor:.3f}")

    # Random delay
    time.sleep(random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX))

def draw_button(surface, rect, text, color=(100, 100, 200)):
    """Draw a button with text"""
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, (200, 200, 200), rect, 2)

    text_surf = small_font.render(text, True, (255, 255, 255))
    text_rect = text_surf.get_rect(center=rect.center)
    surface.blit(text_surf, text_rect)
    return rect

def main():
    global JUMP_FACTOR

    # Capture game region as background
    background = capture_game_region()

    # Create three points
    points = [
        Point(SCREEN_WIDTH//3, SCREEN_HEIGHT//2, POINT_COLORS[0], "Piece"),
        Point(SCREEN_WIDTH*2//3, SCREEN_HEIGHT//2, POINT_COLORS[1], "Target"),
        Point(SCREEN_WIDTH//2, SCREEN_HEIGHT*3//4, POINT_COLORS[2], "Press")
    ]

    # Define buttons
    button_height = 30
    button_width = 120
    button_margin = 10
    buttons = {
        "increase": pygame.Rect(SCREEN_WIDTH - button_width - button_margin,
                                SCREEN_HEIGHT - 5 * (button_height + button_margin),
                                button_width, button_height),
        "decrease": pygame.Rect(SCREEN_WIDTH - button_width - button_margin,
                                SCREEN_HEIGHT - 4 * (button_height + button_margin),
                                button_width, button_height),
        "jump": pygame.Rect(SCREEN_WIDTH - button_width - button_margin,
                            SCREEN_HEIGHT - 3 * (button_height + button_margin),
                            button_width, button_height),
        "reset": pygame.Rect(SCREEN_WIDTH - button_width - button_margin,
                             SCREEN_HEIGHT - 2 * (button_height + button_margin),
                             button_width, button_height),
        "capture": pygame.Rect(SCREEN_WIDTH - button_width - button_margin,
                               SCREEN_HEIGHT - 1 * (button_height + button_margin),
                               button_width, button_height),
        "auto_target": pygame.Rect(SCREEN_WIDTH - button_width - button_margin,
                                   SCREEN_HEIGHT - 6 * (button_height + button_margin),
                                   button_width, button_height)
    }

    selected_point = None
    last_jump_time = 0
    jump_count = 0
    jump_success = False

    # Main loop
    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Check points
                for point in points:
                    if point.is_over(mouse_pos):
                        selected_point = point
                        point.start_drag(mouse_pos)
                        break



                # Check buttons
                if buttons["increase"].collidepoint(mouse_pos):
                    JUMP_FACTOR += JUMP_FACTOR_INCREMENT
                    if JUMP_FACTOR > MAX_JUMP_FACTOR:
                        JUMP_FACTOR = MAX_JUMP_FACTOR


                elif buttons["auto_target"].collidepoint(mouse_pos):
                    img = ImageGrab.grab(bbox=GAME_REGION)
                    pos = find_block_target(img)
                    if pos:
                        points[1].x = pos[0]
                        points[1].y = pos[1]
                        print(f"Target block auto-set to: {pos}")
                    else:
                        print("No suitable target block found")


                elif buttons["decrease"].collidepoint(mouse_pos):
                    JUMP_FACTOR -= JUMP_FACTOR_INCREMENT
                    if JUMP_FACTOR < MIN_JUMP_FACTOR:
                        JUMP_FACTOR = MIN_JUMP_FACTOR

                elif buttons["jump"].collidepoint(mouse_pos):
                    # Calculate distance and jump
                    distance = calculate_distance(points[0], points[1])
                    simulate_jump(points[2], distance, JUMP_FACTOR)
                    jump_count += 1
                    last_jump_time = time.time()
                    jump_success = True
                    time.sleep(0.3)
                    # 刷新背景图
                    background = capture_game_region()

                    # 棋子位置识别与红点自动更新
                    img = ImageGrab.grab(bbox=GAME_REGION)
                    piece_pos = find_piece_position(img)
                    if piece_pos:
                        points[0].x = piece_pos[0]
                        points[0].y = piece_pos[1]
                        print(f"Auto-adjusted Piece position to: {piece_pos}")
                    else:
                        print("Failed to detect Piece position")


                elif buttons["reset"].collidepoint(mouse_pos):
                    points = [
                        Point(SCREEN_WIDTH//3, SCREEN_HEIGHT//2, POINT_COLORS[0], "Piece"),
                        Point(SCREEN_WIDTH*2//3, SCREEN_HEIGHT//2, POINT_COLORS[1], "Target"),
                        Point(SCREEN_WIDTH//2, SCREEN_HEIGHT*3//4, POINT_COLORS[2], "Press")
                    ]

                elif buttons["capture"].collidepoint(mouse_pos):
                    background = capture_game_region()

            elif event.type == pygame.MOUSEBUTTONUP:
                if selected_point:
                    selected_point.stop_drag()
                    selected_point = None

            elif event.type == pygame.MOUSEMOTION:
                if selected_point:
                    selected_point.drag(mouse_pos)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Calculate distance and jump
                    distance = calculate_distance(points[0], points[1])
                    simulate_jump(points[2], distance, JUMP_FACTOR)
                    jump_count += 1
                    last_jump_time = time.time()
                    jump_success = True
                    time.sleep(0.3)
                    # 刷新背景图
                    background = capture_game_region()

                    # 棋子位置识别与红点自动更新
                    img = ImageGrab.grab(bbox=GAME_REGION)
                    piece_pos = find_piece_position(img)
                    if piece_pos:
                        points[0].x = piece_pos[0]
                        points[0].y = piece_pos[1]
                        print(f"Auto-adjusted Piece position to: {piece_pos}")
                    else:
                        print("Failed to detect Piece position")


                elif event.key == pygame.K_r:  # Reset points
                    points = [
                        Point(SCREEN_WIDTH//3, SCREEN_HEIGHT//2, POINT_COLORS[0], "Piece"),
                        Point(SCREEN_WIDTH*2//3, SCREEN_HEIGHT//2, POINT_COLORS[1], "Target"),
                        Point(SCREEN_WIDTH//2, SCREEN_HEIGHT*3//4, POINT_COLORS[2], "Press")
                    ]

                elif event.key == pygame.K_c:  # Recapture region
                    background = capture_game_region()

                elif event.key == pygame.K_UP:  # Increase factor
                    JUMP_FACTOR += JUMP_FACTOR_INCREMENT
                    if JUMP_FACTOR > MAX_JUMP_FACTOR:
                        JUMP_FACTOR = MAX_JUMP_FACTOR

                elif event.key == pygame.K_DOWN:  # Decrease factor
                    JUMP_FACTOR -= JUMP_FACTOR_INCREMENT
                    if JUMP_FACTOR < MIN_JUMP_FACTOR:
                        JUMP_FACTOR = MIN_JUMP_FACTOR

                elif event.key == pygame.K_ESCAPE:
                    running = False

        # Draw background
        screen.blit(background, (0, 0))

        # Draw connection line
        if not points[0].dragging and not points[1].dragging:
            pygame.draw.line(screen, (255, 255, 0),
                             (points[0].x, points[0].y),
                             (points[1].x, points[1].y), 2)

            # Draw distance text
            distance = calculate_distance(points[0], points[1])
            distance_text = medium_font.render(f"Distance: {distance:.1f} px", True, (255, 255, 0))
            mid_x = (points[0].x + points[1].x) // 2
            mid_y = (points[0].y + points[1].y) // 2
            screen.blit(distance_text, (mid_x - distance_text.get_width()//2, mid_y - 30))

        # Draw points
        for point in points:
            point.draw(screen)

        # Draw info panel
        panel_width = 250
        panel_height = 180
        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        screen.blit(panel, (10, 10))

        # Draw instructions
        instructions = [
            "Instructions:",
            "1. Drag points to position:",
            "   - Red: Piece bottom",
            "   - Green: Target position",
            "   - Blue: Press position",
            "2. Press SPACE to jump",
            "3. Use buttons or keys:",
            "   - UP/DOWN: Adjust factor",
            "   - R: Reset points",
            "   - C: Refresh screen"
        ]

        for i, line in enumerate(instructions):
            text = small_font.render(line, True, (255, 255, 255))
            screen.blit(text, (20, 20 + i*20))

        # Draw factor info
        factor_text = medium_font.render(f"Jump Factor: {JUMP_FACTOR:.3f}", True, (0, 255, 255))
        screen.blit(factor_text, (20, SCREEN_HEIGHT - 50))

        # Draw buttons
        draw_button(screen, buttons["auto_target"], "Auto Target")
        draw_button(screen, buttons["increase"], "Increase Factor")
        draw_button(screen, buttons["decrease"], "Decrease Factor")
        draw_button(screen, buttons["jump"], "JUMP (Space)", (0, 150, 0))
        draw_button(screen, buttons["reset"], "Reset Points (R)")
        draw_button(screen, buttons["capture"], "Capture Screen (C)")

        # Draw jump count
        count_text = font.render(f"Jumps: {jump_count}", True, (0, 255, 255))
        screen.blit(count_text, (SCREEN_WIDTH - count_text.get_width() - 20, 20))

        # Draw status
        if time.time() - last_jump_time < 2 and jump_success:
            status_text = font.render("Jump Success!", True, (0, 255, 0))
            screen.blit(status_text, (SCREEN_WIDTH//2 - status_text.get_width()//2, SCREEN_HEIGHT - 50))

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
