from config import Settings
from subtitles import SubtitleState


# =============================================================================
#                                UI WINDOW
# =============================================================================

class SubtitleWindow:
    # Owns the Tk window that renders live subtitle lines.
    # --------------------------------------------------------------------------
    # The window remains responsive because background workers update shared state
    # while all Tk operations remain on the Tk thread.
    # --------------------------------------------------------------------------

    def __init__(self, settings: Settings) -> None:
        # Creates and configures the subtitle window widgets.
        # ----------------------------------------------------------------------
        # @param settings: Validated UI configuration applied to Tk widgets.
        # @return: None.
        # ----------------------------------------------------------------------
        # import Tk lazily so non-UI modules can be loaded in headless contexts.
        import tkinter as tk

        # retain configuration for later layout and style updates.
        self.settings = settings

        # initialize the top-level window before adding child widgets.
        self.tk = tk.Tk()
        self.tk.title("Iris - Director's Assistant")

        # establish a usable fallback size before optional maximization.
        self.tk.geometry("600x300")

        # apply the configured user-resize policy.
        self.tk.resizable(self.settings.ui.window_resizable, self.settings.ui.window_resizable)

        # apply the configured background before creating text widgets.
        self.tk.configure(bg=self.settings.ui.window_background_color)

        if self.settings.ui.window_zoomed:
            # prefer native maximization and retain a platform-neutral fallback.
            try:
                self.tk.state("zoomed")
            except Exception:
                w = self.tk.winfo_screenwidth()
                h = self.tk.winfo_screenheight()
                self.tk.geometry(f"{w}x{h}+0+0")
            #end try

            # retain subtitle visibility when the configured overlay mode is enabled.
            if self.settings.ui.window_keep_on_top:
                self.tk.attributes("-topmost", True)
        #end if

        # bind common exit shortcuts to destroy the top-level window.
        self.tk.bind_all("<Escape>", lambda e: self.tk.destroy())
        self.tk.bind_all("<Control-c>", lambda e: self.tk.destroy())
        self.tk.bind_all("<Control-C>", lambda e: self.tk.destroy())

        # retain a Tk variable for compatibility with existing window state.
        self.var = tk.StringVar(value="")

        # create the styled text widget that renders subtitle snapshots.
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
        self.text.tag_configure("center", justify="center")

        # define tags that distinguish historical and newest subtitle lines.
        self.text.tag_configure("normal", foreground="white")
        self.text.tag_configure("last", foreground="yellow")
    #end def


    #def set_text(self, s: str) -> None:
    def set_text(self, lines) -> None:
        # Replaces the rendered subtitle content while preserving line styles.
        # ----------------------------------------------------------------------
        # @param lines: Snapshot of subtitle line dictionaries in display order.
        # @return: None.
        # ----------------------------------------------------------------------
        # enable edits only long enough to atomically replace the text widget content.
        
        self.text.config(state="normal")
        self.text.delete("1.0", "end")

        # retain an empty disabled widget when there is no subtitle content.
        if (len(lines)==0): return

        # apply the newest-line tag only to content marked current by shared state.
        for line in lines:
            if not line['last']: 
                self.text.insert("end", line['text'] + "\n", "center normal")
            else:
                self.text.insert("end", line['text'] + "\n", "center last")


        self.text.config(state="disabled")
    #end def


    def refresh_wraplength(self) -> None:
        # Recalculates text-widget width after the window changes size.
        # ----------------------------------------------------------------------
        # @return: None.
        # ----------------------------------------------------------------------
        # derive character capacity from available width while preserving padding.
        try:
            width = self.tk.winfo_width()
            # retain padding when converting pixel width into character capacity.
            self.text.configure(wrap="word")
            wrap_length = max(200, width - 2 * self.settings.ui.window_text_padding_x)
            self.text.configure(width=max(1, int(wrap_length / max(1, self.settings.ui.window_font_size / 2))))
        except Exception:
            pass
    #end def


    def run(self, subtitles: SubtitleState, interval_ms: int) -> None:
        # Runs the Tk event loop and periodically renders subtitle state.
        # ----------------------------------------------------------------------
        # @param subtitles: Thread-safe subtitle state read on each UI tick.
        # @param interval_ms: Delay between UI ticks in milliseconds.
        # @return: None.
        # ----------------------------------------------------------------------

        def ui_tick() -> None:
            # Renders a fresh subtitle snapshot and schedules the next UI update.
            # ------------------------------------------------------------------
            # @return: None.
            # ------------------------------------------------------------------
            # update wrapping before reading lines so resize changes apply immediately.
            self.refresh_wraplength()

            # render the current thread-safe line snapshot without blocking Tk.
            self.set_text(subtitles.lines())

            # stop scheduling work after the window has been destroyed.
            if self.tk.winfo_exists():
                self.tk.after(interval_ms, ui_tick)
        #end def


        self.tk.after(interval_ms, ui_tick)
        self.tk.mainloop()
    #end def
#end class
