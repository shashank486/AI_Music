"""
Optimized Streamlit App for MelodAI Music Generator

This is the main optimized Streamlit application that provides a complete UI
for music generation with performance optimizations, advanced features, and
professional styling.
"""

import sys
import os
import time
import uuid
import json
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
import torch

# Add root directory to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# Import optimization utilities
from app.optimization_utils import (
    PerformanceMonitor,
    LazyLoader,
    CacheManager,
    MemoryManager,
    session_manager,
    render_performance_dashboard,
    perf_monitor
)

# Import advanced features
from app.advanced_features import run_advanced_page

# Backend imports
from backend.input_processor import InputProcessor
from backend.prompt_enhancer import PromptEnhancer
from backend.generate import generate_from_enhanced, load_model

# Optional audio processing
try:
    from backend.audio_processor import AudioProcessor
    HAS_AUDIO_PROCESSOR = True
except ImportError:
    HAS_AUDIO_PROCESSOR = False

# Optional music variations
try:
    from backend.music_variations import generate_variations, extend_music, batch_generate
    HAS_MUSIC_VARIATIONS = True
except ImportError:
    HAS_MUSIC_VARIATIONS = False

# Feedback persistence
FEEDBACK_FILE = Path(ROOT_DIR) / ".melodai_feedback.json"

def load_feedback_from_disk():
    """Load feedback from disk."""
    try:
        if FEEDBACK_FILE.exists():
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}

def save_feedback_to_disk(feedback_dict):
    """Save feedback to disk."""
    try:
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_FILE, "w", encoding="utf-8") as fh:
            json.dump(feedback_dict, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _ensure_feedback_initialized():
    """Initialize feedback in session state."""
    if "user_feedback" not in st.session_state:
        st.session_state.user_feedback = load_feedback_from_disk() or {}

def save_user_feedback(item_id, feedback_data):
    """Save user feedback."""
    _ensure_feedback_initialized()
    st.session_state.user_feedback[item_id] = feedback_data
    save_feedback_to_disk(st.session_state.user_feedback)

# History management functions
def _ensure_history_initialized():
    """Initialize history in session state."""
    if "history" not in st.session_state:
        st.session_state.history = []

def add_history_item(prompt, audio_path, params=None, model="unknown", gen_time_secs=0.0):
    """Add item to history."""
    _ensure_history_initialized()

    item = {
        "id": str(uuid.uuid4()),
        "prompt": prompt,
        "audio_file": audio_path,
        "timestamp": datetime.now().isoformat(),
        "model": model,
        "generation_time": gen_time_secs,
        "params": params or {}
    }

    st.session_state.history.insert(0, item)  # Add to beginning

    # Keep only last 50 items
    if len(st.session_state.history) > 50:
        st.session_state.history = st.session_state.history[:50]

def render_history_section():
    """Render the history section with audio playback and feedback."""
    _ensure_history_initialized()

    if not st.session_state.history:
        st.info("🎼 No music generated yet. Create your first piece above!")
        return

    st.markdown("---")
    st.markdown("## 📚 Generation History")

    # History controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        sort_by = st.selectbox(
            "Sort by:",
            ["Newest First", "Oldest First", "Generation Time"],
            key="history_sort"
        )
    with col2:
        filter_model = st.selectbox(
            "Filter model:",
            ["All"] + list(set(item.get("model", "unknown") for item in st.session_state.history)),
            key="history_filter"
        )
    with col3:
        if st.button("🗑️ Clear History", key="clear_history"):
            st.session_state.history = []
            st.success("History cleared!")
            st.experimental_rerun()

    # Apply sorting and filtering
    history_items = st.session_state.history.copy()

    if filter_model != "All":
        history_items = [item for item in history_items if item.get("model") == filter_model]

    if sort_by == "Oldest First":
        history_items.reverse()
    elif sort_by == "Generation Time":
        history_items.sort(key=lambda x: x.get("generation_time", 0), reverse=True)

    # Display history items
    for i, item in enumerate(history_items):
        with st.expander(f"🎵 {item.get('prompt', 'No prompt')[:60]}... ({item.get('timestamp', '').split('T')[0]})", expanded=(i == 0)):
            col1, col2 = st.columns([2, 1])

            with col1:
                # Audio playback
                if os.path.exists(item.get("audio_file", "")):
                    try:
                        with open(item["audio_file"], "rb") as f:
                            audio_bytes = f.read()
                        st.audio(audio_bytes, format="audio/wav")
                    except Exception as e:
                        st.error(f"Could not load audio: {e}")
                else:
                    st.warning("Audio file not found")

                # Metadata
                st.markdown(f"**Model:** {item.get('model', 'Unknown')}")
                st.markdown(f"**Generated:** {item.get('timestamp', 'Unknown')}")
                if item.get("generation_time"):
                    st.markdown(f"**Generation Time:** {item['generation_time']:.2f}s")

                # Parameters
                if item.get("params"):
                    with st.expander("Parameters", expanded=False):
                        st.json(item["params"])

            with col2:
                # Feedback section
                item_id = item["id"]
                _ensure_feedback_initialized()

                st.markdown("### 💬 Feedback")

                # Rating
                rating = st.slider(
                    "Rate this generation:",
                    1, 5, 3,
                    key=f"rating_{item_id}",
                    help="1 = Poor, 5 = Excellent"
                )

                # Thumbs up/down
                col_up, col_down = st.columns(2)
                with col_up:
                    thumbs_up = st.button("👍", key=f"thumbs_up_{item_id}")
                with col_down:
                    thumbs_down = st.button("👎", key=f"thumbs_down_{item_id}")

                # Comment
                comment = st.text_area(
                    "Comments:",
                    key=f"comment_{item_id}",
                    height=60,
                    placeholder="What did you think?"
                )

                # Categories
                categories = st.multiselect(
                    "Categories:",
                    ["Melodic", "Rhythmic", "Atmospheric", "Energetic", "Calm", "Experimental"],
                    key=f"categories_{item_id}"
                )

                # Save feedback
                if st.button("💾 Save Feedback", key=f"save_feedback_{item_id}"):
                    feedback_data = {
                        "rating": rating,
                        "thumbs_up": thumbs_up,
                        "thumbs_down": thumbs_down,
                        "comment": comment,
                        "categories": categories,
                        "timestamp": datetime.now().isoformat()
                    }
                    save_user_feedback(item_id, feedback_data)
                    st.success("Feedback saved!")

                # Show existing feedback
                if item_id in st.session_state.user_feedback:
                    existing = st.session_state.user_feedback[item_id]
                    st.markdown("**Previous Feedback:**")
                    st.markdown(f"⭐ Rating: {existing.get('rating', 'N/A')}/5")
                    if existing.get("comment"):
                        st.markdown(f"💬 {existing['comment']}")

def render_main_page():
    """Render the main music generation page."""
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="color: #7c3aed; font-size: 3rem; font-weight: 800; margin-bottom: 0.5rem;">
            🎵 MelodAI
        </h1>
        <p style="color: #64748b; font-size: 1.2rem; margin-bottom: 2rem;">
            Generate music with AI — from simple prompts to complex compositions
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize components
    input_processor = InputProcessor()
    prompt_enhancer = PromptEnhancer()

    # Sidebar controls
    st.sidebar.markdown("## 🎛️ Generation Settings")

    # Model selection with caching
    model_options = CacheManager.cache_model_info()
    model_names = list(model_options.keys())

    selected_model = st.sidebar.selectbox(
        "🤖 AI Model:",
        model_names,
        index=0,
        help="Choose the MusicGen model for generation"
    )

    # Duration slider
    duration = st.sidebar.slider(
        "⏱️ Duration (seconds):",
        min_value=10,
        max_value=120,
        value=30,
        step=5,
        help="Length of generated music"
    )

    # Temperature control
    temperature = st.sidebar.slider(
        "🌡️ Temperature:",
        min_value=0.1,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="Creativity level (higher = more experimental)"
    )

    # Advanced parameters
    with st.sidebar.expander("⚙️ Advanced Parameters", expanded=False):
        top_k = st.slider("Top-K:", 0, 200, 50, help="Token selection diversity")
        top_p = st.slider("Top-P:", 0.0, 1.0, 0.95, step=0.01, help="Nucleus sampling")
        cfg_scale = st.slider("CFG Scale:", 0.0, 5.0, 1.0, step=0.1, help="Classifier-free guidance")

    # Dark mode toggle
    st.sidebar.markdown("---")
    dark_mode = st.sidebar.checkbox("🌙 Dark Mode", value=False, key="dark_mode")

    # Performance dashboard
    render_performance_dashboard()

    # Main content area
    st.markdown("### 🎼 Create Music")

    # Prompt input section
    with st.container():
        st.markdown("""
        <div style="background: linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(59, 130, 246, 0.1));
             padding: 2rem; border-radius: 16px; margin-bottom: 2rem; border: 1px solid rgba(124, 58, 237, 0.2);">
        """, unsafe_allow_html=True)

        prompt = st.text_area(
            "✍️ Describe your music:",
            height=120,
            placeholder="e.g., 'A calm piano melody with gentle strings in a minor key' or 'Energetic electronic beats with synth leads'",
            help="Be descriptive! Include instruments, mood, style, and tempo."
        )

        # Quick preset buttons
        st.markdown("**Quick Presets:**")
        col1, col2, col3, col4 = st.columns(4)

        presets = {
            "🎹 Classical Piano": "A beautiful classical piano piece in C major with flowing melodies",
            "🎸 Rock Anthem": "Energetic rock music with electric guitar riffs and strong drums",
            "🎧 Ambient Chill": "Calm ambient electronic music with soft pads and subtle beats",
            "🎺 Jazz Improv": "Smooth jazz improvisation with saxophone and piano"
        }

        for i, (preset_name, preset_text) in enumerate(presets.items()):
            if locals()[f"col{i+1}"].button(preset_name, key=f"preset_{i}"):
                prompt = preset_text

        st.markdown("</div>", unsafe_allow_html=True)

    # Generation section
    col_gen, col_space = st.columns([1, 2])

    with col_gen:
        generate_button = st.button(
            "🎵 Generate Music",
            type="primary",
            use_container_width=True,
            disabled=not prompt.strip()
        )

    # Generation logic
    if generate_button and prompt.strip():
        with st.spinner("🎼 Generating your music... This may take a few minutes."):

            # Start performance monitoring
            perf_monitor.start_timer("music_generation")

            try:
                # Process and enhance prompt
                processed_input = input_processor.process_input(prompt)
                enhanced_prompt = prompt_enhancer.enhance_prompt(processed_input)

                # Show enhanced prompt
                with st.expander("✨ Enhanced Prompt", expanded=True):
                    st.markdown(f"**Original:** {prompt}")
                    st.markdown(f"**Enhanced:** {enhanced_prompt}")

                # Generate music
                audio_path = generate_from_enhanced(
                    enhanced_prompt=enhanced_prompt,
                    duration=duration,
                    model_name=selected_model,
                    temperature=temperature,
                    top_k=top_k,
                    top_p=top_p,
                    cfg_scale=cfg_scale
                )

                # End performance monitoring
                gen_time = perf_monitor.end_timer("music_generation")

                # Add to history
                add_history_item(
                    prompt=enhanced_prompt,
                    audio_path=audio_path,
                    params={
                        "original_prompt": prompt,
                        "model": selected_model,
                        "duration": duration,
                        "temperature": temperature,
                        "top_k": top_k,
                        "top_p": top_p,
                        "cfg_scale": cfg_scale
                    },
                    model=selected_model,
                    gen_time_secs=gen_time
                )

                st.success("✅ Music generated successfully!")
                st.balloons()

                # Auto-play generated music
                if os.path.exists(audio_path):
                    with open(audio_path, "rb") as f:
                        audio_bytes = f.read()
                    st.audio(audio_bytes, format="audio/wav")

                    # Download button
                    st.download_button(
                        "⬇️ Download Music",
                        data=audio_bytes,
                        file_name=f"melodai_{int(time.time())}.wav",
                        mime="audio/wav"
                    )

            except Exception as e:
                perf_monitor.end_timer("music_generation")
                st.error(f"❌ Generation failed: {str(e)}")
                st.info("💡 Try adjusting your prompt or using a different model.")

    # Render history
    render_history_section()

def main():
    """Main application entry point."""
    # Page configuration
    st.set_page_config(
        page_title="MelodAI - AI Music Generator",
        page_icon="🎵",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize session state
    session_manager.initialize_defaults({
        "current_page": "main",
        "history": [],
        "user_feedback": {},
        "dark_mode": False
    })

    # Register history functions for advanced features
    st.session_state.add_history_func = add_history_item
    st.session_state.ensure_history_func = _ensure_history_initialized

    # Navigation
    pages = {
        "🎼 Main Generator": "main",
        "🎛️ Advanced Features": "advanced",
        "🎚️ Audio Studio": "audio_studio" if HAS_AUDIO_PROCESSOR else None
    }

    # Filter out None values
    pages = {k: v for k, v in pages.items() if v is not None}

    st.sidebar.markdown("## 🧭 Navigation")
    selected_page = st.sidebar.selectbox(
        "Choose a page:",
        list(pages.keys()),
        key="page_selector"
    )

    current_page = pages[selected_page]

    # Apply dark mode
    if st.session_state.get("dark_mode", False):
        st.markdown("""
        <style>
        .main {
            background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 50%, #3a3a3a 100%) !important;
            background-attachment: fixed;
        }
        .block-container {
            background: transparent !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # Render selected page
    if current_page == "main":
        render_main_page()
    elif current_page == "advanced":
        run_advanced_page()
    elif current_page == "audio_studio":
        from app.streamlit_app import render_audio_studio_page
        render_audio_studio_page()

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0; color: #64748b; font-size: 0.8rem;">
        <p>🎵 <strong>MelodAI</strong></p>
        <p>Powered by MusicGen & Streamlit</p>
        <p>v1.0.0</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
