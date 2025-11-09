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

- Synthetically generated simulated data, training XGBoost model
- "Stuck?" button that logs user metrics; with each automatic popup, user confirmation on if was an accurate prediction
- Model retrained every 100 new data points

**API integration**

- API calls linked to MCP with documentation
- Hint hierarchy with progressively more informative hints

**Frontend**

- Popup with "were you stuck?" confirmation button
- Manual "Stuck?" button
- Professor dashboard to see where studnets are stuck
- Student dashboard
- Area to input class ID (or maybe track github classroom) and upload directory for documentation for LLM to pull from

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

Now available on the VSCode Extension Marketplace! 
<img width="299" height="181" alt="1" src="https://github.com/user-attachments/assets/dc3482d1-371c-455f-beda-a5ea7daedd3f" />

