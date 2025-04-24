import asyncio
from random import randint
from PIL import Image
import requests
from dotenv import get_key
import os 
from time import sleep
import io # Import io for BytesIO

HUGGINGFACE_API_KEY = get_key('.env', 'HuggingFaceAPIKey')
if not HUGGINGFACE_API_KEY:
    print("[Error] Hugging Face API Key (HuggingFaceAPIKey) not found in .env file.")
    print("Please add 'HuggingFaceAPIKey=your_key_here' to your .env file.")
    print("You can get a key from https://huggingface.co/settings/tokens")
    # Don't exit immediately - try to create the status file first
    try:
        img_gen_data_path = r'Frontend\Files\ImageGeneration.data'
        os.makedirs(os.path.dirname(img_gen_data_path), exist_ok=True)
        with open(img_gen_data_path, "w") as f:
            f.write("False, False")
        print("[Info] Reset image generation status to prevent future attempts.")
    except Exception as e:
        print(f"[Error] Failed to reset image generation status: {e}")
    # Now exit
    exit()

def open_images(prompt):
    folder_path = r"Data"
    if not os.path.isdir(folder_path):
        print(f"[Error] Data directory '{folder_path}' not found. Cannot open images.")
        return
        
    safe_prompt = prompt.replace(" ", "_").replace("\\", "_").replace("/", "_") # Basic sanitization

    Files = [f"{safe_prompt}{i}.jpg" for i in range(1,5)]

    images_opened = 0
    for jpg_file in Files:
        image_path = os.path.join(folder_path, jpg_file)
        if not os.path.exists(image_path):
            print(f"[Warning] Image file not found: {image_path}")
            continue
            
        try:
            img = Image.open(image_path)
            print(f"Opening image: {image_path}")
            img.show() # Launches external viewer
            images_opened += 1
            # sleep(0.5) # Removed sleep after show() for faster opening
        except FileNotFoundError: 
             print(f"[Error] Image file disappeared before opening: {image_path}")
        except IOError as e:
            print(f"[Error] Failed to open image {image_path}: {e}")
        except Exception as e:
            print(f"[Error] Unexpected error opening image {image_path}: {e}")
            
    if images_opened == 0:
         print("[Info] No images were successfully opened.")

API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"} # Use loaded key

async def query(payload):
    try:
        # Add more robust timeout and error handling
        response = await asyncio.to_thread(
            requests.post, 
            API_URL, 
            headers=headers, 
            json=payload, 
            timeout=90  # Increased timeout for image generation
        )
        
        # Check for successful response
        if response.status_code == 200:
            print(f"[Success] API request successful, received {len(response.content)} bytes")
            return response.content
        else:
            print(f"[Error] API request failed with status code: {response.status_code}")
            print(f"Response text: {response.text[:200]}...")  # Print first 200 chars of response
            return None
            
    except requests.exceptions.Timeout:
        print("[Error] Hugging Face API request timed out after 90 seconds.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[Error] Hugging Face API request failed: {e}")
        return None
    except Exception as e:
         print(f"[Error] Unexpected error during API query: {e}")
         return None

async def generate_image(prompt: str):
    data_dir = "Data"
    try:
        os.makedirs(data_dir, exist_ok=True)
    except OSError as e:
        print(f"[Error] Failed to create directory '{data_dir}': {e}")
        return # Cannot proceed without directory
    
    tasks = []
    safe_prompt = prompt.replace(" ", "_").replace("\\", "_").replace("/", "_")

    print(f"Queueing 4 image generation tasks for prompt: '{prompt}'")
    for i in range(4):
        seed = randint(0, 1000000)
        payload = {
            "inputs": f"{prompt}, 4k, sharp, high detail, seed={seed}"
        }
        task = asyncio.create_task(query(payload))
        tasks.append(task)

    image_results = await asyncio.gather(*tasks)

    images_saved = 0
    for i, image_bytes in enumerate(image_results):
        if image_bytes is None:
             print(f"[Warning] Task {i+1} failed, skipping image save.")
             continue
        
        # Validate image data using PIL before saving
        try:
            with io.BytesIO(image_bytes) as img_buffer:
                 with Image.open(img_buffer) as img:
                     img.verify() # Check if PIL can understand the format
                 print(f"[Info] Task {i+1} returned valid image data.")
        except Exception as img_e:
            print(f"[Warning] Task {i+1} returned invalid/corrupted image data (PIL Error: {img_e}), skipping save.")
            continue
             
        file_path = os.path.join(data_dir, f"{safe_prompt}{i + 1}.jpg")
        try:
            with open(file_path, "wb") as f:
                f.write(image_bytes)
            print(f"Successfully saved image: {file_path}")
            images_saved += 1
        except IOError as e:
            print(f"[Error] Failed to write image file {file_path}: {e}")
        except Exception as e:
            print(f"[Error] Unexpected error saving image {file_path}: {e}")
            
    if images_saved == 0:
         print("[Error] Failed to save any generated images.")

def GenerateImages(prompt: str):
    # Clean up the prompt if it contains extra data
    prompt = prompt.strip()
    if not prompt:
        print("[Error] Empty prompt provided for image generation.")
        return
        
    print(f"Starting image generation process for prompt: {prompt}")
    try:
        # generate_image sanitizes the prompt internally for saving
        asyncio.run(generate_image(prompt))
        # Call open_images with the original (stripped) prompt
        # open_images will sanitize it again internally for opening
        open_images(prompt) 
    except Exception as e:
        print(f"[Error] Error during asyncio execution for image generation: {e}")

# Main loop - Added more specific error handling
if __name__ == "__main__":
    image_data_file = r"Frontend\Files\ImageGeneration.data"
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(image_data_file), exist_ok=True)
        
        # Check if the file exists, create it if not with default content
        if not os.path.exists(image_data_file):
            print(f"[Info] {image_data_file} not found, creating with default 'False, False'.")
            with open(image_data_file, "w", encoding='utf-8') as f:
                f.write("False, False")
                
        # Read the data
        with open(image_data_file, "r", encoding='utf-8') as f:
            Data = f.read().strip()
            
        if not Data:
            print(f"[Warning] {image_data_file} is empty. Assuming 'False, False'.")
            Data = "False, False"
            
        print(f"DEBUG: Raw content of data file: '{Data}'")
        
        # Improved splitting logic with better whitespace handling
        parts = [part.strip() for part in Data.split(",")]
        
        if len(parts) >= 2:
            Prompt, Status = parts[0], parts[1]
            print(f"DEBUG: Parsed prompt: '{Prompt}', Status: '{Status}'")
            
            # More robust status check
            if Status.lower() == "true":
                print(f"Found request to generate images for: '{Prompt}'")
                GenerateImages(prompt=Prompt)
                
                # Reset the flag file only after successful execution attempt
                try:
                    with open(image_data_file, "w", encoding='utf-8') as f:
                        f.write("False, False")
                    print(f"[Info] Reset {image_data_file} to 'False, False'.")
                except IOError as e:
                     print(f"[Error] Failed to reset {image_data_file}: {e}")
            else:
                print(f"[Info] No generation requested. Status is '{Status}' (not 'True').")
        else:
            print(f"[Error] Invalid data format in {image_data_file}: '{Data}'. Resetting to 'False, False'.")
            # Attempt to reset the file on format error
            try:
                with open(image_data_file, "w", encoding='utf-8') as f:
                    f.write("False, False")
            except IOError as e:
                 print(f"[Error] Failed to reset {image_data_file} after format error: {e}")
            
    except FileNotFoundError:
         print(f"[Error] Could not find or create {image_data_file}. Cannot proceed with image generation check.")
    except IOError as e:
         print(f"[Error] IOError accessing {image_data_file}: {e}")
    except Exception as e:
        print(f"[Error] An unexpected error occurred in image generation main block: {e}")
        # Optional: Attempt to reset the flag file in case of unexpected error
        try:
            if os.path.exists(image_data_file):
                with open(image_data_file, "w", encoding='utf-8') as f:
                    f.write("False, False")
        except Exception as reset_e:
             print(f"[Error] Failed during emergency reset of {image_data_file}: {reset_e}")
