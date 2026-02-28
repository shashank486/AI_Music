
# ## app/advanced_features.py
# import streamlit as st
# import os
# import sys

# # Fix imports: ensure backend is accessible
# ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# if ROOT_DIR not in sys.path:
#     sys.path.append(ROOT_DIR)

# # Backend modules
# from backend.music_variations import (
#     generate_variations,
#     extend_music,
#     batch_generate
# )


# # ---------------------------------------------------------
# # GLOBAL STYLE
# # ---------------------------------------------------------
# def apply_style():
#     st.markdown("""
#     <style>

#     /* -------- GLOBAL FONT -------- */
#     html, body, [class*="css"] {
#         font-family: 'Inter', sans-serif;
#     }

#     /* -------- HERO BANNER -------- */
#     .hero {
#         background: linear-gradient(135deg, #4f46e5, #3b82f6, #0ea5e9);
#         padding: 30px;
#         text-align: center;
#         border-radius: 18px;
#         color: white;
#         font-size: 28px;
#         font-weight: 800;
#         margin-bottom: 30px;
#         box-shadow: 0 8px 25px rgba(0,0,0,0.3);
#     }

#     /* -------- GLASS EFFECT BOX -------- */
#     .section-box {
#         background: rgba(255,255,255,0.06);
#         backdrop-filter: blur(12px);
#         border: 1px solid rgba(255,255,255,0.1);
#         padding: 25px;
#         border-radius: 16px;
#         color: #e5e7eb;
#         margin-bottom: 30px;
#         box-shadow: 0 4px 20px rgba(0,0,0,0.25);
#     }

#     /* -------- VARIATION BOXES -------- */
#     .variation-box {
#         background: rgba(255,255,255,0.08);
#         padding: 18px;
#         border-radius: 14px;
#         margin-bottom: 10px;
#         border: 1px solid rgba(255,255,255,0.15);
#         transition: 0.25s ease;
#     }
#     .variation-box:hover {
#         transform: scale(1.03);
#         box-shadow: 0 8px 25px rgba(0,0,0,0.35);
#     }

#     /* -------- BUTTON -------- */
#     .stButton>button {
#         background: linear-gradient(90deg, #2563eb, #3b82f6);
#         color: white;
#         padding: 12px 25px !important;
#         border-radius: 12px !important;
#         font-size: 17px;
#         font-weight: 600;
#         border: none;
#         transition: 0.2s ease;
#     }
#     .stButton>button:hover {
#         background: linear-gradient(90deg, #4338ca, #2563eb);
#         transform: translateY(-2px);
#         box-shadow: 0px 5px 18px rgba(59,130,246,0.45);
#     }

#     /* -------- TEXT INPUTS -------- */
#     .stTextInput>div>div>input {
#         background-color: rgba(255,255,255,0.10) !important;
#         color: white !important;
#         border-radius: 10px !important;
#         border: 1px solid rgba(255,255,255,0.15) !important;
#     }

#     textarea {
#         background-color: rgba(255,255,255,0.10) !important;
#         color: white !important;
#         border-radius: 12px !important;
#         border: 1px solid rgba(255,255,255,0.15) !important;
#     }

#     /* -------- SIDEBAR -------- */
#     section[data-testid="stSidebar"] {
#         background: linear-gradient(180deg, #0f172a, #1e293b) !important;
#         color: white !important;
#     }
#     section[data-testid="stSidebar"] .css-1x8cf1d {
#         color: white !important;
#     }

#     /* -------- LABELS -------- */
#     label {
#         font-weight: 600 !important;
#         color: #cbd5e1 !important;
#     }

#     /* -------- HEADINGS -------- */
#     h2, h3, h4 {
#         color: #ffffff !important;
#         font-weight: 700 !important;
#     }

#     </style>
#     """, unsafe_allow_html=True)



# # ---------------------------------------------------------
# # ADVANCED PAGE
# # ---------------------------------------------------------
# def run_advanced_page():
#     apply_style()

#     # Ensure history functions exist
#     if "add_history_func" not in st.session_state or "ensure_history_func" not in st.session_state:
#         st.error("⚠️ History functions not registered. Fix Streamlit App setup.")
#         return

#     add_history_item = st.session_state.add_history_func
#     ensure_history = st.session_state.ensure_history_func

#     st.markdown("<div class='hero'>🎛️ MelodAI — Advanced Features</div>", unsafe_allow_html=True)

#     # Sidebar controls
#     st.sidebar.header("Advanced Controls")
#     duration = st.sidebar.slider("Duration (seconds)", 10, 120, 30)
#     model_name = st.sidebar.selectbox(
#         "Model",
#         ["facebook/musicgen-small", "facebook/musicgen-medium", "facebook/musicgen-melody"]
#     )

#     st.sidebar.markdown("---")

#  # =========================================================================
#     st.markdown("## ⚙️ Advanced Parameters")

#     with st.expander("Advanced Parameters", expanded=False):
#         top_k = st.slider("Top-K", 0, 200, 50, key="adv_topk")
#         top_p = st.slider("Top-P", 0.0, 1.0, 0.95, 0.01, key="adv_topp")
#         cfg = st.slider("CFG Scale", 0.0, 5.0, 1.0, 0.1, key="adv_cfg")
#         expert_mode = st.checkbox("Enable Expert Mode", key="adv_expert_mode")


#     st.markdown("---")

#     # =========================================================================
#     # 2️⃣ GENERATE VARIATIONS + VOTING
#     # =========================================================================
#     st.subheader("🎶 Generate Music Variations")
#     st.markdown("<div class='output-box'>", unsafe_allow_html=True)

#     base_prompt = st.text_input("Base Prompt (leave empty to use last prompt)", key="adv_variation_prompt")
#     num_vars = st.number_input("Number of variations", 1, 6, 3, key="adv_var_count")

#     if st.button("Generate Variations", key="adv_var_btn"):
#         final_prompt = (
#             base_prompt.strip()
#             or st.session_state.get("user_text", "")
#             or st.session_state.get("enhanced_prompt", "")
#         )

#         if not final_prompt:
#             st.error("No base prompt found.")
#         else:
#             with st.spinner("Generating variations..."):
#                 try:
#                     results = generate_variations(
#                         base_prompt=final_prompt,
#                         num_variations=int(num_vars),
#                         duration=int(duration),
#                         model_name=model_name
#                     )

#                     st.session_state.adv_variations = results
#                     st.session_state.adv_votes = {str(i): 0 for i in range(len(results))}

#                     st.success(f"Generated {len(results)} variations!")

#                     for ap, ep in results:
#                         add_history_item(
#                             prompt=final_prompt,
#                             audio_path=ap,
#                             params={"variation_of": final_prompt},
#                             model=model_name,
#                             gen_time_secs=0.0
#                         )

#                 except Exception as e:
#                     st.error("Variation generation failed: " + str(e))

#     # ---------------- SHOW VARIATIONS + VOTING ----------------
#     if st.session_state.get("adv_variations"):
#         st.markdown("### Variations Output")

#         items = st.session_state.adv_variations
#         votes = st.session_state.adv_votes

#         cols = st.columns(len(items))

#         for idx, (ap, ep) in enumerate(items):
#             with cols[idx]:
#                 st.markdown(f"**Variation {idx + 1}**")

#                 try:
#                     with open(ap, "rb") as f:
#                         st.audio(f.read(), format="audio/wav")
#                 except:
#                     st.warning("Audio unavailable.")

#                 st.write("Enhanced Prompt:")
#                 st.write(ep)

#                 if st.button(f"👍 Vote Variation {idx+1}", key=f"vote_{idx}"):
#                     votes[str(idx)] += 1
#                     st.success("Vote counted!")

#                 st.markdown(f"**Votes: {votes[str(idx)]}**")

#         st.markdown("### Votes Summary")
#         st.write(votes)

#     st.markdown("</div>", unsafe_allow_html=True)

#     # ======================================================
#     # 2️⃣ EXTEND MUSIC (from history)
#     # ======================================================
#     st.subheader("⏩ Extend Music")
#     st.markdown("<div class='section-box'>", unsafe_allow_html=True)

#     ensure_history()
#     history_items = {item["id"]: item for item in st.session_state.history}

#     chosen = st.selectbox(
#         "Pick audio to extend",
#         [""] + list(history_items.keys()),
#         format_func=lambda x: (history_items[x]["prompt"] if x else "— Select —")
#     )

#     extra_sec = st.number_input("Extend by (seconds)", 10, 180, 30)

#     if st.button("Extend Selected Audio"):
#         if not chosen:
#             st.error("Select an item to extend.")
#         else:
#             item = history_items[chosen]

#             if not os.path.exists(item["audio_file"]):
#                 st.error("Audio file missing")
#             else:
#                 with st.spinner("Extending..."):
#                     new_file = extend_music(item["audio_file"], extra_sec, model_name)
#                     st.session_state.adv_extended = new_file

#                     # Save to history
#                     add_history_item(
#                         prompt=f"Extension of {item['prompt']}",
#                         audio_path=new_file,
#                         params={"extended_from": chosen},
#                         model=model_name,
#                         gen_time_secs=0.0
#                     )

#                     st.success("Extension created!")

#     if "adv_extended" in st.session_state:
#         try:
#             st.audio(open(st.session_state.adv_extended, "rb"))
#         except:
#             st.warning("Could not open audio")

#     st.markdown("</div>", unsafe_allow_html=True)

#     # ======================================================
#     # 3️⃣ BATCH GENERATION
#     # ======================================================
#     st.subheader("📦 Batch Generator")
#     st.markdown("<div class='section-box'>", unsafe_allow_html=True)

#     prompts_text = st.text_area("Enter multiple prompts (one per line)", height=150)

#     if st.button("Generate Batch"):
#         prompts = [p.strip() for p in prompts_text.split("\n") if p.strip()]

#         if not prompts:
#             st.error("Add prompts!")
#         else:
#             with st.spinner("Generating batch..."):
#                 results = batch_generate(prompts, duration, model_name)
#                 st.session_state.adv_batch = results

#                 for audio_path, ep in results:
#                     add_history_item(
#                         prompt=ep,
#                         audio_path=audio_path,
#                         params={},
#                         model=model_name,
#                         gen_time_secs=0.0
#                     )

#                 st.success("Batch done!")

#     if "adv_batch" in st.session_state:
#         grid = st.session_state.adv_batch
#         cols = st.columns(4)
#         for i, (p, prm) in enumerate(grid):
#             with cols[i % 4]:
#                 try:
#                     st.audio(open(p, "rb"))
#                 except:
#                     st.warning("Audio missing")
#                 st.caption(prm)

#     st.markdown("</div>", unsafe_allow_html=True)







## app/advanced_features.py
import streamlit as st
import os
import sys

# Fix imports: ensure backend is accessible
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from backend.music_variations import (
    generate_variations,
    extend_music,
    batch_generate
)

# ---------------------------------------------------------
# BEAUTIFUL MODERN UI STYLE (Glass + Gradients + Animations)
# ---------------------------------------------------------
def apply_style():
    # Check if dark mode is enabled from main app
    dark_mode = st.session_state.get("dark_mode", False)

    base_css = """
    <style>
    /* -------- GLOBAL ANIMATIONS -------- */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-50px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(50px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes scaleIn {
        from {
            opacity: 0;
            transform: scale(0.9);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }

    @keyframes bounceIn {
        0% {
            opacity: 0;
            transform: scale(0.3);
        }
        50% {
            opacity: 1;
            transform: scale(1.05);
        }
        70% {
            transform: scale(0.9);
        }
        100% {
            opacity: 1;
            transform: scale(1);
        }
    }

    @keyframes shimmer {
        0% {
            background-position: -200% 0;
        }
        100% {
            background-position: 200% 0;
        }
    }

    @keyframes pulse {
        0%, 100% {
            transform: scale(1);
        }
        50% {
            transform: scale(1.05);
        }
    }

    /* -------- GLOBAL FONT -------- */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* -------- HERO BANNER WITH SMOOTH FADE-UP ANIMATION -------- */
    .hero {
        background: linear-gradient(135deg, #4f46e5, #3b82f6, #0ea5e9);
        padding: 30px;
        text-align: center;
        border-radius: 18px;
        color: white;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 30px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        animation: fadeInUp 1.5s ease-out;
        position: relative;
        overflow: hidden;
    }

    .hero::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        animation: 1s ease-out 0s 1 normal none running fadeInUp
    }

    /* -------- ANIMATED SECTIONS -------- */
    .section-box {
        animation: fadeInUp 0.8s ease-out;
        animation-fill-mode: both;
        background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.95) 0%,
            rgba(248, 250, 252, 0.9) 100%);
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 24px;
        padding: 32px;
        margin-bottom: 24px;
        transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow:
            0 12px 40px rgba(148, 163, 184, 0.12),
            0 4px 16px rgba(0, 0, 0, 0.04),
            inset 0 0 0 1px rgba(255, 255, 255, 0.8),
            inset 0 0 60px rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
    }

    .section-box:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow:
            0 20px 60px rgba(139, 92, 246, 0.2),
            0 8px 24px rgba(59, 130, 246, 0.15),
            inset 0 0 0 1px rgba(255, 255, 255, 0.9),
            inset 0 0 80px rgba(255, 255, 255, 0.15);
        border-color: rgba(139, 92, 246, 0.4);
    }

    .variation-box {
        animation: scaleIn 0.6s ease-out;
        animation-fill-mode: both;
        background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.9) 0%,
            rgba(248, 250, 252, 0.8) 100%);
        backdrop-filter: blur(15px) !important;
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 16px rgba(139, 92, 246, 0.1);
        position: relative;
        overflow: hidden;
    }

    .variation-box::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.1), transparent);
        transition: left 0.6s;
    }

    .variation-box:hover::before {
        left: 100%;
    }

    .variation-box:hover {
        transform: scale(1.02) translateY(-3px);
        box-shadow: 0 8px 24px rgba(139, 92, 246, 0.2);
        border-color: rgba(139, 92, 246, 0.4);
    }

    /* -------- PAGE CONTAINER ANIMATION -------- */
    .page-container {
        animation: fadeInUp 1.2s ease-out;
        animation-fill-mode: both;
    }

    /* -------- STAGGERED ANIMATIONS -------- */
    .section-box:nth-child(1) { animation-delay: 0.2s; }
    .section-box:nth-child(2) { animation-delay: 0.4s; }
    .section-box:nth-child(3) { animation-delay: 0.6s; }

    .variation-box:nth-child(1) { animation-delay: 0.1s; }
    .variation-box:nth-child(2) { animation-delay: 0.2s; }
    .variation-box:nth-child(3) { animation-delay: 0.3s; }
    .variation-box:nth-child(4) { animation-delay: 0.4s; }
    .variation-box:nth-child(5) { animation-delay: 0.5s; }
    .variation-box:nth-child(6) { animation-delay: 0.6s; }

    /* -------- LOADING SPINNER ANIMATION -------- */
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .loading-spinner {
        border: 4px solid rgba(139, 92, 246, 0.1);
        border-left: 4px solid #8b5cf6;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        margin: 20px auto;
    }

    /* -------- ADVANCED FEATURES SIDEBAR STYLING -------- */
    /* Light Mode Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg,
            rgba(255, 255, 255, 0.95) 0%,
            rgba(248, 250, 252, 0.92) 25%,
            rgba(241, 245, 249, 0.88) 50%,
            rgba(248, 250, 252, 0.92) 75%,
            rgba(255, 255, 255, 0.95) 100%) !important;
        backdrop-filter: blur(40px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(40px) saturate(180%) !important;
        border-right: 2px solid rgba(139, 92, 246, 0.2) !important;
        box-shadow:
            0 0 50px rgba(139, 92, 246, 0.1),
            inset 0 0 0 1px rgba(255, 255, 255, 0.8) !important;
        position: relative !important;
    }

    section[data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background:
            radial-gradient(circle at 30% 20%, rgba(139, 92, 246, 0.05) 0%, transparent 50%),
            radial-gradient(circle at 70% 80%, rgba(59, 130, 246, 0.05) 0%, transparent 50%);
        pointer-events: none;
        z-index: -1;
    }

    /* Sidebar Text Styling */
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stText,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] h5,
    section[data-testid="stSidebar"] h6 {
        color: #334155 !important;
        text-shadow: 0 1px 2px rgba(255, 255, 255, 0.8) !important;
    }

    /* Sidebar Navigation Buttons */
    section[data-testid="stSidebar"] button {
        background: linear-gradient(135deg,
            rgba(139, 92, 246, 0.9) 0%,
            rgba(59, 130, 246, 0.9) 100%) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border: 2px solid rgba(255, 255, 255, 0.4) !important;
        color: white !important;
        border-radius: 16px !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow:
            0 8px 32px rgba(139, 92, 246, 0.3),
            inset 0 0 0 1px rgba(255, 255, 255, 0.2) !important;
        margin: 6px 0 !important;
        padding: 16px 24px !important;
        width: 100% !important;
        text-align: center !important;
        position: relative !important;
        overflow: hidden !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }

    section[data-testid="stSidebar"] button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg,
            transparent,
            rgba(255, 255, 255, 0.3),
            transparent);
        animation: shimmer 4s infinite;
    }

    section[data-testid="stSidebar"] button:hover {
        background: linear-gradient(135deg,
            rgba(124, 58, 237, 1) 0%,
            rgba(37, 99, 235, 1) 100%) !important;
        transform: translateY(-3px) scale(1.02) !important;
        box-shadow:
            0 12px 40px rgba(139, 92, 246, 0.4),
            inset 0 0 0 2px rgba(255, 255, 255, 0.3),
            0 0 25px rgba(139, 92, 246, 0.3) !important;
        animation: pulse 2s infinite !important;
    }

    /* Sidebar Sliders */
    section[data-testid="stSidebar"] .stSlider > div > div {
        background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.9) 0%,
            rgba(248, 250, 252, 0.8) 100%) !important;
        backdrop-filter: blur(15px) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        border: 2px solid rgba(139, 92, 246, 0.2) !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.1) !important;
    }

    /* Sidebar Selectbox */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.9) 0%,
            rgba(248, 250, 252, 0.8) 100%) !important;
        backdrop-filter: blur(15px) !important;
        border-radius: 12px !important;
        border: 2px solid rgba(139, 92, 246, 0.2) !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(139, 92, 246, 0.1) !important;
        color: #334155 !important;
    }

    section[data-testid="stSidebar"] .stSelectbox > div > div:hover {
        border-color: rgba(139, 92, 246, 0.4) !important;
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.15) !important;
        transform: translateY(-1px) !important;
    }

    /* -------- DARK MODE ADVANCED FEATURES SIDEBAR -------- */
    </style>
    """

    st.markdown(base_css, unsafe_allow_html=True)

    # Add dark mode specific CSS if dark mode is enabled
    if dark_mode:
        dark_mode_css = """
        <style>
        /* -------- DARK MODE ADVANCED FEATURES SIDEBAR -------- */
        .dark-mode section[data-testid="stSidebar"] {
            background: linear-gradient(180deg,
                rgba(32, 32, 32, 0.95) 0%,
                rgba(16, 16, 16, 0.92) 25%,
                rgba(24, 24, 24, 0.88) 50%,
                rgba(16, 16, 16, 0.92) 75%,
                rgba(32, 32, 32, 0.95) 100%) !important;
            backdrop-filter: blur(40px) saturate(180%) !important;
            -webkit-backdrop-filter: blur(40px) saturate(180%) !important;
            border-right: 2px solid rgba(139, 92, 246, 0.4) !important;
            box-shadow:
                0 0 50px rgba(0, 0, 0, 0.5),
                inset 0 0 0 1px rgba(255, 255, 255, 0.1) !important;
        }

        .dark-mode section[data-testid="stSidebar"]::before {
            background:
                radial-gradient(circle at 30% 20%, rgba(139, 92, 246, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 70% 80%, rgba(59, 130, 246, 0.1) 0%, transparent 50%);
        }

        /* Dark Mode Sidebar Text */
        .dark-mode section[data-testid="stSidebar"] .stMarkdown,
        .dark-mode section[data-testid="stSidebar"] .stText,
        .dark-mode section[data-testid="stSidebar"] p,
        .dark-mode section[data-testid="stSidebar"] span,
        .dark-mode section[data-testid="stSidebar"] div,
        .dark-mode section[data-testid="stSidebar"] label,
        .dark-mode section[data-testid="stSidebar"] h1,
        .dark-mode section[data-testid="stSidebar"] h2,
        .dark-mode section[data-testid="stSidebar"] h3,
        .dark-mode section[data-testid="stSidebar"] h4,
        .dark-mode section[data-testid="stSidebar"] h5,
        .dark-mode section[data-testid="stSidebar"] h6 {
            color: #ffffff !important;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5) !important;
        }

        /* Dark Mode Sidebar Buttons */
        .dark-mode section[data-testid="stSidebar"] button {
            background: linear-gradient(135deg,
                rgba(139, 92, 246, 0.9) 0%,
                rgba(59, 130, 246, 0.9) 100%) !important;
            border: 2px solid rgba(255, 255, 255, 0.2) !important;
            box-shadow:
                0 8px 32px rgba(139, 92, 246, 0.4),
                inset 0 0 0 1px rgba(255, 255, 255, 0.1) !important;
        }

        .dark-mode section[data-testid="stSidebar"] button:hover {
            background: linear-gradient(135deg,
                rgba(124, 58, 237, 1) 0%,
                rgba(37, 99, 235, 1) 100%) !important;
            box-shadow:
                0 12px 40px rgba(139, 92, 246, 0.5),
                inset 0 0 0 2px rgba(255, 255, 255, 0.2),
                0 0 25px rgba(139, 92, 246, 0.4) !important;
        }

        /* Dark Mode Sidebar Controls */
        .dark-mode section[data-testid="stSidebar"] .stSlider > div > div,
        .dark-mode section[data-testid="stSidebar"] .stSelectbox > div > div {
            background: linear-gradient(135deg,
                rgba(64, 64, 64, 0.9) 0%,
                rgba(32, 32, 32, 0.8) 100%) !important;
            border: 2px solid rgba(139, 92, 246, 0.3) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        }

        .dark-mode section[data-testid="stSidebar"] .stSelectbox > div > div:hover {
            border-color: rgba(139, 92, 246, 0.5) !important;
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.2) !important;
        }
        </style>
        """
        st.markdown(dark_mode_css, unsafe_allow_html=True)


# ---------------------------------------------------------
# ADVANCED FEATURES PAGE
# ---------------------------------------------------------
def run_advanced_page():
    apply_style()

    if "add_history_func" not in st.session_state or "ensure_history_func" not in st.session_state:
        st.error("⚠️ History functions not registered.")
        return

    add_history_item = st.session_state.add_history_func
    ensure_history = st.session_state.ensure_history_func

    # Page container with transition
    st.markdown("<div class='page-container'>", unsafe_allow_html=True)

    # Hero banner
    st.markdown("<div class='hero'>🎛️ MelodAI — Advanced Features</div>", unsafe_allow_html=True)

    # Sidebar controls with improved styling
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h3 style="color: #7c3aed; margin-bottom: 10px;">🎛️ Advanced Studio</h3>
        <p style="color: #94a3b8; font-size: 12px;">Professional Music Tools</p>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎚️ Generation Settings")
    duration = st.sidebar.slider("Duration (seconds)", 10, 120, 30, help="Length of generated audio")
    model_name = st.sidebar.selectbox(
        "🤖 AI Model",
        ["facebook/musicgen-small", "facebook/musicgen-medium", "facebook/musicgen-melody"],
        help="Choose the MusicGen model"
    )

    st.sidebar.markdown("---")

    # -------------------------------------------------------------------------
    # Advanced parameters section (styled only)
    # -------------------------------------------------------------------------
    st.markdown("<h3> Advanced Parameters</h3>", unsafe_allow_html=True)
    with st.expander("Show Advanced Settings", expanded=False):
        top_k = st.slider("Top-K", 0, 200, 50, key="adv_topk")
        top_p = st.slider("Top-P", 0.0, 1.0, 0.95, 0.01, key="adv_topp")
        cfg = st.slider("CFG Scale", 0.0, 5.0, 1.0, 0.1, key="adv_cfg")
        expert_mode = st.checkbox("Enable Expert Mode", key="adv_expert")

    st.markdown("<hr>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # VARIATIONS (UI improved only)
    # -------------------------------------------------------------------------
    st.subheader(" Generate Music Variations")
    st.markdown("<div class='section-box'>", unsafe_allow_html=True)

    base_prompt = st.text_input("Base Prompt", key="adv_variation_prompt")
    num_vars = st.number_input("Number of variations", 1, 6, 3)

    if st.button("Generate Variations"):
        final_prompt = base_prompt.strip() or st.session_state.get("user_text", "") or st.session_state.get("enhanced_prompt", "")

        if not final_prompt:
            st.error("Enter a valid prompt.")
        else:
            with st.spinner("Generating variations..."):
                try:
                    results = generate_variations(
                        base_prompt=final_prompt,
                        num_variations=int(num_vars),
                        duration=int(duration),
                        model_name=model_name
                    )

                    st.session_state.adv_variations = results
                    st.session_state.adv_votes = {str(i): 0 for i in range(len(results))}

                    st.success("Generated successfully!")

                    for ap, ep in results:
                        add_history_item(
                            prompt=final_prompt,
                            audio_path=ap,
                            params={"variation_of": final_prompt},
                            model=model_name,
                            gen_time_secs=0.0
                        )

                except Exception as e:
                    st.error(str(e))

    # Show variations with improved UI
    if st.session_state.get("adv_variations"):
        st.markdown("### Variations")
        items = st.session_state.adv_variations
        votes = st.session_state.adv_votes

        cols = st.columns(len(items))
        for idx, (ap, ep) in enumerate(items):
            with cols[idx]:
                st.markdown(f"<div class='variation-box'><b>Variation {idx+1}</b></div>", unsafe_allow_html=True)
                try:
                    st.audio(open(ap, "rb").read())
                except:
                    st.warning("Audio missing")

                st.caption(f"Prompt: {ep}")

                if st.button(f"👍 Vote {idx+1}", key=f"vote_{idx}"):
                    votes[str(idx)] += 1
                    st.toast("Vote added!")

                st.write(f"Votes: {votes[str(idx)]}")

        st.markdown("### Vote Summary")
        st.write(votes)

    st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # EXTEND MUSIC
    # -------------------------------------------------------------------------
    st.markdown("### ⏩ Extend Music")
    st.markdown("<div class='section-box'>", unsafe_allow_html=True)

    ensure_history()
    history = {item["id"]: item for item in st.session_state.history}

    chosen = st.selectbox(
        "Select audio to extend",
        [""] + list(history.keys()),
        format_func=lambda x: history[x]["prompt"] if x else "— Select —"
    )

    extra_sec = st.number_input("Extend by seconds", 10, 180, 30)

    if st.button("Extend Selected"):
        if not chosen:
            st.error("Select a track.")
        else:
            item = history[chosen]

            if not os.path.exists(item["audio_file"]):
                st.error("Missing file.")
            else:
                with st.spinner("Extending..."):
                    new_file = extend_music(item["audio_file"], extra_sec, model_name)
                    st.session_state.adv_extended = new_file

                    add_history_item(
                        prompt=f"Extension of {item['prompt']}",
                        audio_path=new_file,
                        params={"extended_from": chosen},
                        model=model_name,
                        gen_time_secs=0.0
                    )

                    st.success("Extended!")

    if "adv_extended" in st.session_state:
        st.audio(open(st.session_state.adv_extended, "rb").read())

    st.markdown("</div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # BATCH GENERATION
    # -------------------------------------------------------------------------
    st.subheader(" Batch Generation")
    st.markdown("<div class='section-box'>", unsafe_allow_html=True)

    batch_text = st.text_area("Enter prompts (one per line)", height=150)

    if st.button("Generate Batch"):
        prompts = [p for p in batch_text.split("\n") if p.strip()]
        if not prompts:
            st.error("Enter prompts.")
        else:
            with st.spinner("Generating batch..."):
                results = batch_generate(prompts, duration, model_name)
                st.session_state.adv_batch = results

                for p, prm in results:
                    add_history_item(
                        prompt=prm,
                        audio_path=p,
                        params={"batch": True},
                        model=model_name,
                        gen_time_secs=0.0
                    )

                st.success("Batch created!")

    if "adv_batch" in st.session_state:
        cols = st.columns(4)
        for i, (p, prm) in enumerate(st.session_state.adv_batch):
            with cols[i % 4]:
                try:
                    st.audio(open(p, "rb").read())
                except:
                    st.warning("Missing audio")

                st.caption(prm)

    st.markdown("</div>", unsafe_allow_html=True)




