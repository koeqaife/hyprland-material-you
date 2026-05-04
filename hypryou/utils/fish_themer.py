import os
import shutil
from pathlib import Path

def install_fish_themes():
    # Define paths
    source_dir = Path("/usr/share/hypryou/themes/fish")
    fish_config_dir = Path.home() / ".config/fish"
    functions_dir = fish_config_dir / "functions"
    config_file = fish_config_dir / "config.fish"
    
    files_to_copy = ["hypryou_colors.fish", "update-vscode-theme.fish"]

    # 1. Check if fish is installed/exists in config
    if not fish_config_dir.exists():
        print("Fish configuration directory not found. Skipping installation.")
        return

    # 2. Ensure functions directory exists
    if not functions_dir.exists():
        print(f"Creating directory: {functions_dir}")
        functions_dir.mkdir(parents=True, exist_ok=True)

    # 3. Copy files
    for file_name in files_to_copy:
        src_path = source_dir / file_name
        dest_path = functions_dir / file_name
        
        if src_path.exists():
            try:
                shutil.copy2(src_path, dest_path)
                print(f"Copied {file_name} to {functions_dir}")
            except PermissionError:
                print(f"Permission denied: Could not copy {file_name}. Try running with sudo if required.")
        else:
            print(f"Source file {src_path} not found.")

    # 4. Integrate into config.fish
    source_commands = [
        f"\nsource {functions_dir}/hypryou_colors.fish",
        f"source {functions_dir}/update-vscode-theme.fish"
    ]

    try:
        content = ""
        if config_file.exists():
            with open(config_file, "r") as f:
                content = f.read()

        # Append only if not already sourced to prevent duplicates
        with open(config_file, "a") as f:
            for cmd in source_commands:
                if cmd.strip() not in content:
                    f.write(cmd)
            print("Integrated themes into config.fish")
            
    except Exception as e:
        print(f"Failed to update config.fish: {e}")

if __name__ == "__main__":
    install_fish_themes()
