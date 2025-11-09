import * as vscode from 'vscode';
import axios from 'axios';

export class StuckDetector {
    private disposables: vscode.Disposable[] = [];
    private monitoring = false;
    private monitoringInterval?: NodeJS.Timeout;
    private signals: any = {};
    private startTime = Date.now();
    
    constructor() {
        console.log('🔧 StuckDetector initialized');
        this.setupEventListeners();
        this.resetSignals();
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
            idle_time_total: 0,
            edit_events: 0,
            error_events: 0,
            edit_velocity: 0,
            backspace_ratio: 0,
            cursor_moves: 0,
            cursor_distance: 0,
            time_since_last_run: 0,
            window_switches: 0,
            file_switches: 0,
            copy_paste_events: 0,
            undo_redo_events: 0,
            search_events: 0,
            autocomplete_events: 0,
            scroll_events: 0,
            time_on_line: 0,
            chars_per_minute: 0,
            lines_per_minute: 0
        };
        this.startTime = Date.now();
    }
    
    private calculateSignals() {
        const now = Date.now();
        const timeElapsed = (now - this.startTime) / 1000; // seconds
        
        // Calculate time-based metrics
        this.signals.idle_time_total = timeElapsed;
        this.signals.chars_per_minute = this.signals.edit_events / (timeElapsed / 60);
        this.signals.lines_per_minute = this.signals.edit_events / (timeElapsed / 60);
        
        console.log('📈 Current ML Signals:');
        console.log(`  • Idle Time: ${this.signals.idle_time_total.toFixed(1)}s`);
        console.log(`  • Edit Events: ${this.signals.edit_events}`);
        console.log(`  • Error Events: ${this.signals.error_events}`);
        console.log(`  • Edit Velocity: ${this.signals.edit_velocity.toFixed(2)}`);
        console.log(`  • Backspace Ratio: ${this.signals.backspace_ratio.toFixed(2)}`);
        console.log(`  • Cursor Moves: ${this.signals.cursor_moves}`);
        console.log(`  • Cursor Distance: ${this.signals.cursor_distance}`);
        console.log(`  • Window Switches: ${this.signals.window_switches}`);
        console.log(`  • File Switches: ${this.signals.file_switches}`);
        console.log(`  • Copy/Paste Events: ${this.signals.copy_paste_events}`);
        console.log(`  • Undo/Redo Events: ${this.signals.undo_redo_events}`);
        console.log(`  • Search Events: ${this.signals.search_events}`);
        console.log(`  • Autocomplete Events: ${this.signals.autocomplete_events}`);
        console.log(`  • Scroll Events: ${this.signals.scroll_events}`);
        console.log(`  • Time on Line: ${this.signals.time_on_line.toFixed(1)}s`);
        console.log(`  • Chars/Min: ${this.signals.chars_per_minute.toFixed(1)}`);
        console.log(`  • Lines/Min: ${this.signals.lines_per_minute.toFixed(1)}`);
        
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
            this.signals.window_switches++;
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
                vscode.window.showWarningMessage(
                    `🤔 You might be stuck! (Confidence: ${(result.confidence * 100).toFixed(1)}%)`,
                    'Get Hint', 'Ignore'
                ).then(selection => {
                    if (selection === 'Get Hint') {
                        this.getHint();
                    }
                });
            } else {
                vscode.window.showInformationMessage(
                    `✅ You're doing great! Keep coding! (Confidence: ${(result.confidence * 100).toFixed(1)}%)`
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
        const context = activeEditor ? {
            language: activeEditor.document.languageId,
            currentLine: activeEditor.selection.active.line,
            selectedText: activeEditor.document.getText(activeEditor.selection) || '',
            surroundingCode: this.getSurroundingCode(activeEditor)
        } : {};
        
        try {
            const response = await axios.post(`${backendUrl}/get-hint`, {
                context: context,
                signals: this.signals
            });
            
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