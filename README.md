# Particl Automated Moderation Tool

An automated content moderation tool for the Particl Marketplace using Large Language Models (LLMs) to analyze and moderate content according to customizable policies.

## Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
  - [Installing Python](#installing-python)
    - [Windows](#windows)
    - [macOS](#macos)
    - [Linux](#linux-ubuntudebian)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Wallet Setup](#wallet-setup)
  - [LLM Model Selection](#llm-model-selection)
  - [Moderation Policies](#moderation-policies)
- [Usage](#usage)
  - [Manual Mode](#manual-mode)
  - [Continuous Mode Flow](#continuous-mode-flow)
  - [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [Related Projects](#related-projects)
- [Official Resources](#official-resources)
- [License](#license)

## Overview

This tool provides automated content moderation for Particl marketplace listings using LLMs. It can:
- Scan marketplace listings automatically
- Process listings through LLM models for content analysis
- Apply customizable moderation policies
- Vote on listings based on moderation results
- Run in continuous mode for automated monitoring

## Prerequisites

- Python 3.8 or higher
- Ollama (for LLM support)
- Particl Core (will be installed through the application)
- Sufficient disk space for blockchain data

### Installing Python

#### Windows
1. Download Python from [python.org](https://www.python.org/downloads/)
2. Run the installer (ensure "Add Python to PATH" is checked)
3. Verify installation by opening Command Prompt and typing: `python --version`
   - If this doesn't work, try: `py --version`

#### macOS
Using Homebrew:
```bash
brew install python
```
Verify installation:
```bash
python3 --version
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```
Verify installation:
```bash
python3 --version
```

Note: Depending on your system configuration, you might need to use `python` instead of `python3` for commands. If one doesn't work, try the other.

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd particl_moderation
```

2. From the root directory of the project, run the setup script:
```bash
# On Linux/macOS
python3 setup_environment.py

# On Windows
python setup_environment.py
```

3. Activate the virtual environment by typing these commands in the root directory of the project:
```bash
# On Linux/macOS
source venv/bin/activate

# On Windows
venv\Scripts\activate
```

4. From the root directory, start the application:
```bash
# On Linux/macOS
python3 app.py

# On Windows
python app.py
```

## Configuration

1. Install Particl Core from the settings menu
2. Start the Particl daemon
3. Create a new wallet or initialize an existing one
4. Deposit PART coins to your wallet (required for voting)
5. Choose and install an LLM model (via settings)
6. Configure moderation policies

### Wallet Setup
- After creating or initializing your wallet, you'll need to deposit PART coins
- Coins are required for voting on marketplace listings
- The wallet must remain unlocked during operation
- Keep sufficient funds for your planned moderation activities

### LLM Model Selection
- Choose from available models in settings
- The default model is Gemma2:2b as it offers the best balance of speed, accuracy and resources (RAM and VRAM/storage) requirements 
- More models will be added over time after they've been throroughly tested for accuracy

### Moderation Policies
- Configure content rules
- Choose to apply rule templates (serve as examples) or create your own rules using natural language
- If creating custom rules, be as precise as possible, and test results on test listings before applying to production listings (from Particl Marketplace)

## Usage

1. Ensure you have PART coins in your wallet for voting
2. Set up moderation policies in settings
3. Choose operation mode:
   - Manual Mode: Scan and process listings on demand. Recommended for initial setup to verify LLM decisions align with your moderation standards
   - Continuous Mode: Enables automated background monitoring and moderation. Requires keeping the terminal window open during operation

### Manual Mode
- Perfect for learning system behavior and testing new moderation policies
- Manually deploy listing scanning and processing from the Scan and Process Listings menu option in the main menu. Choose to moderate test or real listings
- Review individual listings post-processing by navigating to the Display Processed Listings from the menu, or check the /config/results.txt file
- Verify LLM decisions, search for specific items, and edit them as necessary by using the specified keyboard controls
- Broadcast moderation decisions by selection the Broadcast Moderation Decisions menu option in the main menu

### Continuous Mode Flow
1. Continuously scans for new marketplace listings
2. Processes listings through moderation queue
3. Applies LLM analysis based on policies
4. Broadcasts votes automatically
5. Repeats cycle after a delay
6. Logs all actions for review (config/moderation.log)

### Best Practices
- Start with manual mode to understand system behavior and test new moderation policies (important)
- Regularly monitor moderation logs
- Keep sufficient PART balance for voting
- Backup wallet and configuration files
- Remember that LLMs are deterministic systems. Therefore, they can hallucinate or return undesirable moderation decisions. This is why it is vital to thoroughly test new moderation policies on test listings, then deploy manually on live listings before starting the Continuous Mode.

## Troubleshooting

Common issues and solutions:

1. Python Command Not Found
   - Try both `python` and `python3` commands
   - Verify PATH environment variables
   - Reinstall Python if necessary

2. Virtual Environment Issues
   - Ensure you're in the project root directory
   - Try recreating the virtual environment
   - Check Python version compatibility

3. LLM Model Issues
   - Verify Ollama installation
   - Check model installation status
   - Try reinstalling the model with `ollama rm [model_name]` and `ollama run [model_name]` (e.g., `ollama rm gemma2:2b` and `ollama run gemma2:2b`)

4. Wallet Connection Issues
   - Verify daemon is running
   - Check wallet unlock status
   - Ensure sufficient funds

## Related Projects

- [Particl Marketplace](https://github.com/particl/particl-market)
- [Particl Desktop](https://github.com/particl/particl-desktop)
- [OMP Library](https://github.com/particl/omp-lib)
- [Particl Core](https://github.com/particl/particl-core)

## Official Resources

- [Particl Website](https://particl.io)
- [Documentation](https://academy.particl.io)
- [GitHub Organization](https://github.com/particl)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
