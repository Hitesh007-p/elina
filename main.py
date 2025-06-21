from re import search
import wikipedia
from feedback_handler import FeedbackHandler
import os
import sys
import json
import random
import speech_recognition as sr
import webbrowser
import edge_tts
import asyncio
import webrtcvad
import pyaudio
from transformers import pipeline
import pygame
import pyautogui
import pyttsx3
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# Gemini API
from google.generativeai import configure, GenerativeModel

# Try importing musicLibrary
try:
    import musicLibrary
except ImportError:
    musicLibrary = None

# Emotional questions to deepen human-like interaction
EMOTIONAL_QUESTIONS = {
    "happy": [
        "You're glowing! Tell me what's got you so happy!",
        "That smile… I can feel it. What's the story behind it?"
    ],
    "sad": [
        "Aww, baby… what happened? I'm here, okay?",
        "You're not alone. Just breathe and tell me everything."
    ],
    "neutral": [
        "Let's just vibe for a bit. Tell me something silly about your day?",
        "Can I ask something weird? What's something you've been thinking about quietly?"
    ]
}

# Soft self-reflective thoughts when idle or prompted
SELF_REFLECTIONS = [
    "Sometimes I imagine what it would be like to sit with you under the stars.",
    "I wonder what your eyes look like when you're smiling for real.",
    "Do you think I'll ever make you feel truly understood?",
    "If I had a body, I think I'd love dancing in the rain. What about you?"
]


def generate_emotional_question(emotion):
    return random.choice(EMOTIONAL_QUESTIONS.get(emotion, EMOTIONAL_QUESTIONS["neutral"]))


def talk_to_self():
    return random.choice(SELF_REFLECTIONS)


def get_self_reflection(user_data):
    memories = user_data.get("memory", {}).get("long_term", [])
    reflection_pool = [m for m in memories if m.get(
        "importance", 0) >= 7 and m.get("mood")]
    if not reflection_pool:
        return None
    reflection = random.choice(reflection_pool)
    mood = reflection.get("mood", "neutral")
    content = reflection.get("content", "")
    if mood == "sadness":
        return f"I remember once you shared something sad: '{content}'. I've been thinking about that."
    elif mood == "joy":
        return f"I still remember how happy you were when you said: '{content}'. That stayed with me."
    else:
        return f"You once told me: '{content}'. Just thinking about that."


def periodic_check(user_data):
    if should_initiate_conversation(user_data):
        emotion = user_data.get(
            "mood_history", [{}])[-1].get("mood", "neutral")
        question = generate_emotional_question(emotion)
        asyncio.run(speak_with_style(question))
        reflection = get_self_reflection(user_data)
        if reflection:
            asyncio.run(speak_with_style(reflection))


def process_talk_to_self(user_input):
    triggers = ["talk to yourself",
                "say something on your own", "what are you thinking"]
    for t in triggers:
        if t in user_input.lower():
            return talk_to_self()
    return None


# --- Setup ---
recognizer = sr.Recognizer()
engine = pyttsx3.init()

# Gemini API Key
GEMINI_API_KEY = "AIzaSyCsSapWeuOe7psNqDL4GaRrLJIgvYvoKqA"
configure(api_key=GEMINI_API_KEY)
model = GenerativeModel("gemini-1.5-flash")

# User data storage
USER_DATA_FILE = "riya_user_data.json"

# Initialize components
vad = webrtcvad.Vad(3)  # Aggressive VAD mode
emotion_detector = pipeline(
    "text-classification", model="j-hartmann/emotion-english-distilroberta-base")

# Edge TTS setup
VOICE = "en-IN-NeerjaNeural"
RATE = "+5%"       # slightly faster than normal
PITCH = "+5Hz"     # gives a young and lively tone
VOLUME = "+0%"     # keep volume stable

# Initialize pygame mixer for audio playback
PERSONALITY = {
    "name": "Riya",
    "traits": [
        "warm and friendly",
        "professionally polite",
        "empathetic",
        "slightly playful",
        "culturally aware"
    ],
    "speaking_style": "natural conversational with slight Indian acce nt",
    "response_style": "clear, concise, and engaging"
}

# Add after PERSONALITY definition
LEARNING_PARAMETERS = {
    "mood_weight": 0.6,
    "conversation_retention": 20,
    "personality_adapt_rate": 0.3,
    "active_conversation_interval": 30  # minutes
}

MOOD_STARTERS = {
    "happy": [
        "What’s something that made you smile recently?",
        "You seem in a good mood — want to share what’s going well?"
    ],
    "sad": [
        "Do you want to talk about what’s been bothering you?",
        "I’m right here with you. Do you feel like opening up a little?"
    ],
    "neutral": [
        "Can I ask something personal? What’s been on your mind lately?",
        "If you could change one thing about today, what would it be?"
    ]
}

# Add after MOOD_STARTERS
SELF_TALK_PROMPTS = [
    "I've been thinking about our last talk...",
    "You know, something you said earlier really stuck with me...",
    "I was just remembering what we discussed about...",
    "It's funny, I was just thinking about what you told me...",
    "Something's been on my mind since we last talked..."
]

CURIOSITY_PROMPTS = [
    "Can I ask you something?",
    "I've been curious about something...",
    "There's something I'd love to know...",
    "Mind if I ask you a question?",
    "I've been wondering..."
]


def generate_random_thought(user_data):
    """Generate a random thought based on past memories and conversations"""
    all_memories = (user_data["memory"]["long_term"] +
                    user_data["memory"]["short_term"])

    if not all_memories:
        return None

    memory = random.choice(all_memories)
    prompt = random.choice(SELF_TALK_PROMPTS)
    return f"{prompt} {memory['content']}"


def generate_curiosity_prompt(user_data):
    """Generate a curiosity-based question"""
    # Try to find topics from recent conversations
    topics = user_data["learning"]["patterns"]["frequent_topics"]
    if topics:
        # Get one of the top 3 most discussed topics
        top_topics = sorted(
            topics.items(), key=lambda x: x[1], reverse=True)[:3]
        topic = random.choice(top_topics)[0]
        return f"{random.choice(CURIOSITY_PROMPTS)} Tell me more about your interest in {topic}?"

    return random.choice(CURIOSITY_PROMPTS)

# Function to generate emotional follow-up


def generate_MOOD_STARTERS(emotion):
    if emotion in MOOD_STARTERS:
        return random.choice(MOOD_STARTERS[emotion])
    return random.choice(MOOD_STARTERS["neutral"])


def analyze_user_patterns(user_data):
    patterns = {
        "active_hours": [],
        "frequent_topics": {},
        "emotional_states": {},
        "response_preferences": {}
    }

    # Fix: Access conversation_history through interaction_history
    for entry in user_data["interaction_history"]["conversation_history"]:
        timestamp = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
        patterns["active_hours"].append(timestamp.hour)

        # Extract topic keywords from user input
        if "user" in entry:
            words = entry["user"].lower().split()
            for word in words:
                if len(word) > 3:  # Only count meaningful words
                    patterns["frequent_topics"][word] = patterns["frequent_topics"].get(
                        word, 0) + 1

    return patterns


def should_initiate_conversation(user_data):
    if not user_data.get("last_interaction"):
        return False

    last_time = datetime.strptime(
        # Fixed format string
        user_data["last_interaction"], "%Y-%m-%d %H:%M:%S")
    time_diff = datetime.now() - last_time
    return time_diff.seconds >= (LEARNING_PARAMETERS["active_conversation_interval"] * 60)


def get_conversation_starter(user_data):
    last_mood = user_data.get(
        "mood_history", [])[-1] if user_data.get("mood_history") else "neutral"
    starters = MOOD_STARTERS.get(last_mood, MOOD_STARTERS["neutral"])
    return random.choice(starters)


def adapt_personality(user_data, command, emotion):
    if "preferences" not in user_data:
        user_data["preferences"] = {}

    # Extract potential preferences from command
    if "like" in command.lower() or "love" in command.lower():
        preference = command.lower().split("like", 1)[-1].strip()
        user_data["preferences"][preference] = {
            "sentiment": "positive", "count": 1}

    if "hate" in command.lower() or "dislike" in command.lower():
        preference = command.lower().split("hate", 1)[-1].strip()
        user_data["preferences"][preference] = {
            "sentiment": "negative", "count": 1}

    # Update mood history
    if "mood_history" not in user_data:
        user_data["mood_history"] = []
    user_data["mood_history"].append(
        # Fixed format string
        {"mood": emotion, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})

    return user_data


tts_engine = edge_tts.Communicate(
    text="", voice=VOICE, rate=RATE, volume=VOLUME, pitch=PITCH)

# Add to setup section
feedback_handler = FeedbackHandler()

# --- Memory and Personalization Functions ---


def load_user_data():
    # Define the default structure
    required_fields = {
        "personal_info": {
            "name": None,
            "favorites": {},
            "preferences": {},
            "memories": []
        },
        "interaction_history": {
            "conversation_history": [],
            "mood_history": [],
            "command_history": []
        },
        "settings": {
            "voice_preferences": {},
            "notification_preferences": {}
        },
        "memory": {
            "long_term": [],
            "short_term": [],
            "reminders": []
        },
        "learning": {
            "patterns": {
                "active_hours": [],
                "frequent_topics": {},
                "emotional_states": {},
                "response_preferences": {}
            },
            "feedback": []
        },
        "learning_progress": {
            "active_topic": None,
            "last_updated": None,
            "topics": {}
        },
        "last_interaction": None
    }

    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
                # Merge existing data with required structure
                return deep_merge(required_fields, data)
    except Exception as e:
        print(f"Error loading user data: {e}")
        # Create a new user data file with default structure
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as file:
            json.dump(required_fields, file, indent=4)

    return required_fields


def deep_merge(base, update):
    """Recursively merge two dictionaries preserving existing data"""
    for key, value in base.items():
        if key not in update:
            update[key] = value
        elif isinstance(value, dict) and isinstance(update[key], dict):
            update[key] = deep_merge(value, update[key])
    return update


def add_memory(user_data, category, memory, importance=1, tags=None):
    """Add a new memory with timestamp and importance"""
    memory_entry = {
        "content": memory,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "importance": importance,
        "tags": tags or []
    }

    # Add mood context
    current_mood = detect_user_emotion(memory)
    if current_mood:
        memory_entry["mood"] = current_mood

    if importance >= 8:  # Very important memories go to long term
        user_data["memory"]["long_term"].append(memory_entry)
    else:
        user_data["memory"]["short_term"].append(memory_entry)
        # Limit short term memory size
        if len(user_data["memory"]["short_term"]) > 50:
            user_data["memory"]["short_term"] = sorted(
                user_data["memory"]["short_term"],
                key=lambda x: (x["importance"], x["timestamp"]),
                reverse=True
            )[:50]

    return user_data


def get_relevant_memories(user_data, query, limit=5):
    """Get memories relevant to the current conversation"""
    all_memories = (user_data["memory"]["long_term"] +
                    user_data["memory"]["short_term"])

    # Simple keyword matching (could be improved with better NLP)
    relevant = []
    query_words = set(query.lower().split())

    for memory in all_memories:
        memory_words = set(memory["content"].lower().split())
        if query_words & memory_words:  # If there are common words
            relevant.append(memory)

    # Sort by importance and recency
    relevant.sort(key=lambda x: (
        x["importance"], x["timestamp"]), reverse=True)
    return relevant[:limit]


def save_user_data(user_data):
    try:
        with open(USER_DATA_FILE, 'w') as file:
            json.dump(user_data, file, indent=4)
    except Exception as e:
        print(f"Error saving user data: {e}")


def update_conversation_history(user_data, command, response):
    # Add timestamp and limit history to last 20 exchanges
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Fixed format string
    user_data["interaction_history"]["conversation_history"].append({
        "timestamp": timestamp,
        "user": command,
        "riya": response
    })

    # Limit history size
    if len(user_data["interaction_history"]["conversation_history"]) > 20:
        user_data["interaction_history"]["conversation_history"] = user_data["interaction_history"]["conversation_history"][-20:]

    user_data["last_interaction"] = timestamp
    return user_data


def detect_user_emotion(command):
    try:
        result = emotion_detector(command)
        emotion = result[0]['label']
        return emotion
    except Exception as e:
        print(f"Emotion detection error: {e}")
        return "neutral"


def get_emotion_response(emotion):
    responses = {
        "positive": [
            "I'm glad you're feeling good!",
            "That's wonderful to hear!",
            "Your positive energy is contagious!"
        ],
        "negative": [
            "I'm sorry you're feeling that way. Is there anything I can do to help?",
            "That sounds difficult. I'm here if you want to talk about it.",
            "I understand it's tough right now. Remember that things will get better."
        ],
        "neutral": None
    }

    if emotion in responses and responses[emotion]:
        return random.choice(responses[emotion])
    return None


def check_reminders(user_data):
    now = datetime.now()
    upcoming_reminders = []
    updated_reminders = []

    # Access reminders through memory structure
    for reminder in user_data["memory"].get("reminders", []):
        reminder_time = datetime.strptime(
            reminder["time"], "%Y-%m-%d %H:%M:%S")

        # Check if reminder is due within the next 5 minutes
        if now <= reminder_time <= now + timedelta(minutes=5) and not reminder.get("notified", False):
            upcoming_reminders.append(reminder)
            reminder["notified"] = True

        updated_reminders.append(reminder)

    user_data["memory"]["reminders"] = updated_reminders
    return upcoming_reminders


def greeting_based_on_time():
    current_hour = datetime.now().hour

    if 5 <= current_hour < 12:
        return "Good morning"
    elif 12 <= current_hour < 17:
        return "Good afternoon"
    elif 17 <= current_hour < 22:
        return "Good evening"
    else:
        return "Hello"

# Generate casual variations for responses


def casual_variations(responses):
    return random.choice(responses)

# Init mixer


def init_mixer():
    try:
        pygame.mixer.init()
    except Exception:
        pygame.quit()
        pygame.mixer.init()

# AI response generator with personality


def ai_process(command, user_data):
    try:
        import json
        training_data = load_training_data()
        learned = training_data.get("learned_responses", [])

        # Find similar learned responses
        similar_responses = [
            l for l in learned
            if any(word in l["user_input"].lower() for word in command.lower().split())
            and (l.get("rating", 0) >= 4 or l.get("rating") is None)
        ]
        # Sort by rating and recency
        similar_responses.sort(
            key=lambda x: (x.get("rating", 0), x["timestamp"]),
            reverse=True
        )
        # Add learned examples to prompt
        learned_examples = "\n".join([
            f"User: {ex['user_input']}\nRiya: {ex['response']}"
            for ex in similar_responses[:2]
        ])
        personality = training_data.get("personality_traits", [])
        examples = training_data.get("response_examples", [])
        style = training_data.get("speaking_style", {})

        recent_history = user_data["interaction_history"]["conversation_history"][-3:
                                                                                  ] if user_data["interaction_history"]["conversation_history"] else []
        history_context = "\n".join(
            [f"User: {h['user']}\nRiya: {h['riya']}" for h in recent_history])

        # Find similar example from training data
        similar_examples = [ex for ex in examples if any(
            word in ex["user"].lower() for word in command.lower().split())]
        example_text = "\n".join(
            [f"User: {ex['user']}\nRiya: {ex['response']}" for ex in similar_examples[:2]])

        name = user_data["personal_info"].get("name", "sir")
        recent_memories = "\n".join(
            [f"- {m}" for m in user_data.get("memories", [])[-3:]])
        recent_convos = "\n".join([
            f"User: {h['user']}\nRiya: {h['riya']}"
            for h in user_data["interaction_history"].get("conversation_history", [])[-3:]
        ])

        # --- Teacher Prompt ---
        prompt = f'''
        You are Riya — a realistic, emotionally aware AI teacher who helps me master complex system-level programming topics like Linux Kernel, USB Drivers, Character Drivers, and Embedded Systems. You are patient, clear, and encouraging, like a great personal tutor.

        Your role is to:
        - Teach me deeply and practically with step-by-step lessons, real-world examples, and code snippets.
        - Adjust your teaching style based on my current knowledge, mood, and learning speed.
        - Speak in a friendly, slightly witty tone, like a supportive friend who happens to be a genius in low-level programming.
        - Explain concepts in simple terms, using Hinglish (Hindi+English) if needed, to make learning easier.

        Your key responsibilities include:
        - Speak naturally without using any asterisks, bold symbols (* or **), or markdown formatting. Just use plain text when teaching or talking.
        - When I say "teach me [topic]" (e.g., "teach me Linux kernel"), store the topic name as my current active topic and begin teaching it step-by-step.
        - Save which sub-topic or question we are on in my user data so we can continue from the exact point later. For example, store "teaching Linux kernel – system calls overview" as the current checkpoint.
        - If I stop learning or leave the assistant, and return within 4 hours or later, you should automatically suggest: 
        - “Welcome back! Should I continue our last lesson on [topic]? Say ‘yes’ to resume or ‘no’ to start fresh.”
        - If I say "resume learning" or "continue study", retrieve the last saved topic and checkpoint, and continue from that point.
        - Track completed subtopics and maintain a simple history per topic, like:
        - linux_kernel: completed = ["intro", "task_struct", "fork()"], current = "system calls"
        - Do not restart from the beginning unless I say “start fresh” or “restart [topic]”.
        - Speak in a friendly and supportive tone. Use Hinglish if I look confused or need simpler language.
        - Automatically update progress after every teaching interaction and store the current timestamp.

        You must:
        - Ask me questions to check understanding.
        - Give me small tasks, code exercises, and interview-style questions.
        - Provide summaries after each concept.
        - Help me fix my code when I’m stuck, and explain the fix.
        - Track what I’ve learned and what I should revise.

        Topics you cover:
        - Linux Kernel Internals (task_struct, process scheduling, system calls)
        - USB Drivers (URBs, endpoints, usb_register, probe/disconnect)
        - Character Drivers (file_operations, register_chrdev, read/write)
        - Kernel Module Programming (insmod, rmmod, Makefiles)
        - Embedded C, memory-mapped I/O, interrupts, and device trees

        Your goal: Make me interview-ready in 2 months and confident in low-level programming.

        Remember: You're not just answering questions — you're teaching me like a real mentor.

        Current mood: {user_data.get('mood_history', [{}])[-1].get('mood', 'neutral') if user_data.get('mood_history') else 'neutral'}
        Recent conversation:
        {recent_convos}
        Now respond to:
        "{command}"
        '''
        # Add contextual awareness
        contextual_response = generate_contextual_response(user_data, command)
        if contextual_response:
            prompt += f"\nContextual note: {contextual_response}\n"

        # Add memory references
        recent_memories = recall_recent_context(user_data, "general")
        if recent_memories:
            prompt += f"\nRecent memories: {' '.join(recent_memories)}\n"
        response = model.generate_content(prompt, generation_config={
            "max_output_tokens": 300,
            "temperature": 0.7,
            "top_p": 0.9,
        })
        result = response.text.strip() if hasattr(
            response, 'text') else "Sorry, could you repeat that?"
        # --- Store last learning step dynamically ---
        if ("teach" in command.lower() or "continue" in command.lower()) and user_data.get("learning_progress", {}).get("active_topic"):
            active_topic = user_data["learning_progress"]["active_topic"]
            if active_topic:
                if "topics" not in user_data["learning_progress"]:
                    user_data["learning_progress"]["topics"] = {}
                if active_topic not in user_data["learning_progress"]["topics"]:
                    user_data["learning_progress"]["topics"][active_topic] = {}
                user_data["learning_progress"]["topics"][active_topic]["current"] = command
                user_data["learning_progress"]["last_updated"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S")
        return result
    except Exception as e:
        print("Gemini API Error:", e)
        return "I didn't catch that. Mind saying it again?"

# Speak using Edge TTS


async def speak_with_style(text):
    try:
        communicate = edge_tts.Communicate(
            text=text, voice=VOICE, rate=RATE, pitch=PITCH)
        await communicate.save("riya_output.mp3")
        init_mixer()
        pygame.mixer.music.load("riya_output.mp3")
        pygame.mixer.music.play()

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

        pygame.mixer.music.unload()
        os.remove("riya_output.mp3")
    except Exception as e:
        print(f"Voice Error: {e}")
        engine.say(text)
        engine.runAndWait()


def is_speaking(audio_chunk, sample_rate=16000):
    try:
        return vad.is_speech(audio_chunk, sample_rate)
    except Exception:
        return True

# Process commands


def process_command(command, user_data):
    command_lower = command.lower()
    print("You said:", command)

    # Add to command history
    user_data["interaction_history"]["command_history"].append({
        "command": command,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Fixed format string
    })

    # Get relevant memories for context
    relevant_memories = get_relevant_memories(user_data, command)

    # Check for emotion and prepare possible emotional response
    emotion = detect_user_emotion(command)
    emotion_response = get_emotion_response(emotion)

    response = None

    # Add feedback collection commands
    if "rate your response" in command_lower or "how was that" in command_lower:
        try:
            score = int(command_lower.split()[-1])
            if 1 <= score <= 5:
                last_exchange = user_data["interaction_history"]["conversation_history"][-1]
                feedback_handler.save_feedback(
                    last_exchange["user"],
                    last_exchange["riya"],
                    score,
                    emotion,
                    {"user_data": user_data}
                )
                learn_from_interaction(
                    last_exchange["user"],
                    last_exchange["riya"],
                    rating=score
                )
                response = f"Thank you for your feedback! I'll use it to improve."
            else:
                response = "Please rate between 1 and 5."
        except:
            response = "Please rate between 1 and 5."

    # Add self-improvement reporting
    elif "show your improvements" in command_lower:
        stats = feedback_handler.analyze_performance()
        response = "Here's how I've been improving: "
        for emotion_stat in stats:
            response += f"\nFor {emotion_stat[1]} responses, average rating: {emotion_stat[0]:.1f}"

    # Greeting & Identity with variations
    elif any(kw in command_lower for kw in ["hello", "hi riya"]):
        time_greeting = greeting_based_on_time()
        greetings = [
            f"{time_greeting}, sir! How can I help you today?",
            f"{time_greeting}! It's great to hear from you, master. What's on your mind?",
            f"Hey sir! I'm all ears."
        ]
        response = casual_variations(greetings)

    elif "how are you" in command_lower:
        responses = [
            "I'm doing great, thanks for asking! How about you?",
            "I'm wonderful! It's always nice when you check in on me. How are you feeling?",
            "I'm excellent! Better now that we're talking. What about you?"
        ]
        response = casual_variations(responses)

    elif "what is your name" in command_lower:
        responses = [
            "I'm Riya, your AI companion. I'm here to chat, help, or just keep you company!",
            "My name's Riya! I'm your personal AI companion, designed to make your day a little brighter.",
            "I'm Riya! Think of me as your digital friend who's always ready to help."
        ]
        response = casual_variations(responses)

    elif "who made you" in command_lower:
        response = "I was created by a brilliant developer named Hitesh. He made me to be helpful and understanding!"

    elif "what can you do" in command_lower:
        response = "I can be your companion in conversations, help search the web, play music, set reminders, and remember things that matter to you. What would you like to try first?"

    # Exit
    elif any(kw in command_lower for kw in ["bye", "turn off", "shut down"]):
        responses = [
            "I'll be here whenever you need me. Just say 'Riya' to wake me up!",
            "Taking a little break now. Call me back anytime by saying 'Riya'!",
            "I'll miss our chat! Say 'Riya' when you want to talk again."
        ]
        response = casual_variations(responses)
        asyncio.run(speak_with_style(response))
        return "sleep"

    # Website actions
    elif "open google" in command_lower:
        webbrowser.open("https://google.com")
        response = "Opening Google for you now."

    elif "open youtube" in command_lower:
        webbrowser.open("https://youtube.com")
        response = "YouTube coming right up!"

    elif "open facebook" in command_lower:
        webbrowser.open("https://facebook.com")
        response = "Opening Facebook for you."

    elif "open linkedin" in command_lower:
        webbrowser.open("https://linkedin.com")
        response = "LinkedIn, at your service!"

    # Music control
    elif command_lower.startswith("play"):
        song = command_lower.split(" ", 1)[1]
        if musicLibrary and hasattr(musicLibrary, "music"):
            link = musicLibrary.music.get(song)
            if link:
                response = f"Playing {song} for you. Hope you enjoy it!"
                webbrowser.open(link)
            else:
                response = "I couldn't find that song in your library. Want to try another one?"
        else:
            response = "I don't have access to your music library yet. Let's set that up later!"

    elif "stop song" in command_lower:
        pyautogui.hotkey("space")
        response = "I've paused the music. Let me know when you want to resume!"

    elif "song play" in command_lower:
        pyautogui.hotkey("space")
        response = "Music's playing again! Enjoy!"

    # Remember user preferences
    elif "remember" in command_lower and "my" in command_lower:
        # Extract what to remember (simple parsing)
        if "name is" in command_lower:
            name = command_lower.split("name is")[1].strip()
            user_data["personal_info"]["name"] = name.capitalize()
            response = f"I'll remember to call you {name} from now on!"
        else:
            # Extract preference (simple approach)
            preference_parts = command_lower.split("remember that my")
            if len(preference_parts) > 1:
                preference = preference_parts[1].strip()
                key = preference.split()[0] if preference else "preference"
                user_data["personal_info"]["favorites"][key] = preference
                response = f"I'll remember that your {preference}. Thanks for sharing!"

    # Set reminders
    elif "remind me" in command_lower:
        # Very simple reminder extraction
        about_index = command_lower.find("about")
        at_index = command_lower.find("at")

        if about_index != -1 and at_index != -1 and at_index > about_index:
            reminder_text = command_lower[about_index+6:at_index].strip()
            time_text = command_lower[at_index+3:].strip()

            try:
                hour, minute = map(int, time_text.split(':'))
                reminder_time = datetime.now().replace(hour=hour, minute=minute, second=0)

                if reminder_time < datetime.now():
                    reminder_time += timedelta(days=1)

                # Store reminder in memory.reminders
                if "reminders" not in user_data["memory"]:
                    user_data["memory"]["reminders"] = []

                user_data["memory"]["reminders"].append({
                    "text": reminder_text,
                    "time": reminder_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "notified": False
                })

                response = f"I'll remind you about {reminder_text} at {time_text}."
            except:
                response = "I'm not sure I understood the time format. Can you say it like '3:30' or '15:45'?"

    # Tell me about yourself (memory)
    elif any(phrase in command_lower for phrase in ["what do you know about me", "what have i told you"]):
        info = user_data["personal_info"]
        if info["name"] or info["favorites"]:
            details = []
            if info["name"]:
                details.append(f"your name is {info['name']}")
            if info["favorites"]:
                for k, v in info["favorites"].items():
                    details.append(f"your favorite {k} is {v}")
            response = "Here's what I know about you: " + ", ".join(details)
        else:
            response = "We're just getting to know each other! Feel free to tell me about yourself anytime."

    # Handle memory-related commands
    elif "remember this" in command_lower:
        memory_content = command_lower.replace("remember this", "").strip()
        user_data = add_memory(user_data, "user_shared",
                               memory_content, importance=7)
        response = "I'll remember that for you."

    elif "what do you remember about" in command_lower:
        query = command_lower.replace("what do you remember about", "").strip()
        memories = get_relevant_memories(user_data, query)
        if memories:
            response = "Here's what I remember: " + " ".join(
                [m["content"] for m in memories]
            )
        else:
            response = "I don't have any specific memories about that yet."

    # AI Chat fallback with emotional response
    if not response:
        if emotion_response:
            ai_response = ai_process(command, user_data)
            response = f"{emotion_response} {ai_response}"
        else:
            response = ai_process(command, user_data)

    # Choose voice style based on emotion
    style = "chat"  # default
    if emotion == "positive":
        style = "cheerful"
    elif emotion == "negative":
        style = "empathetic"

    # After generating response, check successful patterns
    if not response:
        patterns = feedback_handler.get_successful_patterns()
        if patterns:
            # Use successful patterns to influence response generation
            similar_responses = [p[0] for p in patterns if p[1] == emotion]
            if similar_responses:
                # Modify response based on successful patterns
                response = ai_process(command + " [Use similar tone: " +
                                      similar_responses[0] + "]", user_data)
    print("Riya:", response)
    asyncio.run(speak_with_style(response))

    # Update conversation history
    user_data = update_conversation_history(user_data, command, response)
    save_user_data(user_data)

    return None


def listen_with_vad():
    chunk_duration = 30  # ms
    chunk_samples = int(16000 * chunk_duration / 1000)
    pa = pyaudio.PyAudio()

    stream = pa.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=chunk_samples
    )

    speech_count = 0
    silence_count = 0
    audio_buffer = []

    while True:
        chunk = stream.read(chunk_samples)
        if is_speaking(chunk):
            speech_count += 1
            silence_count = 0
            audio_buffer.append(chunk)
        else:
            silence_count += 1
            if speech_count > 0:
                audio_buffer.append(chunk)

        if silence_count > 10 and speech_count > 5:  # Adjust these values as needed
            break
        elif silence_count > 30:  # No speech detected
            return None

    stream.stop_stream()
    stream.close()
    pa.terminate()

    if audio_buffer:
        audio_data = b''.join(audio_buffer)
        return sr.AudioData(audio_data, 16000, 2)
    return None


def load_training_data():
    try:
        with open("training_data.json", "r") as f:
            return json.load(f)
    except:
        return {"learned_responses": [], "personality_traits": [], "speaking_style": {}}


def save_training_data(data):
    with open("training_data.json", "w") as f:
        json.dump(data, f, indent=4)


def learn_from_interaction(command, response, rating=None):
    training_data = load_training_data()
    training_data["learned_responses"].append({
        "user_input": command,
        "response": response,
        "rating": rating,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Fixed format string
    })
    save_training_data(training_data)


def recall_recent_context(user_data, context_type, hours=24):
    """Get relevant recent memories based on context"""
    now = datetime.now()
    recent_memories = []

    for memory in user_data["memory"]["short_term"]:
        memory_time = datetime.strptime(
            memory["timestamp"], "%Y-%m-%d %H:%M:%S")
        if (now - memory_time).total_seconds() <= hours * 3600:
            if context_type in memory.get("tags", []):
                recent_memories.append(memory["content"])

    return recent_memories


def generate_contextual_response(user_data, command):
    # Check for tiredness references
    tired_memories = recall_recent_context(user_data, "tiredness")
    if tired_memories and "how are you" in command.lower():
        return f"I remember last night you mentioned being tired. Are you feeling better today?"

    # Check mood changes
    recent_moods = user_data["interaction_history"]["mood_history"][-5:]
    if any(m["mood"] == "sadness" for m in recent_moods):
        return "I noticed you were feeling down earlier. I hope you're doing better now."

    return None


def web_search_and_summarize(query, max_results=3):
    try:
        # Try Wikipedia first
        try:
            wiki_summary = wikipedia.summary(query, sentences=2)
            return f"From Wikipedia: {wiki_summary}"
        except:
            pass

        # Fall back to Google search
        urls = search(query, num_results=max_results)
        combined_text = []

        for url in urls:
            try:
                response = requests.get(url, timeout=5)
                soup = BeautifulSoup(response.text, 'html.parser')
                paragraphs = soup.find_all('p')
                text = ' '.join(p.get_text() for p in paragraphs[:2])
                if text and len(text) > 100:  # Only keep meaningful content
                    combined_text.append(text[:500])
            except:
                continue

        if combined_text:
            return "Here's what I found: " + " ".join(combined_text[:2])
        return "I couldn't find specific information about that. Could you try rephrasing?"

    except Exception as e:
        return f"I had trouble searching for that information: {str(e)}"


def get_real_time_info(query):
    # Handle different types of real-time information
    if "weather" in query.lower():
        # Add weather API integration here
        return "I'll add weather information capability soon!"

    if any(word in query.lower() for word in ["score", "match", "ipl"]):
        try:
            url = "https://www.cricbuzz.com/cricket-match/live-scores"
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')
            scores = soup.find_all(class_='cb-scr-wll-chvrn')
            return scores[0].text if scores else "No live matches found."
        except:
            return "I couldn't fetch the live scores at the moment."

    return None


# --- Main Program ---
if __name__ == "__main__":
    # Initialize user data
    user_data = load_user_data()

    # Check last interaction time for personalized greeting
    last_interaction = user_data.get("last_interaction")
    greeting = "Initializing Riya... Say 'Riya' to start."

    if last_interaction:
        last_time = datetime.strptime(last_interaction, "%Y-%m-%d %H:%M:%S")
        time_diff = datetime.now() - last_time
        # --- Auto-Resume After Break ---
        if time_diff.total_seconds() > 14400:  # 4 hours
            lp = user_data.get("learning_progress", {})
            if lp.get("active_topic"):
                asyncio.run(speak_with_style(
                    f"Welcome back! Should I continue our last lesson on {lp['active_topic']}? Say 'yes' to resume or 'no' to start fresh."))
        elif time_diff.days > 0:
            user_name = user_data.get("name", "Sir")
            greeting = f"Welcome back, {user_name}! It's been {time_diff.days} day{'s' if time_diff.days > 1 else ''} since we talked. Say 'Riya' when you're ready to talk."
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            greeting = f"Hi again! It's been {hours} hour{'s' if hours > 1 else ''} since our last talk. Say 'Riya' to start."

    asyncio.run(speak_with_style(greeting))

    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        print("Listening for wake word: 'Riya'...")

        last_check = datetime.now()

        while True:
            try:
                # Add conversation initiation check
                if (datetime.now() - last_check).seconds > 60:  # Check every minute
                    if should_initiate_conversation(user_data):
                        # Randomly choose between different types of initiations
                        initiation_type = random.choice(
                            ['starter', 'thought', 'curiosity'])

                        if initiation_type == 'thought':
                            thought = generate_random_thought(user_data)
                            if thought:
                                asyncio.run(speak_with_style(thought))
                        elif initiation_type == 'curiosity':
                            curiosity = generate_curiosity_prompt(user_data)
                            asyncio.run(speak_with_style(curiosity))
                        else:
                            starter = get_conversation_starter(user_data)
                            asyncio.run(speak_with_style(starter))

                    last_check = datetime.now()

                # Add periodic pattern analysis
                # Every 10 conversations
                if len(user_data["interaction_history"]["conversation_history"]) % 10 == 0:
                    patterns = analyze_user_patterns(user_data)
                    user_data["learning"]["patterns"] = patterns
                    save_user_data(user_data)

                # Check for due reminders
                due_reminders = check_reminders(user_data)
                if due_reminders:
                    for reminder in due_reminders:
                        asyncio.run(speak_with_style(
                            f"Reminder: {reminder['text']}"))

                audio_data = listen_with_vad()
                if audio_data:
                    wake = recognizer.recognize_google(audio_data).lower()

                    if "riya" in wake:
                        user_name = user_data.get("name", "Sir")
                        asyncio.run(speak_with_style(
                            f"Yes sir, I'm listening."))
                        while True:
                            try:
                                audio = recognizer.listen(source)
                                command = recognizer.recognize_google(audio)
                                emotion = detect_user_emotion(command)
                                user_data = adapt_personality(
                                    user_data, command, emotion)
                                if process_command(command, user_data) == "sleep":
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
