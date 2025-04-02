import speech_recognition as sr
import webbrowser
import pyttsx3
import musicLibrary
from google.generativeai import configure, GenerativeModel
from gtts import gTTS
import pygame
import os
import pyautogui


# Initialize recognizer and text-to-speech engine
recognizer = sr.Recognizer()
engine = pyttsx3.init()

# Gemini API Configuration
GEMINI_API_KEY = "AIzaSyCsSapWeuOe7psNqDL4GaRrLJIgvYvoKqA"
configure(api_key=GEMINI_API_KEY)
model = GenerativeModel("gemini-2.0-flash")

# Initialize pygame mixer


def init_mixer():
    pygame.mixer.init()


def ai_process(command):
    """Handle commands using Gemini API with short responses"""
    try:
        modified_prompt = f"Respond very briefly (2-3 sentences max): {command}"
        response = model.generate_content(
            modified_prompt,
            generation_config={"max_output_tokens": 200}
        )
        return response.text if hasattr(response, 'text') else "I'll keep it short: Can't process that."
    except Exception as e:
        print(f"API Error: {e}")
        return "Brief update: Error occurred."


def speak(text):
    """Improved text-to-speech function using gTTS"""
    tts = gTTS(text=text, lang='en')
    tts.save('temp.mp3')

    init_mixer()
    pygame.mixer.music.load('temp.mp3')
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

    pygame.mixer.music.unload()
    os.remove("temp.mp3")


def process_command(command):
    """Process user commands"""
    command_lower = command.lower()

    if "open google" in command_lower:
        webbrowser.open("https://google.com")
    elif "open facebook" in command_lower:
        webbrowser.open("https://facebook.com")
    elif "open youtube" in command_lower:
        webbrowser.open("https://youtube.com")
    elif "open linkedin" in command_lower:
        webbrowser.open("https://linkedin.com")
    elif command_lower.startswith("play"):
        song = command_lower.split(" ", 1)[1]
        link = musicLibrary.music.get(song)
        if link:
            webbrowser.open(link)
        else:
            speak("Sorry, I couldn't find that song.")
    elif "stop song" in command_lower:
        speak("Stopping the song.")
        pyautogui.hotkey("space")
    elif "song play" in command_lower:
        speak("Playing the song.")
        pyautogui.hotkey("space")

    else:
        output = ai_process(command)
        print(f"AI Response: {output}")
        speak(output)


if __name__ == "__main__":
    speak("Initializing Elina... Say 'Elina' to start.")

    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Waiting for 'Elina' to start listening...")

        while True:
            try:
                # Listen for the wake word "Spider"
                audio = recognizer.listen(
                    source, timeout=5, phrase_time_limit=3)
                wake_word = recognizer.recognize_google(audio).lower()

                if "spider" in wake_word:
                    speak("Yes sir, I am listening.")
                    print("Elina activated! Listening for commands...")

                    while True:  # Keep listening for commands
                        try:
                            audio = recognizer.listen(source)
                            command = recognizer.recognize_google(audio)
                            process_command(command)
                        except sr.UnknownValueError:
                            pass
                        except Exception as e:
                            print(f"Error: {e}")

            except sr.UnknownValueError:
                pass
            except Exception as e:
                print(f"Error: {e}")
