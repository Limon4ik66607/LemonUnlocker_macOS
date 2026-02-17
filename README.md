# 🍋 Lemon Unlocker for macOS

![Downloads](https://img.shields.io/github/downloads/Limon4ik66607/LemonUnlocker_macOS/total?style=for-the-badge&color=yellow)
![Platform](https://img.shields.io/badge/platform-macOS-white?style=for-the-badge&logo=apple&logoColor=black)

**Universal Tool for Downloading and Unlocking DLCs for The Sims 4 on Mac**

This is the native macOS version of Lemon Unlocker. It includes all the features of the Windows version but is optimized for Apple Silicon and Intel Macs.

## 📦 Installation

1.  **Download**: Get the latest `LemonUnlocker.dmg` from the [Releases Page](https://github.com/Limon4ik66607/LemonUnlocker_Mac/releases).
2.  **Open**: Double-click the `.dmg` file.
3.  **Install**: Drag `Lemon Unlocker` into the `Applications` folder shortcut.

## ⚠️ "App is damaged" or "Cannot be opened" Error

Because I am an independent developer and don't pay Apple $99/year for a developer ID, macOS might block the app.

**If you see "App is damaged and can't be opened":**

1.  Open the **Terminal** app (Cmd+Space, type "Terminal").
2.  Paste this command and press Enter:
    ```bash
    xattr -cr /Applications/LemonUnlocker.app
    ```
3.  Open the app again. It should work now!

## ✨ Key Features

*   **🚀 Native macOS App**: Optimized for macOS interface and file system.
*   **🔓 Integrated Unlocker**: Built-in Anadius DLC Unlocker adapted for macOS.
    *   Creates separate wrapper app for DLC support.
    *   No need for Wine or Windows VMs.
*   **⬇️ DLC Downloader**: Download DLCs directly to your Mac.
*   **🛠️ 7-Zip Included**: Comes with a bundled 7-Zip archiver.

## 🎮 How to Use

1.  **Grant Permissions**: On first launch, click **OK** if asked for access to Documents (Sims 4 saves).
2.  **Install Unlocker**: 
    *   Go to the **Unlocker** tab.
    *   Click **Install**.
    *   *Note*: This creates a new "The Sims 4" app in your `~/Applications` folder. **Always launch the game from there!**
3.  **Download DLCs**: Use the **Library** or **Catalog** tabs.
4.  **Update Configs**: After downloading, go to **Unlocker** -> **Update Configs**.

## 📜 Credits

*   **Lemon Unlocker**: Developed by [Limon4ik66607](https://github.com/Limon4ik66607).
*   **DLC Unlocker Core**: Based on the work of **Anadius** (macOS version).
*   **Channel**: https://t.me/lemon4elosimshub

---
*Made with 🍋 by Limon4ik*
