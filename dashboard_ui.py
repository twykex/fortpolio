import Pico_ResTouch_LCD_3_5
import time
import framebuf
import urequests
import json
import gc
import secrets
import _thread
import math

# --- CONFIGURATION ---
BASE_URL = "https://script.google.com/macros/s/AKfycbzmS90JXXehedhyzJingavVNn2IxAdfKGlQTyFq_FkeRxYsE3hbkMaef7ewlZozl_F9/exec"
DATA_URL = BASE_URL + "?key=" + secrets.GOOGLE_KEY

SAFE_HEIGHT = 140
CYCLE_SPEED = 8
UPDATE_INTERVAL = 60

# --- SHARED MEMORY ---
shared_data = {
    "net_worth": "Loading...",
    "change": "...",
    "market_status": "CLOSED",
    "history": [],
    "allocation": [],
    "rsi": 50  # Default neutral
}
data_lock = _thread.allocate_lock()


# --- MATH ENGINE (QUANT) ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1: return 50
    gains = []
    losses = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        if delta >= 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))

    # Simple Average RSI (Smoothed is better but hard with limited data)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return int(rsi)


# --- NETWORK THREAD ---
def network_thread():
    while True:
        try:
            response = urequests.get(DATA_URL)
            if response.status_code == 200:
                new_data = json.loads(response.text)
                response.close()

                # Run Quant Math on Core 1
                hist = new_data.get("history", [])
                rsi_val = calculate_rsi(hist)

                with data_lock:
                    shared_data["net_worth"] = new_data.get("net_worth", "Error")
                    shared_data["change"] = new_data.get("change", "0%")
                    shared_data["market_status"] = new_data.get("market_status", "CLOSED")
                    shared_data["history"] = hist
                    shared_data["allocation"] = new_data.get("allocation", [])
                    shared_data["rsi"] = rsi_val
            else:
                response.close()
        except Exception as e:
            print("Net Error:", e)
        time.sleep(UPDATE_INTERVAL)


# --- GRAPHICS ENGINE ---
def draw_gradient_bg(lcd, width, height):
    # Deep "Bloomberg Terminal" Gradient
    for y in range(height):
        # 0x0000 to 0x18E3 (Dark Slate Blue)
        b = int((y / height) * 20)
        g = int((y / height) * 10)
        color = (g << 5) | b
        lcd.line(0, y, width, y, color)


def draw_card(lcd, x, y, w, h, color):
    # Draws a "Glass" card with rounded corners effect
    lcd.rect(x + 2, y, w - 4, h, color)
    lcd.rect(x, y + 2, w, h - 4, color)
    # Bezel
    lcd.rect(x + 2, y, w - 4, h, 0xFFFF)
    lcd.rect(x, y + 2, w, h - 4, 0xFFFF)


def draw_dna_bar(lcd, allocation, x, y, w, h):
    # Stacked Bar Chart
    if not allocation: return

    current_x = x
    colors = [0x07E0, 0x07FF, 0xF81F, 0xFFE0, 0xF800]  # Green, Cyan, Purple, Yellow, Red

    # 1. Draw The Segments
    for i, asset in enumerate(allocation):
        if i >= 4: break  # Max 4 segments to prevent clutter
        seg_w = int(asset["weight"] * w)
        if seg_w < 2: continue

        color = colors[i % len(colors)]
        lcd.fill_rect(current_x, y, seg_w, h, color)

        # Label inside bar if wide enough
        if seg_w > 30:
            lcd.text(asset["symbol"], current_x + 2, y + 4, 0x0000)

        current_x += seg_w

    # 2. Draw Frame
    lcd.rect(x, y, w, h, 0xFFFF)


def draw_rsi_gauge(lcd, rsi, x, y, w):
    # Linear Gauge
    lcd.text(f"RSI MOMENTUM: {rsi}", x, y, 0xFFFF)

    bar_y = y + 15
    bar_h = 10
    lcd.rect(x, bar_y, w, bar_h, 0x8410)  # Gray Track

    # Color Logic
    fill_color = 0x07E0  # Green (Neutral/Bullish)
    if rsi > 70: fill_color = 0xF800  # Red (Overbought)
    if rsi < 30: fill_color = 0x07FF  # Cyan (Oversold/Buy the dip)

    # Fill
    fill_w = int((rsi / 100) * w)
    lcd.fill_rect(x, bar_y, fill_w, bar_h, fill_color)

    # Markers
    lcd.line(x + int(w * 0.3), bar_y - 2, x + int(w * 0.3), bar_y + 12, 0xFFFF)  # 30
    lcd.line(x + int(w * 0.7), bar_y - 2, x + int(w * 0.7), bar_y + 12, 0xFFFF)  # 70


def draw_big_char(lcd, char, x, y, color, scale):
    buffer = bytearray(8)
    fb = framebuf.FrameBuffer(buffer, 8, 8, framebuf.MONO_HLSB)
    fb.text(char, 0, 0, 1)
    for row in range(8):
        line = buffer[row]
        for col in range(8):
            if (line >> (7 - col)) & 1:
                lcd.fill_rect(x + (col * scale), y + (row * scale), scale, scale, color)


def draw_string(lcd, string, x, y, color, scale):
    cursor = x
    for char in string:
        draw_big_char(lcd, char, cursor, y, color, scale)
        cursor += (8 * scale) + 2


# --- MAIN APP ---
def start():
    lcd = Pico_ResTouch_LCD_3_5.LCD_3inch5()
    lcd.bl_ctrl(100)
    _thread.start_new_thread(network_thread, ())

    page = 0
    last_switch = time.time()

    C_WHITE = 0xFFFF
    C_RED = 0xF800
    C_GREEN = 0x07E0

    while True:
        with data_lock:
            nw = shared_data["net_worth"]
            ch = shared_data["change"]
            status = shared_data["market_status"]
            alloc = list(shared_data["allocation"])
            rsi = shared_data["rsi"]

        # Background & Limit Line
        draw_gradient_bg(lcd, 480, SAFE_HEIGHT)
        lcd.line(0, SAFE_HEIGHT, 480, SAFE_HEIGHT, C_RED)

        # Status Light
        s_col = 0x8410  # Gray
        if status == "OPEN":
            s_col = C_GREEN
        elif status == "AFTER-MKT":
            s_col = 0xFD20
        lcd.fill_rect(460, 5, 10, 5, s_col)

        # PAGE LOGIC
        if time.time() - last_switch > CYCLE_SPEED:
            page = 1 - page
            last_switch = time.time()

        if page == 0:
            # --- PAGE 1: THE EXECUTIVE SUMMARY ---
            lcd.text("NET LIQUIDITY", 10, 10, 0x8410)

            # Huge Value
            scale = 7 if len(nw) < 7 else 5
            draw_string(lcd, nw, 10, 30, C_WHITE, scale)

            # Allocation DNA Bar (The "Visual" Upgrade)
            draw_dna_bar(lcd, alloc, 10, 100, 460, 20)

            # Labels for DNA
            lcd.text("PORTFOLIO DNA ->", 10, 88, 0x07FF)

        else:
            # --- PAGE 2: THE QUANT DASHBOARD ---
            # Top Half: RSI Indicator
            draw_rsi_gauge(lcd, rsi, 10, 20, 220)

            # Bottom Half: Top Mover Card
            if alloc:
                top = alloc[0]  # Largest holding
                draw_card(lcd, 250, 10, 220, 110, 0x0000)  # Glass Card frame
                lcd.text("TOP HOLDING", 260, 20, 0xFFFF)
                draw_string(lcd, top["symbol"], 260, 40, C_GREEN, 4)
                lcd.text(f"Price: {top['price']}", 260, 80, 0xFFFF)
                lcd.text(f"Weight: {int(top['weight'] * 100)}%", 260, 95, 0x07FF)

        # Progress
        w = int(((time.time() - last_switch) / CYCLE_SPEED) * 480)
        lcd.line(0, SAFE_HEIGHT - 2, w, SAFE_HEIGHT - 2, 0x07FF)

        lcd.show_up()