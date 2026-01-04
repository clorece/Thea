# Rin - AI Desktop Companion

> An edge intelligence companion for your personal computer.

<div align="center">
  <img src="frontend/src/assets/rin-pfp.jpg" alt="Image used for profile picture by daisukerichard on x! Please see credits below! " width="500"/>
</div>

<p align="center">Image used for profile picture by daisukerichard on x! Please see credits below!</p>

Rin is an intelligent, visually-aware desktop companion designed to quietly support your digital life. She observes your screen, understands your context, and offers guidance or company when you need it.

## Features
*   **Visual Awareness**: Rin "sees" your active window and understands what you are working on or playing.
*   **Audio Awareness**: Rin "hears" system audio (music, game sounds) via loopback and uses it to understand the vibe.
*   **Episodic Memory**: Rin remembers recent activities (e.g., "Back to coding?"), creating a continuous sense of companionship.
*   **Notification Center**: A dedicated, scrollable hub for Rin's observations and thoughts, separate from the chat.
*   **Smart Idle System**:
    *   **Active (Green)**: Rin is watching and ready to chat.
    *   **Rest Mode (Yellow)**: Activates after 120s of inactivity. Rin pauses observation to save resources.
*   **Sequential Chat**: Rin communicates in natural, paced bursts (split messages) rather than long blocks of text.
*   **Stealth User Mode**: Launches completely silently in the background via `start.bat`.
*   **Chat Interface**: A clean, modern chat UI with smooth animations and "glass" aesthetics.

## Roadmap & Future Implementations: Rin's Thinking System

**Goal:** Transform Rin into a Cloud-Accelerated Edge Intelligence that thinks before speaking and learns continuously.

### Phase 1: Real-Time Thinking (Active Mode)
*   **Observation Buffer**: Accumulate observations (last 5-10) instead of immediate reactions.
*   **Thinking Pauses**: Periodic analysis (every 45s) to determine significance.
*   **Significance Detection**: Filter repetitive actions; only trigger for meaningful changes (new activity, deep focus).
*   **Thoughtful Responses**: Gemini generates intentional messages or chooses `STAY_QUIET` to reduce noise by ~90%.

### Phase 2: Deep Thinking (Idle Mode)
*   **Idle Detection**: Triggers after 2 minutes of inactivity.
*   **Edge Knowledge Organization**: Merge duplicate knowledge, decay old items, and rebuild graph connections locally.
*   **Pattern Analysis**: Identify workflows and temporal habits.
*   **Gemini Validation**: Send top insights to the cloud for validation and deepening.
*   **Response Pre-computation**: Generate and cache 3-5 responses for likely future contexts while user is AFK.

### Phase 3: Data Structure Improvements
*   **Hierarchical Knowledge Graph**: Tiers for Core Identity, Working Memory, and Episodic Memory.
*   **Knowledge Decay**: Automatic confidence decay for unused information.
*   **Smart Caching**: Context-hash based caching with LRU eviction and TTL.

### Phase 4: UX & Integration
*   **Thinking Indicators**: Visual status for "Thinking" or "Deep Reflection".
*   **Proactive Insight Sharing**: Share deep thoughts discovered during idle time (based on relevance).
*   **"What are you thinking?"**: Feature to ask Rin about her current internal reflections.
*   **Personality Consistency**: Enforce tone consistency across edge and cloud responses.

### Architecture Principles
*   **Thin Client / Thick Edge**: Default to local computation; use cloud strategically.
*   **Dual Thinking Modes**: Real-time (45s) + Deep (Idle).
*   **Cost-Conscious**: Drastic API reduction through buffering and significance checks.

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

    > **Important Note:**
    > Unfortunately setup.bat is currently bugged, if you are updating or installing Python or Node.js please restart immediately after setup.bat,
    > then relaunch the setup batch file after restart to finishes the install for those, otherwise you will keep looping on the installation.
    > This may force you to do more than 1 restart and setup initializations.
    > I know this is not ideal, and will make a fix for it as soon as possible.

3.  **Configure API Key**:
    *   Create a file named `GEMINI_API_KEY.txt` in the root directory.
    *   Paste your Gemini API key inside it.

### Usage

*   **Start Rin**: Double-click **`start.bat`**.
    *   This launches Rin in **User Mode**.
*   **Debug Mode**: If you need to see logs or troubleshoot, use `debug.bat`.
*   **Shutdown**: Click the Power button in the Rin header to cleanly shut down both the UI and the background brain.

## Personalization

You can inform Rin about yourself by editing `user_profile.txt` in the root directory:
```text
Username=YourName
DateOfBirth=January 1
Interests=Coding, Gaming, Sci-Fi
Dislikes=Spiders, Lag
```

## Reporting Issues

If you encounter any bugs or issues, please report them via the **[GitHub Issues](https://github.com/clorece/rin/issues)** tab.

**When reporting a bug, please:**
1.  Describe the issue clearly.
2.  Attach your **`backend.log`** file (located in the `logs/` folder).
    *   *Note: Check the log for any sensitive information before sharing, though it mostly contains system status and error traces.*
3.  Include steps to reproduce the problem if possible.

## Credits

**Profile Picture Art**:
By **[@daisukerichard](https://x.com/daisukerichard)**
*   [Original Post](https://x.com/daisukerichard/status/1599329420879491073)

If you are the original owner of credited work and assets, and would like credit adjustments or removal of assets from the project, please feel free to contact me through github.

**Development**:
Built with Electron, React, FastAPI, and Google Gemini.
