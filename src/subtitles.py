# =============================================================================
#                              DATA STRUCTURES
# =============================================================================

import time
import threading

class SubtitleState:
    # Stores subtitle lines shared by the network and Tk UI threads.
    # --------------------------------------------------------------------------
    # Access to mutable line state is protected by a lock so producers and
    # consumers see complete line-list changes.
    # --------------------------------------------------------------------------

    def __init__(self, max_lines: int = 12):
        # Initializes the bounded, thread-safe subtitle line buffer.
        # ----------------------------------------------------------------------
        # @param max_lines: Preferred maximum number of retained subtitle lines.
        # @return: None.
        # ----------------------------------------------------------------------
        # retain line metadata so the UI can distinguish the newest content.
        self.display_lines = []
        # serialize access between the streaming and UI threads.
        self.lock = threading.Lock()
        # retain the configured display capacity for trimming.
        self.max_lines = max_lines
    #end def


    def add(self, lines):
        # Appends formatted lines and marks them as the newest subtitle content.
        # ----------------------------------------------------------------------
        # @param lines: Formatted subtitle lines to append in display order.
        # @return: None.
        # ----------------------------------------------------------------------
        # update all line metadata atomically for the UI reader.
        with self.lock:
            # clear the newest marker before designating incoming lines as current.
            for l in self.display_lines: l['last'] = False

            # preserve creation time and newest-line styling for each addition.
            for line in lines: self.display_lines.append({'text':line, 'ts':time.time(), 'last':True})
            print(self.display_lines)
    #end def


    def clear_old(self):
        # Trims retained subtitle lines to the configured display capacity.
        # ----------------------------------------------------------------------
        # @return: None.
        # ----------------------------------------------------------------------
        # perform trimming while holding the same lock used by readers and writers.
        with self.lock:
            # discard an older batch when the line limit is exceeded.
            if (len(self.display_lines) > self.max_lines):
                while (len(self.display_lines) >= 4): del self.display_lines[0]
        #end with
    #end def


    def clear(self):
        # Removes all retained subtitle lines.
        # ----------------------------------------------------------------------
        # @return: None.
        # ----------------------------------------------------------------------
        # replace the list atomically so readers never observe a partial clear.
        with self.lock:
            self.display_lines = []
    #end def


    def displayed_text(self):
        # Returns retained subtitle lines as a newline-delimited string.
        # ----------------------------------------------------------------------
        # @return: Subtitle text in display order.
        # ----------------------------------------------------------------------
        # trim before rendering so stale lines do not reach the UI.
        text = ''
        self.clear_old()
        with self.lock:
            for line in self.display_lines:
                text += line['text'] + "\n"
        print("display>", text);
        return text;
    #end def

    def lines(self):
        # Returns a snapshot of retained subtitle line metadata.
        # ----------------------------------------------------------------------
        # @return: Independent list of line dictionaries in display order.
        # ----------------------------------------------------------------------
        # trim before copying so callers receive only displayable lines.
        text = []
        self.clear_old()
        with self.lock:
            for line in self.display_lines:
                text.append(line)
        return text;
    #end def

#end class


