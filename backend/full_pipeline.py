# backend/full_pipeline.py


import os

# Import with fallback for robustness
try:
    from .input_processor import InputProcessor
except ImportError:
    try:
        from backend.input_processor import InputProcessor
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.input_processor import InputProcessor

try:
    from .prompt_enhancer import PromptEnhancer
except ImportError:
    try:
        from backend.prompt_enhancer import PromptEnhancer
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.prompt_enhancer import PromptEnhancer

try:
    from .generate import generate_from_enhanced
except ImportError:
    try:
        from backend.generate import generate_from_enhanced
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.generate import generate_from_enhanced

try:
    from .quality_scorer import QualityScorer
except ImportError:
    try:
        from backend.quality_scorer import QualityScorer
    except ImportError:
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from backend.quality_scorer import QualityScorer



def run_music_pipeline(user_text, output_name="pipeline_output.wav", use_quality_scorer=True, 
                       enable_post_processing=True, post_processing_config=None):

    # STEP 1: Extract params using LLM
    ip = InputProcessor(api_key=os.getenv("OPENAI_API_KEY"))
    params = ip.process_input(user_text)
    print("\nExtracted Parameters:")
    print(params)

    # STEP 2: Enhance prompt
    enhancer = PromptEnhancer()
    variations = enhancer.generate_variations(params, n=3)
    final_prompt = variations[0]

    print("\nFinal Enhanced Prompt:")
    print(final_prompt)

    # STEP 3: Generate music with quality scoring
    if use_quality_scorer:
        try:
            scorer = QualityScorer()
            print("\n🎵 Quality Scorer enabled - will auto-retry if quality < 65/100")



            def generate_with_quality():
                return generate_from_enhanced(
                    prompt=final_prompt,
                    duration=params.get("duration", 8),
                    model_name="facebook/musicgen-small",
                    enable_post_processing=enable_post_processing,
                    post_processing_config=post_processing_config
                )


            # Use quality scorer's evaluate_and_maybe_retry
            report, generated_paths = scorer.evaluate_and_maybe_retry(
                generate_callable=lambda p, d, m: generate_from_enhanced(
                    prompt=final_prompt,
                    duration=d,
                    model_name=m,
                    enable_post_processing=enable_post_processing,
                    post_processing_config=post_processing_config
                ),
                base_prompt=final_prompt,
                duration=params.get("duration", 8),
                model_name="facebook/musicgen-small",
                expected_params={"duration": params.get("duration", 8)}
            )

            if generated_paths:
                final_output = generated_paths[-1]  # Use the best quality version
                print(f"   Quality Pass: {'✅' if report.get('pass', False) else '❌'}")
                print(f"   Retries used: {len(generated_paths) - 1}")
            else:


                print("❌ Quality scorer failed, using fallback generation")
                final_output = generate_from_enhanced(
                    prompt=final_prompt,
                    duration=params.get("duration", 8),
                    model_name="facebook/musicgen-small",
                    enable_post_processing=enable_post_processing,
                    post_processing_config=post_processing_config
                )


        except ImportError:
            print("⚠️ Quality scorer not available, using standard generation")
            final_output = generate_from_enhanced(
                prompt=final_prompt,
                duration=params.get("duration", 8),
                model_name="facebook/musicgen-small",
                enable_post_processing=enable_post_processing,
                post_processing_config=post_processing_config
            )
        except Exception as e:
            print(f"⚠️ Quality scorer error: {e}, using standard generation")
            final_output = generate_from_enhanced(
                prompt=final_prompt,
                duration=params.get("duration", 8),
                model_name="facebook/musicgen-small",
                enable_post_processing=enable_post_processing,
                post_processing_config=post_processing_config
            )
    else:


        # Standard generation without quality scoring
        print("\n🎵 Standard generation (quality scorer disabled)")
        final_output = generate_from_enhanced(
            prompt=final_prompt,
            duration=params.get("duration", 8),
            model_name="facebook/musicgen-small",
            enable_post_processing=enable_post_processing,
            post_processing_config=post_processing_config
        )


    # Display comprehensive cache statistics after pipeline completion
    try:
        from .cache_manager import get_cache_manager
        cache_manager = get_cache_manager()
        

        print("\n" + "=" * 60)
        print("🎵 MUSIC GENERATION PIPELINE COMPLETED")
        print("=" * 60)
        print(f"✅ Generated file: {final_output}")
        print(f"📁 Output location: examples/outputs/")
        
        # Show post-processing information
        if enable_post_processing:
            print(f"\n🎚️  AUDIO POST-PROCESSING: ENABLED")
            if post_processing_config:
                print(f"   Effects configured: {list(post_processing_config.keys())}")
            else:
                print(f"   Using default effects configuration")
        else:
            print(f"\n🎚️  AUDIO POST-PROCESSING: DISABLED")
        
        # Show cache health report
        health_report = cache_manager.get_cache_health_report()
        print(f"\n🏥 CACHE HEALTH STATUS: {health_report['health_status']} ({health_report['overall_health_score']:.1f}/100)")
        
        if health_report['health_issues']:
            print("⚠️  Health Issues:")
            for issue in health_report['health_issues']:
                print(f"   • {issue}")
        
        # Show cache statistics
        cache_stats = cache_manager.get_formatted_stats()
        print(f"\n{cache_stats}")
        
        # Show recommendations if any
        if health_report['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for rec in health_report['recommendations']:
                print(f"   • {rec}")
                
        print("=" * 60)
        
    except Exception as e:
        print(f"\n⚠️  Cache statistics display failed: {e}")
        print(f"✅ Music generation completed: {final_output}")

    return final_output
