# Rin - AI Desktop Companion

> An edge intelligence companion for your personal computer.

<div align="center">
  <img src="frontend/src/assets/rin-pfp.jpg" alt="Image used for profile picture by daisukerichard on x! Please see credits below! " width="500"/>
</div>

<p align="center">Image used for profile picture by daisukerichard on x! Please see credits below!</p>

Rin is an intelligent, visually-aware desktop companion designed to quietly support your digital life. She observes your screen, understands your context, and offers guidance or company when you need it.

## Features

*   **Visual Awareness**: Rin "sees" your active window and understands what you are working on or playing.
*   **Proactive Reactions**: She reacts to your context with relevant emojis and short comments without needing a prompt.
*   **Smart Idle System**:
    *   **Active (Green)**: Rin is watching and ready to chat.
    *   **Rest Mode (Yellow)**: Activates after 120s of inactivity. Rin pauses observation to save resources and assumes a resting state.
*   **Stealth User Mode**: Launches completely silently in the background (no terminal windows) via `start.bat`.
*   **Chat Interface**: A clean, modern chat UI to talk with Rin directly.

## Roadmap & Future Implementations

*   **Edge Intelligence**: We are implementing true edge intelligence concepts. Future versions will allow Rin to create her own data structures and store memories based on your PC contents and day-to-day activities, tailoring her personality and knowledge specifically to you.
*   **Local LLM (Ollama)**: We plan to verify and implement Ollama support as an alternative to Gemini. This will allow for easier, free, and unlimited access to the companion using local hardware.
*   **Compact View**: A less obstructive and more minimal UI
*   **Vocalized Responses and Microphone Inputs**: An optional system of communication where users can enable vocal communication instead of chat bubbles displayed by the companion, as well as an optional voice recording where users can chat with the companion using a microphone.

## Getting Started

### Prerequisites
*   Windows 10/11
*   Python 3.10+
*   Node.js & npm
*   A Google Gemini API Key (Multimodal)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/clorece/rin.git
    cd rin
    ```

4.  **Run Setup**:
    Double-click `setup.bat`. This will:
    *   Create a Python virtual environment for the backend.
    *   Install Python dependencies.
    *   Install Node.js dependencies for the frontend.

    > **⚠️ IMPORTANT SETUP NOTE:**
    > Unfortunately setup.bat is currently bugged, if you are updating or installing Python or Node.js please restart immediately after setup.bat,
    > then relaunch the setup batch file after restart to finishes the install for those, otherwise you will keep looping on the installation.
    > This may force you to do more than 1 restart and setup initializations.
    > I know this is not ideal, and will make a fix for it as soon as possible.

3.  **Configure API Key**:
    *   Create a file named `GEMINI_API_KEY.txt` in the root directory.
    *   Paste your Gemini API key inside it (starts with `AIza...`).

### Usage

*   **Start Rin**: Double-click **`start.bat`**.
    *   This launches Rin in **User Mode** (Silent backend, no debug consoles).
*   **Debug Mode**: If you need to see logs or troubleshoot, use `debug.bat`.
*   **Shutdown**: Click the Power button in the Rin header to cleanly shut down both the UI and the background brain.

## Personalization

You can teach Rin about yourself by editing `user_profile.txt` in the root directory:
```text
Username=YourName
DateOfBirth=January 1
Interests=Coding, Gaming, Sci-Fi
Dislikes=Spiders, Lag
```

## Credits

**Profile Picture Art**:
By **[@daisukerichard](https://x.com/daisukerichard)**
*   [Original Post](https://x.com/daisukerichard/status/1599329420879491073)

If you are the original owner of credited work and assets, and would like credit adjustments or removal of assets from the project, please feel free to contact me through github.

**Development**:
Built with Electron, React, FastAPI, and Google Gemini.
