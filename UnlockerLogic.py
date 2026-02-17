import os
import sys
import shutil
import subprocess
import time
import shlex
import tempfile
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt6.QtCore import Qt


class AdminElevator:

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
        try:
            exe = sys.executable
            args = " ".join([shlex.quote(a) for a in sys.argv])
            script = f'do shell script "{exe} {args}" with administrator privileges'
            subprocess.run(['osascript', '-e', script], check=True)
            sys.exit(0)
        except Exception as e:
            print(f"Failed to elevate privileges: {e}")
            return False


class ConfigManager:
    def __init__(self):
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

    def set(self, key, value):
        self.config[key] = value

    def save(self):
        try:
            import json
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")


class UnlockerManager:

    @staticmethod
    def get_base_path():
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        return os.path.dirname(os.path.abspath(__file__))

    @staticmethod
    def get_unlocker_app_path():
        app_name = "DLC Unlocker - The Sims 4.app"
        system_apps = "/Applications"
        
        if os.access(system_apps, os.W_OK):
            print(f"✅ Installing to {system_apps} (system-wide)")
            return os.path.join(system_apps, app_name)
        
        try:
            test_file = os.path.join(system_apps, ".lemon_test")
            cmd = f'do shell script "touch \\"{test_file}\\"" with administrator privileges'
            
            result = subprocess.run(
                ['osascript', '-e', cmd],
                capture_output=True,
                timeout=60,
                text=True
            )
            
            if result.returncode == 0:
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
        
        home = os.path.expanduser("~")
        home_apps = os.path.join(home, "Applications")
        
        if not os.path.exists(home_apps):
            try:
                os.makedirs(home_apps, exist_ok=True)
                print(f"ℹ️  Created user Applications folder: {home_apps}")
            except Exception as e:
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
        app_path = UnlockerManager.get_unlocker_app_path()
        unlocker_bin = os.path.join(app_path, "Contents", "MacOS", "unlocker")
        return os.path.exists(unlocker_bin)

    @staticmethod
    @staticmethod
    def install_ea_unlocker(logger, loc_strings=None):
        """
        Create the DLC Unlocker .app bundle for The Sims 4.
        This replicates what 'prepare DLC Unlockers' bash script does.
        """
        if not loc_strings:
            loc_strings = {
                "install_success": "✅ DLC Unlocker installed successfully!",
                "location_app": "📍 Location: /Applications/\n   (Finder → Applications)",
                "location_user": "📍 Location: ~/Applications/\n   (Finder → Go → Home → Applications)\n   or search 'DLC Unlocker' in Spotlight (⌘+Space)",
                "important_note": "⚠️ IMPORTANT: Run 'DLC Unlocker - The Sims 4' app\nBEFORE launching the game each time!"
            }

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

        if not os.path.exists(unlocker_src):
            logger.log(f"Primary source path not found: {unlocker_src}", "WARNING")
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

        required_files = ["unlocker", "anadius.dylib", "thesims4.cfg"]
        missing_files = []
        for fname in required_files:
            if not os.path.exists(os.path.join(unlocker_src, fname)):
                missing_files.append(fname)
        
        if missing_files:
            return False, f"Required files missing: {', '.join(missing_files)}\nSource: {unlocker_src}"

        try:
            app_path = UnlockerManager.get_unlocker_app_path()
        except PermissionError as e:
            return False, str(e)
        
        bundle_path = os.path.join(app_path, "Contents", "MacOS")

        try:
            try:
                os.makedirs(bundle_path, exist_ok=True)
            except Exception as e:
                return False, f"Cannot create app bundle directory (permission denied): {bundle_path}\n\n{str(e)}"

            if not os.access(bundle_path, os.W_OK):
                return False, (
                    f"No write permission to: {bundle_path}\n\n"
                    "Please grant Full Disk Access to LemonUnlocker in:\n"
                    "System Preferences → Security & Privacy → Privacy → Full Disk Access"
                )
            
            logger.log(f"Creating .app bundle at: {app_path}")

            src = os.path.join(unlocker_src, "unlocker")
            dst = os.path.join(bundle_path, "unlocker")
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
            logger.log("Copied unlocker binary")

            shutil.copy2(
                os.path.join(unlocker_src, "anadius.dylib"),
                os.path.join(bundle_path, "anadius.dylib")
            )
            logger.log("Copied anadius.dylib")

            for dylib in ["anadius_online.dylib", "ts4_config_update.dylib"]:
                src_dylib = os.path.join(unlocker_src, dylib)
                if os.path.exists(src_dylib):
                    shutil.copy2(src_dylib, os.path.join(bundle_path, dylib))
                    logger.log(f"Copied {dylib}")

            shutil.copy2(
                os.path.join(unlocker_src, "thesims4.cfg"),
                os.path.join(bundle_path, "anadius.cfg")
            )
            logger.log("Copied config (thesims4.cfg -> anadius.cfg)")

            override_src = os.path.join(unlocker_src, "thesims4override.cfg")
            if os.path.exists(override_src):
                shutil.copy2(override_src, os.path.join(bundle_path, "anadius_override.cfg"))
                logger.log("Copied override config")

            plist_src = os.path.join(unlocker_src, "Info.plist")
            plist_dst = os.path.join(app_path, "Contents", "Info.plist")
            
            if os.path.exists(plist_src):
                shutil.copy2(plist_src, plist_dst)
                logger.log("Copied Info.plist")
            else:
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
            
            icon_src = os.path.join(unlocker_src, "icon.icns")
            if os.path.exists(icon_src):
                resources_dir = os.path.join(app_path, "Contents", "Resources")
                os.makedirs(resources_dir, exist_ok=True)
                shutil.copy2(icon_src, os.path.join(resources_dir, "icon.icns"))
                logger.log("Copied app icon")

            try:
                subprocess.run(
                    ['xattr', '-rc', app_path],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                logger.log("Removed quarantine attributes")
            except Exception as e:
                logger.log(f"Could not remove quarantine: {e}", "WARNING")

            if app_path.startswith("/Applications/"):
                location_msg = loc_strings["location_app"]
            else:
                location_msg = loc_strings["location_user"]

            return True, (
                f"{loc_strings['install_success']}\n\n"
                f"{location_msg}\n"
                f"{loc_strings['important_note']}"
            )

        except Exception as e:
            logger.log(f"Installation failed: {str(e)}", "ERROR")
            return False, f"Installation failed: {str(e)}"

    @staticmethod
    def update_sims4_config(logger, game_path=None):
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
            
            override_src = os.path.join(unlocker_src, "thesims4override.cfg")
            if os.path.exists(override_src):
                shutil.copy2(override_src, os.path.join(bundle_path, "anadius_override.cfg"))
                logger.log("Updated override config")
            
            if game_path:
                try:
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
    def create_game_launcher(logger, game_path=None, loc_strings=None):
        if not loc_strings:
            loc_strings = {
                "launcher_title": "Sims 4 Launcher",
                "launcher_start_unlocker": "Starting DLC Unlocker...",
                "launcher_start_game": "Launching The Sims 4...",
                "launcher_success": "Game launched! Have fun! 🎮",
                "launcher_error": "Failed to launch game:"
            }

        unlocker_path = UnlockerManager.get_unlocker_app_path()
        if not os.path.exists(unlocker_path):
            return False, "DLC Unlocker not installed. Install it first."
        
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

        if sys.platform == "darwin" and game_path.endswith("The Sims 4 Packs"):
            parent_dir = os.path.dirname(game_path)
            potential_app = os.path.join(parent_dir, "The Sims 4.app")
            if os.path.exists(potential_app):
                 print(f"ℹ️  Found game app at: {potential_app}")
                 game_path = potential_app
            else:
                 std_app = "/Applications/The Sims 4.app"
                 if os.path.exists(std_app):
                      game_path = std_app

        if unlocker_path.startswith("/Applications/"):
            launcher_dir = "/Applications"
        else:
            launcher_dir = os.path.dirname(unlocker_path)
        
        launcher_name = "Play Sims 4 with DLC.app"
        launcher_path = os.path.join(launcher_dir, launcher_name)
        
        logger.log(f"Creating game launcher at: {launcher_path}")
        
        unlocker_escaped = unlocker_path.replace('"', '\\"')
        game_escaped = game_path.replace('"', '\\"')
        
        applescript = f'''
on run
    try
        display notification "{loc_strings['launcher_start_unlocker']}" with title "{loc_strings['launcher_title']}"
        
        do shell script "open -g \\"{unlocker_escaped}\\""
        
        delay 3
        
        display notification "{loc_strings['launcher_start_game']}" with title "{loc_strings['launcher_title']}"
        
        do shell script "open \\"{game_escaped}\\""
        
        delay 1
        display notification "{loc_strings['launcher_success']}" with title "{loc_strings['launcher_title']}"
        
    on error errMsg
        display dialog "{loc_strings['launcher_error']}" & return & errMsg buttons {{"OK"}} default button 1 with icon stop
    end try
end run
'''
        
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.applescript', 
                                            delete=False, encoding='utf-8') as f:
                f.write(applescript)
                script_file = f.name
            
            logger.log("Compiling AppleScript launcher...")
            
            result = subprocess.run(
                ['osacompile', '-o', launcher_path, script_file],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            os.remove(script_file)
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                return False, f"Failed to compile launcher: {error_msg}"
            
            logger.log("Launcher compiled successfully")
            
            try:
                base_dir = UnlockerManager.get_base_path()
                icon_path = os.path.join(base_dir, "icon.png")
                
                if os.path.exists(icon_path):
                    logger.log("Adding icon to launcher...")
            except:
                pass
            
            try:
                subprocess.run(['xattr', '-rc', launcher_path],
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL)
                logger.log("Removed quarantine from launcher")
            except:
                pass
            
            loc_success_title = loc_strings.get("launcher_created_title", "🚀 Game Launcher created successfully!")
            loc_location = loc_strings.get("launcher_location", "📍 Location: ")
            loc_finder = loc_strings.get("launcher_finder", "(Finder → Applications)")

            if launcher_path.startswith("/Applications/"):
                location_info = f"{loc_location} /Applications/\n   {loc_finder}\n\n"
            else:
                location_info = f"{loc_location} ~/Applications/\n   {loc_finder}\n\n"

            return True, (
                f"{loc_success_title}\n\n"
                f"{location_info}"
                f"{loc_strings.get('launcher_success_msg', '✨ Now you can launch created app to play!')}"
            )
            
        except subprocess.TimeoutExpired:
            return False, "Launcher creation timed out"
        except Exception as e:
            logger.log(f"Failed to create launcher: {str(e)}", "ERROR")
            return False, f"Failed to create launcher: {str(e)}"