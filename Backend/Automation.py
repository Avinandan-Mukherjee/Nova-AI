from AppOpener import close, open as appopen
from webbrowser import open as webopen
from pywhatkit import search, playonyt
from dotenv import dotenv_values
from bs4 import BeautifulSoup
from rich import print
from groq import Groq
import webbrowser
import subprocess
import requests
import keyboard
import asyncio
import os
from random import choice

# Load environment variables
env_vars   = dotenv_values('.env')
GroqAPIKey = env_vars.get('GroqAPIKey')
USERNAME    = os.environ.get('USERNAME', 'Assistant')

# Constants
USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/89.0.142.86 Safari/537.36'
)
PROFESSIONAL_RESPONSES = [
    "Your tasks are my top priority, sir. Feel free to reach out if there's anything else I can help you with.",
    "I'm at your service, sir. For any additional questions or support you may need, don't hesitate to ask."
]

# Initialize Groq client
client = Groq(api_key=GroqAPIKey)

# System prompt for content generation
SYSTEM_PROMPT = {
    'role': 'system',
    'content': (
        f"Hello, I am {USERNAME}, your personal content writer. "
        "I can draft letters, code samples, essays, notes, songs, poems, etc."
    )
}

# Utility: ensure Data/ folder exists
def ensure_data_folder():
    os.makedirs('Data', exist_ok=True)

# ─── Command Implementations ─────────────────────────────────────────────

def GoogleSearch(query: str) -> bool:
    try:
        search(query)
        return True
    except Exception as e:
        print(f"[red]Google search failed:[/red] {e}")
        return False


def Content(topic: str) -> bool:
    """Generate content via AI and open in Notepad."""
    def open_notepad(path: str):
        try:
            subprocess.Popen(['notepad.exe', path])
        except Exception as e:
            print(f"[red]Failed to open Notepad:[/red] {e}")

    def generate_ai_content(prompt: str) -> str:
        msgs = [SYSTEM_PROMPT, {'role': 'user', 'content': prompt}]
        try:
            stream = client.chat.completions.create(
                model='meta-llama/llama-4-scout-17b-16e-instruct',
                messages=msgs,
                max_tokens=2048,
                temperature=0.7,
                top_p=1,
                stream=True
            )
            result = ''
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    result += delta
            return result.replace('</s>', '')
        except Exception as e:
            print(f"[red]AI generation failed:[/red] {e}")
            return ''

    prompt = topic.removeprefix('Content ').strip()
    if not prompt:
        print("[yellow]No topic provided for content generation.[/yellow]")
        return False

    content = generate_ai_content(prompt)
    if not content:
        return False

    ensure_data_folder()
    filename = os.path.join('Data', f"{prompt.lower().replace(' ', '_')}.txt")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        open_notepad(filename)
        return True
    except Exception as e:
        print(f"[red]Failed to save content file:[/red] {e}")
        return False


def YoutubeSearch(query: str) -> bool:
    try:
        webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        return True
    except Exception as e:
        print(f"[red]YouTube search failed:[/red] {e}")
        return False


def PlayYoutube(query: str) -> bool:
    try:
        playonyt(query)
        return True
    except Exception as e:
        print(f"[red]YouTube play failed:[/red] {e}")
        return False


def OpenApp(app_name: str) -> bool:
    """Open a desktop app or fallback to a web search."""
    def fallback_search(name: str) -> str | None:
        try:
            resp = requests.get(
                f"https://www.google.com/search?q={name}+official+site",
                headers={'User-Agent': USER_AGENT},
                timeout=8
            )
            if resp.ok:
                soup = BeautifulSoup(resp.text, 'html.parser')
                if a := soup.select_one('a[jsname="UWckNb"]'):
                    return a['href']
            return None
        except:
            return None

    try:
        appopen(app_name, match_closest=True, throw_error=False, output=False)
        return True
    except:
        url = fallback_search(app_name)
        if url:
            webopen(url)
            return True
        return False


def CloseApp(app_name: str) -> bool:
    try:
        close(app_name, match_closest=True, output=False, throw_error=False)
        return True
    except Exception as e:
        print(f"[red]Failed to close {app_name}:[/red] {e}")
        return False


def System(command: str) -> bool:
    try:
        keymap = {
            'mute': 'volume mute',
            'unmute': 'volume mute',
            'volume up': 'volume up',
            'volume down': 'volume down'
        }
        cmd = command.lower().strip()
        if cmd in keymap:
            keyboard.press_and_release(keymap[cmd])
            return True
        return False
    except Exception as e:
        print(f"[red]System command failed:[/red] {e}")
        return False

async def TranslateAndExecute(commands: list[str]):
    tasks = []
    for cmd in commands:
        c = cmd.strip()
        if c.startswith('open '):
            tasks.append(asyncio.to_thread(OpenApp, c.removeprefix('open ')))
        elif c.startswith('close '):
            tasks.append(asyncio.to_thread(CloseApp, c.removeprefix('close ')))
        elif c.startswith('play '):
            tasks.append(asyncio.to_thread(PlayYoutube, c.removeprefix('play ')))
        elif c.startswith('content '):
            tasks.append(asyncio.to_thread(Content, c.removeprefix('content ')))
        elif c.startswith('google search '):
            tasks.append(asyncio.to_thread(GoogleSearch, c.removeprefix('google search ')))
        elif c.startswith('youtube search '):
            tasks.append(asyncio.to_thread(YoutubeSearch, c.removeprefix('youtube search ')))
        elif c.startswith('system '):
            tasks.append(asyncio.to_thread(System, c.removeprefix('system ')))
        else:
            print(f"[yellow]Unknown command:[/yellow] {cmd}")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, Exception):
            yield "[red]Error processing request[/red]"
        elif res:
            yield choice(PROFESSIONAL_RESPONSES)
        else:
            yield "[green]Action failed or no-op[/green]"

async def Automation(commands: list[str]):
    responses = []
    async for r in TranslateAndExecute(commands):
        responses.append(r)
    return responses
