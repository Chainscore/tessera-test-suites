"""
Performance testing and profiling utilities for Tessera

Structure:
- tools/: Core profiling utilities
- tests/: PVM benchmark tests  
- examples/: Usage demonstrations
"""


from .tools import (
    Profiler,
    profile,
    profile_function,
    quick_profile,
    time_and_profile,
    compare_profiles,
    view_profile,
    list_profiles,
    BenchmarkSuite,
    BenchmarkResult,
    time_function,
    profile_and_time,
    compare_execution_times,
    load_test_vector,
    create_performance_baseline,
    check_performance_regression
)

__all__ = [
    'Profiler',
    'profile', 
    'profile_function',
    'quick_profile',
    'time_and_profile',
    'compare_profiles',
    'view_profile',
    'list_profiles',
    'BenchmarkSuite',
    'BenchmarkResult',
    'time_function',
    'profile_and_time',
    'compare_execution_times',
    'load_test_vector',
    'create_performance_baseline',
    'check_performance_regression'
] 