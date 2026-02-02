import Pico_ResTouch_LCD_3_5
import time


def start():
    lcd = Pico_ResTouch_LCD_3_5.LCD_3inch5()
    lcd.bl_ctrl(100)
    lcd.fill(0x0000)  # Black background

    # Title
    lcd.text("NET WORTH", 10, 10, 0xFFFF)  # White

    # Value (Big Green Text)
    # Note: Default font is small. We will draw a box for now.
    lcd.fill_rect(10, 30, 200, 5, 0x07E0)  # Green Line
    lcd.text("$717,085", 10, 45, 0x07E0)

    lcd.text("Status: ONLINE", 10, 200, 0xFFFF)

    lcd.show_up()

    while True:
        time.sleep(1)