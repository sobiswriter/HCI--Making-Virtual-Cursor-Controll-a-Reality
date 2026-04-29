import PyInstaller.__main__
import os
import sys

# Define the paths
script_name = "main.py"
exe_name = "HCI_Spatial_Cursor"
icon_path = "penguin.ico"
data_file = "hand_landmarker.task"

# Ensure icon exists, otherwise fall back to no icon
if not os.path.exists(icon_path):
    icon_path = None
    print(f"Warning: {icon_path} not found. Proceeding without icon.")

# PyInstaller arguments
args = [
    script_name,
    "--onefile",
    f"--name={exe_name}",
    f"--add-data={data_file};.",
    "--collect-all=mediapipe",
    "--clean",
]

if icon_path:
    args.append(f"--icon={icon_path}")

print(f"Starting build for {exe_name}...")
PyInstaller.__main__.run(args)
print("\nBuild complete! Check the 'dist' folder for your executable.")
