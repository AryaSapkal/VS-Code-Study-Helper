import numpy as np
import pandas as pd
from typing import Dict
import random

class SyntheticDataGenerator:
    """Generate realistic stuck/not-stuck scenarios"""
    
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        random.seed(seed)
    
    def generate_dataset(self, n_samples: int = 10000) -> pd.DataFrame:
        """Generate complete training dataset"""
        
        # 60% stuck, 40% productive (realistic class imbalance)
        n_stuck = int(n_samples * 0.6)
        n_productive = n_samples - n_stuck
        
        print(f"Generating {n_stuck} stuck scenarios...")
        stuck_samples = [self._generate_stuck_scenario() for _ in range(n_stuck)]
        
        print(f"Generating {n_productive} productive scenarios...")
        productive_samples = [self._generate_productive_scenario() for _ in range(n_productive)]
        
        all_samples = stuck_samples + productive_samples
        random.shuffle(all_samples)
        
        df = pd.DataFrame(all_samples)
        return df
    
    def _generate_stuck_scenario(self) -> Dict:
        """Generate features for a 'stuck' scenario"""
        
        # Different stuck patterns
        pattern = random.choice([
            'syntax_error_loop',      # Repeated syntax errors
            'logic_bug_confusion',    # Can't figure out algorithm
            'api_misunderstanding',   # Wrong API usage
            'concept_gap',            # Doesn't understand concept
            'typo_hunt',              # Looking for small bug
        ])
        
        if pattern == 'syntax_error_loop':
            # Student keeps getting same syntax error
            return {
                'idle_time_total': np.random.normal(45, 10),
                'idle_time_max': np.random.normal(30, 5),
                'edit_events': np.random.randint(20, 50),
                'edit_velocity': np.random.normal(2, 0.5),  # slow typing
                'backspace_ratio': np.random.normal(0.7, 0.1),  # lots of deleting
                'cursor_moves': np.random.randint(30, 60),
                'cursor_distance': np.random.normal(100, 20),
                'cursor_entropy': np.random.normal(2.5, 0.3),
                'error_events': np.random.randint(8, 15),
                'unique_errors': np.random.randint(1, 3),  # same error!
                'error_repeat_count': np.random.randint(5, 10),
                'error_persistence': np.random.normal(0.8, 0.1),
                'time_since_last_run': np.random.normal(180, 30),
                'run_attempt_count': np.random.randint(0, 2),
                'context_switches': np.random.randint(3, 8),
                'focus_time_avg': np.random.normal(15, 3),
                'comment_keywords': np.random.randint(1, 3),
                'comment_length_avg': np.random.normal(50, 10),
                'is_stuck': 1,
                'pattern': pattern
            }
        
        elif pattern == 'logic_bug_confusion':
            # Code runs but gives wrong output
            return {
                'idle_time_total': np.random.normal(60, 15),
                'idle_time_max': np.random.normal(40, 10),
                'edit_events': np.random.randint(15, 35),
                'edit_velocity': np.random.normal(1.5, 0.3),
                'backspace_ratio': np.random.normal(0.5, 0.1),
                'cursor_moves': np.random.randint(40, 80),
                'cursor_distance': np.random.normal(150, 30),
                'cursor_entropy': np.random.normal(2.8, 0.2),  # very random
                'error_events': np.random.randint(0, 2),  # no syntax errors
                'unique_errors': np.random.randint(0, 1),
                'error_repeat_count': 0,
                'error_persistence': 0,
                'time_since_last_run': np.random.normal(90, 20),
                'run_attempt_count': np.random.randint(3, 8),  # keeps testing
                'context_switches': np.random.randint(8, 15),
                'focus_time_avg': np.random.normal(8, 2),
                'comment_keywords': np.random.randint(1, 4),
                'comment_length_avg': np.random.normal(60, 15),
                'is_stuck': 1,
                'pattern': pattern
            }
        
        elif pattern == 'api_misunderstanding':
            # Doesn't know how to use a library
            return {
                'idle_time_total': np.random.normal(50, 12),
                'idle_time_max': np.random.normal(35, 8),
                'edit_events': np.random.randint(25, 45),
                'edit_velocity': np.random.normal(3, 0.5),
                'backspace_ratio': np.random.normal(0.6, 0.1),
                'cursor_moves': np.random.randint(20, 40),
                'cursor_distance': np.random.normal(80, 15),
                'cursor_entropy': np.random.normal(2.0, 0.3),
                'error_events': np.random.randint(6, 12),
                'unique_errors': np.random.randint(2, 4),
                'error_repeat_count': np.random.randint(3, 6),
                'error_persistence': np.random.normal(0.6, 0.1),
                'time_since_last_run': np.random.normal(120, 25),
                'run_attempt_count': np.random.randint(2, 5),
                'context_switches': np.random.randint(10, 20),  # switching to docs
                'focus_time_avg': np.random.normal(10, 3),
                'comment_keywords': np.random.randint(0, 2),
                'comment_length_avg': np.random.normal(40, 10),
                'is_stuck': 1,
                'pattern': pattern
            }
        
        elif pattern == 'concept_gap':
            # Doesn't understand fundamental concept
            return {
                'idle_time_total': np.random.normal(70, 15),
                'idle_time_max': np.random.normal(50, 10),
                'edit_events': np.random.randint(5, 15),  # barely typing
                'edit_velocity': np.random.normal(0.5, 0.2),
                'backspace_ratio': np.random.normal(0.8, 0.1),
                'cursor_moves': np.random.randint(10, 25),
                'cursor_distance': np.random.normal(40, 10),
                'cursor_entropy': np.random.normal(1.5, 0.3),
                'error_events': np.random.randint(0, 3),
                'unique_errors': np.random.randint(0, 2),
                'error_repeat_count': 0,
                'error_persistence': 0,
                'time_since_last_run': np.random.normal(240, 40),  # not even trying
                'run_attempt_count': 0,
                'context_switches': np.random.randint(5, 12),
                'focus_time_avg': np.random.normal(20, 5),
                'comment_keywords': np.random.randint(2, 5),  # lots of TODOs
                'comment_length_avg': np.random.normal(80, 20),
                'is_stuck': 1,
                'pattern': pattern
            }
        
        else:  # typo_hunt
            # One small bug causing big problems
            return {
                'idle_time_total': np.random.normal(35, 8),
                'idle_time_max': np.random.normal(20, 5),
                'edit_events': np.random.randint(30, 60),
                'edit_velocity': np.random.normal(4, 0.8),
                'backspace_ratio': np.random.normal(0.4, 0.1),
                'cursor_moves': np.random.randint(50, 100),  # hunting through code
                'cursor_distance': np.random.normal(200, 40),
                'cursor_entropy': np.random.normal(2.7, 0.3),
                'error_events': np.random.randint(10, 20),
                'unique_errors': 1,  # same error everywhere
                'error_repeat_count': 1,
                'error_persistence': np.random.normal(0.95, 0.05),
                'time_since_last_run': np.random.normal(90, 15),
                'run_attempt_count': np.random.randint(4, 10),
                'context_switches': np.random.randint(2, 6),
                'focus_time_avg': np.random.normal(12, 3),
                'comment_keywords': np.random.randint(0, 1),
                'comment_length_avg': np.random.normal(20, 5),
                'is_stuck': 1,
                'pattern': pattern
            }
    
    def _generate_productive_scenario(self) -> Dict:
        """Generate features for productive coding (not stuck)"""
        
        pattern = random.choice([
            'steady_progress',
            'debugging_successfully',
            'implementing_feature',
            'refactoring'
        ])
        
        if pattern == 'steady_progress':
            # Everything going smoothly
            return {
                'idle_time_total': np.random.normal(10, 3),
                'idle_time_max': np.random.normal(8, 2),
                'edit_events': np.random.randint(30, 60),
                'edit_velocity': np.random.normal(8, 2),  # typing fast
                'backspace_ratio': np.random.normal(0.2, 0.05),  # minimal deletion
                'cursor_moves': np.random.randint(15, 30),
                'cursor_distance': np.random.normal(50, 10),
                'cursor_entropy': np.random.normal(1.2, 0.2),  # focused movement
                'error_events': np.random.randint(0, 3),
                'unique_errors': np.random.randint(0, 2),
                'error_repeat_count': 0,
                'error_persistence': 0,
                'time_since_last_run': np.random.normal(45, 10),
                'run_attempt_count': np.random.randint(3, 7),
                'context_switches': np.random.randint(0, 3),
                'focus_time_avg': np.random.normal(40, 10),
                'comment_keywords': 0,
                'comment_length_avg': np.random.normal(15, 5),
                'is_stuck': 0,
                'pattern': pattern
            }
        
        elif pattern == 'debugging_successfully':
            # Finding and fixing bugs effectively
            return {
                'idle_time_total': np.random.normal(15, 5),
                'idle_time_max': np.random.normal(10, 3),
                'edit_events': np.random.randint(20, 40),
                'edit_velocity': np.random.normal(5, 1),
                'backspace_ratio': np.random.normal(0.3, 0.05),
                'cursor_moves': np.random.randint(25, 45),
                'cursor_distance': np.random.normal(80, 15),
                'cursor_entropy': np.random.normal(1.5, 0.2),
                'error_events': np.random.randint(3, 8),
                'unique_errors': np.random.randint(2, 4),
                'error_repeat_count': np.random.randint(0, 2),
                'error_persistence': np.random.normal(0.3, 0.1),  # errors go away
                'time_since_last_run': np.random.normal(30, 8),
                'run_attempt_count': np.random.randint(5, 10),  # testing frequently
                'context_switches': np.random.randint(2, 6),
                'focus_time_avg': np.random.normal(25, 8),
                'comment_keywords': 0,
                'comment_length_avg': np.random.normal(20, 5),
                'is_stuck': 0,
                'pattern': pattern
            }
        
        elif pattern == 'implementing_feature':
            # Adding new functionality
            return {
                'idle_time_total': np.random.normal(12, 4),
                'idle_time_max': np.random.normal(10, 3),
                'edit_events': np.random.randint(40, 80),
                'edit_velocity': np.random.normal(10, 2),  # typing a lot
                'backspace_ratio': np.random.normal(0.15, 0.05),
                'cursor_moves': np.random.randint(20, 40),
                'cursor_distance': np.random.normal(60, 12),
                'cursor_entropy': np.random.normal(1.3, 0.2),
                'error_events': np.random.randint(1, 5),
                'unique_errors': np.random.randint(1, 3),
                'error_repeat_count': 0,
                'error_persistence': np.random.normal(0.2, 0.1),
                'time_since_last_run': np.random.normal(60, 15),
                'run_attempt_count': np.random.randint(2, 5),
                'context_switches': np.random.randint(4, 10),  # multiple files
                'focus_time_avg': np.random.normal(20, 5),
                'comment_keywords': 0,
                'comment_length_avg': np.random.normal(25, 8),
                'is_stuck': 0,
                'pattern': pattern
            }
        
        else:  # refactoring
            # Cleaning up code
            return {
                'idle_time_total': np.random.normal(8, 3),
                'idle_time_max': np.random.normal(6, 2),
                'edit_events': np.random.randint(50, 100),
                'edit_velocity': np.random.normal(12, 3),
                'backspace_ratio': np.random.normal(0.4, 0.1),  # reorganizing
                'cursor_moves': np.random.randint(30, 60),
                'cursor_distance': np.random.normal(100, 20),
                'cursor_entropy': np.random.normal(1.8, 0.3),
                'error_events': np.random.randint(0, 2),
                'unique_errors': np.random.randint(0, 1),
                'error_repeat_count': 0,
                'error_persistence': 0,
                'time_since_last_run': np.random.normal(50, 12),
                'run_attempt_count': np.random.randint(4, 8),
                'context_switches': np.random.randint(1, 4),
                'focus_time_avg': np.random.normal(35, 10),
                'comment_keywords': 0,
                'comment_length_avg': np.random.normal(18, 5),
                'is_stuck': 0,
                'pattern': pattern
            }