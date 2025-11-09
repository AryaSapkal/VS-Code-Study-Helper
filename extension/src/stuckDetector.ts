import * as vscode from 'vscode';
import axios from 'axios';

interface MLSignals {
    idle_time_total: number;
    idle_time_max: number;
    edit_events: number;
    edit_velocity: number;
    backspace_ratio: number;
    cursor_moves: number;
    cursor_distance: number;
    cursor_entropy: number;
    error_events: number;
    unique_errors: number;
    error_repeat_count: number;
    error_persistence: number;
    time_since_last_run: number;
    run_attempt_count: number;
    context_switches: number;
    focus_time_avg: number;
    comment_keywords: number;
    comment_length_avg: number;
}

export class StuckDetector {
    private disposables: vscode.Disposable[] = [];
    private monitoring = false;
    private monitoringInterval?: NodeJS.Timeout;
    private signals: MLSignals;
    private startTime = Date.now();
    private lastActivityTime = Date.now();
    private maxIdleTime = 0;
    
    // Error tracking
    private errorMessages: Set<string> = new Set();
    private errorCounts: Map<string, number> = new Map();
    private lastErrorMessage: string = '';
    private lastErrorCount: number = 0;
    
    // Cursor tracking
    private cursorPositions: number[] = [];
    private lastCursorLine: number = 0;
    
    // Execution tracking
    private lastRunTime: number = Date.now();
    
    // File tracking
    private currentFile: string = '';
    private fileStartTime: number = Date.now();
    private fileTimes: number[] = [];
    
    // Comment tracking
    private stuckKeywords = ['todo', 'fix', 'fixme', 'bug', 'help', 'stuck', 'broken', 'issue'];
    
    constructor() {
        console.log('Nudge.ai initialized');
        this.signals = this.createEmptySignals();
        this.setupEventListeners();
        this.resetSignals();
    }
    
    private createEmptySignals(): MLSignals {
        return {
            idle_time_total: 0,
            idle_time_max: 0,
            edit_events: 0,
            edit_velocity: 0,
            backspace_ratio: 0,
            cursor_moves: 0,
            cursor_distance: 0,
            cursor_entropy: 0,
            error_events: 0,
            unique_errors: 0,
            error_repeat_count: 0,
            error_persistence: 0,
            time_since_last_run: 0,
            run_attempt_count: 0,
            context_switches: 0,
            focus_time_avg: 0,
            comment_keywords: 0,
            comment_length_avg: 0
        };
    }
    
    private setupEventListeners() {
        // Document change events
        this.disposables.push(
            vscode.workspace.onDidChangeTextDocument(this.onTextChange.bind(this))
        );
        
        // Selection change events  
        this.disposables.push(
            vscode.window.onDidChangeTextEditorSelection(this.onSelectionChange.bind(this))
        );
        
        // Window focus events
        this.disposables.push(
            vscode.window.onDidChangeWindowState(this.onWindowStateChange.bind(this))
        );
        
        // Error/diagnostic events
        this.disposables.push(
            vscode.languages.onDidChangeDiagnostics(this.onDiagnosticsChange.bind(this))
        );
        
        // Debug/execution events
        this.disposables.push(
            vscode.debug.onDidStartDebugSession(this.onDebugStart.bind(this))
        );
        
        // Active editor change (file switching)
        this.disposables.push(
            vscode.window.onDidChangeActiveTextEditor(this.onActiveEditorChange.bind(this))
        );
    }
    
    private resetSignals() {
        console.log('📊 Resetting ML signals...');
        this.signals = this.createEmptySignals();
        this.startTime = Date.now();
        this.lastActivityTime = Date.now();
        this.maxIdleTime = 0;
        this.errorMessages.clear();
        this.errorCounts.clear();
        this.cursorPositions = [];
        this.fileTimes = [];
    }
    
    private updateActivity() {
        const now = Date.now();
        const idleTime = (now - this.lastActivityTime) / 1000;
        
        if (idleTime > this.maxIdleTime) {
            this.maxIdleTime = idleTime;
        }
        
        this.lastActivityTime = now;
    }
    
    private calculateSignals(): MLSignals {
        const now = Date.now();
        const timeElapsed = (now - this.startTime) / 1000; // seconds
        
        // Calculate idle times
        this.signals.idle_time_total = (now - this.lastActivityTime) / 1000;
        this.signals.idle_time_max = this.maxIdleTime;
        
        // Calculate edit velocity
        if (timeElapsed > 0) {
            this.signals.edit_velocity = this.signals.edit_events / timeElapsed;
        }
        
        // Calculate cursor entropy (measure of randomness in cursor movement)
        if (this.cursorPositions.length > 1) {
            this.signals.cursor_entropy = this.calculateEntropy(this.cursorPositions);
        }
        
        // Calculate error metrics
        this.signals.unique_errors = this.errorMessages.size;
        this.signals.error_repeat_count = Array.from(this.errorCounts.values())
            .filter(count => count > 1).length;
        
        // Calculate error persistence (same error keeps appearing)
        if (this.signals.error_events > 0 && this.lastErrorCount > 0) {
            this.signals.error_persistence = this.lastErrorCount / this.signals.error_events;
        }
        
        // Calculate time since last run
        this.signals.time_since_last_run = (now - this.lastRunTime) / 1000;
        
        // Calculate average focus time per file
        if (this.fileTimes.length > 0) {
            const sum = this.fileTimes.reduce((a, b) => a + b, 0);
            this.signals.focus_time_avg = sum / this.fileTimes.length;
        }
        
        console.log('📈 Current ML Signals:');
        console.log(`  • Idle Time Total: ${this.signals.idle_time_total.toFixed(1)}s`);
        console.log(`  • Idle Time Max: ${this.signals.idle_time_max.toFixed(1)}s`);
        console.log(`  • Edit Events: ${this.signals.edit_events}`);
        console.log(`  • Edit Velocity: ${this.signals.edit_velocity.toFixed(2)}`);
        console.log(`  • Backspace Ratio: ${this.signals.backspace_ratio.toFixed(2)}`);
        console.log(`  • Cursor Moves: ${this.signals.cursor_moves}`);
        console.log(`  • Cursor Distance: ${this.signals.cursor_distance}`);
        console.log(`  • Cursor Entropy: ${this.signals.cursor_entropy.toFixed(2)}`);
        console.log(`  • Error Events: ${this.signals.error_events}`);
        console.log(`  • Unique Errors: ${this.signals.unique_errors}`);
        console.log(`  • Error Repeat Count: ${this.signals.error_repeat_count}`);
        console.log(`  • Error Persistence: ${this.signals.error_persistence.toFixed(2)}`);
        console.log(`  • Time Since Last Run: ${this.signals.time_since_last_run.toFixed(1)}s`);
        console.log(`  • Run Attempt Count: ${this.signals.run_attempt_count}`);
        console.log(`  • Context Switches: ${this.signals.context_switches}`);
        console.log(`  • Focus Time Avg: ${this.signals.focus_time_avg.toFixed(1)}s`);
        console.log(`  • Comment Keywords: ${this.signals.comment_keywords}`);
        console.log(`  • Comment Length Avg: ${this.signals.comment_length_avg.toFixed(1)}`);
        
        return this.signals;
    }
    
    private calculateEntropy(positions: number[]): number {
        // Calculate Shannon entropy of cursor positions to measure randomness
        if (positions.length < 2) return 0;
        
        // Calculate differences between consecutive positions
        const diffs = [];
        for (let i = 1; i < positions.length; i++) {
            diffs.push(Math.abs(positions[i] - positions[i-1]));
        }
        
        // Group into bins (0-5 lines, 6-20 lines, 21+ lines)
        const bins = [0, 0, 0];
        for (const diff of diffs) {
            if (diff <= 5) bins[0]++;
            else if (diff <= 20) bins[1]++;
            else bins[2]++;
        }
        
        // Calculate entropy
        let entropy = 0;
        const total = diffs.length;
        for (const count of bins) {
            if (count > 0) {
                const p = count / total;
                entropy -= p * Math.log2(p);
            }
        }
        
        return entropy;
    }
    
    private onTextChange(event: vscode.TextDocumentChangeEvent) {
        this.updateActivity();
        this.signals.edit_events++;
        
        // Calculate backspace ratio
        const changes = event.contentChanges;
        let deletions = 0;
        let insertions = 0;
        
        for (const change of changes) {
            if (change.text === '') {
                deletions += change.rangeLength;
            } else {
                insertions += change.text.length;
                
                // Check for stuck keywords in comments
                const text = change.text.toLowerCase();
                for (const keyword of this.stuckKeywords) {
                    if (text.includes(keyword) && (text.includes('//') || text.includes('#') || text.includes('/*'))) {
                        this.signals.comment_keywords++;
                    }
                }
                
                // Track comment length
                if (text.includes('//') || text.includes('#') || text.includes('/*')) {
                    const commentLength = change.text.length;
                    const currentTotal = this.signals.comment_length_avg * (this.signals.edit_events - 1);
                    this.signals.comment_length_avg = (currentTotal + commentLength) / this.signals.edit_events;
                }
            }
        }
        
        const totalChanges = deletions + insertions;
        if (totalChanges > 0) {
            // Update backspace ratio as running average
            const currentRatio = deletions / totalChanges;
            const n = this.signals.edit_events;
            this.signals.backspace_ratio = (this.signals.backspace_ratio * (n - 1) + currentRatio) / n;
        }
    }
    
    private onSelectionChange(event: vscode.TextEditorSelectionChangeEvent) {
        this.updateActivity();
        this.signals.cursor_moves++;
        
        // Calculate cursor distance (line-based)
        if (event.selections.length > 0) {
            const selection = event.selections[0];
            const currentLine = selection.active.line;
            
            // Track distance from last position
            const distance = Math.abs(currentLine - this.lastCursorLine);
            this.signals.cursor_distance += distance;
            
            // Store position for entropy calculation
            this.cursorPositions.push(currentLine);
            if (this.cursorPositions.length > 50) {
                this.cursorPositions.shift(); // Keep last 50 positions
            }
            
            this.lastCursorLine = currentLine;
        }
    }
    
    private onWindowStateChange(event: vscode.WindowState) {
        if (!event.focused) {
            this.signals.context_switches++;
        }
    }
    
    private onDiagnosticsChange(event: vscode.DiagnosticChangeEvent) {
        // Track errors from diagnostics (syntax errors, type errors, etc.)
        for (const uri of event.uris) {
            const diagnostics = vscode.languages.getDiagnostics(uri);
            const errors = diagnostics.filter(d => 
                d.severity === vscode.DiagnosticSeverity.Error
            );
            
            // Update error count
            const previousErrorCount = this.signals.error_events;
            this.signals.error_events = errors.length;
            
            // Track unique error messages
            for (const error of errors) {
                const errorMsg = error.message;
                this.errorMessages.add(errorMsg);
                
                // Track error frequency
                const currentCount = this.errorCounts.get(errorMsg) || 0;
                this.errorCounts.set(errorMsg, currentCount + 1);
                
                // Track if same error persists
                if (errorMsg === this.lastErrorMessage) {
                    this.lastErrorCount++;
                } else {
                    this.lastErrorMessage = errorMsg;
                    this.lastErrorCount = 1;
                }
            }
        }
    }
    
    private onDebugStart() {
        this.updateActivity();
        this.signals.run_attempt_count++;
        this.lastRunTime = Date.now();
        this.signals.time_since_last_run = 0;
        console.log('▶️ Code execution detected');
    }
    
    private onActiveEditorChange(editor: vscode.TextEditor | undefined) {
        if (!editor) return;
        
        const newFile = editor.document.uri.toString();
        
        // Track file switch
        if (newFile !== this.currentFile && this.currentFile !== '') {
            this.signals.context_switches++;
            
            // Calculate time spent on previous file
            const timeOnFile = (Date.now() - this.fileStartTime) / 1000;
            this.fileTimes.push(timeOnFile);
            if (this.fileTimes.length > 20) {
                this.fileTimes.shift(); // Keep last 20
            }
            
            console.log(`📄 File switch: ${timeOnFile.toFixed(1)}s on previous file`);
        }
        
        this.currentFile = newFile;
        this.fileStartTime = Date.now();
    }
    
    public async checkIfStuck() {
        console.log('🔍 Checking if user is stuck...');
        
        const signals = this.calculateSignals();
        const config = vscode.workspace.getConfiguration('stuckDetector');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        
        try {
            const response = await axios.post(`${backendUrl}/predict-stuck`, {
                signals: signals
            });
            
            const result = response.data;
            console.log('🤖 ML Prediction Result:', result);
            
            if (result.is_stuck) {
                vscode.window.showWarningMessage(
                    `🤔 You might be stuck! (Confidence: ${(result.confidence * 100).toFixed(1)}%)`,
                    'Get Hint', 'I\'m Not Stuck', 'Ignore'
                ).then(selection => {
                    if (selection === 'Get Hint') {
                        this.getHint();
                        // Log confirmed stuck
                        this.logFeedback(true, 'confirmed');
                    } else if (selection === 'I\'m Not Stuck') {
                        // Log rejected prediction
                        this.logFeedback(false, 'rejected');
                    }
                });
            } else {
                vscode.window.showInformationMessage(
                    `✅ You're doing great! Keep coding!`
                );
            }
            
        } catch (error) {
            console.error('❌ Error checking stuck status:', error);
            vscode.window.showErrorMessage('Failed to check stuck status. Is the backend running?');
        }
    }
    
    public async getHint() {
        console.log('💡 Getting AI hint...');
        
        const config = vscode.workspace.getConfiguration('stuckDetector');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        
        // Get current context
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            vscode.window.showWarningMessage('No active editor found');
            return;
        }
        
        const currentLine = activeEditor.document.lineAt(activeEditor.selection.active.line);
        const contextWord = this.getWordAtPosition(activeEditor);
        
        const context = {
            contextWord: contextWord || '',
            languageId: activeEditor.document.languageId,
            heuristic: 'manual_request',
            codeSnippet: this.getSurroundingCode(activeEditor)
        };
        
        try {
            const response = await axios.post(`${backendUrl}/get-hint`, context);
            
            const result = response.data;
            console.log('💡 AI Hint:', result.hint);
            
            vscode.window.showInformationMessage(
                result.hint,
                'Thanks!', 'More Help'
            ).then(selection => {
                if (selection === 'More Help') {
                    vscode.env.openExternal(vscode.Uri.parse('https://stackoverflow.com'));
                }
            });
            
        } catch (error) {
            console.error('❌ Error getting hint:', error);
            vscode.window.showErrorMessage('Failed to get hint. Is the backend running?');
        }
    }
    
    private async logFeedback(wasStuck: boolean, source: 'manual' | 'confirmed' | 'rejected') {
        const config = vscode.workspace.getConfiguration('stuckDetector');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        
        try {
            await axios.post(`${backendUrl}/log-ml-feedback`, {
                signals: this.signals,
                was_stuck: wasStuck,
                source: source
            });
            
            console.log(`✅ Logged feedback: ${source} - stuck: ${wasStuck}`);
            
        } catch (error) {
            console.error('❌ Error logging feedback:', error);
        }
    }
    
    public async reportStuck() {
        console.log('🆘 User manually reported being stuck');
        await this.logFeedback(true, 'manual');
        await this.getHint();
        vscode.window.showInformationMessage('Thanks for the feedback! Getting you a hint...');
    }
    
    private getWordAtPosition(editor: vscode.TextEditor): string {
        const position = editor.selection.active;
        const range = editor.document.getWordRangeAtPosition(position);
        return range ? editor.document.getText(range) : '';
    }
    
    private getSurroundingCode(editor: vscode.TextEditor): string {
        const currentLine = editor.selection.active.line;
        const startLine = Math.max(0, currentLine - 5);
        const endLine = Math.min(editor.document.lineCount - 1, currentLine + 5);
        
        const range = new vscode.Range(startLine, 0, endLine, 0);
        return editor.document.getText(range);
    }
    
    public toggleMonitoring() {
        if (this.monitoring) {
            this.stopMonitoring();
        } else {
            this.startMonitoring();
        }
    }
    
    private startMonitoring() {
        console.log('📡 Starting automatic monitoring...');
        this.monitoring = true;
        
        const config = vscode.workspace.getConfiguration('stuckDetector');
        const interval = config.get<number>('monitoringInterval', 30000);
        
        this.monitoringInterval = setInterval(() => {
            this.checkIfStuck();
        }, interval);
        
        vscode.window.showInformationMessage('📡 Automatic stuck detection enabled!');
    }
    
    private stopMonitoring() {
        console.log('🛑 Stopping automatic monitoring...');
        this.monitoring = false;
        
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = undefined;
        }
        
        vscode.window.showInformationMessage('🛑 Automatic stuck detection disabled!');
    }
    
    dispose() {
        this.stopMonitoring();
        this.disposables.forEach(d => d.dispose());
    }
}