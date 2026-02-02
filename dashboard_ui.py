import Pico_ResTouch_LCD_3_5
import time
import framebuf
import urequests
import json
import gc
import secrets  # <--- IMPORT THIS

# --- CONFIGURATION ---
# We keep the base URL public, but append the secret key from the safe
BASE_URL = "https://script.google.com/macros/s/AKfycbzmS90JXXehedhyzJingavVNn2IxAdfKGlQTyFq_FkeRxYsE3hbkMaef7ewlZozl_F9/exec"
DATA_URL = BASE_URL + "?key=" + secrets.GOOGLE_KEY

SAFE_HEIGHT = 140
CYCLE_SPEED = 8
UPDATE_INTERVAL = 300
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
    if not data or len(data) < 2: return

    max_val = max(data)
    min_val = min(data)
    range_val = max_val - min_val if max_val != min_val else 1

    prev_px = x
    prev_py = y + h - int((data[0] - min_val) / range_val * h)
    step_x = w / (len(data) - 1)

    for i in range(1, len(data)):
        new_px = x + int(i * step_x)
        new_py = y + h - int((data[i] - min_val) / range_val * h)

        # Clip to safe zone
        if prev_py > SAFE_HEIGHT: prev_py = SAFE_HEIGHT
        if new_py > SAFE_HEIGHT: new_py = SAFE_HEIGHT

        lcd.line(prev_px, prev_py, new_px, new_py, 0x07E0)  # Green Line
        prev_px = new_px
        prev_py = new_py


# --- NETWORK HELPER ---
def fetch_live_data():
    print("Fetching Google Data...")
    try:
        response = urequests.get(DATA_URL)
        if response.status_code == 200:
            data = json.loads(response.text)
            response.close()
            print("Success:", data)
            return data
        response.close()
    except Exception as e:
        print("Fetch Failed:", e)
    return None


# --- MAIN APP ---
def start():
    lcd = Pico_ResTouch_LCD_3_5.LCD_3inch5()
    lcd.bl_ctrl(100)

    # Default/Loading Data
    current_data = {
        "net_worth": "Loading...",
        "change": "...",
        "history": [10, 10, 10]
    }

    page = 0
    last_switch = time.time()
    last_fetch = 0  # Force immediate fetch

    while True:
        current_time = time.time()

        # 1. FETCH DATA (Every 5 mins)
        if current_time - last_fetch > UPDATE_INTERVAL:
            # Draw a tiny yellow dot to show we are loading
            lcd.fill_rect(470, 0, 10, 10, 0xFFE0)
            lcd.show_up()

            new_data = fetch_live_data()
            if new_data:
                current_data = new_data

            last_fetch = current_time
            # Clear loading dot
            lcd.fill_rect(470, 0, 10, 10, 0x0000)

            # Clean up RAM
            gc.collect()

        # 2. SWITCH PAGES
        if current_time - last_switch > CYCLE_SPEED:
            page = 1 - page
            last_switch = current_time
            lcd.fill_rect(0, 0, 480, SAFE_HEIGHT, 0x0000)

        # 3. DRAW UI
        # Red line for broken screen limit
        lcd.line(0, SAFE_HEIGHT, 480, SAFE_HEIGHT, 0xF800)

        if page == 0:
            # --- SUMMARY ---
            lcd.text("TOTAL NET WORTH", 10, 10, 0xFFFF)

            # Draw Net Worth (Scale based on length to fit screen)
            nw_str = str(current_data["net_worth"])
            scale = 7 if len(nw_str) < 8 else 5
            draw_string_huge(lcd, nw_str, 10, 35, 0x07E0, scale=scale)

            lcd.text(f"Day Change: {current_data['change']}", 20, 110, 0xFFFF)

        else:
            # --- GRAPH ---
            lcd.text("7-DAY TREND", 10, 10, 0xFFFF)
            draw_chart(lcd, current_data["history"], 10, 25, 460, 100, 0xFFFF)

        # Progress Bar
        bar_width = int(((current_time - last_switch) / CYCLE_SPEED) * 480)
        lcd.line(0, SAFE_HEIGHT - 2, bar_width, SAFE_HEIGHT - 2, 0x001F)

        lcd.show_up()
        time.sleep(0.1)