import os
import sys
import shutil
import subprocess
import time
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtCore import Qt


class AdminElevator:
    """macOS admin helper — uses osascript for privilege escalation."""

    @staticmethod
    def is_admin():
        try:
            return os.geteuid() == 0
        except AttributeError:
            return False

    @staticmethod
    def requires_admin(path):
        try:
            test_file = os.path.join(path, ".test_write")
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            return False
        except:
            return True

    @staticmethod
    def elevate():
        """Re-launch current script with admin via osascript (AppleScript)."""
        try:
            exe = sys.executable
            args = " ".join([f'"{a}"' for a in sys.argv])
            cmd = f'osascript -e \'do shell script "{exe} {args}" with administrator privileges\''
            subprocess.Popen(cmd, shell=True)
            sys.exit(0)
        except Exception as e:
            pass


class UnlockerManager:
    """
    macOS Unlocker Manager.
    
    On Mac the DLC Unlocker works differently from Windows:
    - Instead of copying version.dll, we create a .app bundle
      (DLC Unlocker - The Sims 4.app) with the unlocker binary,
      dylibs and config files.
    - The user must run the DLC Unlocker app BEFORE launching the game
      each time they want to play.
    """

    @staticmethod
    def get_base_path():
        """Return the base path where bundled data files live."""
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def get_unlocker_app_path():
        """Return the path where we'll create the DLC Unlocker .app bundle."""
        # Place it in ~/Applications or next to our app
        home = os.path.expanduser("~")
        apps_dir = os.path.join(home, "Applications")
        if not os.path.exists(apps_dir):
            os.makedirs(apps_dir, exist_ok=True)
        return os.path.join(apps_dir, "DLC Unlocker - The Sims 4.app")

    @staticmethod
    def check_status():
        """Check if the DLC Unlocker .app bundle exists."""
        app_path = UnlockerManager.get_unlocker_app_path()
        unlocker_bin = os.path.join(app_path, "Contents", "MacOS", "unlocker")
        return os.path.exists(unlocker_bin)

    @staticmethod
    def install_ea_unlocker(logger):
        """
        Create the DLC Unlocker .app bundle for The Sims 4.
        This replicates what 'prepare DLC Unlockers' bash script does.
        """
        # Kill EA processes first
        try:
            subprocess.run(['pkill', '-f', 'EADesktop'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'EA Desktop'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'Origin'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
        except:
            pass

        base_dir = UnlockerManager.get_base_path()
        unlocker_src = os.path.join(base_dir, "unlocker_mac", "files")

        # Verify source files exist
        required_files = ["unlocker", "anadius.dylib", "thesims4.cfg", "Info.plist"]
        for fname in required_files:
            if not os.path.exists(os.path.join(unlocker_src, fname)):
                return False, f"Source file not found: {fname}"

        app_path = UnlockerManager.get_unlocker_app_path()
        bundle_path = os.path.join(app_path, "Contents", "MacOS")

        try:
            # Create .app bundle structure
            os.makedirs(bundle_path, exist_ok=True)
            logger.log(f"Creating .app bundle at: {app_path}")

            # Copy unlocker binary
            src = os.path.join(unlocker_src, "unlocker")
            dst = os.path.join(bundle_path, "unlocker")
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)  # Make executable
            logger.log("Copied unlocker binary")

            # Copy anadius.dylib
            shutil.copy2(
                os.path.join(unlocker_src, "anadius.dylib"),
                os.path.join(bundle_path, "anadius.dylib")
            )
            logger.log("Copied anadius.dylib")

            # Copy optional dylibs
            for dylib in ["anadius_online.dylib", "ts4_config_update.dylib"]:
                src_dylib = os.path.join(unlocker_src, dylib)
                if os.path.exists(src_dylib):
                    shutil.copy2(src_dylib, os.path.join(bundle_path, dylib))
                    logger.log(f"Copied {dylib}")

            # Copy config: thesims4.cfg -> anadius.cfg
            shutil.copy2(
                os.path.join(unlocker_src, "thesims4.cfg"),
                os.path.join(bundle_path, "anadius.cfg")
            )
            logger.log("Copied config (thesims4.cfg -> anadius.cfg)")

            # Copy override config: thesims4override.cfg -> anadius_override.cfg
            override_src = os.path.join(unlocker_src, "thesims4override.cfg")
            if os.path.exists(override_src):
                shutil.copy2(override_src, os.path.join(bundle_path, "anadius_override.cfg"))
                logger.log("Copied override config")

            # Copy Info.plist
            plist_dst = os.path.join(app_path, "Contents", "Info.plist")
            shutil.copy2(os.path.join(unlocker_src, "Info.plist"), plist_dst)
            logger.log("Copied Info.plist")

            # Remove quarantine attribute (macOS Gatekeeper)
            try:
                subprocess.run(
                    ['xattr', '-rc', app_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                logger.log("Removed quarantine attributes")
            except:
                pass

            return True, (
                "DLC Unlocker installed successfully!\n\n"
                "⚠️ IMPORTANT: You must run 'DLC Unlocker - The Sims 4' app\n"
                "from ~/Applications BEFORE launching the game each time!"
            )

        except Exception as e:
            return False, str(e)

    @staticmethod
    def update_sims4_config(logger):
        """Update the Sims 4 config in the existing .app bundle."""
        base_dir = UnlockerManager.get_base_path()
        unlocker_src = os.path.join(base_dir, "unlocker_mac", "files")
        
        src_conf = os.path.join(unlocker_src, "thesims4.cfg")
        if not os.path.exists(src_conf):
            return False, "Source thesims4.cfg not found"

        app_path = UnlockerManager.get_unlocker_app_path()
        bundle_path = os.path.join(app_path, "Contents", "MacOS")
        
        if not os.path.exists(bundle_path):
            return False, "DLC Unlocker not installed. Install it first."

        dst_conf = os.path.join(bundle_path, "anadius.cfg")
        try:
            shutil.copy2(src_conf, dst_conf)
            logger.log(f"Updated config: {dst_conf}")
            
            # Also update override config if available
            override_src = os.path.join(unlocker_src, "thesims4override.cfg")
            if os.path.exists(override_src):
                shutil.copy2(override_src, os.path.join(bundle_path, "anadius_override.cfg"))
                logger.log("Updated override config")
            
            return True, "Sims 4 Config updated successfully!"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def uninstall_ea_unlocker(logger):
        """Remove the DLC Unlocker .app bundle."""
        # Kill processes first
        try:
            subprocess.run(['pkill', '-f', 'EADesktop'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'EA Desktop'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'Origin'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(['pkill', '-f', 'unlocker'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1)
        except:
            pass

        app_path = UnlockerManager.get_unlocker_app_path()
        if not os.path.exists(app_path):
            return True, "DLC Unlocker was not installed."

        try:
            shutil.rmtree(app_path)
            logger.log(f"Removed {app_path}")
            return True, "DLC Unlocker uninstalled successfully."
        except Exception as e:
            return False, f"Failed to uninstall: {str(e)}"


class UnlockerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DLC Unlocker Manager")
        self.setFixedSize(400, 280)
        self.parent_ui = parent
        self.setup_ui()
        self.setStyleSheet(
            "QDialog{background-color:#1e1e1e;}"
            "QLabel{color:white;}"
            "QPushButton{background-color:#ffd700;color:black;border:none;"
            "padding:10px;font-weight:bold;border-radius:4px;}"
            "QPushButton:hover{background-color:#ffed4a;}"
        )

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        header = QLabel("Lemon Unlocker Manager (macOS)")
        header.setStyleSheet("font-size:16px;font-weight:bold;color:#ffd700;margin-bottom:10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        btn_install = QPushButton("1. Install DLC Unlocker (Creates .app)")
        btn_install.clicked.connect(self.install_unlocker)
        layout.addWidget(btn_install)

        btn_config = QPushButton("2. Update Sims 4 Config")
        btn_config.clicked.connect(self.update_config)
        layout.addWidget(btn_config)

        info = QLabel(
            "Use Option 1 to create the DLC Unlocker app.\n"
            "Use Option 2 to update configs after new DLCs.\n\n"
            "⚠️ Run DLC Unlocker BEFORE launching the game!"
        )
        info.setStyleSheet("color:#aaa;font-size:11px;text-align:center;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

    def install_unlocker(self):
        success, msg = UnlockerManager.install_ea_unlocker(self.parent_ui.logger)
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.critical(self, "Error", msg)

    def update_config(self):
        success, msg = UnlockerManager.update_sims4_config(self.parent_ui.logger)
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.critical(self, "Error", msg)
