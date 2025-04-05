# Elina - Your Personal AI Assistant

Elina is a voice-controlled personal assistant built using Python. It can perform various tasks like opening websites, playing music, launching Windows applications, and responding intelligently using AI. Elina keeps listening for commands once activated, making it a seamless hands-free experience.

## Features

- **Wake Word Activation**: Say "Elina" to start listening.
- **Open Websites**: Commands like "Open Google", "Open YouTube".
- **Launch Windows Applications**: Commands like "Open WhatsApp", "Open Notepad", "Open Chrome".
- **Play and Stop Music**: "Play [song name]" and "Stop song".
- **AI-Powered Responses**: Ask general questions, and Elina will respond using AI.
- **Continuous Listening**: Once activated, Elina keeps listening for commands.

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/yourusername/elina_personal_assistant.git
   cd elina_personal_assistant
   ```

2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

3. Set up your **Gemini API key** (Replace `YOUR_GEMINI_API_KEY` in the code).

4. Run Elina:
   ```sh
   python elina.py
   ```

## Usage

- **Start Elina**: Say "Elina" to wake it up.
- **Give Commands**:
  - "Open Google"
  - "Open WhatsApp"
  - "Play [song name]"
  - "Stop song"
  - Ask any question (Elina will respond using AI).

## Configuration

If you want to add more applications, update the `app_paths` dictionary in `elina.py` with the application name and its executable path.

## Contributing

Feel free to fork this repository and submit pull requests to improve Elina.

## License

This project is licensed under the MIT License.
