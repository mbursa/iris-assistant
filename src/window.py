import time

from config import Settings
from subtitles import SubtitleState


# =============================================================================
#                                UI WINDOW
# =============================================================================

class SubtitleWindow:
    """
    A simple Tkinter window that is:
      - a normal window (not "fullscreen" exclusive mode)
      - maximized over the screen
      - shows large centered text over a blank background
    """

    def __init__(self, settings: Settings) -> None:
        import tkinter as tk

        self.settings = settings

        self.tk = tk.Tk()
        self.tk.title("Iris - Director's Assistant")

        # initial small window size (width x height)
        self.tk.geometry("600x300")

        # allow resizing (you can set False to lock it)
        self.tk.resizable(self.settings.ui.window_resizable, self.settings.ui.window_resizable)

        # background
        self.tk.configure(bg=self.settings.ui.window_background_color)

        if self.settings.ui.window_zoomed:
            # "Maximized" window behavior on Windows:
            # - state('zoomed') works on Windows Tk builds
            # - fallback: geometry to screen size if zoomed fails
            try:
                self.tk.state("zoomed")
            except Exception:
                w = self.tk.winfo_screenwidth()
                h = self.tk.winfo_screenheight()
                self.tk.geometry(f"{w}x{h}+0+0")
            #end try

            # keep it on top (subtitle style)
            if self.settings.ui.window_keep_on_top:
                self.tk.attributes("-topmost", True)
        #end if

        # escape to quit quickly on ESC or Ctrl+C
        self.tk.bind_all("<Escape>", lambda e: self.tk.destroy())
        self.tk.bind_all("<Control-c>", lambda e: self.tk.destroy())
        self.tk.bind_all("<Control-C>", lambda e: self.tk.destroy())

        self.var = tk.StringVar(value="")

        self.text = tk.Text(
            self.tk,
            bg=self.settings.ui.window_background_color,
            fg=self.settings.ui.window_text_color,
            font=(
                self.settings.ui.window_font_family,
                self.settings.ui.window_font_size,
                self.settings.ui.window_font_weight,
            ),
            wrap="word",
            height=5,
            borderwidth=0,
            highlightthickness=0,
        )
        self.text.pack(
            expand=True,
            fill="both",
            padx=self.settings.ui.window_text_padding_x,
            pady=self.settings.ui.window_text_padding_y,
        )
        #text.pack(expand=True, fill="both")
        self.text.tag_configure("center", justify="center")

        # define styles
        self.text.tag_configure("normal", foreground="white")
        self.text.tag_configure("last", foreground="yellow")
    #end def


    #def set_text(self, s: str) -> None:
    def set_text(self, lines) -> None:
        """Replace the currently displayed subtitle text."""
        #self.var.set(s)
        
        self.text.config(state="normal")
        self.text.delete("1.0", "end")

        if (len(lines)==0): return

        for line in lines:
            if not line['last']: 
                self.text.insert("end", line['text'] + "\n", "center normal")
            else:
                self.text.insert("end", line['text'] + "\n", "center last")


        self.text.config(state="disabled")
    #end def


    def refresh_wraplength(self) -> None:
        """
        Update wrap length dynamically so the label wraps nicely if the window is resized.
        """
        try:
            width = self.tk.winfo_width()
            # keep a margin for padding; this affects wrapping aesthetics
            self.text.configure(wrap="word")
            wrap_length = max(200, width - 2 * self.settings.ui.window_text_padding_x)
            self.text.configure(width=max(1, int(wrap_length / max(1, self.settings.ui.window_font_size / 2))))
        except Exception:
            pass
    #end def


    def run(self, subtitles: SubtitleState, interval_ms: int) -> None:
        """
        Run the Tkinter main loop and call tick_fn periodically.
        tick_fn must not block; it should be a quick subtitles read and UI update.
        """

        def ui_tick() -> None:
            """
            Runs on the Tk thread periodically.
            - Applies current text.
            - Clears subtitles after a few seconds of "no new final translation tokens".
            """
            self.refresh_wraplength()

            now = time.time()

            ## clear display if it's been quiet for too long
            #if (now - state.last_display_update_ts) > params.CLEAR_SUBTITLES_AFTER_SECONDS:
            #    subtitles.clear()
            #    self.set_text("")
            #else: 
            #    # otherwise show whatever the state currently holds
            #    self.set_text(state.display_text)
            ##end if

            #self.set_text(subtitles.displayed_text())

            '''
            # Make sure layout/wrapping has been computed
            self.text.update_idletasks()
            # Count displaylines between 1.0 and end-1c
            disp_lines = self.text.count("1.0", "end-1c", "displaylines")
            if (disp_lines == None): 
                disp_lines = 0 
            else:
                disp_lines = int(disp_lines[0])
            print('disp_lines',disp_lines)
            self.set_text(subtitles.lines(disp_lines))
            '''
            self.set_text(subtitles.lines())

            if self.tk.winfo_exists():
                self.tk.after(interval_ms, ui_tick)
        #end def


        self.tk.after(interval_ms, ui_tick)
        self.tk.mainloop()
    #end def
#end class
