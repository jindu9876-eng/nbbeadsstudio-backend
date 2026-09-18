import sys
import os
import uvicorn

# Ensure the parent directory is in sys.path so 'backend.xxx' imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

if __name__ == "__main__":
    print("Starting NB BEADS STUDIO E-Commerce Backend...")
    print("API documentation is available at http://localhost:8000/docs")
    print("Admin dashboard is available at http://localhost:8000/admin/login")
    uvicorn.run("backend.app:app", host="0.0.0.0", port=8000, reload=True)
