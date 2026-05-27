# =============================================================================
#                              DATA STRUCTURES
# =============================================================================

import time
import threading

class SubtitleState:
    """
    Shared state between:
      - network thread (receives tokens, updates buffers)
      - UI thread (reads current text, decides whether to clear)

    Note: this is intentionally simple; we rely on the GIL and "replace whole string"
    style updates. For heavy concurrency you'd add a lock, but for this pattern it
    is typically fine.
    """

    def __init__(self, max_lines: int = 12):
        self.display_lines = []
        self.lock = threading.Lock()
        self.max_lines = max_lines
    #end def


    def add(self, lines):
        with self.lock:
            for l in self.display_lines: l['last'] = False

            #self.display_lines = []
            for line in lines: self.display_lines.append({'text':line, 'ts':time.time(), 'last':True})
            print(self.display_lines)
    #end def


    def clear_old(self):
        with self.lock:
            '''
            while (len(self.display_lines) > 0):
                if (self.display_lines[0]['ts']+10.0 < time.time()): 
                    del self.display_lines[0]
                else:
                    return
            while (len(self.display_lines) > params.MAX_LINES_ON_SCREEN):
                del self.display_lines[0]
            #end while
            '''
            if (len(self.display_lines) > self.max_lines):
                while (len(self.display_lines) >= 4): del self.display_lines[0]
        #end with
    #end def


    def clear(self):
        with self.lock:
            self.display_lines = []
    #end def


    def displayed_text(self):
        text = ''
        self.clear_old()
        with self.lock:
            for line in self.display_lines:
                text += line['text'] + "\n"
        print("display>", text);
        return text;
    #end def

    def lines(self):
        text = []
        self.clear_old()
        with self.lock:
            for line in self.display_lines:
                text.append(line)
        return text;
    #end def

#end class



