import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
IR_DIR = os.path.join(SRC_DIR, "IR")
CHAT_DIR = os.path.join(SRC_DIR, "chat")
SUMMARISER_DIR = os.path.join(SRC_DIR, "summariser")
QUIZ_DIR = os.path.join(SRC_DIR, "quiz")
RESUME_DIR = os.path.join(SRC_DIR, "resume_project")

GEMINI_API_KEY = "AQ.Ab8RN6KVeXHaMc-38RsclATU9fQX0bVtMRvTjYBFFkN4TWGjbQ"

#import all the directories to sys.path
sys.path.insert(0, SRC_DIR)
sys.path.insert(0, IR_DIR)
sys.path.insert(0, CHAT_DIR)
sys.path.insert(0, SUMMARISER_DIR)
sys.path.insert(0, QUIZ_DIR)

def all_imports():
    sys.path.insert(0, SRC_DIR)
    sys.path.insert(0, IR_DIR)
    sys.path.insert(0, CHAT_DIR)
    sys.path.insert(0, SUMMARISER_DIR)
    sys.path.insert(0, QUIZ_DIR)
    sys.path.insert(0, RESUME_DIR)
    
def chat_imports():
    sys.path.insert(0, IR_DIR)
    sys.path.insert(0, CHAT_DIR)
    sys.path.insert(0, SUMMARISER_DIR)
    
def resume_imports():
    sys.path.insert(0, IR_DIR)
    sys.path.insert(0, RESUME_DIR)