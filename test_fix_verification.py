#!/usr/bin/env python3
"""
Test script to verify the get_cache_manager import fix.
This script tests all the key components that were causing the import errors.
"""

def test_imports():
    """Test all the imports that were failing."""
    print("Testing imports...")
    
    try:
        # Test cache manager import
        from backend.cache_manager import get_cache_manager
        print("✅ cache_manager.get_cache_manager import: SUCCESS")
        
        # Test that we can create a cache manager instance
        cm = get_cache_manager()
        print("✅ CacheManager instance creation: SUCCESS")
        
    except Exception as e:
        print(f"❌ cache_manager import failed: {e}")
        return False
    
    try:
        # Test generate module import (this was the main issue)
        from backend.generate import generate_music, generate_from_enhanced
        print("✅ generate module import: SUCCESS")
        
    except Exception as e:
        print(f"❌ generate module import failed: {e}")
        return False
    
    try:
        # Test quality scorer import
        from backend.quality_scorer import QualityScorer
        print("✅ quality_scorer import: SUCCESS")
        
    except Exception as e:
        print(f"❌ quality_scorer import failed: {e}")
        return False
    
    try:
        # Test full pipeline import
        from backend.full_pipeline import run_music_pipeline
        print("✅ full_pipeline import: SUCCESS")
        
    except Exception as e:
        print(f"❌ full_pipeline import failed: {e}")
        return False
    
    return True

def test_quality_scorer_functionality():
    """Test that quality scorer can access get_cache_manager without error."""
    print("\nTesting quality scorer functionality...")
    
    try:
        from backend.quality_scorer import QualityScorer
        scorer = QualityScorer()
        
        # Test that the scorer was created successfully
        print("✅ QualityScorer instantiation: SUCCESS")
        
        # Test accessing config (basic functionality check)
        config = scorer.config
        print(f"✅ QualityScorer config access: SUCCESS (min_score: {config.min_overall_score})")
        
        return True
        
    except Exception as e:
        print(f"❌ QualityScorer functionality test failed: {e}")
        return False

def main():
    """Main test function."""
    print("=" * 60)
    print("VERIFYING get_cache_manager IMPORT FIX")
    print("=" * 60)
    
    # Test imports
    imports_ok = test_imports()
    
    # Test functionality
    functionality_ok = test_quality_scorer_functionality()
    
    print("\n" + "=" * 60)
    if imports_ok and functionality_ok:
        print("🎉 ALL TESTS PASSED - The fix is working correctly!")
        print("\nThe 'get_cache_manager is not defined' error has been resolved.")
        print("Quality scorer should now work without import errors.")
    else:
        print("❌ SOME TESTS FAILED - There may still be issues.")
    print("=" * 60)

if __name__ == "__main__":
    main()
