import os
import subprocess
import sys
import shutil

def build():
    print("=========================================")
    print("Building Lyrics Overlay Executable App")
    print("=========================================")

    # Define paths
    project_dir = os.path.dirname(os.path.abspath(__file__))
    venv_python = os.path.join(project_dir, ".venv", "Scripts", "python.exe")
    pyinstaller_exe = os.path.join(project_dir, ".venv", "Scripts", "pyinstaller.exe")
    main_script = os.path.join(project_dir, "src", "main.py")

    # Double check if virtual environment pyinstaller exists
    if not os.path.exists(pyinstaller_exe):
        print(f"Error: PyInstaller not found at {pyinstaller_exe}.")
        print("Please ensure dependencies are fully installed first.")
        sys.exit(1)

    print("Running PyInstaller to compile Python into standalone Windows .exe...")
    
    # Command arguments for building a single file, windowed (no console) application
    cmd = [
        pyinstaller_exe,
        "--onefile",
        "--noconsole",
        "--name=LyricsOverlay",
        "--clean",
        f"--workpath={os.path.join(project_dir, 'build')}",
        f"--distpath={os.path.join(project_dir, 'dist')}",
        f"--specpath={project_dir}",
        # Add import paths to make sure src components are linked
        f"--paths={os.path.join(project_dir, 'src')}",
        main_script
    ]

    print(f"Running command: {' '.join(cmd)}")
    
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("PyInstaller completed successfully!")
        print(f"Standalone executable is saved at: {os.path.join(project_dir, 'dist', 'LyricsOverlay.exe')}")
    except subprocess.CalledProcessError as e:
        print("Error: PyInstaller build failed!")
        print("-----------------------------------------")
        print("STDOUT:")
        print(e.stdout)
        print("STDERR:")
        print(e.stderr)
        print("-----------------------------------------")
        sys.exit(1)

    # Clean up temporary build files
    print("Cleaning up temporary build directories...")
    try:
        spec_file = os.path.join(project_dir, "LyricsOverlay.spec")
        if os.path.exists(spec_file):
            os.remove(spec_file)
            
        build_dir = os.path.join(project_dir, "build")
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        print("Clean up completed.")
    except Exception as e:
        print(f"Warning: Failed to clean up temporary files: {e}")

    print("\nSuccess! Your standalone always-on lyrics overlay application is ready!")

if __name__ == "__main__":
    build()
