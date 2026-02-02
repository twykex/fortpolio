import Pico_ResTouch_LCD_3_5
import time
import framebuf


# --- GRAPHICS HELPERS ---
def draw_large_text(lcd, text, x, y, size, color):
    # This is a "hack" to draw big text by drawing rectangles for every pixel
    # It is slow, but fine for a dashboard that doesn't move much
    for char_index, char in enumerate(text):
        # Get the 8x8 bitmap for this character from the built-in font
        # (This relies on standard framebuffer font data typically not exposed easily
        # so we will use a simpler "Pixel Doubling" approach if getting font data is hard.
        # actually, simply drawing the text to a tiny buffer and blowing it up is easier)
        pass

        # SIMPLER APPROACH FOR NOW: Just draw standard text multiple times slightly offset
    # to create a "Bold" effect, until we add a proper font library.
    lcd.text(text, x, y, color)
    lcd.text(text, x + 1, y, color)
    lcd.text(text, x, y + 1, color)
    lcd.text(text, x + 1, y + 1, color)


def draw_chart(lcd, data, x, y, w, h, color):
    # Draws a simple line chart from a list of numbers
    lcd.rect(x, y, w, h, color)  # Border

    if not data:
        return

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

    # Mock Data for the chart (Next we will fetch this from Google Sheets)
    history_data = [710, 712, 708, 715, 716, 717]

    current_screen = 0  # 0 = Summary, 1 = Graph

    while True:
        # 1. Check for Touch
        touch = lcd.touch_get()
        if touch:
            # Simple "Debounce" - wait a bit so it doesn't flicker
            current_screen = 1 - current_screen  # Toggle between 0 and 1
            lcd.fill(0x0000)  # Clear screen on switch
            time.sleep(0.5)

        # 2. Draw Screen
        if current_screen == 0:
            # --- SUMMARY PAGE ---
            # Clear top area only to reduce flicker
            lcd.fill_rect(0, 0, 480, 320, 0x0000)

            lcd.text("TOTAL NET WORTH", 20, 20, 0xFFFF)

            # Draw a box to simulate "Big Text" area
            lcd.fill_rect(20, 50, 5, 40, 0x07E0)  # Decorative bar
            lcd.text("$717,085", 40, 60, 0x07E0)  # Green
            lcd.text("+$6,200 (Today)", 40, 80, 0xFFFF)  # White

            lcd.text("Tap screen for charts ->", 200, 280, 0x001F)  # Blue

        else:
            # --- CHART PAGE ---
            lcd.fill_rect(0, 0, 480, 320, 0x0000)
            lcd.text("7-DAY PERFORMANCE", 20, 20, 0xFFFF)

            draw_chart(lcd, history_data, 40, 60, 400, 200, 0xFFFF)

            lcd.text("<- Tap to back", 20, 280, 0x001F)

        # 3. Update Display
        lcd.show_up()

        # Wait a bit before next loop to save power/cpu
        # (But check touch more often)
        for i in range(10):
            touch_check = lcd.touch_get()
            if touch_check:
                break  # Break wait loop if touched
            time.sleep(0.1)