"""
AI Tools for Enhanced Stuck Detection
Using DedalusRunner's tool calling capabilities to provide better hints
"""

def analyze_code_context(code_snippet: str, language: str, context_word: str) -> str:
    """
    Analyze code snippet to provide contextual insights
    """
    analysis = {
        "language": language,
        "context_word": context_word,
        "insights": []
    }
    
    # Basic code analysis
    lines = code_snippet.split('\n')
    analysis["line_count"] = len(lines)
    
    # Language-specific analysis
    if language == "python":
        if "import" in code_snippet:
            analysis["insights"].append("Code contains imports - check if all modules are available")
        if context_word in ["print", "input", "len", "str", "int", "float"]:
            analysis["insights"].append(f"'{context_word}' is a built-in Python function")
        if context_word.endswith("()"):
            analysis["insights"].append(f"'{context_word}' looks like a function call - check the arguments")
            
    elif language == "javascript":
        if "console.log" in code_snippet:
            analysis["insights"].append("Code uses console.log for debugging")
        if context_word in ["console", "document", "window"]:
            analysis["insights"].append(f"'{context_word}' is a JavaScript global object")
        if "function" in code_snippet or "=>" in code_snippet:
            analysis["insights"].append("Code contains function definitions")
    
    # Look for common patterns
    if "=" in code_snippet:
        analysis["insights"].append("Code contains variable assignments")
    if "if" in code_snippet or "else" in code_snippet:
        analysis["insights"].append("Code contains conditional logic")
    if "for" in code_snippet or "while" in code_snippet:
        analysis["insights"].append("Code contains loops")
    
    return f"Code Analysis: {language} code with {len(lines)} lines. Focus: '{context_word}'. " + "; ".join(analysis["insights"])


def suggest_documentation(context_word: str, language: str) -> str:
    """
    Suggest relevant documentation for the context word
    """
    docs = {
        "python": {
            "print": "https://docs.python.org/3/library/functions.html#print",
            "input": "https://docs.python.org/3/library/functions.html#input", 
            "len": "https://docs.python.org/3/library/functions.html#len",
            "str": "https://docs.python.org/3/library/stdtypes.html#str",
            "list": "https://docs.python.org/3/library/stdtypes.html#list",
            "dict": "https://docs.python.org/3/library/stdtypes.html#dict",
            "for": "https://docs.python.org/3/tutorial/controlflow.html#for-statements",
            "if": "https://docs.python.org/3/tutorial/controlflow.html#if-statements",
            "def": "https://docs.python.org/3/tutorial/controlflow.html#defining-functions",
        },
        "javascript": {
            "console": "https://developer.mozilla.org/en-US/docs/Web/API/Console",
            "document": "https://developer.mozilla.org/en-US/docs/Web/API/Document",
            "function": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Functions",
            "let": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/let",
            "const": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/const",
            "var": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/var",
            "array": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array",
            "object": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object",
        }
    }
    
    language_docs = docs.get(language.lower(), {})
    doc_url = language_docs.get(context_word.lower())
    
    if doc_url:
        return f"Check the official documentation for '{context_word}': {doc_url}"
    else:
        base_urls = {
            "python": "https://docs.python.org/3/search.html?q=",
            "javascript": "https://developer.mozilla.org/en-US/search?q=",
            "java": "https://docs.oracle.com/javase/8/docs/api/",
            "cpp": "https://cppreference.com/",
            "c": "https://cppreference.com/",
        }
        base_url = base_urls.get(language.lower())
        if base_url and "search" in base_url:
            return f"Search the official docs for '{context_word}': {base_url}{context_word}"
        elif base_url:
            return f"Check the official documentation: {base_url}"
        else:
            return f"Try searching for '{context_word}' in the {language} documentation"


def analyze_stuck_pattern(heuristic: str, context_word: str) -> str:
    """
    Analyze the stuck pattern to provide specific guidance
    """
    patterns = {
        "repetitive_editing": f"You're editing '{context_word}' repeatedly. This suggests you might be unsure about the syntax or expected behavior. Try testing smaller parts of your code first.",
        
        "cursor_thrashing": f"Jumping around '{context_word}' indicates you might be looking for something specific. Focus on understanding what this element should do before trying to fix it.",
        
        "idle_too_long": f"Staring at '{context_word}' for a while? Sometimes stepping away and thinking about the problem differently helps. What is this supposed to accomplish?",
        
        "many_errors": f"Multiple errors around '{context_word}' suggest there might be a fundamental issue. Read the error messages carefully - they're trying to guide you to the problem.",
        
        "error_persistence": f"The same error keeps happening with '{context_word}'. Try a different approach or break the problem into smaller pieces.",
        
        "high_complexity": f"The code around '{context_word}' might be getting complex. Consider breaking it into simpler functions or steps.",
    }
    
    return patterns.get(heuristic, f"Working with '{context_word}' - try thinking about what you want to achieve step by step.")


# Tool definitions for DedalusRunner
def create_programming_tools():
    """
    Create tools that can be used with DedalusRunner for enhanced hint generation
    """
    return [analyze_code_context, suggest_documentation, analyze_stuck_pattern]