#!/usr/bin/env python3
"""
Test script to verify the optimized Streamlit app works correctly
"""

import sys
import os

# Add current directory to path
ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

def test_optimized_app():
    """Test the optimized app components."""
    print("🧪 Testing Optimized Streamlit App Components")
    print("=" * 50)
    
    try:
        # Test 1: Import optimization utilities
        print("1. Testing optimization utilities...")
        from app.optimization_utils import (
            PerformanceMonitor, 
            LazyLoader, 
            CacheManager, 
            MemoryManager,
            session_manager
        )
        print("   ✅ Optimization utilities imported successfully")
        
        # Test 2: Test performance monitor
        print("2. Testing PerformanceMonitor...")
        monitor = PerformanceMonitor()
        memory_stats = monitor.get_memory_usage()
        print(f"   ✅ Memory monitoring works: {memory_stats}")
        
        # Test 3: Test lazy loader
        print("3. Testing LazyLoader...")
        def test_loader():
            return "loaded_data"
        
        loader = LazyLoader(test_loader)
        result = loader.load()
        print(f"   ✅ Lazy loading works: {result}")
        
        # Test 4: Test session state manager
        print("4. Testing session state manager...")
        test_defaults = {"test_key": "test_value", "test_number": 42}
        session_manager.initialize_defaults(test_defaults)
        initialized_keys = session_manager.get_initialized_keys()
        print(f"   ✅ Session state manager works: {len(initialized_keys)} keys initialized")
        
        # Test 5: Test cache manager
        print("5. Testing CacheManager...")
        model_info = CacheManager.cache_model_info()
        device = CacheManager.cache_device_detection()
        print(f"   ✅ Cache manager works: model info cached, device = {device}")
        
        # Test 6: Test performance benchmark
        print("6. Testing PerformanceBenchmark...")
        from app.performance_comparison import PerformanceBenchmark
        benchmark = PerformanceBenchmark()
        
        memory_result = benchmark.measure_memory_usage()
        ui_result = benchmark.simulate_ui_operations("model_selection")
        cache_result = benchmark.measure_cache_performance()
        
        print(f"   ✅ Benchmark works:")
        print(f"      - Memory: {memory_result}")
        print(f"      - UI operations: {ui_result['improvement']:.1f}% improvement")
        print(f"      - Cache performance: {cache_result['improvement']:.1f}% improvement")
        
        # Test 7: Test optimized app import
        print("7. Testing optimized app import...")
        from app.streamlit_app_optimized import main
        print("   ✅ Optimized app imports successfully")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("The optimized Streamlit app is ready to run with:")
        print("   streamlit run app/streamlit_app_optimized.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_optimized_app()
    sys.exit(0 if success else 1)

