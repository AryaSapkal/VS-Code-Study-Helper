import * as vscode from 'vscode';
import axios from 'axios';

export class StuckDetector {
    private disposables: vscode.Disposable[] = [];
    private monitoring = false;
    private monitoringInterval?: NodeJS.Timeout;
    private signals: any = {};
    private startTime = Date.now();
    private lastAnswerTime = 0; // Track when last answer was given (5min cooldown)
    
    private statusBarItem?: vscode.StatusBarItem;
    
    constructor(statusBarItem?: vscode.StatusBarItem) {
        console.log('🔧 StuckDetector initialized');
        this.statusBarItem = statusBarItem;
        this.setupEventListeners();
        this.resetSignals();
        this.updateStatusBar();
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
    }
    
    private resetSignals() {
        console.log('📊 Resetting ML signals...');
        this.signals = {
            // Core ML model features (18 total)
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
            context_switches: 0,  // renamed from window_switches
            focus_time_avg: 0,
            comment_keywords: 0,
            comment_length_avg: 0
        };
        this.startTime = Date.now();
    }
    
    private calculateSignals() {
        const now = Date.now();
        const timeElapsed = (now - this.startTime) / 1000; // seconds
        
        // Calculate time-based metrics
        this.signals.idle_time_total = timeElapsed;
        this.signals.idle_time_max = Math.max(this.signals.idle_time_max, timeElapsed / 10); // Simplified
        
        // Calculate edit velocity (edits per second)
        this.signals.edit_velocity = timeElapsed > 0 ? this.signals.edit_events / timeElapsed : 0;
        
        // Calculate cursor entropy (how random the cursor movement is)
        this.signals.cursor_entropy = this.signals.cursor_moves > 0 ? Math.log2(this.signals.cursor_moves + 1) : 0;
        
        // Estimate focus time (inverse of context switches)
        this.signals.focus_time_avg = this.signals.context_switches > 0 ? timeElapsed / (this.signals.context_switches + 1) : timeElapsed;
        
        // Simple heuristics for missing features
        this.signals.unique_errors = Math.min(this.signals.error_events, 5); // Assume max 5 unique errors
        this.signals.error_repeat_count = Math.max(0, this.signals.error_events - this.signals.unique_errors);
        this.signals.error_persistence = this.signals.error_events > 0 ? this.signals.error_events / (timeElapsed / 60) : 0;
        this.signals.run_attempt_count = Math.floor(this.signals.error_events / 2); // Rough estimate
        
        // Time since last run (simulate based on error patterns)
        this.signals.time_since_last_run = this.signals.error_events > 3 ? timeElapsed * 0.8 : timeElapsed * 0.3;
        
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
    
    private onTextChange(event: vscode.TextDocumentChangeEvent) {
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
            }
        }
        
        const totalChanges = deletions + insertions;
        if (totalChanges > 0) {
            this.signals.backspace_ratio = deletions / totalChanges;
        }
        
        // Update edit velocity
        const now = Date.now();
        const timeElapsed = (now - this.startTime) / 1000;
        this.signals.edit_velocity = this.signals.edit_events / timeElapsed;
    }
    
    private onSelectionChange(event: vscode.TextEditorSelectionChangeEvent) {
        this.signals.cursor_moves++;
        
        // Calculate cursor distance (simplified)
        if (event.selections.length > 0) {
            const selection = event.selections[0];
            this.signals.cursor_distance += Math.abs(selection.start.line - selection.end.line);
        }
    }
    
    private onWindowStateChange(event: vscode.WindowState) {
        if (!event.focused) {
            this.signals.context_switches++;  // Updated to match ML model
        }
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
                console.log('💡 ML detected stuck - showing hint with feedback options');
                
                // Update status bar to show detection
                if (this.statusBarItem) {
                    this.statusBarItem.text = "🚨 Stuck Detected!";
                    this.statusBarItem.tooltip = "Getting help...";
                    this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
                }
                
                // Automatically get and show hint with feedback options
                await this.getHintAndShowFeedback();
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
        
        // Update status bar to show hint is being requested
        if (this.statusBarItem) {
            this.statusBarItem.text = "⏳ Getting Hint...";
            this.statusBarItem.tooltip = "Requesting hint from AI...";
        }
        
        const config = vscode.workspace.getConfiguration('stuckDetector');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        
        // Get current context
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            vscode.window.showErrorMessage('No active editor found for hint generation');
            return;
        }

        // Extract context word (word under cursor)
        const position = activeEditor.selection.active;
        const wordRange = activeEditor.document.getWordRangeAtPosition(position);
        const contextWord = wordRange ? activeEditor.document.getText(wordRange) : 'code';
        
        // Determine heuristic based on signals
        let heuristic = 'general_stuck';
        if (this.signals.backspace_ratio > 0.5) heuristic = 'repetitive_editing';
        if (this.signals.cursor_moves > 20) heuristic = 'cursor_thrashing';  
        if (this.signals.idle_time_total > 120) heuristic = 'idle_too_long';
        if (this.signals.error_events > 3) heuristic = 'many_errors';
        
        const hintRequest = {
            contextWord: contextWord,
            languageId: activeEditor.document.languageId,
            heuristic: heuristic,
            codeSnippet: this.getSurroundingCode(activeEditor)
        };
        
        console.log('🔍 Hint request:', hintRequest);
        
        try {
            const response = await axios.post(`${backendUrl}/get-hint`, hintRequest);
            
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
        } finally {
            // Restore status bar
            this.updateStatusBar();
        }
    }

    public async getHintAndShowFeedback() {
        console.log('💡 Getting AI hint with feedback...');
        
        const config = vscode.workspace.getConfiguration('stuckDetector');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        
        // Get current context
        const activeEditor = vscode.window.activeTextEditor;
        if (!activeEditor) {
            vscode.window.showErrorMessage('No active editor found for hint generation');
            return;
        }

        // Extract context word (word under cursor)
        const position = activeEditor.selection.active;
        const wordRange = activeEditor.document.getWordRangeAtPosition(position);
        const contextWord = wordRange ? activeEditor.document.getText(wordRange) : 'code';
        
        // Determine heuristic based on signals
        let heuristic = 'general_stuck';
        if (this.signals.backspace_ratio > 0.5) heuristic = 'repetitive_editing';
        if (this.signals.cursor_moves > 20) heuristic = 'cursor_thrashing';  
        if (this.signals.idle_time_total > 120) heuristic = 'idle_too_long';
        if (this.signals.error_events > 3) heuristic = 'many_errors';
        
        const hintRequest = {
            contextWord: contextWord,
            languageId: activeEditor.document.languageId,
            heuristic: heuristic,
            codeSnippet: this.getSurroundingCode(activeEditor)
        };
        
        console.log('🔍 Hint request:', hintRequest);
        
        try {
            const response = await axios.post(`${backendUrl}/get-hint`, hintRequest);
            
            const result = response.data;
            console.log('💡 AI Hint:', result.hint);
            
            // Show hint with feedback and answer options
            const now = Date.now();
            const answerCooldown = 5 * 60 * 1000; // 5 minutes for answers
            const canGiveAnswer = (now - this.lastAnswerTime) > answerCooldown;
            
            const buttons = ['✅ Helpful', '❌ Not Helpful'];
            if (canGiveAnswer) {
                buttons.push('🎯 Give Answer');
            }
            
            vscode.window.showInformationMessage(
                `💡 ${result.hint}`,
                ...buttons
            ).then(async (selection) => {
                if (selection) {
                    if (selection === '🎯 Give Answer') {
                        // Handle direct answer request
                        this.lastAnswerTime = Date.now();
                        await this.getDirectAnswer(hintRequest);
                    } else {
                        // Send feedback to backend for model improvement
                        const feedback = {
                            helpful: selection === '✅ Helpful',
                            hint: result.hint,
                            context: hintRequest,
                            timestamp: new Date().toISOString()
                        };
                        
                        try {
                            await axios.post(`${backendUrl}/feedback`, feedback);
                            console.log('📊 Feedback sent:', feedback);
                        } catch (error) {
                            console.error('❌ Failed to send feedback:', error);
                        }
                    }
                }
            });
            
        } catch (error) {
            console.error('❌ Error getting hint:', error);
            vscode.window.showErrorMessage('Failed to get hint. Is the backend running?');
        }
    }

    public async getDirectAnswer(hintRequest: any) {
        console.log('🎯 Getting direct answer...');
        
        const config = vscode.workspace.getConfiguration('stuckDetector');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        
        try {
            // Request a direct answer instead of a hint
            const answerRequest = {
                ...hintRequest,
                requestType: 'direct_answer'
            };
            
            const response = await axios.post(`${backendUrl}/get-answer`, answerRequest);
            
            const result = response.data;
            console.log('🎯 Direct Answer:', result.answer);
            
            // Show the answer in a more prominent way
            vscode.window.showWarningMessage(
                `🎯 Direct Answer: ${result.answer}`,
                'Got it!'
            );
            
        } catch (error) {
            console.error('❌ Error getting direct answer:', error);
            vscode.window.showErrorMessage('Failed to get direct answer. Is the backend running?');
        }
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
        const interval = config.get<number>('monitoringInterval', 20000); // Doubled from 10000 to 20000ms (20 seconds)
        
        this.monitoringInterval = setInterval(() => {
            this.checkIfStuck();
        }, interval);
        
        this.updateStatusBar();
        vscode.window.showInformationMessage('📡 Automatic stuck detection enabled!');
    }
    
    private stopMonitoring() {
        console.log('🛑 Stopping automatic monitoring...');
        this.monitoring = false;
        
        if (this.monitoringInterval) {
            clearInterval(this.monitoringInterval);
            this.monitoringInterval = undefined;
        }
        
        this.updateStatusBar();
        vscode.window.showInformationMessage('🛑 Automatic stuck detection disabled!');
    }
    
    private updateStatusBar() {
        if (!this.statusBarItem) return;
        
        if (this.monitoring) {
            // Show that monitoring is active and hints are always available
            this.statusBarItem.text = "🔍 💡 Get Hint";
            this.statusBarItem.tooltip = "Monitoring active - Click to request a coding hint anytime";
            this.statusBarItem.backgroundColor = undefined; // Default color
        } else {
            // Show that monitoring is disabled but hints are still available
            this.statusBarItem.text = "⏸️ 💡 Get Hint";
            this.statusBarItem.tooltip = "Monitoring paused - Click to request a coding hint anytime";
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        }
    }
    
    public simulateStuckBehavior() {
        console.log('🧪 Simulating stuck behavior for testing...');
        
        // Create stuck-like signals
        this.signals.idle_time_total = 180;
        this.signals.edit_events = 2;
        this.signals.edit_velocity = 0.02;
        this.signals.backspace_ratio = 0.8;
        this.signals.cursor_moves = 40;
        this.signals.error_events = 5;
        this.signals.cursor_entropy = 2.5;
        this.signals.context_switches = 4;
        this.signals.unique_errors = 3;
        this.signals.error_repeat_count = 8;
        this.signals.error_persistence = 0.7;
        this.signals.time_since_last_run = 400;
        this.signals.run_attempt_count = 4;
        this.signals.focus_time_avg = 20;
        
        // Immediately check if stuck
        this.checkIfStuck();
        
        vscode.window.showInformationMessage('🧪 Simulated stuck behavior - check should trigger!');
    }

    dispose() {
        this.stopMonitoring();
        this.disposables.forEach(d => d.dispose());
    }
}