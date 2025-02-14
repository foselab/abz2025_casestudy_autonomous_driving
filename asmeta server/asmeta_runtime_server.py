import subprocess
import os
import shutil
import threading
import time

JAR_FILE = "AsmetaServer.jar"
SRC_FOLDER = "src"
BASE_FOLDER = os.path.join(SRC_FOLDER, "main/resources")
MODEL_FOLDER = os.path.join(BASE_FOLDER, "models")
LIBRARIES_FOLDER = os.path.join(BASE_FOLDER, "libraries")

# Ensure directories exist
os.makedirs(BASE_FOLDER, exist_ok=True)
os.makedirs(MODEL_FOLDER, exist_ok=True)
os.makedirs(LIBRARIES_FOLDER, exist_ok=True)

# Function to run the Java process
def run_server():
    global process
    process = subprocess.Popen(
        ["java", "-jar", JAR_FILE],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Redirect stderr to stdout
        text=True,
        bufsize=1,
    )
    # Print output in real-time
    for line in process.stdout:
        print(line, end="")


# Start the server in a separate thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Wait for user input to stop the server
try:
    while server_thread.is_alive():
        time.sleep(1)  # Keep checking if the server thread is alive
except KeyboardInterrupt:
    print("\nInterrupt received. Stopping the server...")

# Stop the server process
process.terminate()
time.sleep(2)  # Give it some time to shut down
process.kill()  # Force stop if still running
print("Server stopped.")

# Cleanup: delete directories
try:
    shutil.rmtree(SRC_FOLDER)
    print(f"Deleted directory: {SRC_FOLDER}")
except Exception as e:
    print(f"Failed to delete {SRC_FOLDER}: {e}")
