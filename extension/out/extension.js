"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.deactivate = exports.activate = void 0;
const vscode = require("vscode");
const stuckDetector_1 = require("./stuckDetector");
function activate(context) {
    console.log('🚀 Stuck Detector extension is now active!');
    // Initialize the stuck detector
    const stuckDetector = new stuckDetector_1.StuckDetector();
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
exports.activate = activate;
function deactivate() {
    console.log('👋 Stuck Detector extension is now deactivated');
}
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map