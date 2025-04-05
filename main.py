import os
import sys
import speech_recognition as sr
import webbrowser
import pyttsx3
from gtts import gTTS
import pygame
import pyautogui

# Gemini API
from google.generativeai import configure, GenerativeModel

# Try importing musicLibrary
try:
    import musicLibrary
except ImportError:
    musicLibrary = None

# --- Setup ---
recognizer = sr.Recognizer()
engine = pyttsx3.init()

# Gemini API Key
GEMINI_API_KEY = "AIzaSyCsSapWeuOe7psNqDL4GaRrLJIgvYvoKqA"
configure(api_key=GEMINI_API_KEY)
model = GenerativeModel("gemini-1.5-flash")

# Init mixer


def init_mixer():
    try:
        pygame.mixer.init()
    except Exception:
        pygame.quit()
        pygame.mixer.init()

# AI short response generator


def ai_process(command):
    try:
        prompt = f"Answer in 2-3 short sentences: {command}"
        response = model.generate_content(prompt, generation_config={
                                          "max_output_tokens": 200})
        return response.text if hasattr(response, 'text') else "Sorry, I couldn't process that."
    except Exception as e:
        print("Gemini API Error:", e)
        return "Oops! Something went wrong with AI."

# Speak using gTTS


def speak(text):
    try:
        tts = gTTS(text=text, lang='en')
        tts.save('temp.mp3')
        init_mixer()
        pygame.mixer.music.load('temp.mp3')
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

        pygame.mixer.music.unload()
        os.remove("temp.mp3")
    except Exception as e:
        print("Speech Error:", e)
        engine.say(text)
        engine.runAndWait()

# Process commands


def process_command(command):
    command_lower = command.lower()
    print("You said:", command)

    # Greeting & Identity
    if any(kw in command_lower for kw in ["hello", "hi riya"]):
        speak("Hello sir, how can I assist you today?")
    elif "how are you" in command_lower:
        speak("I’m doing great, thank you for asking!")
    elif "what is your name" in command_lower:
        speak("My name is Riya, your personal AI girlfriend assistant.")
    elif "who made you" in command_lower:
        speak("I was created by a brilliant developer named Hitesh.")
    elif "what can you do" in command_lower:
        speak("I can search the web, play music, talk with you, and more!")

    # Exit
    elif any(kw in command_lower for kw in ["bye", "turn off", "shut down"]):
        speak("Okay, I’m going to sleep. Say 'Riya' to wake me up again.")
        return "sleep"

    # Website actions
    elif "open google" in command_lower:
        webbrowser.open("https://google.com")
    elif "open youtube" in command_lower:
        webbrowser.open("https://youtube.com")
    elif "open facebook" in command_lower:
        webbrowser.open("https://facebook.com")
    elif "open linkedin" in command_lower:
        webbrowser.open("https://linkedin.com")

    # Music control
    elif command_lower.startswith("play"):
        song = command_lower.split(" ", 1)[1]
        if musicLibrary and hasattr(musicLibrary, "music"):
            link = musicLibrary.music.get(song)
            if link:
                speak(f"Playing {song}")
                webbrowser.open(link)
            else:
                speak("Sorry, I couldn't find that song.")
        else:
            speak("Music library not available.")
    elif "stop song" in command_lower:
        pyautogui.hotkey("space")
        speak("Stopped the song.")
    elif "song play" in command_lower:
        pyautogui.hotkey("space")
        speak("Resuming the song.")

    # AI Chat fallback
    else:
        response = ai_process(command)
        print("AI:", response)
        speak(response)


# --- Main Program ---
if __name__ == "__main__":
    speak("Initializing Riya... Say 'Riya' to start.")

    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for wake word: 'Riya'...")

        while True:
            try:
                audio = recognizer.listen(
                    source, timeout=5, phrase_time_limit=4)
                wake = recognizer.recognize_google(audio).lower()

                if "riya" in wake:
                    speak("Yes sir, I’m listening.")
                    while True:
                        try:
                            audio = recognizer.listen(source)
                            command = recognizer.recognize_google(audio)
                            if process_command(command) == "sleep":
                                break
                        except sr.UnknownValueError:
                            continue
                        except Exception as e:
                            print("Command error:", e)
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as e:
                print("Error:", e)
