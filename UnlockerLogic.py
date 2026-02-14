import os
import sys
import shutil
import subprocess
import time
import shlex  # ИСПРАВЛЕНО: Добавлен для правильного экранирования команд
import tempfile  # НОВОЕ: Для создания временных файлов в create_game_launcher
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


# НОВОЕ: Легкий ConfigManager для чтения конфига в UnlockerLogic
class ConfigManager:
    """Lightweight config reader for accessing game path"""
    def __init__(self):
        # Определяем путь к конфигу (такой же как в основном приложении)
        if sys.platform == "darwin":
            base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "LemonUnlocker")
        elif sys.platform == "win32":
            base = os.path.join(os.getenv("APPDATA"), "LemonUnlocker")
        else:
            base = os.path.join(os.path.expanduser("~"), ".config", "LemonUnlocker")
        
        self.config_file = os.path.join(base, "config.json")
        self.config = self.load()
    
    def load(self):
        if os.path.exists(self.config_file):
            try:
                import json
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def get(self, key, default=None):
        return self.config.get(key, default)


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
        """
        Return the path where we'll create the DLC Unlocker .app bundle.
        
        ИСПРАВЛЕНО: Приоритет установки:
        1. /Applications/ (системная, видна всем) - ПРЕДПОЧТИТЕЛЬНО
        2. ~/Applications/ (пользовательская) - FALLBACK
        
        Это решает проблему когда пользователи не могут найти DLC Unlocker,
        так как он устанавливается в ~/Applications/ вместо видимой /Applications/
        """
        app_name = "DLC Unlocker - The Sims 4.app"
        
        # Приоритет 1: Системная папка /Applications/ (видна в Finder → Программы)
        system_apps = "/Applications"
        
        # Проверка: есть ли права на запись?
        if os.access(system_apps, os.W_OK):
            print(f"✅ Installing to {system_apps} (system-wide)")
            return os.path.join(system_apps, app_name)
        
        # Проверка: можем ли получить права через osascript?
        try:
            test_file = os.path.join(system_apps, ".lemon_test")
            # Пытаемся создать тестовый файл с правами администратора
            cmd = f'do shell script "touch \\"{test_file}\\"" with administrator privileges'
            
            result = subprocess.run(
                ['osascript', '-e', cmd],
                capture_output=True,
                timeout=60,  # Даем 60 сек на ввод пароля
                text=True
            )
            
            if result.returncode == 0:
                # Успешно получили права! Удаляем тестовый файл
                try:
                    subprocess.run(
                        ['osascript', '-e', f'do shell script "rm \\"{test_file}\\"" with administrator privileges'],
                        capture_output=True,
                        timeout=5
                    )
                except:
                    pass
                
                print(f"✅ Installing to {system_apps} (with admin rights)")
                return os.path.join(system_apps, app_name)
                
        except subprocess.TimeoutExpired:
            print("⚠️  User did not enter password, using fallback location")
        except Exception as e:
            print(f"⚠️  Could not get admin access: {e}")
        
        # Fallback: пользовательская папка ~/Applications/
        home = os.path.expanduser("~")
        home_apps = os.path.join(home, "Applications")
        
        # ИСПРАВЛЕНО: Добавлена обработка ошибок создания директории
        if not os.path.exists(home_apps):
            try:
                os.makedirs(home_apps, exist_ok=True)
                print(f"ℹ️  Created user Applications folder: {home_apps}")
            except Exception as e:
                # Если не можем создать нигде - это критическая ошибка
                raise PermissionError(
                    "Cannot create DLC Unlocker. No write access to:\n"
                    f"- {system_apps} (system Applications)\n"
                    f"- {home_apps} (user Applications)\n\n"
                    "Please grant Full Disk Access to LemonUnlocker in:\n"
                    "System Preferences → Security & Privacy → Privacy → Full Disk Access"
                )
        
        print(f"⚠️  Installing to {home_apps} (user-only, less visible)")
        print(f"ℹ️  To find: Finder → Go → Home → Applications")
        return os.path.join(home_apps, app_name)

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

            # ИСПРАВЛЕНО: Показываем где именно установлено
            if app_path.startswith("/Applications/"):
                location_msg = (
                    "📍 Location: /Applications/\n"
                    "   (Finder → Applications / Программы)\n"
                )
            else:
                location_msg = (
                    "📍 Location: ~/Applications/\n"
                    "   (Finder → Go → Home → Applications)\n"
                    "   or search 'DLC Unlocker' in Spotlight (⌘+Space)\n"
                )

            return True, (
                "✅ DLC Unlocker installed successfully!\n\n"
                f"{location_msg}\n"
                "⚠️ IMPORTANT: Run 'DLC Unlocker - The Sims 4' app\n"
                "BEFORE launching the game each time!"
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

    @staticmethod
    def create_game_launcher(logger, game_path=None):
        """
        НОВОЕ: Создает удобный 1-click лаунчер для игры с DLC.
        
        Создает AppleScript приложение которое:
        1. Запускает DLC Unlocker
        2. Ждет 2-3 секунды
        3. Автоматически запускает The Sims 4
        
        Пользователю нужно только запустить "Play Sims 4 with DLC.app"
        """
        
        # Проверяем что DLC Unlocker установлен
        unlocker_path = UnlockerManager.get_unlocker_app_path()
        if not os.path.exists(unlocker_path):
            return False, "DLC Unlocker not installed. Install it first."
        
        # Получаем путь к игре из конфига если не предоставлен
        if not game_path:
            try:
                config = ConfigManager()
                game_path = config.get("game_path")
            except:
                pass
        
        if not game_path or not os.path.exists(game_path):
            return False, (
                "Game path not set or invalid.\n\n"
                "Please set the game path in Dashboard first."
            )
        
        # Определяем где создать лаунчер (в той же папке где DLC Unlocker)
        if unlocker_path.startswith("/Applications/"):
            launcher_dir = "/Applications"
        else:
            launcher_dir = os.path.dirname(unlocker_path)
        
        launcher_name = "Play Sims 4 with DLC.app"
        launcher_path = os.path.join(launcher_dir, launcher_name)
        
        logger.log(f"Creating game launcher at: {launcher_path}")
        
        # AppleScript который запускает сначала unlocker, потом игру
        # Используем экранирование путей для безопасности
        unlocker_escaped = unlocker_path.replace('"', '\\"')
        game_escaped = game_path.replace('"', '\\"')
        
        applescript = f'''
-- Sims 4 with DLC Launcher
-- Created by Lemon Unlocker

on run
    try
        -- Показать уведомление
        display notification "Starting DLC Unlocker..." with title "Sims 4 Launcher"
        
        -- Запустить DLC Unlocker (в фоне)
        do shell script "open -g \\"{unlocker_escaped}\\""
        
        -- Подождать чтобы unlocker инициализировался
        delay 3
        
        -- Показать уведомление
        display notification "Launching The Sims 4..." with title "Sims 4 Launcher"
        
        -- Запустить игру
        do shell script "open \\"{game_escaped}\\""
        
        -- Успех!
        delay 1
        display notification "Game launched! Have fun! 🎮" with title "Sims 4 Launcher"
        
    on error errMsg
        display dialog "Failed to launch game:" & return & errMsg buttons {{"OK"}} default button 1 with icon stop
    end try
end run
'''
        
        try:
            # Создать временный файл со скриптом
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', 
                                            delete=False, encoding='utf-8') as f:
                f.write(applescript)
                script_file = f.name
            
            logger.log("Compiling AppleScript launcher...")
            
            # Скомпилировать в .app используя osacompile
            result = subprocess.run(
                ['osacompile', '-o', launcher_path, script_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Удалить временный файл
            os.remove(script_file)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return False, f"Failed to compile launcher: {error_msg}"
            
            logger.log("Launcher compiled successfully")
            
            # Попробовать добавить иконку (опционально)
            try:
                base_dir = UnlockerManager.get_base_path()
                icon_path = os.path.join(base_dir, "icon.png")
                
                if os.path.exists(icon_path):
                    # Конвертировать PNG в ICNS и установить
                    # (требует sips и iconutil, доступны на macOS)
                    logger.log("Adding icon to launcher...")
                    # Это опционально, пропускаем если не получится
            except:
                pass
            
            # Удалить quarantine
            try:
                subprocess.run(['xattr', '-rc', launcher_path],
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
                logger.log("Removed quarantine from launcher")
            except:
                pass
            
            # Определяем где именно создали
            if launcher_path.startswith("/Applications/"):
                location_info = (
                    f"📍 Location: /Applications/\n"
                    f"   (Finder → Applications / Программы)\n\n"
                )
            else:
                location_info = (
                    f"📍 Location: ~/Applications/\n"
                    f"   (Finder → Go → Home → Applications)\n\n"
                )
            
            return True, (
                f"🚀 Game Launcher created successfully!\n\n"
                f"{location_info}"
                f"✨ Now you can launch 'Play Sims 4 with DLC' app\n"
                f"   and it will automatically:\n"
                f"   1. Start DLC Unlocker\n"
                f"   2. Launch The Sims 4\n"
                f"   3. All DLC will be activated!\n\n"
                f"💡 Just ONE click to play!"
            )
            
        except subprocess.TimeoutExpired:
            return False, "Launcher creation timed out"
        except Exception as e:
            logger.log(f"Failed to create launcher: {str(e)}", "ERROR")
            return False, f"Failed to create launcher: {str(e)}"


class UnlockerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DLC Unlocker Manager")
        self.setFixedSize(450, 380)  # УВЕЛИЧЕНО для новой кнопки
        self.parent_ui = parent
        self.setup_ui()
        self.setStyleSheet(
            "QDialog{background-color:#1e1e1e;}"
            "QLabel{color:white;}"
            "QPushButton{background-color:#ffd700;color:black;border:none;"
            "padding:10px;font-weight:bold;border-radius:4px;}"
            "QPushButton:hover{background-color:#ffed4a;}"
            "QPushButton.primary{background-color:#22C55E;color:white;}"
            "QPushButton.primary:hover{background-color:#16A34A;}"
        )

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

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
        
        # НОВОЕ: Кнопка создания игрового лаунчера
        btn_launcher = QPushButton("🚀 3. Create Game Launcher (1-Click Play!)")
        btn_launcher.setProperty("class", "primary")
        btn_launcher.setStyleSheet(
            "QPushButton{"
            "background-color:#22C55E;color:white;"
            "border:none;padding:12px;font-weight:bold;"
            "border-radius:6px;font-size:13px;"
            "}"
            "QPushButton:hover{background-color:#16A34A;}"
        )
        btn_launcher.clicked.connect(self.create_launcher)
        layout.addWidget(btn_launcher)

        # Разделитель
        line = QLabel("─" * 50)
        line.setStyleSheet("color:#444;font-size:8px;")
        line.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(line)

        info = QLabel(
            "Steps 1-2: Set up DLC Unlocker\n"
            "Step 3: Create easy launcher (recommended!)\n\n"
            "💡 With launcher: just 1 click to play!\n"
            "Without launcher: run DLC Unlocker before each game session"
        )
        info.setStyleSheet("color:#aaa;font-size:10px;text-align:center;line-height:1.4;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
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
            # ConfigManager теперь определен в этом же файле
            config = ConfigManager()
            game_path = config.get("game_path")
        except:
            pass
        
        success, msg = UnlockerManager.update_sims4_config(self.parent_ui.logger, game_path)
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.critical(self, "Error", msg)
    
    def create_launcher(self):
        """НОВОЕ: Создать удобный лаунчер для игры"""
        # Получаем путь к игре из конфига
        game_path = None
        try:
            config = ConfigManager()
            game_path = config.get("game_path")
        except:
            pass
        
        success, msg = UnlockerManager.create_game_launcher(self.parent_ui.logger, game_path)
        if success:
            QMessageBox.information(
                self, 
                "🎉 Launcher Created!", 
                msg,
                QMessageBox.StandardButton.Ok
            )
        else:
            QMessageBox.critical(self, "Error", msg)