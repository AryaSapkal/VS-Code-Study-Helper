import * as vscode from 'vscode';
import { StuckDetector } from './stuckDetector';

export function activate(context: vscode.ExtensionContext) {
    console.log('🚀 Stuck Detector extension is now active!');
    
    // Create status bar item for manual hint requests
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = "💡 Get Hint";
    statusBarItem.tooltip = "Click to request a coding hint";
    statusBarItem.command = 'stuckDetector.getHint';
    statusBarItem.show();
    
    // Initialize the stuck detector with status bar reference
    const stuckDetector = new StuckDetector(statusBarItem);
    
    // Add to subscriptions for cleanup
    context.subscriptions.push(statusBarItem);
    
    // Start monitoring automatically after a short delay
    setTimeout(() => {
        stuckDetector.toggleMonitoring();
    }, 2000);
    
    // Show welcome message
    vscode.window.showInformationMessage('🤖 Stuck Detector is ready to help you code!');
    
    // Register commands
    const checkStatus = vscode.commands.registerCommand('stuckDetector.checkStatus', () => {
        stuckDetector.checkIfStuck();
    });
    
    const getHint = vscode.commands.registerCommand('stuckDetector.getHint', () => {
        stuckDetector.getHint();
    });
    
    const toggleMonitoring = vscode.commands.registerCommand('stuckDetector.toggleMonitoring', () => {
        stuckDetector.toggleMonitoring();
    });
    
    const simulateStuck = vscode.commands.registerCommand('stuckDetector.simulateStuck', () => {
        stuckDetector.simulateStuckBehavior();
    });
    
    context.subscriptions.push(checkStatus, getHint, toggleMonitoring, simulateStuck, stuckDetector);
}

export function deactivate() {
    console.log('👋 Stuck Detector extension is now deactivated');
}