#!/usr/bin/env python3
"""
Test Quality Scorer with 20 Sample Music Prompts

This script generates music for 20 different prompts and evaluates their quality scores.
Run from terminal: python backend/test_quality_samples.py
"""

import os
import sys
import time
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.quality_scorer import QualityScorer
from backend.generate import generate_from_enhanced

# 20 Sample Music Prompts for Testing
SAMPLE_PROMPTS = [
    "happy upbeat pop music with piano and drums",
    "calm ambient music with soft pads and strings",
    "energetic rock music with electric guitar",
    "sad emotional ballad with acoustic guitar",
    "fast techno electronic dance music",
    "classical piano sonata",
    "jazz saxophone improvisation",
    "country folk music with banjo",
    "heavy metal with distorted guitars",
    "reggae music with offbeat rhythm",
    "blues guitar solo",
    "hip hop beats with bass",
    "orchestral symphony",
    "lo-fi hip hop beats",
    "disco funk music",
    "new age meditation music",
    "punk rock with fast drums",
    "R&B soul music",
    "folk acoustic singer-songwriter",
    "electronic synthwave"
]

def main():
    print("🎵 MelodAI Quality Scorer - 20 Sample Test")
    print("=" * 60)
    print(f"Testing {len(SAMPLE_PROMPTS)} music prompts...")
    print()

    # Initialize quality scorer
    scorer = QualityScorer()
    print(f"Quality threshold: {scorer.config.min_overall_score}/100")
    print()

    # Create output directory
    output_dir = Path("examples/outputs/quality_test")
    output_dir.mkdir(exist_ok=True)

    results = []
    summary_stats = {
        "total_samples": len(SAMPLE_PROMPTS),
        "passed": 0,
        "failed": 0,
        "avg_score": 0.0,
        "min_score": 100.0,
        "max_score": 0.0
    }

    for i, prompt in enumerate(SAMPLE_PROMPTS, 1):
        print(f"[{i:2d}/{len(SAMPLE_PROMPTS)}] Testing: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")

        try:
            # Generate music with quality scoring
            start_time = time.time()
            output_file = generate_from_enhanced(
                prompt=prompt,
                duration=8,
                model_name="facebook/musicgen-small"
            )
            gen_time = time.time() - start_time

            # Score the generated music
            report = scorer.score_audio(output_file, expected_params={'duration': 8})

            # Update statistics
            score = report['overall_score']
            summary_stats["avg_score"] += score
            summary_stats["min_score"] = min(summary_stats["min_score"], score)
            summary_stats["max_score"] = max(summary_stats["max_score"], score)

            if report.get('pass', False):
                summary_stats["passed"] += 1
                status = "✅ PASS"
            else:
                summary_stats["failed"] += 1
                status = "❌ FAIL"

            # Store result
            result = {
                "sample_id": i,
                "prompt": prompt,
                "output_file": output_file,
                "generation_time": round(gen_time, 2),
                "quality_report": report
            }
            results.append(result)

            # Print result
            print(f"         Score: {score:.1f}/100 {status} ({gen_time:.1f}s)")
            print(f"         File: {os.path.basename(output_file)}")
            print()

        except Exception as e:
            print(f"         ❌ Error: {e}")
            print()
            result = {
                "sample_id": i,
                "prompt": prompt,
                "error": str(e)
            }
            results.append(result)

    # Calculate final statistics
    summary_stats["avg_score"] /= len(SAMPLE_PROMPTS)

    # Print summary
    print("🎵 Test Summary")
    print("=" * 40)
    print(f"Total Samples: {summary_stats['total_samples']}")
    print(f"Passed: {summary_stats['passed']} ✅")
    print(f"Failed: {summary_stats['failed']} ❌")
    print(".1f")
    print(".1f")
    print(".1f")
    print()

    # Save detailed results
    output_file = output_dir / f"quality_test_results_{int(time.time())}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_info": {
                "timestamp": time.time(),
                "quality_threshold": scorer.config.min_overall_score,
                "total_samples": len(SAMPLE_PROMPTS)
            },
            "summary": summary_stats,
            "results": results
        }, f, indent=2, ensure_ascii=False)

    print(f"📊 Detailed results saved to: {output_file}")
    print()

    # Print top 5 best and worst scores
    valid_results = [r for r in results if 'quality_report' in r]
    if valid_results:
        # Sort by score
        sorted_results = sorted(valid_results, key=lambda x: x['quality_report']['overall_score'], reverse=True)

        print("🏆 Top 5 Best Scores:")
        for i, result in enumerate(sorted_results[:5], 1):
            score = result['quality_report']['overall_score']
            prompt = result['prompt'][:40] + "..." if len(result['prompt']) > 40 else result['prompt']
            print(".1f")

        print()
        print("📉 Top 5 Worst Scores:")
        for i, result in enumerate(sorted_results[-5:], 1):
            score = result['quality_report']['overall_score']
            prompt = result['prompt'][:40] + "..." if len(result['prompt']) > 40 else result['prompt']
            print(".1f")

    print()
    print("🎉 Quality testing complete!")

if __name__ == "__main__":
    main()
