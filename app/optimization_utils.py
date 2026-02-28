# app/optimization_utils.py
"""
Performance Optimization Utilities for Streamlit Music Generator

This module provides utility functions and decorators for optimizing
Streamlit app performance, specifically for the MelodAI music generator.
"""


import streamlit as st
import functools
import time
import os
from typing import Callable, Any, Dict, Optional
from pathlib import Path

# Optional dependencies - handle gracefully if not available
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ====================
# Performance Monitoring
# ====================

class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, operation_name: str):
        """Start timing an operation."""
        self.start_times[operation_name] = time.time()
    
    def end_timer(self, operation_name: str) -> float:
        """End timing an operation and record the duration."""
        if operation_name in self.start_times:
            duration = time.time() - self.start_times[operation_name]
            self.metrics[operation_name] = duration
            return duration
        return 0.0
    

    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics."""
        if not HAS_PSUTIL:
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0}
        
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            return {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'percent': process.memory_percent()
            }
        except Exception:
            return {'rss_mb': 0, 'vms_mb': 0, 'percent': 0}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics."""
        return {
            'timing': self.metrics.copy(),
            'memory': self.get_memory_usage()
        }

# Global performance monitor
perf_monitor = PerformanceMonitor()

# ====================
# Streamlit Optimization Decorators
# ====================

def streamlit_cache_data_with_metrics(ttl: int = 300, show_spinner: bool = True):
    """
    Enhanced cache_data decorator with performance monitoring.
    
    Args:
        ttl: Time to live in seconds
        show_spinner: Whether to show loading spinner
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = f"{func.__name__}_{id(args)}_{id(kwargs)}"
            perf_monitor.start_timer(operation_name)
            
            try:
                # Use st.cache_data with enhanced monitoring
                result = st.cache_data(
                    ttl=ttl,
                    show_spinner=show_spinner
                )(func)(*args, **kwargs)
                
                duration = perf_monitor.end_timer(operation_name)
                return result
            except Exception as e:
                perf_monitor.end_timer(operation_name)
                raise e
        
        return wrapper
    return decorator

def streamlit_cache_resource_with_metrics():
    """Enhanced cache_resource decorator with performance monitoring."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = f"resource_{func.__name__}"
            perf_monitor.start_timer(operation_name)
            
            try:
                result = st.cache_resource(func)(*args, **kwargs)
                perf_monitor.end_timer(operation_name)
                return result
            except Exception as e:
                perf_monitor.end_timer(operation_name)
                raise e
        
        return wrapper
    return decorator

# ====================
# Lazy Loading Utilities
# ====================

class LazyLoader:
    """Lazy loading utility for heavy components."""
    
    def __init__(self, loader_func: Callable, cache_key: Optional[str] = None):
        self.loader_func = loader_func
        self.cache_key = cache_key or loader_func.__name__
        self._cached_result = None
        self._loaded = False
    
    def load(self, *args, **kwargs) -> Any:
        """Load the component (only once)."""
        if not self._loaded:
            perf_monitor.start_timer(f"lazy_load_{self.cache_key}")
            try:
                self._cached_result = self.loader_func(*args, **kwargs)
                self._loaded = True
                perf_monitor.end_timer(f"lazy_load_{self.cache_key}")
            except Exception as e:
                perf_monitor.end_timer(f"lazy_load_{self.cache_key}")
                raise e
        return self._cached_result
    
    def is_loaded(self) -> bool:
        """Check if the component has been loaded."""
        return self._loaded
    
    def reset(self):
        """Reset the loader to force reloading."""
        self._cached_result = None
        self._loaded = False

# ====================
# Session State Optimization
# ====================

class OptimizedSessionState:
    """Optimized session state management."""
    
    def __init__(self):
        self._default_values = {}
        self._initialized_keys = set()
    
    def initialize_defaults(self, defaults: Dict[str, Any]):
        """Initialize session state with defaults efficiently."""
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
                self._initialized_keys.add(key)
            self._default_values[key] = default_value
    
    def safe_get(self, key: str, default=None):
        """Safely get a value from session state."""
        return st.session_state.get(key, default)
    
    def safe_set(self, key: str, value: Any):
        """Safely set a value in session state."""
        st.session_state[key] = value
    
    def get_initialized_keys(self) -> set:
        """Get keys that were initialized by this manager."""
        return self._initialized_keys.copy()

# Global optimized session state manager
session_manager = OptimizedSessionState()

# ====================
# Caching Strategies
# ====================

class CacheManager:
    """Advanced caching strategies for different data types."""
    
    @staticmethod
    @streamlit_cache_data_with_metrics(ttl=1800)  # 30 minutes
    def cache_model_info():
        """Cache model information."""
        return {
            "facebook/musicgen-small": {"params": "300M", "speed": "fast"},
            "facebook/musicgen-medium": {"params": "1.5B", "speed": "medium"},
            "facebook/musicgen-large": {"params": "3.3B", "speed": "slow"}
        }
    
    @staticmethod
    @streamlit_cache_data_with_metrics(ttl=300)  # 5 minutes
    def cache_device_detection():
        """Cache device detection results."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
            return "cpu"
        except Exception:
            return "cpu"
    
    @staticmethod
    @streamlit_cache_data_with_metrics(ttl=600)  # 10 minutes
    def cache_ui_presets():
        """Cache UI preset configurations."""
        return {
            "quick": {"duration": 15, "temperature": 0.8, "model": "small"},
            "standard": {"duration": 30, "temperature": 1.0, "model": "medium"},
            "pro": {"duration": 60, "temperature": 1.2, "model": "large"}
        }

# ====================
# Memory Management
# ====================

class MemoryManager:
    """Manage memory usage and cleanup."""
    
    @staticmethod
    def cleanup_large_objects():
        """Clean up large objects from session state."""
        keys_to_clean = [
            'large_audio_data',
            'cached_waveforms',
            'temp_analysis_results'
        ]
        
        cleaned_count = 0
        for key in keys_to_clean:
            if key in st.session_state:
                del st.session_state[key]
                cleaned_count += 1
        
        return cleaned_count
    
    @staticmethod
    def optimize_session_state():
        """Optimize session state by removing unnecessary data."""
        # Limit history to prevent memory bloat
        if 'history' in st.session_state and len(st.session_state.history) > 20:
            st.session_state.history = st.session_state.history[:20]
        
        # Clean up temporary data
        temp_keys = [key for key in st.session_state.keys() 
                    if key.startswith('temp_') or key.startswith('cache_')]
        
        for key in temp_keys:
            if key not in ['temp_current_generation']:  # Keep current generation
                del st.session_state[key]
    

    @staticmethod
    def get_memory_stats() -> Dict[str, Any]:
        """Get detailed memory statistics."""
        try:
            import gc
            import sys
            
            stats = {
                'session_state_keys': len(st.session_state),
                'gc_collections': 0,
                'gc_collected': 0,
                'largest_objects': {}
            }
            
            # Get garbage collection stats if available
            try:
                gc_stats = gc.get_stats()
                stats['gc_collections'] = sum(stat['collections'] for stat in gc_stats)
                stats['gc_collected'] = sum(stat['collected'] for stat in gc_stats)
            except Exception:
                pass
            
            # Get system memory stats if psutil is available
            if HAS_PSUTIL:
                try:
                    system_memory = psutil.virtual_memory()
                    stats['system_memory_mb'] = system_memory.used / 1024 / 1024
                    stats['system_memory_percent'] = system_memory.percent
                except Exception:
                    pass
            
            # Get object counts by type (simplified without heavy processing)
            try:
                object_counts = {}
                # Only sample first 1000 objects to avoid performance issues
                for i, obj in enumerate(gc.get_objects()):
                    if i >= 1000:  # Limit to prevent performance issues
                        break
                    obj_type = type(obj).__name__
                    object_counts[obj_type] = object_counts.get(obj_type, 0) + 1
                
                stats['largest_objects'] = dict(sorted(object_counts.items(), 
                                                    key=lambda x: x[1], reverse=True)[:10])
            except Exception:
                pass
            
            return stats
        except Exception:
            return {'session_state_keys': len(st.session_state)}

# ====================
# Performance Dashboard
# ====================

def render_performance_dashboard():
    """Render a performance monitoring dashboard."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Performance Monitor")
    
    # Memory usage
    memory_stats = MemoryManager.get_memory_stats()
    if memory_stats:
        st.sidebar.metric(
            "Memory Usage", 
            f"{memory_stats['system_memory_mb']:.1f} MB",
            f"{memory_stats['system_memory_percent']:.1f}%"
        )
    
    # Operation timing
    metrics = perf_monitor.get_metrics()
    if metrics['timing']:
        st.sidebar.markdown("**Operation Times:**")
        for operation, duration in metrics['timing'].items():
            st.sidebar.caption(f"{operation}: {duration:.3f}s")
    
    # Cleanup button
    if st.sidebar.button("🧹 Cleanup Memory"):
        cleaned = MemoryManager.cleanup_large_objects()
        MemoryManager.optimize_session_state()
        st.sidebar.success(f"Cleaned {cleaned} objects")
        if hasattr(st, "experimental_rerun"):
            try:
                st.experimental_rerun()
            except Exception:
                pass

# ====================
# Utility Functions
# ====================

def debounce_rerun(delay: float = 1.0):
    """Debounce rerun calls to prevent excessive reruns."""
    if 'last_rerun' not in st.session_state:
        st.session_state.last_rerun = 0
    
    current_time = time.time()
    if current_time - st.session_state.last_rerun > delay:
        st.session_state.last_rerun = current_time
        return True
    return False

def minimize_reruns(func: Callable) -> Callable:
    """Decorator to minimize unnecessary reruns."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Only run if necessary conditions are met
        if not debounce_rerun():
            return None
        
        return func(*args, **kwargs)
    return wrapper

# ====================
# Configuration
# ====================

# Performance settings
PERFORMANCE_CONFIG = {
    'cache_ttl_seconds': 300,
    'max_history_items': 20,
    'memory_cleanup_interval': 600,  # 10 minutes
    'enable_monitoring': True,
    'debounce_delay': 0.5
}

def get_performance_config() -> Dict[str, Any]:
    """Get performance configuration."""
    return PERFORMANCE_CONFIG.copy()

# ====================
# Export utilities for main app
# ====================

__all__ = [
    'PerformanceMonitor',
    'LazyLoader', 
    'OptimizedSessionState',
    'CacheManager',
    'MemoryManager',
    'render_performance_dashboard',
    'streamlit_cache_data_with_metrics',
    'streamlit_cache_resource_with_metrics',
    'minimize_reruns',
    'debounce_rerun',
    'perf_monitor',
    'session_manager',
    'PERFORMANCE_CONFIG',
    'get_performance_config'
]
