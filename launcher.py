"""
Launcher for Game-Changing Translator (Nuitka build).
This tiny script is compiled separately and acts as the user-facing exe.
It launches the real application from the _internal/ subdirectory.
"""
import subprocess
import os
import sys

def main():
    launcher_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    real_exe = os.path.join(launcher_dir, "_internal", "main.exe")
    
    if not os.path.exists(real_exe):
        print(f"Error: Could not find {real_exe}")
        input("Press Enter to exit...")
        sys.exit(1)
    
    # Launch the real application from the launcher's directory
    # so that logs, config etc. are created next to the launcher
    result = subprocess.call([real_exe] + sys.argv[1:], cwd=launcher_dir)
    sys.exit(result)

if __name__ == "__main__":
    main()
