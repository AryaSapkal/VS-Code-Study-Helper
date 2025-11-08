from dataclasses import dataclass
from typing import List

@dataclass
class FeatureDefinition:
    """Single feature definition"""
    name: str
    description: str
    data_type: str  # 'continuous', 'count', 'binary'
    expected_range: tuple  # (min, max)

#feature definitions
FEATURES = [
    # idle time
    FeatureDefinition('idle_time_total', 'Total idle time in window (seconds)', 'continuous', (0, 120)),
    FeatureDefinition('idle_time_max', 'Longest single idle period (seconds)', 'continuous', (0, 90)),
    
    # editing
    FeatureDefinition('edit_events', 'Number of edit events', 'count', (0, 150)),
    FeatureDefinition('edit_velocity', 'Characters per second', 'continuous', (0, 20)),
    FeatureDefinition('backspace_ratio', 'Deletions / additions', 'continuous', (0, 1)),
    
    # cursor mvmt
    FeatureDefinition('cursor_moves', 'Number of cursor position changes', 'count', (0, 200)),
    FeatureDefinition('cursor_distance', 'Total lines traversed', 'continuous', (0, 300)),
    FeatureDefinition('cursor_entropy', 'Randomness of movement (0-3)', 'continuous', (0, 3)),
    
    # error features
    FeatureDefinition('error_events', 'Total error occurrences', 'count', (0, 30)),
    FeatureDefinition('unique_errors', 'Number of distinct errors', 'count', (0, 10)),
    FeatureDefinition('error_repeat_count', 'How many errors repeated', 'count', (0, 15)),
    FeatureDefinition('error_persistence', 'Same error persistence (0-1)', 'continuous', (0, 1)),
    
    # execution features
    FeatureDefinition('time_since_last_run', 'Seconds since last code execution', 'continuous', (0, 300)),
    FeatureDefinition('run_attempt_count', 'Number of run attempts', 'count', (0, 15)),
    
    # tab switching
    FeatureDefinition('context_switches', 'Number of file switches', 'count', (0, 30)),
    FeatureDefinition('focus_time_avg', 'Average time per file (seconds)', 'continuous', (0, 60)),
    
    # comment features
    FeatureDefinition('comment_keywords', 'Count of stuck keywords in comments', 'count', (0, 5)),
    FeatureDefinition('comment_length_avg', 'Average comment length', 'continuous', (0, 150)),
]

def get_feature_names() -> List[str]:
    """Return list of feature names for DataFrame columns"""
    return [f.name for f in FEATURES]

def get_feature_descriptions() -> dict:
    """Return feature name -> description mapping"""
    return {f.name: f.description for f in FEATURES}