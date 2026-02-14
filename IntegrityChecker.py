import os
import hashlib
import json
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class IntegrityManager(QObject):
    # Signal to report progress/status: (dlc_id, status_code)
    # Status Codes:
    # 0: OK
    # 1: MISSING_FILES
    # 2: CORRUPTED (Hash Mismatch)
    # 3: UNKNOWN (No hash data)
    # 4: CHECKING (In progress)
    status_signal = pyqtSignal(str, int)
    
    def __init__(self, game_path):
        super().__init__()
        self.game_path = game_path
        self.integrity_db = {} 
        # Future: Load from integrity.json
        # self.load_database()

    def load_database(self):
        try:
            with open("integrity.json", "r") as f:
                self.integrity_db = json.load(f)
        except:
            self.integrity_db = {}

    def get_file_hash(self, file_path):
        """Calculates MD5 hash of a file."""
        if not os.path.exists(file_path):
            return None
        
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return None

    def check_dlc(self, dlc_id, dlc_name):
        """
        Checks integrity of a specific DLC.
        Currently performs a BASIC check (Folder exists & not empty).
        Future: Will compare against self.integrity_db.
        """
        # Determine folder name (EP01, GP05, etc. or Name based)
        # Note: In our system, installed folders usually match the dlc_id (e.g. "EP01", "GP01")
        # unless user renamed them. We assume robust installation standard.
        
        target_path = os.path.join(self.game_path, dlc_id)
        
        if not os.path.exists(target_path):
            self.status_signal.emit(dlc_id, 1) # Missing
            return 1
            
        # Basic Check: Is folder empty?
        files = os.listdir(target_path)
        if not files:
            self.status_signal.emit(dlc_id, 1) # Missing/Empty
            return 1
            
        # MD5 Check (if DB exists)
        if dlc_id in self.integrity_db:
             expected_files = self.integrity_db[dlc_id]["files"]
             for fname, expected_hash in expected_files.items():
                 fpath = os.path.join(target_path, fname)
                 if not os.path.exists(fpath):
                     self.status_signal.emit(dlc_id, 2) # Corrupted (Missing specific file)
                     return 2
                 
                 # Full hash check (can be slow, maybe optional?)
                 real_hash = self.get_file_hash(fpath)
                 if real_hash != expected_hash:
                     self.status_signal.emit(dlc_id, 2) # Corrupted
                     return 2
        
        # If we got here and have no DB, assume OK for now if folder exists
        self.status_signal.emit(dlc_id, 0) # OK
        return 0

class IntegrityWorker(QThread):
    def __init__(self, manager, dlc_list):
        super().__init__()
        self.manager = manager
        self.dlc_list = dlc_list # List of (id, name) tuples
        self._is_running = True

    def run(self):
        for dlc_id, dlc_name in self.dlc_list:
            if not self._is_running:
                break
            # Report "Checking"
            self.manager.status_signal.emit(dlc_id, 4) 
            # Perform check
            self.manager.check_dlc(dlc_id, dlc_name)
            
    def stop(self):
        self._is_running = False
