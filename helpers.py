import tkinter.font
FONTS = {}
WIDTH, HEIGHT, HSTEP, VSTEP, C, SCROLL_STEP = 800, 600, 13, 18, 0, 100
CHECKBOX_HEIGHT = 16

def get_font(size, weight, slant, family):
    key = (size, weight, slant, family)

    # If the font is not in the cache, create it and add it to the cache
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=slant, family=family)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]
