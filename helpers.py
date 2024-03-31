import tkinter.font
FONTS = {}
WIDTH, HEIGHT, HSTEP, VSTEP, C, SCROLL_STEP = 800, 600, 13, 18, 0, 100
CHECKBOX_HEIGHT = 16
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]
ENTRIES = [
    ("no names. we are nameless!", "cerealkiller"),
    ("HACK THE PLANET!!!", "crashoverride"),
]




def get_font(size, weight, slant, family):
    key = (size, weight, slant, family)

    # If the font is not in the cache, create it and add it to the cache
    if key not in FONTS:
        font = tkinter.font.Font(size=size, weight=weight, slant=slant, family=family)
        label = tkinter.Label(font=font)
        FONTS[key] = (font, label)
    return FONTS[key][0]
