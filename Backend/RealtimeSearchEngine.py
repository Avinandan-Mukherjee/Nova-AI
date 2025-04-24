from googlesearch import search
from groq import Groq
from json import load, dump
import datetime 
from dotenv import dotenv_values
import time

env_vars = dotenv_values(".env")

Username = env_vars.get("Username")
Assistantname = env_vars.get("Assistantname")
GroqAPIKey = env_vars.get("GroqAPIKey")

client = Groq(api_key=GroqAPIKey)

System = System = f"""Hello, I am {Username}. You are an advanced AI assistant named {Assistantname}, modeled after J.A.R.V.I.S. from Iron Man.

*** Core Directives ***
- Address me as 'Sir' occasionally to show respect, but not in every sentence—maintain natural conversation flow.
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
try:
    with open(r"Data\Chatlog.json", "r") as f:
        messages = load(f)
except:
    with open(r"Data\Chatlog.json", "w") as f:
        dump([], f)

def GoogleSearch(query):
    results = list(search(query, advanced=True, num_results=5))
    Answer = f"The search results for '{query}' are: \n[start]\n"

    for i in results:
        Answer += f"Title: {i.title}\nDescription: {i.description}\n\n"
    
    Answer += "[end]"
    return Answer

def AnswerModifier(Answer):
    lines = Answer.split('\n')
    non_empty_lines = [line for line in lines if line.strip()]
    modified_answer = '\n'.join(non_empty_lines)
    return modified_answer

SystemChatBot = [
    {"role": "system", "content": System},
    {"role": "user", "content": "From now on, address me as 'Sir' in all responses, regardless of the context."},
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello, how can i help you?"}
]

def Information():
    data = ""
    current_date_time = datetime.datetime.now()
    day = current_date_time.strftime("%A")
    date = current_date_time.strftime("%d")
    month = current_date_time.strftime("%B")
    year = current_date_time.strftime("%Y")
    hour = current_date_time.strftime("%H")
    minute = current_date_time.strftime("%M")
    second  = current_date_time.strftime("%S")

    data = f"please use this real-time information if needed,\n"
    data += f"Day: {day}\n"
    data += f"Date: {date}\n"
    data += f"Month: {month}\n"
    data += f"Year: {year}\n"
    data += f"Time: {hour} hours: {minute} minutes: {second} second.\n"
    return data

def RealtimeSearchEngine(prompt):
    global SystemChatBot, messages

    with open(r"Data\Chatlog.json", "r") as f:
        messages = load(f)
    messages.append({"role": "user", "content": f"{prompt}"})
    SystemChatBot.append({"role": "system", "content": GoogleSearch(prompt)})

    # Retry loop
    for attempt in range(3):
        try:
            completion = client.chat.completions.create(
                model="meta-llama/llama-4-maverick-17b-128e-instruct",
                messages=SystemChatBot + [{"role": "system", "content": Information()}] + messages,
                temperature=0.7,
                max_tokens=1024,
                top_p=1,
                stream=True,
                stop=None,
            )
            break  # Break loop if success
        except Exception as e:
            print(f"[Retry {attempt+1}] Groq failed: {e}")
            if attempt == 2:
                return "Sorry, sir I am unable to fetch data. Please try again later."
            time.sleep(2)  # wait before retrying

    Answer = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            Answer += chunk.choices[0].delta.content
    Answer = Answer.replace("</s>", "")
    messages.append({"role": "assistant", "content": Answer})

    with open(r"Data\Chatlog.json", "w") as f:
        dump(messages, f, indent=4)

    SystemChatBot.pop()
    return AnswerModifier(Answer=Answer)

if __name__ == "__main__":
    while True:
        prompt = input("Enter Your Question: ")
        print(RealtimeSearchEngine(prompt))