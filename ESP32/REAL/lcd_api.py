import time

class LcdApi:
    # Implements the API for talking with HD44780 compatible character LCDs.
    
    LCD_CLR             = 0x01
    LCD_HOME            = 0x02
    LCD_ENTRY_MODE      = 0x04
    LCD_CTRL            = 0x08
    LCD_CDSHIFT         = 0x10
    LCD_FUNCTION        = 0x20
    LCD_CGRAM           = 0x40
    LCD_DDRAM           = 0x80

    LCD_ENTRY_RIGHT     = 0x00
    LCD_ENTRY_LEFT      = 0x02
    LCD_ENTRY_SHIFT_INC = 0x01
    LCD_ENTRY_SHIFT_DEC = 0x00

    LCD_CTRL_DISPLAY_OFF= 0x00
    LCD_CTRL_DISPLAY_ON = 0x04
    LCD_CTRL_CURSOR_OFF = 0x00
    LCD_CTRL_CURSOR_ON  = 0x02
    LCD_CTRL_BLINK_OFF  = 0x00
    LCD_CTRL_BLINK_ON   = 0x01

    LCD_FUNCTION_4BIT   = 0x00
    LCD_FUNCTION_8BIT   = 0x10
    LCD_FUNCTION_1LINE  = 0x00
    LCD_FUNCTION_2LINES = 0x08
    LCD_FUNCTION_10DOTS = 0x04
    LCD_FUNCTION_8DOTS  = 0x00

    def __init__(self, num_lines, num_columns):
        self.num_lines = num_lines
        if self.num_lines > 4:
            self.num_lines = 4
        self.num_columns = num_columns
        if self.num_columns > 40:
            self.num_columns = 40
        self.cursor_x = 0
        self.cursor_y = 0
        self.impl_write = None
        self.display_off()
        self.backlight_on()
        self.clear()
        self.hal_write_command(self.LCD_ENTRY_MODE | self.LCD_ENTRY_LEFT)
        self.hide_cursor()
        self.display_on()

    def clear(self):
        self.hal_write_command(self.LCD_CLR)
        self.hal_write_command(self.LCD_HOME)
        self.cursor_x = 0
        self.cursor_y = 0

    def show_cursor(self):
        self.hal_write_command(self.LCD_CTRL | self.LCD_CTRL_DISPLAY_ON |
                               self.LCD_CTRL_CURSOR_ON)

    def hide_cursor(self):
        self.hal_write_command(self.LCD_CTRL | self.LCD_CTRL_DISPLAY_ON |
                               self.LCD_CTRL_CURSOR_OFF)

    def blink_cursor_on(self):
        self.hal_write_command(self.LCD_CTRL | self.LCD_CTRL_DISPLAY_ON |
                               self.LCD_CTRL_CURSOR_ON | self.LCD_CTRL_BLINK_ON)

    def blink_cursor_off(self):
        self.hal_write_command(self.LCD_CTRL | self.LCD_CTRL_DISPLAY_ON |
                               self.LCD_CTRL_CURSOR_ON | self.LCD_CTRL_BLINK_OFF)

    def display_on(self):
        self.hal_write_command(self.LCD_CTRL | self.LCD_CTRL_DISPLAY_ON)

    def display_off(self):
        self.hal_write_command(self.LCD_CTRL | self.LCD_CTRL_DISPLAY_OFF)

    def backlight_on(self):
        self.hal_backlight_on()

    def backlight_off(self):
        self.hal_backlight_off()

    def move_to(self, cursor_x, cursor_y):
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y
        addr = cursor_x & 0x3f
        if cursor_y & 1:
            addr += 0x40
        if cursor_y & 2:
            addr += self.num_columns
        self.hal_write_command(self.LCD_DDRAM | addr)

    def putchar(self, char):
        if char == '\n':
            if self.impl_write:
                self.impl_write(char)
            else:
                self.cursor_x = 0
                self.cursor_y += 1
                if self.cursor_y >= self.num_lines:
                    self.cursor_y = 0
                self.move_to(self.cursor_x, self.cursor_y)
        else:
            if self.impl_write:
                self.impl_write(char)
            else:
                self.hal_write_data(ord(char))
                self.cursor_x += 1
                if self.cursor_x >= self.num_columns:
                    self.cursor_x = 0
                    self.cursor_y += 1
                    if self.cursor_y >= self.num_lines:
                        self.cursor_y = 0
                    self.move_to(self.cursor_x, self.cursor_y)

    def putstr(self, string):
        for char in string:
            self.putchar(char)

    def hal_backlight_on(self):
        pass

    def hal_backlight_off(self):
        pass

    def hal_write_command(self, cmd):
        raise NotImplementedError

    def hal_write_data(self, data):
        raise NotImplementedError

    def hal_sleep_us(self, usecs):
        time.sleep_us(usecs)
