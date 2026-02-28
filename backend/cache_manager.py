"""
Intelligent Caching System for MusicGen Backend

This module provides a CacheManager class that implements intelligent caching
to improve performance by avoiding redundant music generation for identical
prompts and parameters.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import threading
from collections import OrderedDict


class CacheManager:
    """
    Manages caching of generated music files with intelligent eviction and statistics.

    Features:
    - Cache identical (prompt + parameters) combinations
    - LRU eviction policy with size limits
    - Cache statistics tracking
    - Background cache warming
    - Thread-safe operations
    """


    def __init__(self, cache_dir: str = "cache", max_files: int = 50, max_size_mb: int = 500):
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory to store cached files
            max_files: Maximum number of files to cache
            max_size_mb: Maximum cache size in MB
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.max_files = max_files
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cache_ttl = 3600  # 1 hour TTL

        # Thread-safe data structures
        self._lock = threading.RLock()
        self._cache_index: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "total_requests": 0,
            "cache_size_bytes": 0,
            "files_cached": 0,
            "evictions": 0,
            "most_cached_prompts": {},
            "avg_generation_time": 0.0,
            "total_generation_time": 0.0,
            "cache_warming_hits": 0,
            "popular_moods_cached": []
        }

        # Load existing cache index
        self._load_cache_index()

        # Background warming queue
        self._warming_queue = []
        self._warming_thread = None
        
        # Popular moods for cache warming on startup
        self.popular_moods = [
            "happy upbeat music with piano and strings",
            "calm ambient electronic music",
            "energetic rock music with drums and guitar",
            "sad emotional piano ballad",
            "jazz smooth saxophone melody",
            "classical orchestral music",
            "lo-fi hip hop beats for studying",
            "folk acoustic guitar music"
        ]
        

        # Start cache warming on initialization
        self._startup_cache_warming()

    def _startup_cache_warming(self) -> None:
        """Warm up cache with popular moods on startup."""
        try:
            print("[CacheManager] Starting cache warming with popular moods...")
            
            # Start warming in background thread
            if self._warming_thread is None or not self._warming_thread.is_alive():
                self._warming_thread = threading.Thread(target=self._background_warming, daemon=True)
                self._warming_thread.start()
                
            # Add popular moods to warming queue
            with self._lock:
                for mood in self.popular_moods:
                    params = {"duration": 8, "model_name": "facebook/musicgen-small", "source": "startup_warming"}
                    self._warming_queue.append((mood, params))
                    
            print(f"[CacheManager] Added {len(self.popular_moods)} popular moods to cache warming queue")
            
        except Exception as e:
            print(f"[CacheManager] Failed to start cache warming: {e}")

    def get_cache_key(self, prompt: str, params: Dict[str, Any]) -> str:
        """
        Generate a unique cache key from prompt and parameters.

        Args:
            prompt: The music generation prompt
            params: Dictionary of generation parameters

        Returns:
            MD5 hash string as cache key
        """
        # Create a deterministic string from prompt and sorted params
        param_str = json.dumps(params, sort_keys=True)
        key_string = f"{prompt}|{param_str}"
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, cache_key: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Retrieve cached audio file and metadata if exists.

        Args:
            cache_key: The cache key to look up

        Returns:
            Tuple of (file_path, metadata) if found, None otherwise
        """
        with self._lock:
            self._stats["total_requests"] += 1

            if cache_key in self._cache_index:
                entry = self._cache_index[cache_key]


                # Check if file still exists and is not expired
                cache_file = self.cache_dir / f"{cache_key}.wav"
                if cache_file.exists() and time.time() - entry["timestamp"] < self.cache_ttl:  # Use configurable TTL
                    # Move to end (most recently used)
                    self._cache_index.move_to_end(cache_key)
                    self._stats["hits"] += 1


                    # Update most cached prompts
                    prompt = entry.get("prompt", "")
                    self._stats["most_cached_prompts"][prompt] = self._stats["most_cached_prompts"].get(prompt, 0) + 1
                    
                    # Track cache warming hits
                    if entry.get("source") == "cache_warming":
                        self._stats["cache_warming_hits"] += 1

                    return str(cache_file), entry
                else:
                    # File expired or missing, remove from index
                    del self._cache_index[cache_key]
                    self._stats["files_cached"] = len(self._cache_index)

            self._stats["misses"] += 1
            return None

    def set(self, cache_key: str, audio_file: str, metadata: Dict[str, Any]) -> None:
        """
        Store audio file and metadata in cache.

        Args:
            cache_key: The cache key
            audio_file: Path to the audio file to cache
            metadata: Metadata dictionary containing prompt, params, etc.
        """
        with self._lock:
            cache_file = self.cache_dir / f"{cache_key}.wav"

            # Copy audio file to cache
            import shutil
            shutil.copy2(audio_file, cache_file)

            # Add to index
            entry = {
                "timestamp": time.time(),
                "file_size": cache_file.stat().st_size,
                **metadata
            }

            self._cache_index[cache_key] = entry
            self._stats["files_cached"] = len(self._cache_index)
            self._stats["cache_size_bytes"] += entry["file_size"]

            # Update most cached prompts
            prompt = metadata.get("prompt", "")
            self._stats["most_cached_prompts"][prompt] = self._stats["most_cached_prompts"].get(prompt, 0) + 1

            # Evict if necessary
            self._evict_if_needed()

    def _evict_if_needed(self) -> None:
        """Evict least recently used items if cache limits exceeded."""
        while (len(self._cache_index) > self.max_files or
               self._stats["cache_size_bytes"] > self.max_size_bytes) and self._cache_index:

            # Remove least recently used
            cache_key, entry = self._cache_index.popitem(last=False)
            cache_file = self.cache_dir / f"{cache_key}.wav"

            if cache_file.exists():
                cache_file.unlink()

            self._stats["cache_size_bytes"] -= entry["file_size"]
            self._stats["evictions"] += 1
            self._stats["files_cached"] = len(self._cache_index)

    def _load_cache_index(self) -> None:
        """Load cache index from disk."""
        index_file = self.cache_dir / "cache_index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                    self._cache_index = OrderedDict(data.get("index", {}))
                    self._stats.update(data.get("stats", {}))
            except Exception:
                # If loading fails, start with empty cache
                pass

    def _save_cache_index(self) -> None:
        """Save cache index to disk."""
        index_file = self.cache_dir / "cache_index.json"
        data = {
            "index": dict(self._cache_index),
            "stats": self._stats
        }
        try:
            with open(index_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass


    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary containing detailed cache statistics
        """
        with self._lock:
            stats = self._stats.copy()
            stats["hit_rate"] = (stats["hits"] / stats["total_requests"]) if stats["total_requests"] > 0 else 0.0
            stats["cache_size_mb"] = stats["cache_size_bytes"] / (1024 * 1024)
            stats["cache_size_gb"] = stats["cache_size_mb"] / 1024
            stats["storage_usage_percent"] = (stats["cache_size_bytes"] / self.max_size_bytes) * 100
            stats["files_usage_percent"] = (len(self._cache_index) / self.max_files) * 100
            
            # Top cached prompts
            sorted_prompts = sorted(stats["most_cached_prompts"].items(), key=lambda x: x[1], reverse=True)
            stats["top_cached_prompts"] = sorted_prompts[:10]  # Top 10
            
            # Cache efficiency metrics
            stats["efficiency_score"] = self._calculate_efficiency_score()
            stats["warming_effectiveness"] = self._calculate_warming_effectiveness()
            
            return stats
    
    def _calculate_efficiency_score(self) -> float:
        """Calculate cache efficiency score (0-100)."""
        if self._stats["total_requests"] == 0:
            return 0.0
        
        hit_rate = self._stats["hits"] / self._stats["total_requests"]
        storage_efficiency = min(100.0, (self._stats["cache_size_bytes"] / self.max_size_bytes) * 100)
        
        # Combine hit rate and storage utilization
        efficiency = (hit_rate * 70) + (storage_efficiency * 0.3)
        return min(100.0, efficiency)
    
    def _calculate_warming_effectiveness(self) -> float:
        """Calculate cache warming effectiveness."""
        total_warming_hits = self._stats.get("cache_warming_hits", 0)
        if total_warming_hits == 0:
            return 0.0
        
        warming_hit_rate = total_warming_hits / self._stats["total_requests"]
        return min(100.0, warming_hit_rate * 100)
    
    def get_formatted_stats(self) -> str:
        """Get formatted cache statistics for display."""
        stats = self.get_stats()
        
        formatted = []
        formatted.append("📊 CACHE STATISTICS")
        formatted.append("=" * 50)
        formatted.append(f"📈 Hit Rate: {stats['hit_rate']:.1%}")
        formatted.append(f"💾 Storage Used: {stats['cache_size_mb']:.1f} MB / {self.max_size_bytes / (1024*1024):.0f} MB ({stats['storage_usage_percent']:.1f}%)")
        formatted.append(f"📁 Files Cached: {len(self._cache_index)} / {self.max_files} ({stats['files_usage_percent']:.1f}%)")
        formatted.append(f"⚡ Efficiency Score: {stats['efficiency_score']:.1f}/100")
        formatted.append(f"🔥 Cache Warming Effectiveness: {stats['warming_effectiveness']:.1f}%")
        formatted.append(f"✅ Cache Hits: {stats['hits']}")
        formatted.append(f"❌ Cache Misses: {stats['misses']}")
        formatted.append(f"🔄 Evictions: {stats['evictions']}")
        formatted.append("")
        
        # Top cached prompts
        if stats["top_cached_prompts"]:
            formatted.append("🎵 TOP CACHED PROMPTS:")
            formatted.append("-" * 30)
            for i, (prompt, count) in enumerate(stats["top_cached_prompts"][:5], 1):
                short_prompt = prompt[:60] + "..." if len(prompt) > 60 else prompt
                formatted.append(f"{i}. {short_prompt} ({count} times)")
        
        return "\n".join(formatted)


    def clear_cache(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Clear all cached files and reset statistics.
        
        Args:
            confirm: If True, perform clear operation
            
        Returns:
            Dictionary with operation results
        """
        if not confirm:
            return {
                "success": False,
                "message": "Clear operation cancelled - confirmation required",
                "files_cleared": 0,
                "space_freed_mb": 0.0
            }
            
        with self._lock:
            files_cleared = 0
            space_freed = 0
            
            for cache_key in list(self._cache_index.keys()):
                cache_file = self.cache_dir / f"{cache_key}.wav"
                if cache_file.exists():
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    files_cleared += 1
                    space_freed += file_size

            self._cache_index.clear()
            self._stats = {
                "hits": 0,
                "misses": 0,
                "total_requests": 0,
                "cache_size_bytes": 0,
                "files_cached": 0,
                "evictions": 0,
                "most_cached_prompts": {},
                "avg_generation_time": 0.0,
                "total_generation_time": 0.0,
                "cache_warming_hits": 0,
                "popular_moods_cached": []
            }
            self._save_cache_index()
            
            return {
                "success": True,
                "message": f"Cache cleared successfully",
                "files_cleared": files_cleared,
                "space_freed_mb": space_freed / (1024 * 1024)
            }
    
    def selective_clear(self, older_than_hours: int = 24) -> Dict[str, Any]:
        """
        Clear cache entries older than specified hours.
        
        Args:
            older_than_hours: Age threshold in hours
            
        Returns:
            Dictionary with operation results
        """
        with self._lock:
            files_cleared = 0
            space_freed = 0
            current_time = time.time()
            cutoff_time = current_time - (older_than_hours * 3600)
            
            for cache_key in list(self._cache_index.keys()):
                entry = self._cache_index[cache_key]
                if entry["timestamp"] < cutoff_time:
                    cache_file = self.cache_dir / f"{cache_key}.wav"
                    if cache_file.exists():
                        file_size = cache_file.stat().st_size
                        cache_file.unlink()
                        files_cleared += 1
                        space_freed += file_size
                    
                    del self._cache_index[cache_key]
                    self._stats["cache_size_bytes"] -= entry["file_size"]

            self._stats["files_cached"] = len(self._cache_index)
            self._save_cache_index()
            
            return {
                "success": True,
                "message": f"Cleared {files_cleared} entries older than {older_than_hours} hours",
                "files_cleared": files_cleared,
                "space_freed_mb": space_freed / (1024 * 1024)
            }


    def export_cache(self, export_dir: str = None) -> Dict[str, Any]:
        """
        Export cache contents to a directory with comprehensive metadata.
        
        Args:
            export_dir: Directory to export cache to (optional, creates timestamped dir)
            
        Returns:
            Dictionary with export results
        """
        if export_dir is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            export_dir = f"cache_export_{timestamp}"
            
        export_path = Path(export_dir)
        export_path.mkdir(exist_ok=True)

        with self._lock:
            files_exported = 0
            total_size = 0
            
            # Create detailed export
            export_data = {
                "export_info": {
                    "export_time": time.time(),
                    "export_directory": str(export_path),
                    "original_cache_dir": str(self.cache_dir)
                },
                "cache_stats": self.get_stats(),
                "cache_entries": {},
                "summary": {
                    "total_files": 0,
                    "total_size_mb": 0.0,
                    "oldest_entry": None,
                    "newest_entry": None
                }
            }
            
            # Copy all cache files and collect metadata
            for cache_key, entry in self._cache_index.items():
                cache_file = self.cache_dir / f"{cache_key}.wav"
                if cache_file.exists():
                    # Copy file
                    dest_file = export_path / f"{cache_key}.wav"
                    shutil.copy2(cache_file, dest_file)
                    
                    # Add to export metadata
                    export_data["cache_entries"][cache_key] = {
                        **entry,
                        "export_path": str(dest_file),
                        "file_exists": True
                    }
                    
                    files_exported += 1
                    total_size += entry["file_size"]
                    
                    # Track temporal info
                    if export_data["summary"]["oldest_entry"] is None or entry["timestamp"] < export_data["summary"]["oldest_entry"]:
                        export_data["summary"]["oldest_entry"] = entry["timestamp"]
                    if export_data["summary"]["newest_entry"] is None or entry["timestamp"] > export_data["summary"]["newest_entry"]:
                        export_data["summary"]["newest_entry"] = entry["timestamp"]
            
            # Update summary
            export_data["summary"]["total_files"] = files_exported
            export_data["summary"]["total_size_mb"] = total_size / (1024 * 1024)
            
            # Export comprehensive metadata
            with open(export_path / "cache_export_metadata.json", 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            # Export simple index for quick reference
            simple_index = {
                "cache_keys": list(self._cache_index.keys()),
                "export_time": time.time(),
                "file_count": files_exported
            }
            with open(export_path / "cache_index.json", 'w') as f:
                json.dump(simple_index, f, indent=2)
                
            return {
                "success": True,
                "export_directory": str(export_path),
                "files_exported": files_exported,
                "total_size_mb": total_size / (1024 * 1024),
                "metadata_file": str(export_path / "cache_export_metadata.json")
            }

    def warm_cache(self, popular_prompts: list, params_template: Dict[str, Any] = None) -> None:
        """
        Pre-generate and cache popular prompts.

        Args:
            popular_prompts: List of prompts to pre-generate
            params_template: Default parameters for generation
        """
        if params_template is None:
            params_template = {"duration": 8, "model_name": "facebook/musicgen-small"}

        with self._lock:
            self._warming_queue.extend([
                (prompt, params_template.copy()) for prompt in popular_prompts
            ])

        # Start background warming if not already running
        if self._warming_thread is None or not self._warming_thread.is_alive():
            self._warming_thread = threading.Thread(target=self._background_warming, daemon=True)
            self._warming_thread.start()

    def _background_warming(self) -> None:
        """Background thread for cache warming."""
        # Import here to avoid circular imports
        from .generate import generate_music

        while self._warming_queue:
            try:
                prompt, params = self._warming_queue.pop(0)
                cache_key = self.get_cache_key(prompt, params)

                # Check if already cached
                if self.get(cache_key) is None:
                    print(f"[CacheManager] Warming cache for prompt: {prompt[:50]}...")

                    # Generate music
                    start_time = time.time()
                    output_file = generate_music(
                        prompt=prompt,
                        duration=params.get("duration", 8),
                        outfile=f"cache_warm_{cache_key}.wav",
                        model_name=params.get("model_name", "facebook/musicgen-small")
                    )
                    generation_time = time.time() - start_time

                    # Cache the result
                    metadata = {
                        "prompt": prompt,
                        "params": params,
                        "generation_time": generation_time,
                        "source": "cache_warming"
                    }
                    self.set(cache_key, output_file, metadata)

                    print(f"[CacheManager] Cached prompt in {generation_time:.2f}s")

            except Exception as e:
                print(f"[CacheManager] Cache warming failed for prompt: {e}")


    def validate_cache(self, clean_expired: bool = True, fix_corruption: bool = True) -> Dict[str, Any]:
        """
        Validate cache integrity and clean up invalid entries.
        
        Args:
            clean_expired: Remove expired entries
            fix_corruption: Attempt to fix corrupted entries
            
        Returns:
            Dictionary with detailed validation results
        """
        with self._lock:
            validation_results = {
                "validation_time": time.time(),
                "total_entries": len(self._cache_index),
                "valid_entries": 0,
                "expired_entries": 0,
                "missing_files": 0,
                "corrupted_entries": 0,
                "fixed_entries": 0,
                "removed_entries": [],
                "errors": [],
                "recommendations": []
            }
            
            current_time = time.time()
            
            for cache_key, entry in list(self._cache_index.items()):
                cache_file = self.cache_dir / f"{cache_key}.wav"
                entry_issues = []
                
                # Check if file exists
                if not cache_file.exists():
                    entry_issues.append("file_missing")
                    validation_results["missing_files"] += 1
                    
                # Check if entry is expired
                elif clean_expired and (current_time - entry["timestamp"]) > self.cache_ttl:
                    entry_issues.append("expired")
                    validation_results["expired_entries"] += 1
                    
                # Check for corruption (basic validation)
                elif fix_corruption and cache_file.exists():
                    try:
                        # Basic file integrity check
                        file_size = cache_file.stat().st_size
                        if file_size == 0:
                            entry_issues.append("zero_size")
                            validation_results["corrupted_entries"] += 1
                        elif file_size != entry.get("file_size", 0):
                            entry_issues.append("size_mismatch")
                            validation_results["corrupted_entries"] += 1
                            
                        # Check if file is readable
                        with open(cache_file, 'rb') as f:
                            f.read(1024)  # Read first 1KB
                            
                    except Exception as e:
                        entry_issues.append(f"read_error: {str(e)}")
                        validation_results["corrupted_entries"] += 1
                
                # Process issues
                if entry_issues:
                    validation_results["errors"].append({
                        "cache_key": cache_key,
                        "prompt": entry.get("prompt", ""),
                        "issues": entry_issues,
                        "timestamp": entry["timestamp"]
                    })
                    
                    # Attempt fixes based on issue type
                    if "file_missing" in entry_issues or "zero_size" in entry_issues:
                        # Remove corrupted entry
                        del self._cache_index[cache_key]
                        validation_results["removed_entries"].append(cache_key)
                        validation_results["fixed_entries"] += 1
                        
                    elif "expired" in entry_issues and clean_expired:
                        # Remove expired entry
                        cache_file.unlink()
                        del self._cache_index[cache_key]
                        validation_results["removed_entries"].append(cache_key)
                        
                    elif "size_mismatch" in entry_issues:
                        # Update file size in metadata
                        if cache_file.exists():
                            entry["file_size"] = cache_file.stat().st_size
                            validation_results["fixed_entries"] += 1
                    else:
                        validation_results["valid_entries"] += 1
                else:
                    validation_results["valid_entries"] += 1
            
            # Update stats
            self._stats["files_cached"] = len(self._cache_index)
            self._save_cache_index()
            
            # Generate recommendations
            if validation_results["expired_entries"] > 0:
                validation_results["recommendations"].append(f"Consider running selective_clear() to remove {validation_results['expired_entries']} expired entries")
            if validation_results["corrupted_entries"] > 0:
                validation_results["recommendations"].append(f"Found {validation_results['corrupted_entries']} corrupted entries - cache integrity should be monitored")
            if validation_results["valid_entries"] == 0:
                validation_results["recommendations"].append("Cache is empty - consider warming cache with popular prompts")
            
            return validation_results
    
    def get_cache_health_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive cache health report.
        
        Returns:
            Dictionary with health metrics and recommendations
        """
        stats = self.get_stats()
        validation = self.validate_cache(clean_expired=False, fix_corruption=True)
        
        health_score = 100.0
        health_issues = []
        
        # Calculate health score based on various factors
        if stats["hit_rate"] < 0.3:
            health_score -= 20
            health_issues.append("Low cache hit rate")
        
        if stats["storage_usage_percent"] > 90:
            health_score -= 15
            health_issues.append("Cache storage near capacity")
        elif stats["storage_usage_percent"] < 10:
            health_score -= 10
            health_issues.append("Cache underutilized")
        
        if validation["corrupted_entries"] > 0:
            health_score -= validation["corrupted_entries"] * 5
            health_issues.append(f"{validation['corrupted_entries']} corrupted entries")
        
        if validation["expired_entries"] > validation["valid_entries"] * 0.2:
            health_score -= 10
            health_issues.append("Many expired entries")
        
        health_score = max(0.0, health_score)
        
        return {
            "overall_health_score": health_score,
            "health_status": "Excellent" if health_score >= 90 else "Good" if health_score >= 70 else "Fair" if health_score >= 50 else "Poor",
            "health_issues": health_issues,
            "statistics": stats,
            "validation_summary": {
                "valid_entries": validation["valid_entries"],
                "expired_entries": validation["expired_entries"],
                "corrupted_entries": validation["corrupted_entries"],
                "total_entries": validation["total_entries"]
            },
            "recommendations": validation["recommendations"]
        }

    def __del__(self):
        """Save cache index on destruction."""
        try:
            self._save_cache_index()
        except Exception:
            pass


# Global cache manager instance
_cache_manager_instance = None

def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager()
    return _cache_manager_instance
