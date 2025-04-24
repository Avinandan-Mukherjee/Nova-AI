import os
import subprocess
import threading
import json
import asyncio
from time import sleep, time
from asyncio import run
import sys
 
 
from dotenv import dotenv_values


from Frontend.GUI import (
    GraphicalUserInterface,
    SetAssistantStatus,
    ShowTextToScreen,
    TempDirectoryPath,
    SetMicrophoneStatus,
    GetAssistantStatus,
    GetMicrophoneStatus,
    QueryModifier,
    AnswerModifier,
    register_main_username_ref,
)
from Backend.Model import FirstLayerDMM
from Backend.RealtimeSearchEngine import RealtimeSearchEngine
from Backend.SpeechToText import SpeechRecognition
from Backend.Automation import Automation
from Backend.TextToSpeech import TextToSpeech
from Backend.Chatbot import ChatBot

env_vars = dotenv_values(".env")
Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
DefaultMessages = f'''{Username}: Hello {Assistantname}: Hello, {Username}! How can I help you today?
{Assistantname}: Welcome back, {Username}! {Username}: Thank you {Assistantname}: How can I help you today, {Username}?'''
subprocesses = []
Functions = ["open", "close", "play", "system", "content", "google search", "youtube search"]

# Global variables
processing = False  # Flag to indicate system is busy processing
loop = None  # Global asyncio event loop

# Register the Username variable with the GUI module so it can be updated
register_main_username_ref('Username')

# Check if we need to load Username from the fallback file
if Username == "Your Name Here" or not Username:
    try:
        temp_username_path = TempDirectoryPath('Username.data')
        if os.path.exists(temp_username_path):
            with open(temp_username_path, "r", encoding='utf-8') as f:
                temp_username = f.read().strip()
                if temp_username:
                    Username = temp_username
                    print(f"[Info] Loaded Username from temporary file: {Username}")
    except Exception as e:
        print(f"[Error] Failed to load Username from temporary file: {e}")

def ShowDefaultMessages():
    try:
        with open(r'Data\Chatlog.json', "r", encoding="utf-8") as File:
            content = File.read()
            if len(content) < 5:
                # Only write default if chatlog is essentially empty
                db_path = TempDirectoryPath('Database.data')
                resp_path = TempDirectoryPath('Responses.data')
                try:
                    with open(db_path, "w", encoding="utf-8") as db_file:
                        db_file.write("")
                    with open(resp_path, "w", encoding="utf-8") as resp_file:
                        resp_file.write(DefaultMessages)
                except IOError as e:
                    print(f"[Error] Failed to write default message files: {e}")
    except FileNotFoundError:
        print("[Error] Chatlog.json not found. Cannot check for default messages.")
    except Exception as e:
        print(f"[Error] An unexpected error occurred in ShowDefaultMessages: {e}")

def ReadChatlogJson():
    try:
        with open(r'Data\Chatlog.json', "r", encoding="utf-8") as File:
            return File.read()
    except FileNotFoundError:
        print("[Error] Chatlog.json not found during read.")
        return "[]"
    except Exception as e:
        print(f"[Error] Failed to read Chatlog.json: {e}")
        return "[]"

def ChatLogIntegration():
    json_string = ReadChatlogJson()
    formatted_chatlog = ""
    try:
        json_data = json.loads(json_string)
        for entry in json_data:
            role = entry.get("role", "unknown").lower()
            content = entry.get("content", "")
            if role == "user":
                formatted_chatlog += f"{Username}: {content}\n"
            elif role == "assistant":
                formatted_chatlog += f"{Assistantname}: {content}\n"
    except json.JSONDecodeError as e:
        print(f"[Error] Failed to decode Chatlog.json: {e}")
    except Exception as e:
        print(f"[Error] Failed processing chat log data: {e}")

    try:
        # Ensure directory exists before writing
        os.makedirs(os.path.dirname(TempDirectoryPath('Database.data')), exist_ok=True)
        with open(TempDirectoryPath('Database.data'), "w", encoding="utf-8") as File:
            File.write(AnswerModifier(formatted_chatlog))
    except IOError as e:
        print(f"[Error] Failed to write formatted chat log to Database.data: {e}")

def ShowChatOnGUI():
    db_path = TempDirectoryPath('Database.data')
    try:
        with open(db_path, "r", encoding="utf-8") as File:
            Data = File.read()
        if len(str(Data)) > 0:
            lines = Data.splitlines()
            result = '\n'.join(lines)
            # Re-open in write mode to update
            with open(db_path, "w", encoding="utf-8") as File:
                File.write(result)
    except FileNotFoundError:
        print(f"[Error] {db_path} not found in ShowChatOnGUI.")
    except IOError as e:
        print(f"[Error] Failed reading/writing {db_path} in ShowChatOnGUI: {e}")
    except Exception as e:
        print(f"[Error] An unexpected error occurred in ShowChatOnGUI: {e}")

def reload_user_info():
    """Reload Username from .env file and temporary file"""
    global Username, DefaultMessages
    # Reload from .env
    new_env_vars = dotenv_values(".env")
    new_username = new_env_vars.get("Username")
    
    if new_username and new_username != "Your Name Here":
        Username = new_username
        print(f"[Info] Reloaded Username from .env: {Username}")
    else:
        # Try fallback file
        try:
            temp_username_path = TempDirectoryPath('Username.data')
            if os.path.exists(temp_username_path):
                with open(temp_username_path, "r", encoding='utf-8') as f:
                    temp_username = f.read().strip()
                    if temp_username:
                        Username = temp_username
                        print(f"[Info] Reloaded Username from temporary file: {Username}")
        except Exception as e:
            print(f"[Error] Failed to load Username from temporary file: {e}")
    
    # Update DefaultMessages with current username
    DefaultMessages = f'''{Username}: Hello {Assistantname}: Hello, {Username}! How can I help you today?
{Assistantname}: Welcome back, {Username}! {Username}: Thank you {Assistantname}: How can I help you today, {Username}?'''
    
    return Username

def InitialExecution():
    # Make sure we have the latest user info
    reload_user_info()
    
    SetMicrophoneStatus("False")
    ShowTextToScreen("")
    ShowDefaultMessages()
    ChatLogIntegration()
    ShowChatOnGUI()

InitialExecution()

async def process_query_async(query):
    """Process a query asynchronously."""
    global processing, Username
    
    if not query:
        return
    
    # Reload user info to ensure we're using the latest username
    reload_user_info()
    
    processing = True
    print(f"[NOVA] Processing: '{query}'")
    SetAssistantStatus("Processing... ")
    
    try:
        # Run all potentially blocking operations in executor
        
        # Get decision from model
        Decision = await loop.run_in_executor(None, lambda: FirstLayerDMM(query))
        print(f"[NOVA] Decision: {Decision}")
        
        # Process image generation
        ImageExecution = False
        ImageGenerationQuery = ""
        for queries in Decision:
            if "generate" in queries:
                ImageGenerationQuery = queries.replace("generate image", "").strip()
                ImageExecution = True
        
        # Process automation commands
        TaskExecution = False
        for queries in Decision:
            if not TaskExecution and any(queries.startswith(func) for func in Functions):
                try:
                    # Use the current event loop instead of asyncio.run()
                    automation_task = Automation(list(Decision))
                    automation_result = await automation_task
                    TaskExecution = True
                except Exception as e:
                    print(f"[Error] Automation execution failed: {e}")
                    ShowTextToScreen(f"{Assistantname}: I'm sorry, I encountered an error while executing that command.")
                    await loop.run_in_executor(None, lambda: TextToSpeech("I'm sorry, I encountered an error while executing that command."))
                    TaskExecution = True  # Set to true to prevent fallback to general query
        
        # Handle image generation
        if ImageExecution:
            try:
                img_gen_data_path = r'Frontend\Files\ImageGeneration.data'
                await loop.run_in_executor(None, lambda: os.makedirs(os.path.dirname(img_gen_data_path), exist_ok=True))
                
                # Define as regular function instead of async
                def write_image_data():
                    with open(img_gen_data_path, "w") as File:
                        # Ensure there's no extra spacing around the comma
                        File.write(f"{ImageGenerationQuery.strip()},True")
                
                # Execute as regular function in thread executor
                await loop.run_in_executor(None, write_image_data)
                
                python_executable = sys.executable
                script_path = os.path.join("Backend", "ImageGeneration.py")
                
                # Run subprocess in executor
                def start_subprocess():
                    p1 = subprocess.Popen(
                        [python_executable, script_path],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE, shell=False
                    )
                    subprocesses.append(p1)
                    return p1
                
                await loop.run_in_executor(None, start_subprocess)
                print(f"[NOVA] Started image generation process")
                
                # Add a custom response for image generation to avoid AI generating descriptive text
                img_response = f"I'm generating an image of {ImageGenerationQuery} for you now."
                ShowTextToScreen(f"{Assistantname}: {img_response}")
                await loop.run_in_executor(None, lambda: TextToSpeech(img_response))
                
                # Skip further processing since we're handling image generation
                SetAssistantStatus("Available... ")
                processing = False
                return
                
            except Exception as e:
                error_msg = f"I'm sorry, I couldn't generate the image. Error: {e}"
                print(f"[Error] Image generation failed: {e}")
                ShowTextToScreen(f"{Assistantname}: {error_msg}")
                await loop.run_in_executor(None, lambda: TextToSpeech("I'm sorry, I couldn't generate the image."))
        
        # Generate answer based on query type - Only reached if not image generation
        G = any(i.startswith("general") for i in Decision)
        R = any(i.startswith("realtime") for i in Decision)
        Answer = None
        
        if (G and R) or R:
            SetAssistantStatus("Searching... ")
            merged_query = " and ".join(
                " ".join(i.split()[1:]) for i in Decision 
                if i.startswith("general") or i.startswith("realtime")
            )
            Answer = await loop.run_in_executor(None, lambda: RealtimeSearchEngine(QueryModifier(merged_query)))
        else:
            # Process other query types
            for Queries in Decision:
                if "general" in Queries and not Answer:
                    SetAssistantStatus("Processing... ")
                    QueryFinal = Queries.replace("general", "")
                    Answer = await loop.run_in_executor(None, lambda: ChatBot(QueryModifier(QueryFinal)))
                
                elif "realtime" in Queries and not Answer:
                    SetAssistantStatus("Searching... ")
                    QueryFinal = Queries.replace("realtime", "")
                    Answer = await loop.run_in_executor(None, lambda: RealtimeSearchEngine(QueryModifier(QueryFinal)))
                
                # Handle exit command
                elif "exit" in Queries:
                    QueryFinal = "Goodbye, sir."
                    Answer = await loop.run_in_executor(None, lambda: ChatBot(QueryModifier(QueryFinal)))
                    
                    # Display and speak exit message
                    SetAssistantStatus("Answering... ")
                    if Answer:
                        ShowTextToScreen(f"{Assistantname}: {Answer}")
                        await loop.run_in_executor(None, lambda: TextToSpeech(Answer))
                    else:
                        await loop.run_in_executor(None, lambda: TextToSpeech(QueryFinal))
                        ShowTextToScreen(f"{Assistantname}: {QueryFinal}")
                    
                    # Delay for UI update
                    await asyncio.sleep(1.0)
                    print("[NOVA] Exiting application")
                    os._exit(1)
        
        # Display and speak the answer
        if Answer:
            print(f"[NOVA] Answer: '{Answer[:50]}...'")
            ShowTextToScreen(f"{Assistantname}: {Answer}")
            SetAssistantStatus("Answering... ")
            await loop.run_in_executor(None, lambda: TextToSpeech(Answer))
        else:
            if not (TaskExecution or ImageExecution):
                print("[NOVA] No answer generated")
                # Let the user know if we couldn't generate an answer
                no_answer_msg = "I'm sorry, I couldn't find an answer to your question."
                ShowTextToScreen(f"{Assistantname}: {no_answer_msg}")
                await loop.run_in_executor(None, lambda: TextToSpeech(no_answer_msg))
        
        # Reset status and handle errors for user feedback
        SetAssistantStatus("Available... ")
    
    except Exception as e:
        error_msg = f"I'm sorry, an error occurred: {str(e)}"
        print(f"[Error] Processing error: {e}")
        ShowTextToScreen(f"{Assistantname}: {error_msg}")
        await loop.run_in_executor(None, lambda: TextToSpeech("I'm sorry, an error occurred while processing your request."))
        SetAssistantStatus("Available... ")
    
    finally:
        # Always reset busy flag when done
        processing = False
        print("[NOVA] Processing complete")

def start_processing(speech):
    """Start processing speech with asyncio."""
    global loop
    
    if not loop or loop.is_closed():
        return
    
    if not speech:
        return
    
    print(f"[NOVA] Starting asyncio task for: '{speech}'")
    
    # Create and schedule the asyncio task
    asyncio.run_coroutine_threadsafe(process_query_async(speech), loop)

def check_text_input():
    """Check for and process text input."""
    query_data_path = TempDirectoryPath('Query.data')
    try:
        if not os.path.exists(query_data_path) or os.path.getsize(query_data_path) == 0:
            return False
            
        with open(query_data_path, "r", encoding='utf-8') as file:
            query = file.read().strip()
            
        # Clear the file
        with open(query_data_path, "w", encoding='utf-8') as file:
            file.write("")
            
        if query:
            print(f"[NOVA] Text input detected: '{query}'")
            
            # Process with asyncio
            start_processing(query)
            return True
    except Exception as e:
        print(f"[Error] Text input check failed: {e}")
        
    return False

def listen_for_speech():
    """Listen for speech and process it immediately with asyncio."""
    try:
        # ONLY check mic status for listening purposes, NOT for processing
        if GetMicrophoneStatus() != "True":
            return False
        
        # Don't start new listening if already processing
        if processing:
            return False
        
        # Listen for speech
        SetAssistantStatus("Listening... ")
        speech = SpeechRecognition()
        
        if not speech:
            return False
            
        print(f"[NOVA] Speech detected: '{speech}'")
        ShowTextToScreen(f"{Username}: {speech}")
        
        # IMPORTANT: Once speech is detected, processing should start regardless of mic state
        # Start processing with asyncio - this runs independently from this point on
        start_processing(speech)
        
        return True
        
    except Exception as e:
        print(f"[Error] Speech recognition error: {e}")
        return False

async def main_loop():
    """Main asyncio loop."""
    while True:
        try:
            # Check for text input (regardless of mic state) 
            check_text_input()
            
            # Listen for speech (this function already checks mic state internally)
            listen_for_speech()
            
            # Update UI status if needed (regardless of mic state)
            if not processing and GetAssistantStatus() != "Available... ":
                SetAssistantStatus("Available... ")
            
            # Use asyncio sleep instead of regular sleep
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"[Error] Main loop error: {e}")
            await asyncio.sleep(1)  # Longer sleep on error

def run_asyncio_loop():
    """Run the asyncio event loop in a dedicated thread."""
    global loop
    
    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Schedule the main loop task
    loop.create_task(main_loop())
    
    try:
        # Run the event loop indefinitely
        loop.run_forever()
    except Exception as e:
        print(f"[Error] Asyncio loop error: {e}")
    finally:
        # Clean up
        loop.close()

def SecondThread():
    """GUI thread."""
    GraphicalUserInterface()

if __name__ == "__main__":
    # Start asyncio thread
    asyncio_thread = threading.Thread(target=run_asyncio_loop, daemon=True)
    asyncio_thread.start()
    
    # Wait for asyncio to initialize
    sleep(0.5)
    
    # Start GUI thread (blocks until closed)
    SecondThread()