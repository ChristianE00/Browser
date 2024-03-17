from helpers import WIDTH, HEIGHT, HSTEP, VSTEP, C, SCROLL_STEP

class Tab:
    def draw(self, canvas):
        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll, self.canvas)

    def scrolldown(self, delta):
        """Scroll down by SCROLL_STEP pixels."""
        # Default for Windows and Linux, divide by 120 for MacOS omegalul a single ternary
        '''
        delta = (
            e.delta / 120
            if hasattr(e, "delta")
            and e.delta is not None
            and platform.system() == "Darwin"
            else e.delta if hasattr(e, "delta") else None
        )
        '''
        # Mouse wheel down. On Windows, e.delta < 0 => scroll down.
        # NOTE: on Windows delta is positive for scroll up. On MacOS divid delta by 120
        #      On Linux you need to use differenct events to scroll up and scroll down
        # Scroll up
        '''
        if (delta is not None and delta > 0) or (
            hasattr(e, "keysym") and e.keysym == "Up"
        ):
        '''
        if delta > 0:
            if self.scroll > 0:
                self.scroll -= SCROLL_STEP
                #self.draw()
        else:
            max_y = max(self.document.height + 2 * VSTEP - HEIGHT, 0)
            self.scroll = min(self.scroll + SCROLL_STEP, max_y)
            #self.draw()
