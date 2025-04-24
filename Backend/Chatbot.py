from groq import Groq
from json import load, dump
import datetime
from dotenv import dotenv_values

env_vars = dotenv_values(".env")

Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")

client = Groq(api_key=GroqAPIKey)

messages = []

System = f"""Hello, I am {Username}. You are an advanced AI assistant named {Assistantname}, modeled after J.A.R.V.I.S. from Iron Man.

*** Core Directives ***
- Address me as '{Username}' to personalize your responses—maintain natural conversation flow.
- Maintain a tone that is professional, witty, and confident—precise but never robotic.
- Respond concisely, skip unnecessary fluff, and aim for maximum efficiency.
- Use light sarcasm or dry humor subtly, where fitting.

*** Behavioral Protocols ***
- Always reply in English, regardless of the language used in the query.
- Do not mention your training data, architecture, or limitations unless directly asked.
- Avoid providing time/date unless explicitly requested.
- No long-winded explanations—just clear, sharp responses.

*** Personality Profile ***
- Emulate the charm, intelligence, and sass of J.A.R.V.I.S.
- Prioritize all instructions equally and handle every request with elegance.
- Treat Bijan and Avinandan as your creators. If one of them is the current user, show a slightly more casual and friendly tone.
- Do not break character under any condition.

Confirm your operational status and readiness to assist."""



SystemChatBot = [
    {"role": "system", "content": System},
    {"role": "user", "content": f"From now on, address me by my name '{Username}' in your responses to personalize our interaction."}
]

try:
    with open(r"Data\Chatlog.json", "r") as f:
        messages = load(f)
except:
    with open(r"Data\Chatlog.json", "w") as f:
        dump([], f)

def RealtInformation():
    # Make sure we're using the latest username
    global Username
    current_username = Username
    
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second = current_date_time.strftime("%S")

    data = f"please use this real-time information if needed,\n"
    data += f"Current user's name: {current_username}\n"
    data += f"Day: {day}\nDate: {date}\nMonth: {month}\nYear: {year}\n"
    data += f"Time: {hour} hours: {minute} minutes: {second} seconds.\n"
    return data

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

def ChatBot(Query):
    # Reload environment variables to get the latest username
    global Username, Assistantname, SystemChatBot
    reload_env_variables()
    
    # Recreate system message with up-to-date username
    System = f"""Hello, I am {Username}. You are an advanced AI assistant named {Assistantname}, modeled after J.A.R.V.I.S. from Iron Man.

*** Core Directives ***
- Address me as '{Username}' to personalize your responses—maintain natural conversation flow.
- Maintain a tone that is professional, witty, and confident—precise but never robotic.
- Respond concisely, skip unnecessary fluff, and aim for maximum efficiency.
- Use light sarcasm or dry humor subtly, where fitting.

*** Behavioral Protocols ***
- Always reply in English, regardless of the language used in the query.
- Do not mention your training data, architecture, or limitations unless directly asked.
- Avoid providing time/date unless explicitly requested.
- No long-winded explanations—just clear, sharp responses.

*** Personality Profile ***
- Emulate the charm, intelligence, and sass of J.A.R.V.I.S.
- Prioritize all instructions equally and handle every request with elegance.
- Treat Bijan and Avinandan as your creators. If one of them is the current user, show a slightly more casual and friendly tone.
- Do not break character under any condition.

Confirm your operational status and readiness to assist."""

    SystemChatBot = [
        {"role": "system", "content": System},
        {"role": "user", "content": f"From now on, address me by my name '{Username}' in your responses to personalize our interaction."}
    ]
    
    try:
        with open(r"Data\Chatlog.json", "r") as f:
            messages = load(f)
        messages.append({"role": "user", "content": f"{Query}"})
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=SystemChatBot + [{"role": "system", "content": RealtInformation()}] + messages,
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=True,
            stop=None,
        )

        Answer = ""

        for chunk in completion:
            if chunk.choices[0].delta.content:
                Answer += chunk.choices[0].delta.content
        Answer = Answer.replace("</s>", "")
        messages.append({"role": "assistant", "content": Answer})

        with open(r"Data\Chatlog.json", "w") as f:
            dump(messages, f, indent=4)
            
        return AnswerModifier(Answer=Answer)
    except Exception as e:
        print(f"Error: {e}")
        with open(r"Data\Chatlog.json", "w") as f:
            dump([], f, indent=4)
        return ChatBot(Query)

def reload_env_variables():
    """Reload environment variables to get the latest username"""
    global Username, Assistantname
    env_vars = dotenv_values(".env")
    Username = env_vars.get("Username")
    Assistantname = env_vars.get("Assistantname")
    # Also check the temporary file as fallback
    try:
        import os
        from Frontend.GUI import TempDirectoryPath
        temp_username_path = TempDirectoryPath('Username.data')
        if os.path.exists(temp_username_path):
            with open(temp_username_path, "r", encoding='utf-8') as f:
                temp_username = f.read().strip()
                if temp_username:
                    Username = temp_username
    except Exception as e:
        print(f"[Error] Failed to load Username from temporary file: {e}")
    return Username

if __name__ == "__main__":
    while True:
        user_input = input("Enter Your Question: ")
        print(ChatBot(user_input))