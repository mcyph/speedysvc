class ThreadedConsole:
    def __init__(self, OldFile):
        # Make sure long lines don't kill eclipse!
        self.OldFile = OldFile
        self.LPending = []
        import _thread
        _thread.start_new_thread(self.loop, ())

    def loop(self):
        while 1:
            i = 0
            while 1:
                if not self.LPending:
                    break
                try:
                    text = self.LPending[i]
                    i += 1
                except IndexError:
                    self.LPending = [] # THREADSAFE WARNING!
                    break

                if False:
                    while 1:
                        if len(text) > 100:
                            try: self.OldFile.write('%s\r\n' % text[:97].rstrip('\r\n'))
                            except: pass # WARNING!
                            #self.OldFile.write(text[:97])
                            text = text[97:]
                        else: break
                self.OldFile.write(text)
            time.sleep(0.05)

    def __getattr__(self, name):
        return getattr(self.OldFile, name)

    def write(self, text):
        self.LPending.append(text)


sys.stdout = DummyStdout(sys.stdout)
sys.stderr = DummyStdout(sys.stderr)
