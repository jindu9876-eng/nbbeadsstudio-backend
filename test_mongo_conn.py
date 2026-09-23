import os
import sys
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables from .env
load_dotenv()

# Default URI or from environment variable MONGODB_URI
uri = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://jindu9876_db_user:<db_password>@jineee.cf8x3nc.mongodb.net/?appName=jineee&compressors=zlib"
)

# If db_password placeholder is still present, inform user
if "<db_password>" in uri:
    print("\n[!] Notice: '<db_password>' is currently a placeholder in your MongoDB URI.")
    print("    Please replace '<db_password>' with your real MongoDB Atlas password in backend/.env or in this script.\n")

print(f"Connecting to MongoDB Atlas at:\n{uri}\n")

client = MongoClient(uri)
try:
    client.admin.command("ping")
    print("Connected successfully to MongoDB Atlas!")
    client.close()
except Exception as e:
    raise Exception("The following error occurred: ", e)
