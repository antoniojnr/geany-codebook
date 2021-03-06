import geany
import os
import hashlib
import json
import getpass
import socket

from difflib import Differ
from os.path import expanduser
from datetime import datetime
from socket import error as socket_error

class Codebook(geany.Plugin):

    __plugin_name__ = "Codebook"
    __plugin_version__ = "0.01"
    __plugin_description__ = "A plugin to collect code data."
    __plugin_author__ = "Antonio Dias <antonio.dias@ifpb.edu.br>"

    def __init__(self):
        geany.Plugin.__init__(self)
        user_path = expanduser("~")
        self.codebook_path = user_path + "/codebook"

        try:
            os.makedirs(self.codebook_path)
        except OSError:
            if not os.path.isdir(self.codebook_path):
                raise

        geany.signals.connect("document-open", self.on_open_document)
        geany.signals.connect("document-activate", self.on_open_document)
        geany.signals.connect("document-close", self.on_close_document)
        geany.signals.connect("editor-notify", self.on_editor_notify)

        self.prev_file = ""
        self.last_state = ""
        self.current_doc = ""
        self.events = {}
        
    def get_header(self, path):
        ip = "127.0.0.1"
        
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except socket_error:
            pass

        return {
            "user": getpass.getuser(),
            "host": socket.gethostname(),
            "ip": ip,
            "file": path
        }

    def get_filename_hash(self, path):
        return hashlib.md5(str(path).encode("utf-8")).hexdigest()

    def on_editor_notify(self, sigman, notification, c):
        current = geany.document.get_current().editor.scintilla
            
        if self.current_doc not in self.events:
            self.events[self.current_doc] = []

        cursor = current.get_current_position()
        pos = {
            "pos": cursor,
            "l": current.get_current_line(),
            "c": current.get_col_from_position(cursor)
        }
        
        if c.nmhdr.code != 2013:
            cur_changes = geany.document.get_current().editor.scintilla.get_contents()
            if self.last_state != cur_changes:
                diff = list(Differ().compare(self.last_state, cur_changes))
                event = self.diff_to_event(diff, pos)
                self.events[self.current_doc].append(event)
                if len(self.events[self.current_doc]) % 5 == 0:
                    self.save_events()
                    
            self.last_state = cur_changes

        return False

    def diff_to_event(self, diff, pos):
        striped = self.get_diff(diff)
        mod = ""

        for char in striped:
            mod += char[2]

        return {
            "v": mod, 
            "pos": pos, 
            "ac": "i" if striped[0][0] == "+" else "r",
            "ts": datetime.now().isoformat()
        }
        
    def get_diff(self, diff):
        return [s for s in diff if s[0] in ['+', '-', '?']]

    def on_open_document(self, sigmanager, doc):
        self.current_doc = self.get_filename_hash(doc.file_name)
        header_path = self.codebook_path + "/" + self.current_doc + ".header"
        data_path = self.codebook_path + "/" + self.current_doc + ".data"    
        
        if os.path.isfile(data_path):
            if self.current_doc not in self.events:
                self.events[self.current_doc] = []
            
            with open(data_path) as data_file:
                json_data = json.loads(data_file.read())
                self.events[self.current_doc] += json_data
        
        if not os.path.isfile(header_path):
            with open(header_path, "w") as header_file:
                json.dump(self.get_header(doc.file_name), header_file)
    
    def save_events(self):
        for k, v in self.events.iteritems():
			path = self.codebook_path + "/" + k + ".data"
			with open(path, "w") as f:
				json.dump(v, f)
                
    def on_close_document(self, sigmanager, doc):
        self.save_events()

    def cleanup(self):
        print("Plugin cleaning up")
