import Pico_ResTouch_LCD_3_5
import time
import framebuf

# --- CONFIGURATION ---
SAFE_HEIGHT = 140  # We only use the top 140 pixels
CYCLE_SPEED = 5  # Seconds per page


# --- GRAPHICS HELPERS ---
def draw_big_char(lcd, char, x, y, color, scale=3):
    buffer = bytearray(8)
    fb = framebuf.FrameBuffer(buffer, 8, 8, framebuf.MONO_HLSB)
    fb.text(char, 0, 0, 1)
    for row in range(8):
        line = buffer[row]
        for col in range(8):
            if (line >> (7 - col)) & 1:
                lcd.fill_rect(x + (col * scale), y + (row * scale), scale, scale, color)


def draw_string_huge(lcd, string, x, y, color, scale=3):
    cursor_x = x
    for char in string:
        draw_big_char(lcd, char, cursor_x, y, color, scale)
        cursor_x += (8 * scale) + 2


def draw_chart(lcd, data, x, y, w, h, color):
    lcd.rect(x, y, w, h, color)
    if not data: return
    max_val = max(data)
    min_val = min(data)
    range_val = max_val - min_val if max_val != min_val else 1

    prev_px = x
    prev_py = y + h - int((data[0] - min_val) / range_val * h)
    step_x = w / (len(data) - 1)

    for i in range(1, len(data)):
        new_px = x + int(i * step_x)
        new_py = y + h - int((data[i] - min_val) / range_val * h)
        lcd.line(prev_px, prev_py, new_px, new_py, 0x07E0)  # Green Line
        prev_px = new_px
        prev_py = new_py


# --- MAIN APP ---
def start():
    lcd = Pico_ResTouch_LCD_3_5.LCD_3inch5()
    lcd.bl_ctrl(100)

    history_data = [710, 712, 708, 715, 716, 717]
    page = 0
    last_switch = time.time()

    while True:
        # Check if it's time to switch pages
        if time.time() - last_switch > CYCLE_SPEED:
            page = 1 - page  # Toggle 0 -> 1 -> 0
            last_switch = time.time()
            lcd.fill_rect(0, 0, 480, SAFE_HEIGHT, 0x0000)  # Clear only safe zone

        # Draw red line to mark the "Dead Zone"
        lcd.line(0, SAFE_HEIGHT, 480, SAFE_HEIGHT, 0xF800)

        if page == 0:
            # --- PAGE 1: BIG NUMBERS ---
            lcd.text("TOTAL NET WORTH", 10, 10, 0xFFFF)
            draw_string_huge(lcd, "$717k", 10, 35, 0x07E0, scale=7)  # Huge text
            lcd.text("+$6,200 (Today)", 20, 100, 0xFFFF)

            # Progress bar for next page switch
            bar_width = int(((time.time() - last_switch) / CYCLE_SPEED) * 480)
            lcd.line(0, SAFE_HEIGHT - 2, bar_width, SAFE_HEIGHT - 2, 0x001F)  # Blue line

        else:
            # --- PAGE 2: WIDE CHART ---
            lcd.text("7-DAY PERFORMANCE", 10, 10, 0xFFFF)
            draw_chart(lcd, history_data, 10, 25, 460, 100, 0xFFFF)

            # Progress bar
            bar_width = int(((time.time() - last_switch) / CYCLE_SPEED) * 480)
            lcd.line(0, SAFE_HEIGHT - 2, bar_width, SAFE_HEIGHT - 2, 0x001F)

        lcd.show_up()

        # Don't check touch anymore, it's broken
        time.sleep(0.1)