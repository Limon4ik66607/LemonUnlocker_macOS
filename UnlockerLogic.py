import os
import sys
import shutil
import subprocess
import time
import shlex  # ИСПРАВЛЕНО: Добавлен для правильного экранирования команд
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
            # ИСПРАВЛЕНО: Правильное экранирование аргументов для shell
            args = " ".join([shlex.quote(a) for a in sys.argv])
            
            # ИСПРАВЛЕНО: Правильное экранирование для AppleScript
            script = f'do shell script "{exe} {args}" with administrator privileges'
            
            # ИСПРАВЛЕНО: Используем список аргументов вместо shell=True для безопасности
            subprocess.run(['osascript', '-e', script], check=True)
            sys.exit(0)
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
            return False


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
        home = os.path.expanduser("~")
        apps_dir = os.path.join(home, "Applications")
        
        # ИСПРАВЛЕНО: Добавлена обработка ошибок создания директории
        if not os.path.exists(apps_dir):
            try:
                os.makedirs(apps_dir, exist_ok=True)
            except Exception as e:
                # Fallback to /Applications if user ~/Applications fails
                apps_dir = "/Applications"
                if not os.access(apps_dir, os.W_OK):
                    raise PermissionError(
                        "Cannot create unlocker app. No write access to:\n"
                        f"- {os.path.join(home, 'Applications')}\n"
                        f"- /Applications\n\n"
                        "Please grant Full Disk Access to LemonUnlocker in System Preferences."
                    )
        
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
        killed_processes = []
        processes_to_kill = ['EADesktop', 'EA Desktop', 'Origin']
        
        for proc_name in processes_to_kill:
            try:
                result = subprocess.run(
                    ['pkill', '-f', proc_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if result.returncode == 0:
                    killed_processes.append(proc_name)
                    logger.log(f"Killed process: {proc_name}")
            except Exception as e:
                logger.log(f"Could not kill {proc_name}: {e}", "WARNING")
        
        if killed_processes:
            logger.log(f"Terminated {len(killed_processes)} EA processes")
            time.sleep(1)

        base_dir = UnlockerManager.get_base_path()
        unlocker_src = os.path.join(base_dir, "unlocker_mac", "files")

        # ИСПРАВЛЕНО: Проверка существования директории с исходниками с fallback
        if not os.path.exists(unlocker_src):
            logger.log(f"Primary source path not found: {unlocker_src}", "WARNING")
            # Попробовать альтернативные пути
            alt_paths = [
                os.path.join(base_dir, "files"),
                os.path.join(base_dir, "unlocker_mac"),
                os.path.join(os.path.dirname(base_dir), "unlocker_mac", "files"),
                os.path.join(os.path.dirname(base_dir), "files")
            ]
            
            for alt in alt_paths:
                if os.path.exists(alt):
                    unlocker_src = alt
                    logger.log(f"Using alternative path: {unlocker_src}")
                    break
            
            if not os.path.exists(unlocker_src):
                return False, (
                    f"Unlocker source directory not found.\n\n"
                    f"Expected at: {os.path.join(base_dir, 'unlocker_mac', 'files')}\n\n"
                    f"Please ensure unlocker files are included in the app bundle."
                )

        # Verify source files exist
        required_files = ["unlocker", "anadius.dylib", "thesims4.cfg"]
        missing_files = []
        for fname in required_files:
            if not os.path.exists(os.path.join(unlocker_src, fname)):
                missing_files.append(fname)
        
        if missing_files:
            return False, f"Required files missing: {', '.join(missing_files)}\nSource: {unlocker_src}"

        # ИСПРАВЛЕНО: Обработка ошибок при получении пути к app
        try:
            app_path = UnlockerManager.get_unlocker_app_path()
        except PermissionError as e:
            return False, str(e)
        
        bundle_path = os.path.join(app_path, "Contents", "MacOS")

        try:
            # ИСПРАВЛЕНО: Create .app bundle structure с проверкой прав
            try:
                os.makedirs(bundle_path, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create app bundle directory (permission denied): {bundle_path}\n\n{str(e)}"

            # ИСПРАВЛЕНО: Проверка прав на запись
            if not os.access(bundle_path, os.W_OK):
                return False, (
                    f"No write permission to: {bundle_path}\n\n"
                    "Please grant Full Disk Access to LemonUnlocker in:\n"
                    "System Preferences → Security & Privacy → Privacy → Full Disk Access"
                )
            
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

            # ИСПРАВЛЕНО: Copy or create Info.plist
            plist_src = os.path.join(unlocker_src, "Info.plist")
            plist_dst = os.path.join(app_path, "Contents", "Info.plist")
            
            if os.path.exists(plist_src):
                shutil.copy2(plist_src, plist_dst)
                logger.log("Copied Info.plist")
            else:
                # Создаем минимальный Info.plist
                plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>unlocker</string>
    <key>CFBundleIdentifier</key>
    <string>com.lemon.dlcunlocker</string>
    <key>CFBundleName</key>
    <string>DLC Unlocker - The Sims 4</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
</dict>
</plist>"""
                with open(plist_dst, 'w') as f:
                    f.write(plist_content)
                logger.log("Created default Info.plist")
            
            # ИСПРАВЛЕНО: Copy icon if available
            icon_src = os.path.join(unlocker_src, "icon.icns")
            if os.path.exists(icon_src):
                resources_dir = os.path.join(app_path, "Contents", "Resources")
                os.makedirs(resources_dir, exist_ok=True)
                shutil.copy2(icon_src, os.path.join(resources_dir, "icon.icns"))
                logger.log("Copied app icon")

            # Remove quarantine attribute (macOS Gatekeeper)
            try:
                subprocess.run(
                    ['xattr', '-rc', app_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                logger.log("Removed quarantine attributes")
            except Exception as e:
                logger.log(f"Could not remove quarantine: {e}", "WARNING")

            return True, (
                "DLC Unlocker installed successfully!\n\n"
                "⚠️ IMPORTANT: You must run 'DLC Unlocker - The Sims 4' app\n"
                "from ~/Applications BEFORE launching the game each time!"
            )

        except Exception as e:
            logger.log(f"Installation failed: {str(e)}", "ERROR")
            return False, f"Installation failed: {str(e)}"

    @staticmethod
    def update_sims4_config(logger, game_path=None):
        """
        Update the Sims 4 config in the existing .app bundle.
        ИСПРАВЛЕНО: Теперь также добавляет путь к игре в конфиг.
        """
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
            
            # ИСПРАВЛЕНО: Добавить путь к игре если предоставлен
            if game_path:
                try:
                    # Если путь к .app, используем его
                    if game_path.endswith(".app"):
                        with open(dst_conf, 'a', encoding='utf-8') as f:
                            f.write(f"\n[Game]\n")
                            f.write(f"ExecutablePath={game_path}\n")
                        logger.log(f"Added game path to config: {game_path}")
                except Exception as e:
                    logger.log(f"Could not add game path: {e}", "WARNING")
            
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
        # ИСПРАВЛЕНО: Получаем путь к игре из конфига и передаем в update_sims4_config
        game_path = None
        try:
            from UnlockerLogic import ConfigManager
            config = ConfigManager()
            game_path = config.get("game_path")
        except:
            pass
        
        success, msg = UnlockerManager.update_sims4_config(self.parent_ui.logger, game_path)
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.critical(self, "Error", msg)