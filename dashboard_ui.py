import Pico_ResTouch_LCD_3_5
import time
import framebuf
import urequests
import json
import gc
import secrets
import _thread

# --- CONFIGURATION ---
BASE_URL = "https://script.google.com/macros/s/AKfycbzmS90JXXehedhyzJingavVNn2IxAdfKGlQTyFq_FkeRxYsE3hbkMaef7ewlZozl_F9/exec"
DATA_URL = BASE_URL + "?key=" + secrets.GOOGLE_KEY

SAFE_HEIGHT = 140  # Limit drawing to top half
CYCLE_SPEED = 6  # Seconds per page
UPDATE_INTERVAL = 60  # Check for new data every minute

# --- GLOBAL SHARED DATA ---
shared_data = {
    "net_worth": "Loading...",
    "change": "...",
    "market_status": "CLOSED",
    "history": [],
    "assets": []
}
data_lock = _thread.allocate_lock()


# --- CORE 1: NETWORK WORKER ---
def network_thread():
    while True:
        try:
            response = urequests.get(DATA_URL)
            if response.status_code == 200:
                new_data = json.loads(response.text)
                response.close()
                with data_lock:
                    shared_data["net_worth"] = new_data.get("net_worth", "Error")
                    shared_data["change"] = new_data.get("change", "0%")
                    shared_data["market_status"] = new_data.get("market_status", "CLOSED")
                    shared_data["history"] = new_data.get("history", [])
                    shared_data["assets"] = new_data.get("assets", [])
            else:
                response.close()
        except Exception as e:
            print("Network Error:", e)

        time.sleep(UPDATE_INTERVAL)

    # --- GRAPHICS ENGINE ---


def draw_gradient_bg(lcd, width, height):
    # Renders a 'Bloomberg' Navy Blue Gradient
    # Top: Black (0x0000) -> Bottom: Deep Blue (0x0010)
    for y in range(height):
        # We use a bitwise trick to get a blue gradient
        # 5-6-5 RGB: Blue is the last 5 bits.
        # We scale y to fit 0-31 range for blue intensity
        intensity = int((y / height) * 20)
        lcd.line(0, y, width, y, intensity)


def draw_filled_chart(lcd, data, x, y, w, h, line_color, fill_color):
    if not data or len(data) < 2: return

    max_val = max(data)
    min_val = min(data)
    range_val = max_val - min_val if max_val != min_val else 1

    step_x = w / (len(data) - 1)

    # Calculate points
    points = []
    for i in range(len(data)):
        px = int(x + (i * step_x))
        # Invert Y (Screen Y grows down)
        py = int(y + h - ((data[i] - min_val) / range_val * h))
        if py > SAFE_HEIGHT: py = SAFE_HEIGHT
        points.append((px, py))

    # 1. Draw Fill (Vertical columns)
    for i in range(len(points) - 1):
        x_start = points[i][0]
        x_end = points[i + 1][0]

        # Simple interpolation for fill
        for curr_x in range(x_start, x_end):
            # Calculate Y at this X
            ratio = (curr_x - x_start) / (x_end - x_start) if (x_end - x_start) != 0 else 0
            curr_y = int(points[i][1] + (points[i + 1][1] - points[i][1]) * ratio)

            # Draw vertical line from curve down to bottom axis
            if curr_y < y + h:
                lcd.line(curr_x, curr_y, curr_x, y + h, fill_color)

    # 2. Draw Line on top
    for i in range(len(points) - 1):
        lcd.line(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1], line_color)
        # Bold effect
        lcd.line(points[i][0], points[i][1] - 1, points[i + 1][0], points[i + 1][1] - 1, line_color)


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

    # Launch Network Thread
    _thread.start_new_thread(network_thread, ())

    page = 0
    sub_page = 0
    last_switch = time.time()

    # Colors
    C_WHITE = 0xFFFF
    C_GREEN = 0x07E0
    C_RED = 0xF800
    C_CYAN = 0x07FF
    C_ORANGE = 0xFD20
    C_GRAY = 0x8410
    C_FILL = 0x0016  # Dark blue for chart fill

    while True:
        # 1. READ DATA SAFELY
        with data_lock:
            nw = shared_data["net_worth"]
            ch = shared_data["change"]
            status = shared_data["market_status"]
            hist = list(shared_data["history"])
            assets = list(shared_data["assets"])

        # 2. DRAW BACKGROUND
        draw_gradient_bg(lcd, 480, SAFE_HEIGHT)
        lcd.line(0, SAFE_HEIGHT, 480, SAFE_HEIGHT, C_RED)  # Limit line

        # 3. DRAW MARKET STATUS LIGHT
        # Top Right Corner
        status_color = C_GRAY
        if status == "OPEN":
            status_color = C_GREEN
        elif status == "AFTER-MKT":
            status_color = C_ORANGE

        # Draw "LED"
        lcd.fill_rect(460, 10, 8, 8, status_color)

        # 4. RENDER PAGE
        elapsed = time.time() - last_switch
        if elapsed > CYCLE_SPEED:
            page += 1
            if page > 1: page = 0
            if page == 1 and assets:
                sub_page = (sub_page + 1) % len(assets)
            last_switch = time.time()

        if page == 0:
            # --- HOME: NET WORTH ---
            draw_filled_chart(lcd, hist, 0, 40, 480, SAFE_HEIGHT - 40, C_CYAN, C_FILL)

            lcd.text("TOTAL EQUITY", 10, 10, C_GRAY)

            # Auto-scale text
            scale = 6
            if len(nw) > 8: scale = 5

            # Value
            draw_string(lcd, nw, 10, 30, C_WHITE, scale)

            # Change (Green or Red)
            ch_color = C_RED if "-" in str(ch) else C_GREEN
            lcd.text(f"Day: {ch}", 15, 90, ch_color)

        else:
            # --- ASSETS: TOP MOVERS ---
            if not assets:
                lcd.text("Fetching Assets...", 20, 60, C_WHITE)
            else:
                asset = assets[sub_page]
                sym = asset["symbol"]
                price = asset["price"]
                raw_pct = asset["raw_pct"]  # e.g., 0.69 or -4

                # Format Percentage correctly
                pct_str = "{:.2f}%".format(raw_pct)
                if raw_pct > 0: pct_str = "+" + pct_str

                col = C_GREEN if raw_pct >= 0 else C_RED

                lcd.text(f"TOP MOVER ({sub_page + 1}/{len(assets)})", 10, 10, C_GRAY)

                # Ticker
                draw_string(lcd, sym, 10, 30, C_WHITE, 7)

                # Price box
                lcd.fill_rect(280, 40, 140, 50, col)
                lcd.text(pct_str, 290, 55, 0x0000)  # Black text
                lcd.text(str(price), 290, 70, 0x0000)

        # 5. PROGRESS BAR
        bw = int((elapsed / CYCLE_SPEED) * 480)
        lcd.line(0, SAFE_HEIGHT - 2, bw, SAFE_HEIGHT - 2, C_CYAN)

        lcd.show_up()
        # No sleep needed (Core 0 runs UI as fast as possible)