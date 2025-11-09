import * as vscode from 'vscode';
import { StuckDetector } from './stuckDetector';

export function activate(context: vscode.ExtensionContext) {
    console.log('🚀 Stuck Detector extension is now active!');
    
    // Initialize the stuck detector
    const stuckDetector = new StuckDetector();
    
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
    
    context.subscriptions.push(checkStatus, getHint, toggleMonitoring, stuckDetector);
}

export function deactivate() {
    console.log('👋 Stuck Detector extension is now deactivated');
}