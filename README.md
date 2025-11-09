# 🧠 Study Helper — VS Code Extension for Learning Programming

**Study Helper** is a VS Code extension that helps students learn programming more effectively.  
It detects when you’re stuck or making repeated errors and gently provides hints, documentation, or debugging tips — right inside your editor.


# System Architecture
```mermaid
flowchart LR
    A[Signals] --> B[ML Predictive Model]
    B --> C[API Call]
    C --> D[Documentation MCP]
    D --> E[Frontend]
```

# Project Structure

```
.
├── backend
│   ├── data
│   │   └── synthetic
│   │       └── training_data.csv
│   ├── database.py
│   ├── main.py
│   ├── models
│   │   └── stuck_predictor_v1.pkl
│   ├── requirements.txt
│   ├── test_api.py
│   └── test_ml.py
├── data
│   ├── feedback.jsonl
│   └── synthetic
│       └── training_data.csv
├── extension
│   ├── out
│   │   ├── extension.js
│   │   ├── extension.js.map
│   │   ├── stuckDetector.js
│   │   └── stuckDetector.js.map
│   ├── package.json
│   ├── src
│   │   ├── extension.ts
│   │   └── stuckDetector.ts
│   └── tsconfig.json
├── ml
│   ├── blackbox.py
│   ├── data
│   │   └── synthetic
│   │       ├── test_data.csv
│   │       └── training_data.csv
│   ├── features.py
│   ├── generation_script.py
│   ├── models.py
│   ├── retrain_model.py
│   └── synthetic_data_generation.py
├── models
│   └── stuck_predictor_v1.pkl
├── README.md
└── requirements.txt
```
    
**Stuck Signals**

- **Idle time**: user stops typing for a while
- **Repetitive editing**: repeated backspacing + retyping
- **Cursor thrashing**: jumping around with minimal progress
- **Frequent and similar error messages**
- **No code execution attempts**
- **Tab switching** (if trackable)
- **Specific comments**: very long comments, terms such as "todo" "fix" etc


**ML integration of stuck signals**

- perhaps generate synthetic simulated data, train a small model (decision tree maybe), use as heuristic
- add a "stuck?" button and log user behavior to build dataset; with each popup, add a check and X if it accurately predicted user data, to train model better

**API integration**

- link api calls to mcp with documentation, perhaps locally downloaded docs
- hint hierarchy: first link documentation, then hint, then answer (maybe keep this on cooldown to not abuse)

**Frontend**

- popup with "were you stuck?" button
- "hint/stuck?" button
- professor dashboard to see where studnets are stuck
- student dashboard
- area to input class ID (or maybe track github classroom) and upload directory for documentation for LLM to pull from







---

## 🚀 Features

- ⏱️ Detects inactivity
- 💡 Suggests hints and relevant documentation
- 🧭 Simple, non-intrusive popups for help
- 🔍 Customizable triggers for learning assistance
- 🌐 Integration with AI models and Model Context Protocol (MCP)

---

## 🧩 Example Use Case

1. You’re writing Python code and stop typing for 20 seconds.  
2. The extension notices inactivity and suggests:  
   > “Need help? Check Python indentation syntax here.”  
3. You can see a pop-up to read more or get AI-generated explanations.

---

## 🛠️ Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/<your-username>/vscode-study-helper.git
   cd vscode-study-helper
2. Install Dependencies
npm install

3. Open the project in VS Code:
code .

4. Press F5 to launch the Extension Development Host (a new VS Code window with your extension active).

