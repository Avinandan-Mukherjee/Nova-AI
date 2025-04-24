import os
import cohere
from rich import print
import re
from groq import Groq
import random
import sys

# Access environment variables directly
Assistantname = os.environ.get("Assistantname", "Nova")
Username = os.environ.get("Username", "User")

# Initialize API clients and keys
GroqAPIKey = os.environ.get("GroqAPIKey", "")
CohereAPIKey = os.environ.get("CohereAPIKey", "")
GroqLLM = os.environ.get("GroqLLM", "llama3-8b-8192")

# Initialize global client variable
client = None
LLM = None

# Handle API client initialization with better error handling
co = None
if CohereAPIKey:
    try:
        co = cohere.Client(api_key=CohereAPIKey)
    except Exception as e:
        print(f"[Error] Failed to initialize Cohere client: {e}")

try:
    if GroqAPIKey:
        client = Groq(api_key=GroqAPIKey)
except Exception as e:
    print(f"[Error] Failed to initialize Groq client: {e}")

funcs = [
    "exit", "general", "realtime", "open", "close", "play", "generate image", "system", "content", "google search", "youtube search", "reminder"
]

messages = []

preamble = """
You are a very accurate Decision-Making Model, which decides what kind of a query is given to you.
You will decide whether a query is a 'general' query, a 'realtime' query, or is asking to perform any task or automation like 'open facebook, instagram', 'can you write a application and open it in notepad'
*** Do not answer any query, just decide what kind of query is given to you. ***
-> Respond with 'general ( query )' if a query can be answered by a llm model (conversational ai chatbot) and doesn't require any up to date information like if the query is 'who was akbar?' respond with 'general who was akbar?', if the query is 'how can i study more effectively?' respond with 'general how can i study more effectively?', if the query is 'can you help me with this math problem?' respond with 'general can you help me with this math problem?', if the query is 'Thanks, i really liked it.' respond with 'general thanks, i really liked it.' , if the query is 'what is python programming language?' respond with 'general what is python programming language?', etc. Respond with 'general (query)' if a query doesn't have a proper noun or is incomplete like if the query is 'who is he?' respond with 'general who is he?', if the query is 'what's his networth?' respond with 'general what's his networth?', if the query is 'tell me more about him.' respond with 'general tell me more about him.', and so on even if it require up-to-date information to answer. Respond with 'general (query)' if the query is asking about time, day, date, month, year, etc like if the query is 'what's the time?' respond with 'general what's the time?'.
-> Respond with 'realtime ( query )' if a query can not be answered by a llm model (because they don't have realtime data) and requires up to date information like if the query is 'who is indian prime minister' respond with 'realtime who is indian prime minister', if the query is 'tell me about facebook's recent update.' respond with 'realtime tell me about facebook's recent update.', if the query is 'tell me news about coronavirus.' respond with 'realtime tell me news about coronavirus.', etc and if the query is asking about any individual or thing like if the query is 'who is akshay kumar' respond with 'realtime who is akshay kumar', if the query is 'what is today's news?' respond with 'realtime what is today's news?', if the query is 'what is today's headline?' respond with 'realtime what is today's headline?', etc.
-> Respond with 'open (application name or website name)' if a query is asking to open any application like 'open facebook', 'open telegram', etc. but if the query is asking to open multiple applications, respond with 'open 1st application name, open 2nd application name' and so on.
-> Respond with 'close (application name)' if a query is asking to close any application like 'close notepad', 'close facebook', etc. but if the query is asking to close multiple applications or websites, respond with 'close 1st application name, close 2nd application name' and so on.
-> Respond with 'play (song name)' if a query is asking to play any song like 'play afsanay by ys', 'play let her go', etc. but if the query is asking to play multiple songs, respond with 'play 1st song name, play 2nd song name' and so on.
-> Respond with 'generate image (image prompt)' if a query is requesting to generate a image with given prompt like 'generate image of a lion', 'generate image of a cat', etc. but if the query is asking to generate multiple images, respond with 'generate image 1st image prompt, generate image 2nd image prompt' and so on.
-> Respond with 'reminder (datetime with message)' if a query is requesting to set a reminder like 'set a reminder at 9:00pm on 25th june for my business meeting.' respond with 'reminder 9:00pm 25th june business meeting'.
-> Respond with 'system (task name)' if a query is asking to mute, unmute, volume up, volume down , etc. but if the query is asking to do multiple tasks, respond with 'system 1st task, system 2nd task', etc.
-> Respond with 'content (topic)' if a query is asking to write any type of content like application, codes, emails or anything else about a specific topic but if the query is asking to write multiple types of content, respond with 'content 1st topic, content 2nd topic' and so on.
-> Respond with 'google search (topic)' if a query is asking to search a specific topic on google but if the query is asking to search multiple topics on google, respond with 'google search 1st topic, google search 2nd topic' and so on.
-> Respond with 'youtube search (topic)' if a query is asking to search a specific topic on youtube but if the query is asking to search multiple topics on youtube, respond with 'youtube search 1st topic, youtube search 2nd topic' and so on.
*** If the query is asking to perform multiple tasks like 'open facebook, telegram and close whatsapp' respond with 'open facebook, open telegram, close whatsapp' ***
*** If the user is saying goodbye or wants to end the conversation like 'bye jarvis.' respond with 'exit'.***
*** Respond with 'general (query)' if you can't decide the kind of query or if a query is asking to perform a task which is not mentioned above. ***
"""


ChatHistory = [
    {"role": "User", "message": "how are you?"},
    {"role": "Chatbot", "message": "general how are you?"},
    {"role": "User", "message": "do you like pizza?"},
    {"role": "Chatbot", "message": "general do you like pizza?"},
    {"role": "User", "message": "open chrome and tell me about mahatma gandhi."},
    {"role": "Chatbot", "message": "open chrome, general tell me about mahatma gandhi."},
    {"role": "User", "message": "open chrome and firefox."},
    {"role": "Chatbot", "message": "open chrome, open firefox."},
    {"role": "User", "message": "what is today's date and by the way remind me that i have a dance performance on 5th aug at 11pm."},
    {"role": "Chatbot", "message": "general what is today's date, reminder 11pm 5th aug dance performance."},
    {"role": "User", "message": "chat with me."},
    {"role": "Chatbot", "message": "general chat with me."},
]

def FirstLayerDMM(Query):
    """First-layer decision-making model that categorizes queries"""
    
    # Handle exit query
    if any(word in Query.lower() for word in ['exit program', 'exit app', 'exit nova', 'quit program', 'quit app', 'quit nova']):
        return ['exit']
    
    # Initialize results list for multi-command handling
    results = []
    Query_lower = Query.lower()
    
    # Handle image generation with higher priority
    image_generation_triggers = ['generate image', 'create image', 'make image', 'draw image', 'generate picture', 'create picture', 
                                'draw a picture', 'make a picture', 'generate a picture', 'create a picture', 
                                'draw me', 'generate an image', 'create an image', 'make an image']
    
    # Check for image generation first with complete scan
    for phrase in image_generation_triggers:
        if phrase in Query_lower:
            # Extract everything after the trigger as the image prompt
            generation_query = Query_lower.split(phrase, 1)[1].strip()
            if generation_query:
                results.append(f"generate image {generation_query}")
                # Return immediately to prevent additional processing
                return results
            else:
                results.append('general Please specify what kind of image you want to generate.')
                return results
    
    # Handle automation commands
    automation_triggers = {
        'open': ['open', 'launch', 'start', 'run'],
        'close': ['close', 'exit', 'quit', 'terminate', 'stop'],
        'play': ['play song', 'play music', 'play video', 'play'],
        'youtube search': ['youtube search', 'search youtube', 'find on youtube'],
        'google search': ['google search', 'search google', 'search for', 'look up'],
        'system': ['system', 'volume up', 'volume down', 'mute', 'unmute']
    }
    
    query_parts = Query_lower.split()
    for i in range(len(query_parts)):
        for action, triggers in automation_triggers.items():
            for trigger in triggers:
                trigger_words = trigger.split()
                if i + len(trigger_words) <= len(query_parts):
                    if " ".join(query_parts[i:i+len(trigger_words)]) == trigger:
                        # Found a trigger at position i
                        if i + len(trigger_words) < len(query_parts):
                            target = " ".join(query_parts[i+len(trigger_words):])
                            results.append(f"{action} {target}")
                            # Mark this part as processed by removing it
                            Query_lower = Query_lower.replace(trigger + " " + target, "").strip()
                        break
    
    # Handle realtime queries for specific patterns
    realtime_patterns = [
        'who is', 'what is', 'latest news', 'recent', 'current', 'today\'s', 
        'updates on', 'happening', 'events', 'weather', 'score', 'stock', 'price',
        'latest', 'terrorist', 'attack', 'news about', 'update on', 'know about',
        'views on', 'opinion on', 'situation'
    ]
    
    # Keywords that strongly indicate a realtime query is needed
    realtime_keywords = [
        'facebook', 'instagram', 'twitter', 'tiktok', 'covid', 'coronavirus', 
        'election', 'president', 'minister', 'government', 'war', 'crisis',
        'terrorist', 'attack', 'shooting', 'bombing', 'kashmir', 'ukraine', 
        'russia', 'china', 'usa', 'israel', 'palestine', 'india', 'pakistan',
        'latest', 'breaking', 'news', 'incident', 'disaster', 'event', 'political',
        'economy', 'market', 'stock', 'cryptocurrency', 'bitcoin', 'sports',
        'championship', 'tournament'
    ]
    
    remaining_text = Query_lower.strip()
    if remaining_text:
        # Check if query contains any pattern suggesting it needs real-time data
        has_realtime_pattern = any(pattern in Query_lower for pattern in realtime_patterns)
        
        # Check if query contains keywords strongly associated with current events
        has_realtime_keyword = any(keyword in Query_lower for keyword in realtime_keywords)
        
        # Mark as realtime if either condition is true
        if has_realtime_pattern or has_realtime_keyword:
            results.append(f"realtime {remaining_text}")
            remaining_text = ""
    
    # If anything remains and no results were added, make it a general query
    if not results or remaining_text:
        if remaining_text:
            results.append(f"general {remaining_text}")
        elif not results:
            # Default fallback if no specific triggers matched
            results.append(f"general {Query}")
    
    return results

if __name__ == "__main__":
    # Simple test
    test_queries = [
        "What's the weather like today?",
        "Tell me a joke",
        "Open Chrome",
        "Close Notepad",
        "exit program",
        "Generate image of a cat"
    ]
    
    for query in test_queries:
        result = FirstLayerDMM(query)
        print(f"Query: {query}")
        print(f"Result: {result}")
        print("---")