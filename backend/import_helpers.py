"""
Centralized import helpers for robust module imports across different execution contexts.

This module provides functions that handle imports consistently whether they're called from:
- Direct Python execution
- Streamlit app execution  
- Module imports
- Package imports
"""

import sys
import os
from typing import Any, Optional


def setup_backend_path():
    """Ensure the backend directory is in the Python path."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    
    # Add both current directory and parent directory to path
    for path in [current_dir, parent_dir]:
        if path not in sys.path:
            sys.path.insert(0, path)


def safe_import(module_name: str, function_name: Optional[str] = None, fallback_name: Optional[str] = None):
    """
    Safely import a function with multiple fallback strategies.
    
    Args:
        module_name: Module to import (e.g., 'cache_manager')
        function_name: Specific function to import (optional)
        fallback_name: Alternative name if function_name fails (optional)
    
    Returns:
        The imported function or module
    """
    setup_backend_path()
    
    # Try relative import first
    try:
        if function_name:
            relative_module = f".{module_name}"
            if fallback_name:
                module = __import__(relative_module, fromlist=[function_name, fallback_name])
                return getattr(module, function_name) if hasattr(module, function_name) else getattr(module, fallback_name)
            else:
                module = __import__(relative_module, fromlist=[function_name])
                return getattr(module, function_name)
        else:
            relative_module = f".{module_name}"
            return __import__(relative_module, fromlist=[module_name])
    except (ImportError, AttributeError):
        pass
    
    # Try absolute import
    try:
        if function_name:
            full_module = f"backend.{module_name}"
            module = __import__(full_module, fromlist=[function_name])
            if hasattr(module, function_name):
                return getattr(module, function_name)
            elif fallback_name and hasattr(module, fallback_name):
                return getattr(module, fallback_name)
            else:
                raise ImportError(f"Function {function_name} not found in {module_name}")
        else:
            full_module = f"backend.{module_name}"
            return __import__(full_module, fromlist=[module_name])
    except (ImportError, AttributeError):
        pass
    
    # Try direct import with path manipulation
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        
        if function_name:
            module = __import__(module_name, fromlist=[function_name])
            if hasattr(module, function_name):
                return getattr(module, function_name)
            elif fallback_name and hasattr(module, fallback_name):
                return getattr(module, fallback_name)
            else:
                raise ImportError(f"Function {function_name} not found in {module_name}")
        else:
            return __import__(module_name, fromlist=[module_name])
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import {function_name or 'function'} from {module_name}: {e}")


def get_cache_manager():
    """Get cache manager with robust import handling."""
    return safe_import('cache_manager', 'get_cache_manager')


def get_quality_scorer():
    """Get quality scorer class with robust import handling."""
    return safe_import('quality_scorer', 'QualityScorer')


def get_generate_functions():
    """Get generate functions with robust import handling."""
    setup_backend_path()
    
    # Import the entire generate module
    try:
        # Try relative import first
        from .generate import generate_from_enhanced, generate_music, load_model
        return generate_from_enhanced, generate_music, load_model
    except ImportError:
        try:
            # Try absolute import
            from backend.generate import generate_from_enhanced, generate_music, load_model
            return generate_from_enhanced, generate_music, load_model
        except ImportError:
            # Last resort - add to path and import
            setup_backend_path()
            from generate import generate_from_enhanced, generate_music, load_model
            return generate_from_enhanced, generate_music, load_model


def get_input_processor():
    """Get input processor with robust import handling."""
    return safe_import('input_processor', 'InputProcessor')


def get_prompt_enhancer():
    """Get prompt enhancer with robust import handling."""
    return safe_import('prompt_enhancer', 'PromptEnhancer')
