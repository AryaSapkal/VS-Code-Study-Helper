import * as vscode from 'vscode';
import { getWebviewContent } from './webview';
import { initializeApp, getApps } from 'firebase/app';
import { getFirestore, Firestore, collection, addDoc, getDocs, writeBatch } from 'firebase/firestore';
import Dedalus from 'dedalus-labs';
import { randomUUID } from 'crypto'; // We still need this for a fallback
import * as dotenv from 'dotenv';
import * as path from 'path';
import * as fs from 'fs';

// Load environment variables with explicit path for VS Code extensions
const envPath = path.resolve(__dirname, '..', '.env');
dotenv.config({ path: envPath });

// Fallback: Manual .env file reading for VS Code extensions
function loadEnvFallback(): { [key: string]: string } {
  const envVars: { [key: string]: string } = {};
  try {
    if (fs.existsSync(envPath)) {
      const envContent = fs.readFileSync(envPath, 'utf8');
      const lines = envContent.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
          const [key, ...values] = trimmed.split('=');
          envVars[key] = values.join('=');
        }
      }
    }
  } catch (error) {
    console.log('Could not read .env file:', error);
  }
  return envVars;
}

// Load environment variables with fallback
const manualEnv = loadEnvFallback();

// --- SECURE API CONFIGURATION ---
const DEDALUS_API_KEY = process.env.DEDALUS_API_KEY || manualEnv.DEDALUS_API_KEY || "your_dedalus_api_key_here";
const PROFESSOR_PASSWORD = "hackprinceton2025"; // Demo password - in production, use proper auth
const firebaseConfig = {
  apiKey: process.env.FIREBASE_API_KEY || manualEnv.FIREBASE_API_KEY || "your_firebase_api_key_here",
  authDomain: "ai-code-helper-92f7d.firebaseapp.com",
  projectId: "ai-code-helper-92f7d",
  storageBucket: "ai-code-helper-92f7d.firebasestorage.app",
  messagingSenderId: "935753222141",
  appId: "1:935753222141:web:db56af2c5942709e353b94",
  measurementId: "G-6S5WF8RV9Z"
};

// -----------------------------

// --- Global State ---
let dashboardPanel: vscode.WebviewPanel | undefined;
let db: Firestore;
let dedalusClient: Dedalus; 
let changeHistory: { timestamp: number, changes: number }[] = [];
let fileHistory: { timestamp: number, filePath: string }[] = [];
let cursorHistory: { timestamp: number, line: number, character: number }[] = [];
let lastActivity: { timestamp: number, line: number, filePath: string } = { timestamp: 0, line: -1, filePath: '' };
let idleTimer: NodeJS.Timeout | undefined;
let textListener: vscode.Disposable | undefined;
let cursorListener: vscode.Disposable | undefined;
let activeEditorListener: vscode.Disposable | undefined;
let isHintInProgress = false;
let globalStudentId: string; // This will now be a real name

//
// THIS IS THE NEW ASYNC ACTIVATION
//
export async function activate(context: vscode.ExtensionContext) {
  console.log('Stuck Detector is active!');
  
  // Debug: Check if environment variables loaded
  console.log('Environment check:');
  console.log('- DEDALUS_API_KEY loaded:', DEDALUS_API_KEY !== "your_dedalus_api_key_here");
  console.log('- FIREBASE_API_KEY loaded:', firebaseConfig.apiKey !== "your_firebase_api_key_here");
  console.log('- Env file path:', path.resolve(__dirname, '..', '.env'));

  // --- 1. DETERMINE USER ROLE (PROFESSOR OR STUDENT) ---
  let userMode = context.globalState.get<string>('stuckDetector.userMode');
  
  if (!userMode) {
    // First time setup - ask what role they are
    const roleChoice = await vscode.window.showQuickPick([
      {
        label: '👨‍🎓 Student',
        detail: 'I want AI hints when I get stuck coding',
        value: 'student'
      },
      {
        label: '👩‍🏫 Professor/Instructor', 
        detail: 'I want to view class analytics dashboard',
        value: 'professor'
      }
    ], {
      placeHolder: 'Select your role',
      canPickMany: false
    });

    if (!roleChoice) {
      vscode.window.showErrorMessage('Setup cancelled. Extension will not activate.');
      return;
    }

    // If professor was selected, verify password
    if (roleChoice.value === 'professor') {
      const passwordInput = await vscode.window.showInputBox({
        prompt: "Enter professor password to access student analytics",
        placeHolder: "Password required for data protection",
        password: true
      });

      if (passwordInput !== PROFESSOR_PASSWORD) {
        vscode.window.showErrorMessage('Invalid password. Access denied.');
        return;
      }
      vscode.window.showInformationMessage('Professor access granted! 👩‍🏫');
    }

    userMode = roleChoice.value;
    await context.globalState.update('stuckDetector.userMode', userMode);
  }

  if (userMode === 'student') {
    // Student setup - get their name
    let storedStudentId = context.globalState.get<string>('stuckDetector.studentId');
    if (!storedStudentId) {
      const studentName = await vscode.window.showInputBox({
        prompt: "Enter your name (this helps your professor see class analytics)",
        placeHolder: "e.g., Alex Smith"
      });

      if (studentName) {
        globalStudentId = studentName;
      } else {
        globalStudentId = `student-${randomUUID()}`;
      }
      await context.globalState.update('stuckDetector.studentId', globalStudentId);
    } else {
      globalStudentId = storedStudentId;
    }
    console.log(`Initializing for Student: ${globalStudentId}`);
  } else {
    // Professor mode - no student ID needed
    globalStudentId = 'professor-view';
    console.log('Initializing in Professor Mode');
  }


  // --- 2. Initialize SDKs ---
  try {
    if (getApps().length === 0) {
      const app = initializeApp(firebaseConfig);
      db = getFirestore(app);
      console.log("Firebase initialized.");
    } else {
      db = getFirestore();
    }
    
    if (!DEDALUS_API_KEY || DEDALUS_API_KEY.includes("your_dedalus_api_key")) {
        throw new Error("Dedalus API key is missing.");
    }
    dedalusClient = new Dedalus({ apiKey: DEDALUS_API_KEY });
    console.log("Dedalus Labs client initialized.");

  } catch (error) {
    console.error("SDK initialization error:", error);
    vscode.window.showErrorMessage('Stuck Detector: Failed to connect to SDKs. Did you paste your keys?');
    return;
  }

  // --- 3. Register Commands Based on User Mode ---
  let showDashboardCommand = vscode.commands.registerCommand('stuckDetector.showDashboard', async () => {
    if (userMode !== 'professor') {
      vscode.window.showWarningMessage('Class analytics are only available for professors. Use "My Analytics" to see your personal stats.');
      return;
    }
    
    // Re-verify professor password for extra security
    const passwordVerify = await vscode.window.showInputBox({
      prompt: "Re-enter professor password to view student data",
      password: true,
      placeHolder: "Security verification required"
    });

    if (passwordVerify !== PROFESSOR_PASSWORD) {
      vscode.window.showErrorMessage('Access denied. Invalid password.');
      return;
    }
    
    if (dashboardPanel) {
      dashboardPanel.reveal(vscode.ViewColumn.One);
      return;
    }
    dashboardPanel = vscode.window.createWebviewPanel(
      'stuckDetectorDashboard', 'AI TA - Class Analytics Dashboard', vscode.ViewColumn.One, 
      { enableScripts: true, retainContextWhenHidden: true }
    );
    dashboardPanel.webview.html = getWebviewContent(firebaseConfig);
    
    dashboardPanel.webview.onDidReceiveMessage(
      async message => {
        if (message.command === 'clearData') {
          console.log('Clear Data command received from webview');
          await clearStuckEvents();
          vscode.window.showInformationMessage('Analytics data cleared!');
        }
      },
      undefined,
      context.subscriptions
    );

    dashboardPanel.onDidDispose(() => { dashboardPanel = undefined; }, null, context.subscriptions);
  });

  // --- 4. Register the "Start Analyzing" Command (for students) ---
  let startCommand = vscode.commands.registerCommand('stuckDetector.start', () => {
    if (userMode !== 'student') {
      vscode.window.showWarningMessage('AI hints are only available for students. Professors use the dashboard to view analytics.');
      return;
    }
    
    vscode.window.showInformationMessage(`🤖 AI TA activated for: ${globalStudentId}. I'll help when you get stuck!`);
    stopListeners();
    
    textListener = vscode.workspace.onDidChangeTextDocument(event => {
      if (event.document.uri.scheme === 'vscode-webview') { return; }
      if (event.contentChanges.length === 0) { return; }
      if (event.reason === vscode.TextDocumentChangeReason.Undo || event.reason === vscode.TextDocumentChangeReason.Redo) { return; }
      
      const now = Date.now();
      const changes = event.contentChanges.length;
      changeHistory.push({ timestamp: now, changes });
      
      // Track activity for idle detection
      const editor = vscode.window.activeTextEditor;
      if (editor) {
        const position = editor.selection.active;
        const filePath = vscode.workspace.asRelativePath(event.document.uri);
        trackActivity(position.line, filePath);
      }
      
      checkHeuristics(event.document, 'churn');
    });

    // Track cursor movements (line jumping detection)
    cursorListener = vscode.window.onDidChangeTextEditorSelection(event => {
      const now = Date.now();
      const position = event.selections[0].active;
      cursorHistory.push({ 
        timestamp: now, 
        line: position.line, 
        character: position.character 
      });
      
      // Track activity for idle detection
      const filePath = vscode.workspace.asRelativePath(event.textEditor.document.uri);
      trackActivity(position.line, filePath);
      
      checkHeuristics(event.textEditor.document, 'cursor');
    });

    // Track file switching
    activeEditorListener = vscode.window.onDidChangeActiveTextEditor(editor => {
      if (!editor || editor.document.uri.scheme === 'vscode-webview') { return; }
      
      const now = Date.now();
      const filePath = vscode.workspace.asRelativePath(editor.document.uri);
      fileHistory.push({ timestamp: now, filePath });
      
      // Track activity for idle detection
      const position = editor.selection.active;
      trackActivity(position.line, filePath);
      
      checkHeuristics(editor.document, 'file');
    });
  });

  // --- 5. Register the "Stop" Command ---
  let stopCommand = vscode.commands.registerCommand('stuckDetector.stop', () => {
    if (userMode !== 'student') {
      vscode.window.showWarningMessage('Only students can stop/start AI hints.');
      return;
    }
    stopListeners();
    vscode.window.showInformationMessage('🤖 AI TA stopped.');
  });

  // --- 6. Register Student Personal Analytics Command ---
  let studentAnalyticsCommand = vscode.commands.registerCommand('stuckDetector.myAnalytics', () => {
    if (userMode !== 'student') {
      vscode.window.showWarningMessage('Personal analytics are only available for students.');
      return;
    }
    
    if (dashboardPanel) {
      dashboardPanel.reveal(vscode.ViewColumn.One);
      return;
    }
    dashboardPanel = vscode.window.createWebviewPanel(
      'studentAnalytics', `📈 My Learning Analytics - ${globalStudentId}`, vscode.ViewColumn.One, 
      { enableScripts: true, retainContextWhenHidden: true }
    );
    // Pass student mode flag to webview
    dashboardPanel.webview.html = getWebviewContent(firebaseConfig, globalStudentId);
    
    dashboardPanel.onDidDispose(() => { dashboardPanel = undefined; }, null, context.subscriptions);
  });

  // --- 7. Register Mode Switching Command ---
  let switchModeCommand = vscode.commands.registerCommand('stuckDetector.switchMode', async () => {
    const newMode = await vscode.window.showQuickPick([
      {
        label: '👨‍🎓 Switch to Student Mode',
        detail: 'Get AI hints when stuck coding',
        value: 'student'
      },
      {
        label: '👩‍🏫 Switch to Professor Mode',
        detail: 'View class analytics dashboard',
        value: 'professor'
      }
    ], {
      placeHolder: `Currently in ${userMode} mode. Select new mode:`,
    });

    if (newMode && newMode.value !== userMode) {
      // If switching to professor mode, verify password
      if (newMode.value === 'professor') {
        const passwordInput = await vscode.window.showInputBox({
          prompt: "Enter professor password to switch to professor mode",
          password: true,
          placeHolder: "Password required for access"
        });

        if (passwordInput !== PROFESSOR_PASSWORD) {
          vscode.window.showErrorMessage('Invalid password. Mode switch cancelled.');
          return;
        }
      }

      await context.globalState.update('stuckDetector.userMode', newMode.value);
      vscode.window.showInformationMessage(`Switched to ${newMode.value} mode. Please reload VS Code.`, 'Reload')
        .then(selection => {
          if (selection === 'Reload') {
            vscode.commands.executeCommand('workbench.action.reloadWindow');
          }
        });
    }
  });

  context.subscriptions.push(showDashboardCommand, startCommand, stopCommand, studentAnalyticsCommand, switchModeCommand);
}

function stopListeners() {
  if (textListener) { textListener.dispose(); textListener = undefined; }
  if (cursorListener) { cursorListener.dispose(); cursorListener = undefined; }
  if (activeEditorListener) { activeEditorListener.dispose(); activeEditorListener = undefined; }
  if (idleTimer) { clearTimeout(idleTimer); idleTimer = undefined; }
  changeHistory = [];
  cursorHistory = [];
  fileHistory = [];
  lastActivity = { timestamp: 0, line: -1, filePath: '' };
}

// Track activity and reset idle timer
function trackActivity(line: number, filePath: string) {
  const now = Date.now();
  lastActivity = { timestamp: now, line, filePath };
  
  // Clear existing idle timer
  if (idleTimer) {
    clearTimeout(idleTimer);
  }
  
  // Set new idle timer (30 seconds of inactivity)
  idleTimer = setTimeout(() => {
    checkIdleState();
  }, 30000); // 30 seconds
}

// Check if user has been idle on the same line
function checkIdleState() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || isHintInProgress) return;
  
  const currentPosition = editor.selection.active;
  const currentFilePath = vscode.workspace.asRelativePath(editor.document.uri);
  const now = Date.now();
  
  // Check if still on the same line and file as when activity was last tracked
  if (currentPosition.line === lastActivity.line && 
      currentFilePath === lastActivity.filePath &&
      now - lastActivity.timestamp >= 30000) { // 30 seconds
    
    console.log(`IDLE DETECTED! User staring at line ${currentPosition.line + 1} for 30+ seconds`);
    
    // Get context word at current position
    const wordRange = editor.document.getWordRangeAtPosition(currentPosition);
    if (wordRange) {
      const contextWord = editor.document.getText(wordRange);
      checkHeuristics(editor.document, 'idle');
    }
  }
}

// Smart categorization using Dedalus API
async function categorizeKeyword(keyword: string): Promise<string> {
  try {
    const prompt = `Categorize this programming keyword into a single, clear concept category. 
Examples:
- "fetch", "fetc", "api", "axios" -> "API Calls"
- "useState", "useEffect", "useRef" -> "React Hooks" 
- "async", "await", "promise", "then" -> "Async Programming"
- "map", "filter", "reduce", "forEach" -> "Array Methods"
- "if", "else", "switch", "case" -> "Conditionals"
- "for", "while", "do" -> "Loops"

Keyword: "${keyword}"
Return only the category name, nothing else.`;

    const response = await dedalusClient.chat.create({
      input: [{ role: "user", content: prompt }],
      model: "gpt-4o-mini"
    });

    const category = (response as any).choices?.[0]?.message?.content || 
                    (response as any).final_output || 
                    (response as any).content || 
                    keyword; // Fallback to original keyword

    return category.trim();
  } catch (error) {
    console.error("Categorization error:", error);
    // Fallback to manual categorization
    return getCategoryFallback(keyword);
  }
}

// Fallback categorization when API fails
function getCategoryFallback(keyword: string): string {
  const lowerKeyword = keyword.toLowerCase();
  
  const categories = {
    'API Calls': ['fetch', 'api', 'axios', 'request', 'response', 'http', 'get', 'post'],
    'React Hooks': ['usestate', 'useeffect', 'useref', 'usememo', 'usecallback', 'usecontext'],
    'Async Programming': ['async', 'await', 'promise', 'then', 'catch', 'settimeout'],
    'Array Methods': ['map', 'filter', 'reduce', 'foreach', 'find', 'some', 'every'],
    'Conditionals': ['if', 'else', 'switch', 'case', 'ternary'],
    'Loops': ['for', 'while', 'do', 'loop'],
    'Functions': ['function', 'arrow', 'callback', 'return'],
    'Variables': ['const', 'let', 'var', 'variable'],
    'Objects': ['object', 'property', 'key', 'value', 'destructuring'],
    'DOM': ['document', 'element', 'queryselector', 'addeventlistener'],
    'Error Handling': ['error', 'try', 'catch', 'throw', 'exception']
  };

  for (const [category, keywords] of Object.entries(categories)) {
    if (keywords.some(k => lowerKeyword.includes(k) || k.includes(lowerKeyword))) {
      return category;
    }
  }

  return keyword; // If no match, return original
}

async function clearStuckEvents() {
  try {
    const stuckEventsRef = collection(db, "stuckEvents");
    const querySnapshot = await getDocs(stuckEventsRef);
    const batch = writeBatch(db);
    querySnapshot.forEach((doc) => { batch.delete(doc.ref); });
    await batch.commit();
    console.log("All stuck events deleted.");
    if (dashboardPanel) {
        dashboardPanel.webview.postMessage({ command: 'dataCleared' });
    }
  } catch (error) {
    console.error("Error clearing Firestore: ", error);
  }
}

function checkHeuristics(document: vscode.TextDocument, heuristic: 'churn' | 'cursor' | 'file' | 'idle') {
  const now = Date.now();
  const WINDOW_MS = 5000; // 5-second window for all heuristics
  
  // Clean old data
  changeHistory = changeHistory.filter(c => now - c.timestamp < WINDOW_MS);
  cursorHistory = cursorHistory.filter(c => now - c.timestamp < WINDOW_MS);
  fileHistory = fileHistory.filter(c => now - c.timestamp < WINDOW_MS);

  let shouldTrigger = false;
  let detectedPattern = '';

  if (heuristic === 'churn') {
    // Original code churn detection
    if (changeHistory.length > 5) {
      shouldTrigger = true;
      detectedPattern = `Rapid typing: ${changeHistory.length} changes in 5s`;
    }
  } else if (heuristic === 'cursor') {
    // Cursor jumping detection
    if (cursorHistory.length > 8) {
      const lineJumps = cursorHistory.filter((curr, i, arr) => {
        if (i === 0) return false;
        const prev = arr[i - 1];
        return Math.abs(curr.line - prev.line) > 5; // Jumping more than 5 lines
      }).length;
      
      if (lineJumps > 3) {
        shouldTrigger = true;
        detectedPattern = `Line jumping: ${lineJumps} big jumps in 5s`;
      }
    }
  } else if (heuristic === 'file') {
    // File switching detection
    if (fileHistory.length > 4) {
      const uniqueFiles = new Set(fileHistory.map(f => f.filePath)).size;
      if (uniqueFiles > 2) {
        shouldTrigger = true;
        detectedPattern = `File switching: ${uniqueFiles} different files in 5s`;
      }
    }
  } else if (heuristic === 'idle') {
    // Idle detection - always trigger when called (already validated in checkIdleState)
    shouldTrigger = true;
    detectedPattern = `Idle staring: 30+ seconds on same line`;
  }

  if (shouldTrigger) {
    console.log(`${heuristic.toUpperCase()} PATTERN DETECTED! ${detectedPattern}`);
    const editor = vscode.window.activeTextEditor;
    if (!editor) { return; }
    const position = editor.selection.active;
    const wordRange = document.getWordRangeAtPosition(position);
    if (!wordRange) { return; }
    const contextWord = document.getText(wordRange);
    const filePath = vscode.workspace.asRelativePath(document.uri);
    offerSuggestion(contextWord, document.languageId, heuristic, filePath);
    
    // Clear the specific history that triggered
    if (heuristic === 'churn') changeHistory = [];
    else if (heuristic === 'cursor') cursorHistory = [];
    else if (heuristic === 'file') fileHistory = [];
    else if (heuristic === 'idle') {
      // Reset idle timer and activity tracking
      if (idleTimer) clearTimeout(idleTimer);
      lastActivity = { timestamp: now, line: position.line, filePath };
    }
  }
}

async function offerSuggestion(contextWord: string, languageId: string, heuristic: 'churn' | 'cursor' | 'file' | 'idle', filePath: string) {
  if (isHintInProgress) { return; }
  if (!contextWord || contextWord.length < 3 || contextWord === 'const' || contextWord === 'let') {
    return;
  }

  isHintInProgress = true;
  
  // Contextual messages based on detection method
  const detectionMessages = {
    'churn': `I noticed rapid changes around "${contextWord}"...`,
    'cursor': `I see you're jumping around near "${contextWord}"...`,
    'file': `You're switching between files, currently at "${contextWord}"...`,
    'idle': `You've been staring at "${contextWord}" for a while...`
  };
  
  vscode.window.showInformationMessage(detectionMessages[heuristic]);
  
  // Enhanced prompt based on detection pattern
  const contextualPrompts = {
    'churn': `A user is making rapid changes to code around "${contextWord}" in ${languageId}, suggesting they're stuck on implementation.`,
    'cursor': `A user is jumping between lines of code around "${contextWord}" in ${languageId}, suggesting they're trying to understand how pieces connect.`,
    'file': `A user is switching between multiple files and is currently looking at "${contextWord}" in ${languageId}, suggesting they're trying to trace how code flows between files.`,
    'idle': `A user has been staring at "${contextWord}" in ${languageId} for over 30 seconds without moving, suggesting they're deeply stuck or confused about this concept.`
  };
  
  const systemPrompt = `You are a coding tutor. ${contextualPrompts[heuristic]} DO NOT write code. DO NOT solve the problem. Ask one single, short, guiding question that helps them think about the core concept or debugging approach.`;
  const fullPrompt = systemPrompt + `\n\nKeyword: "${contextWord}"\nDetection: ${heuristic}`;
  let aiHint = `(No hint generated)`;

  try {
    // --- THIS IS THE **REAL** DEDALUS AI CALL ---
    const response = await dedalusClient.chat.create({
      model: "gemini-2.5-flash-preview-09-2025", 
      input: [{ role: "user", content: fullPrompt }]
    });
    aiHint = (response as any).choices?.[0]?.message?.content || (response as any).final_output || (response as any).content || "Keep going, you've got this!";
    vscode.window.showInformationMessage(aiHint, "Got it!");
  } catch (error) {
    console.error("Dedalus AI error:", error);
    vscode.window.showErrorMessage('AI Assistant failed to get hint.');
    const errorMessage = error instanceof Error ? error.message : String(error);
    aiHint = `(AI FAILED: ${errorMessage})`;
  } finally {
    // --- SMART CATEGORIZATION ---
    const category = await categorizeKeyword(contextWord);
    console.log(`Categorized "${contextWord}" -> "${category}"`);
    
    // --- WE LOG THE EVENT WITH BOTH ORIGINAL AND CATEGORIZED DATA ---
    await addDoc(collection(db, "stuckEvents"), {
      timestamp: new Date(),
      studentId: globalStudentId,
      contextWord: contextWord,
      category: category, // Smart categorized version for charts
      heuristic: heuristic, 
      language: languageId,
      filePath: filePath,
      hint: aiHint
    });
    setTimeout(() => { isHintInProgress = false; }, 10000);
  }
}

export function deactivate() {
  stopListeners();
  if (dashboardPanel) {
    dashboardPanel.dispose();
  }
}