# 🍋 Lemon Unlocker for macOS

![Downloads](https://img.shields.io/github/downloads/Limon4ik66607/LemonUnlocker_Mac/total?style=for-the-badge&color=yellow)
![Platform](https://img.shields.io/badge/platform-macOS-white?style=for-the-badge&logo=apple&logoColor=black)

**Universal Tool for Downloading and Unlocking DLCs for The Sims 4 on Mac**

This is the native macOS version of Lemon Unlocker. It includes all the features of the Windows version but is optimized for Apple Silicon and Intel Macs.

## 📦 Installation

1.  **Download**: Get the latest `LemonUnlocker.dmg` from the [Releases Page](https://github.com/Limon4ik66607/LemonUnlocker_Mac/releases).
2.  **Open**: Double-click the `.dmg` file.
3.  **Install**: Drag `Lemon Unlocker` into the `Applications` folder shortcut.

## ⚠️ How to Open (Important!)

Because this app is not signed with an expensive Apple Developer ID ($99/year), macOS Gatekeeper will block it by default.

**To open it for the first time:**

1.  Go to your **Applications** folder.
2.  **Right-click** (or Control+Click) on `Lemon Unlocker`.
3.  Select **Open** in the context menu.
4.  Click **Open** in the dialog box that appears.

> **Note:** You only need to do this once. After that, you can open it normally.

### If you see "App is damaged and can't be opened"

Open the **Terminal** app and verify the signature manually by running:

```bash
xattr -cr /Applications/LemonUnlocker.app
```

Then try opening it again.

## ✨ Key Features

*   **🚀 Native macOS App**: Optimized for macOS interface and file system.
*   **🔓 Integrated Unlocker**: Built-in Anadius DLC Unlocker adapted for macOS.
    *   Creates `.app` bundles in `~/Applications`.
    *   No need for Wine or Windows VMs.
*   **⬇️ DLC Downloader**: Download DLCs directly to your Mac.
*   **🛠️ 7-Zip Included**: Comes with a bundled 7-Zip archiver for handling DLC files.

## 🎮 How to Use

1.  **Grant Permissions**: On first launch, the app might ask for access to your Documents folder (where The Sims 4 saves are). Click **OK**.
2.  **Install Unlocker**: Go to the **Unlocker** tab and click **Install**. 
    *   *Note*: The unlocker creates a separate "The Sims 4" app in your `~/Applications` folder. Use *that* one to play with DLCs.
3.  **Download DLCs**: Use the **Library** or **Catalog** tabs.
4.  **Update Configs**: After downloading, go to **Unlocker** -> **Update Configs**.

## 📜 Credits

*   **Lemon Unlocker**: Developed by [Limon4ik66607](https://github.com/Limon4ik66607).
*   **DLC Unlocker Core**: Based on the work of **Anadius** (macOS version).
*   **Channel**: https://t.me/lemon4elosimshub

---
*Made with 🍋 by Limon4ik*
