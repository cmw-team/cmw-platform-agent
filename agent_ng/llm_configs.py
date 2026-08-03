"""
LLM Configuration Module
========================

This module contains the default LLM provider configurations.
Configurations can be enriched at runtime with pricing data from OpenRouter.

The configurations are defined as a dictionary mapping LLMProvider enum values
to LLMConfig dataclass instances. This separation improves maintainability
and allows for easier enrichment with dynamic pricing data.
"""

from .llm_manager import LLMConfig, LLMProvider


def get_default_llm_configs() -> dict[LLMProvider, LLMConfig]:
    """
    Returns the default LLM configurations.

    This function can be extended to load configurations from JSON files
    or enrich them with pricing data from external APIs (e.g., OpenRouter).

    Returns:
        Dictionary mapping LLMProvider to LLMConfig instances.
    """
    return {
        # LLMProvider.GEMINI: LLMConfig(
        #     name="Google Gemini",
        #     type_str="gemini",
        #     api_key_env="GEMINI_KEY",
        #     max_history=25,
        #     tool_support=True,
        #     force_tools=False,
        #     vision_support=True,  # Gemini supports vision
        #     video_support=True,  # Gemini supports video
        #     audio_support=True,  # Gemini supports audio
        #     models=[
        #         {
        #             "model": "gemini-2.5-flash",
        #             "token_limit": 1048576,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": False,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #         {
        #             "model": "gemini-2.5-pro",
        #             "token_limit": 2097152,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": False,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #         {
        #             "model": "gemini-3.1-flash-lite-preview",
        #             "token_limit": 1048576,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": False,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #         {
        #             "model": "gemini-3.1-pro-preview",
        #             "token_limit": 1048576,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": False,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #         {
        #             "model": "gemini-3-flash-preview",
        #             "token_limit": 1048576,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": False,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #     ],
        #     enable_chunking=False,
        # ),
        # LLMProvider.GROQ: LLMConfig(
        #     name="Groq",
        #     type_str="groq",
        #     api_key_env="GROQ_API_KEY",
        #     max_history=15,
        #     tool_support=True,
        #     force_tools=True,
        #     models=[
        #         {
        #             "model": "groq/compound",
        #             "token_limit": 131072,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "llama-3.3-70b-versatile",
        #             "token_limit": 131072,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "llama-3.3-70b-8192",
        #             "token_limit": 16000,
        #             "max_tokens": 4096,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #     ],
        #     enable_chunking=False,
        # ),
        # LLMProvider.HUGGINGFACE: LLMConfig(
        #     name="HuggingFace",
        #     type_str="huggingface",
        #     api_key_env="HUGGINGFACE_API_KEY",
        #     max_history=20,
        #     tool_support=False,
        #     force_tools=False,
        #     models=[
        #         {
        #             "model": "Qwen/Qwen2.5-Coder-32B-Instruct",
        #             "task": "text-generation",
        #             "token_limit": 3000,
        #             "max_new_tokens": 1024,
        #             "do_sample": False,
        #             "temperature": 0,
        #         },
        #         {
        #             "model": "microsoft/DialoGPT-medium",
        #             "task": "text-generation",
        #             "token_limit": 1000,
        #             "max_new_tokens": 512,
        #             "do_sample": False,
        #             "temperature": 0,
        #         },
        #         {
        #             "model": "gpt2",
        #             "task": "text-generation",
        #             "token_limit": 1000,
        #             "max_new_tokens": 256,
        #             "do_sample": False,
        #             "temperature": 0,
        #         },
        #     ],
        #     enable_chunking=True,
        # ),
        # LLMProvider.OPENAI: LLMConfig(
        #     name="OpenAI-compatible",
        #     type_str="openai",
        #     api_key_env="OPENAI_API_KEY",
        #     api_base_env="OPENAI_BASE_URL",
        #     max_history=20,
        #     tool_support=True,
        #     force_tools=False,
        #     vision_support=True,
        #     # Add models here or via AGENT_DEFAULT_MODEL + AGENT_PROVIDER=openai.
        #     # OPENAI_BASE_URL defaults to https://api.openai.com/v1.
        #     models=[],
        #     enable_chunking=True,
        # ),
        # LLMProvider.OPENROUTER: LLMConfig(
        #     name="OpenRouter",
        #     type_str="openrouter",
        #     api_key_env="OPENROUTER_API_KEY",
        #     api_base_env="OPENROUTER_BASE_URL",
        #     max_history=20,
        #     tool_support=True,
        #     force_tools=False,
        #     vision_support=True,  # OpenRouter supports VL models
        #     video_support=True,  # Some models support video
        #     audio_support=True,  # Some models support audio
        #     models=[
        #         {
        #             "model": "anthropic/claude-sonnet-4.5",
        #             "token_limit": 1000000,
        #             "max_tokens": 64000,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": True,
        #         },
        #         {
        #             "model": "anthropic/claude-sonnet-4.6",
        #             "token_limit": 1000000,
        #             "max_tokens": 64000,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": True,
        #         },
        #         {
        #             "model": "deepseek/deepseek-chat-v3.1:free",
        #             "token_limit": 131000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "deepseek/deepseek-r1-0528",
        #             "token_limit": 131000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "deepseek/deepseek-v3.1-terminus",
        #             "token_limit": 131000,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "deepseek/deepseek-v3.1-terminus:exacto",
        #             "token_limit": 131000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "deepseek/deepseek-v3.2-speciale",
        #             "token_limit": 163840,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "deepseek/deepseek-v4-pro",
        #             "token_limit": 1048576,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": False,
        #         },
        #         {
        #             "model": "deepseek/deepseek-v4-flash",
        #             "token_limit": 1048576,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": False,
        #         },
        #         {
        #             "model": "google/gemma-3-flash-preview",
        #             "token_limit": 1048576,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "google/gemma-3-pro-preview",
        #             "token_limit": 1048576,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "google/gemma-4-31b-it:free",
        #             "token_limit": 131072,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "minimax/minimax-m2.1",
        #             "token_limit": 196608,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "minimax/minimax-m2.5:free",
        #             "token_limit": 196608,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "minimax/minimax-m3",
        #             "token_limit": 524288,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": False,
        #         },
        #         {
        #             "model": "mistralai/codestral-2508",
        #             "token_limit": 256000,
        #             "max_tokens": 4096,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "moonshotai/kimi-k2-0905:exacto",
        #             "token_limit": 262144,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "moonshotai/kimi-k2-thinking",
        #             "token_limit": 262144,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "moonshotai/kimi-k2.5",
        #             "token_limit": 262144,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "nvidia/nemotron-3-super-120b-a12b:free",
        #             "token_limit": 256000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "nvidia/nemotron-nano-9b-v2:free",
        #             "token_limit": 128000,
        #             "max_tokens": 4096,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "openai/gpt-5-mini",
        #             "token_limit": 400000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "openai/gpt-oss-120b:free",
        #             "token_limit": 131072,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "openai/gpt-oss-120b:exacto",
        #             "token_limit": 131072,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "qwen/qwen-plus-2025-07-28",
        #             "token_limit": 1000000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "qwen/qwen3.6-plus",
        #             "token_limit": 1000000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": True,
        #             "video_support": True,
        #         },
        #         {
        #             "model": "google/gemini-2.5-flash",
        #             "token_limit": 1048576,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,  # via input_audio (not audio_url); see OpenRouter audio guide
        #         },
        #         {
        #             "model": "google/gemini-3.1-flash-lite-preview",
        #             "token_limit": 1048576,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #         {
        #             "model": "google/gemini-3.1-pro-preview",
        #             "token_limit": 1048576,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #         {
        #             "model": "google/gemini-3-flash-preview",
        #             "token_limit": 1048576,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #         {
        #             "model": "xiaomi/mimo-v2.5",
        #             "token_limit": 1000000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": False,  # OpenRouter: text-only
        #             "video_support": False,  # OpenRouter: text-only
        #             "audio_support": False,  # OpenRouter: text-only
        #         },
        #         {
        #             "model": "xiaomi/mimo-v2-omni",
        #             "token_limit": 262144,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #             "vision_support": True,
        #             "video_support": True,
        #             "audio_support": True,
        #         },
        #         {
        #             "model": "qwen/qwen3-coder:free",
        #             "token_limit": 262144,
        #             "max_tokens": 4096,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "qwen/qwen3-coder-flash",
        #             "token_limit": 128000,
        #             "max_tokens": 4096,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "qwen/qwen3-coder-plus",
        #             "token_limit": 128000,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "qwen/qwen3-coder:exacto",
        #             "token_limit": 262144,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "qwen/qwen3-max",
        #             "token_limit": 256000,
        #             "max_tokens": 32768,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "x-ai/grok-4-fast",
        #             "token_limit": 2000000,
        #             "max_tokens": 30000,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "x-ai/grok-4-fast:free",
        #             "token_limit": 2000000,
        #             "max_tokens": 8192,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "x-ai/grok-4.20",
        #             "token_limit": 2000000,
        #             "max_tokens": 30000,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "x-ai/grok-4.20-multi-agent",
        #             "token_limit": 2000000,
        #             "max_tokens": 30000,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "x-ai/grok-4.1-fast",
        #             "token_limit": 2000000,
        #             "max_tokens": 30000,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "x-ai/grok-code-fast-1",
        #             "token_limit": 256000,
        #             "max_tokens": 10000,
        #            "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "z-ai/glm-4.5-air:free",
        #             "token_limit": 200000,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "z-ai/glm-4.6:exacto",
        #             "token_limit": 200000,
        #             "max_tokens": 128000,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "z-ai/glm-4.7",
        #             "token_limit": 200000,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "minimax/minimax-m2.7",
        #             "token_limit": 196608,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #         {
        #             "model": "z-ai/glm-5.1",
        #             "token_limit": 200000,
        #             "max_tokens": 65536,
        #             "temperature": 0,
        #             "force_tools": True,
        #         },
        #     ],
        #     enable_chunking=False,
        # ),
        LLMProvider.POLZA: LLMConfig(
            name="Polza.ai",
            type_str="polza",
            api_key_env="POLZA_API_KEY",
            api_base_env="POLZA_BASE_URL",
            max_history=20,
            tool_support=True,
            force_tools=False,
            # Some models support vision (qwen3.6-plus, grok-4.20); text-only
            # models (glm-5.1, minimax-m2.7) have vision_support=False per-model.
            vision_support=True,
            # Billing is in RUB (cost_rub field).  Set POLZA_RUB_TO_USD_RATE
            # (RUB per 1 USD, e.g. 90) for USD conversion in the billing pipeline.
            models=[
                {
                    # Top pick: cheapest of the three, decent quality for
                    # template-driven text summarization.
                    # Price: 15.42 RUB/1M input / 30.84 RUB/1M output.
                    "model": "deepseek/deepseek-v4-flash",
                    "token_limit": 1048576,
                    "max_tokens": 65536,
                    "temperature": 0,
                    "force_tools": False,
                    "vision_support": False,
                },
                # {
                #     # Too expensive (605.76 RUB/1M output); commented out.
                #     "model": "deepseek/deepseek-v4-pro",
                #     "token_limit": 1048576,
                #     "max_tokens": 65536,
                #     "temperature": 0,
                #     "force_tools": False,
                #     "vision_support": False,
                # },
                {
                    # OpenAI open-weight MoE; strict tool calling and precise
                    # instruction-following for skills with rigid output
                    # formats (e.g. "exactly 10 questions, no commentary").
                    # Price: 11.01 RUB/1M input / 82.60 RUB/1M output.
                    "model": "openai/gpt-oss-120b",
                    "token_limit": 131072,
                    "max_tokens": 65536,
                    "temperature": 0,
                    "force_tools": True,
                    "vision_support": False,
                },
                {
                    # Full multimodal Gemini via Polza.
                    # Active for audio routing when VL_GEMINI_PROVIDER=polza.
                    # YouTube stays on Gemini Direct (VL_YOUTUBE_GEMINI_PROVIDER=google).
                    # Price: 12.93 RUB/1M input / 107.74 RUB/1M output.
                    "model": "google/gemini-2.5-flash",
                    "token_limit": 1048576,
                    "max_tokens": 65535,
                    "temperature": 0,
                    "force_tools": True,
                    "vision_support": True,
                    "video_support": True,
                    "audio_support": True,
                },
                {
                    # Cheap/fast Qwen3.6 tier; text-only on Polza (no image
                    # pricing tier listed despite base model multimodal specs).
                    # Price: 20.65 RUB/1M input / 123.91 RUB/1M output.
                    "model": "qwen/qwen3.6-flash",
                    "token_limit": 1000000,
                    "max_tokens": 65536,
                    "temperature": 0,
                    "force_tools": True,
                    "vision_support": False,
                },
                # {
                #     # Too expensive (487.36 RUB/1M output); commented out.
                #     # Qwen flagship; agent-centric workloads per Polza
                #     # (coding, office/productivity tasks).
                #     "model": "qwen/qwen3.7-max",
                #     "token_limit": 1000000,
                #     "max_tokens": 65536,
                #     "temperature": 0,
                #     "force_tools": True,
                #     "vision_support": False,
                # },
                {
                    # Price: 35.79 RUB/1M input / 214.77 RUB/1M output.
                    "model": "qwen/qwen3.6-plus",
                    "token_limit": 1000000,
                    "max_tokens": 65536,
                    "temperature": 0,
                    "force_tools": True,
                    "vision_support": True,
                },
                # {
                #     # Context too small (41K) for full meeting transcripts
                #     # plus skill body (up to 15K); commented out.
                #     # Price: 5.40 RUB/1M input / 43.23 RUB/1M output.
                #     "model": "qwen/qwen3-8b",
                #     "token_limit": 41000,
                #     "max_tokens": 8000,
                #     "temperature": 0,
                #     "force_tools": True,
                #     "vision_support": True,
                # },
                {
                    # Top pick for meeting-summary/transcript synthesis
                    # (cmw-summarize-meeting skill): best-in-class open
                    # reasoning model for long-document synthesis and
                    # reliable tool calling (web_search/MCP).
                    # Price: 66.08 RUB/1M input / 275.34 RUB/1M output.
                    "model": "moonshotai/kimi-k2-thinking",
                    "token_limit": 262144,
                    "max_tokens": 65536,
                    "temperature": 0,
                    "force_tools": True,
                    "vision_support": False,
                },
                {
                    # Price: 33.04 RUB/1M input / 132.17 RUB/1M output.
                    "model": "minimax/minimax-m3",
                    "token_limit": 524288,
                    "max_tokens": 65536,
                    "temperature": 0,
                    "force_tools": False,
                    "vision_support": False,
                },
                # {
                #     # Older and more expensive than minimax-m3 above
                #     # (264.33 vs 132.17 RUB/1M output); commented out.
                #     # Price: 66.08 RUB/1M input / 264.33 RUB/1M output.
                #     "model": "minimax/minimax-m2.7",
                #     "token_limit": 204800,
                #     "max_tokens": 65536,
                #     "temperature": 0,
                #     "force_tools": True,
                #     "vision_support": False,
                # },
                # {
                #     # Too expensive (323.33 RUB/1M output); commented out.
                #     "model": "z-ai/glm-5.1",
                #     "token_limit": 202752,
                #     "max_tokens": 65536,
                #     "temperature": 0,
                #     "force_tools": True,
                #     "vision_support": False,
                # },
                {
                    # Primary Grok pick for daily use; Polza markets it for
                    # agentic workflows and high-factuality instruction
                    # following.
                    # Price: 137.67 RUB/1M input / 275.34 RUB/1M output.
                    "model": "x-ai/grok-4.3",
                    "token_limit": 1000000,
                    "max_tokens": 65536,
                    "temperature": 0,
                    "force_tools": True,
                    "vision_support": False,
                },
                {
                    # Kept specifically as the context-overflow fallback
                    # target (see native_langchain_streaming.py
                    # _select_fallback_model_for_agent / FALLBACK_MODEL_DEFAULT):
                    # 2M context is the largest in this list, needed for the
                    # "На переполнении сменить модель" switch to actually
                    # have somewhere strictly larger to go. Same price as
                    # grok-4.3 above.
                    # Price: 137.67 RUB/1M input / 275.34 RUB/1M output.
                    "model": "x-ai/grok-4.20",
                    "token_limit": 2000000,
                    "max_tokens": 131072,
                    "temperature": 0,
                    "force_tools": True,
                    "vision_support": True,
                },
                # {
                #     # Search-grounding differentiator is moot: web search
                #     # goes through Tavily, not the LLM's native retrieval.
                #     # Sonar's backbone is optimized for short search
                #     # snippets, not strict-template text synthesis.
                #     # Price: 110.14 RUB/1M input / 110.14 RUB/1M output.
                #     "model": "perplexity/sonar",
                #     "token_limit": 127072,
                #     "max_tokens": 65536,
                #     "temperature": 0,
                #     "force_tools": True,
                #     "vision_support": False,
                # },
                # {
                #     # Too expensive (396.50 RUB/1M output); commented out.
                #     # NVIDIA frontier-reasoning/orchestration MoE (550B
                #     # total, 55B active). Not part of the Google/DeepSeek/
                #     # Qwen/MiniMax/GLM/Grok family ordering above.
                #     "model": "nvidia/nemotron-3-ultra-550b-a55b",
                #     "token_limit": 512000,
                #     "max_tokens": 65536,
                #     "temperature": 0,
                #     "force_tools": True,
                #     "vision_support": False,
                # },
                # {
                #     # "Lite" tier meant for focused sub-steps in
                #     # multi-agent workflows, not primary text synthesis.
                #     # Also more expensive than the full gemini-2.5-flash
                #     # tier above despite being the "lite" variant.
                #     # Price: 33.04 RUB/1M input / 275.34 RUB/1M output.
                #     "model": "google/gemini-3.5-flash-lite",
                #     "token_limit": 1000000,
                #     "max_tokens": 65536,
                #     "temperature": 0,
                #     "force_tools": True,
                #     "vision_support": True,
                # },
                # {
                #     # Omni model: image + video + audio input.
                #     # Used as VL_AUDIO_MODEL when AGENT_PROVIDER=polza.
                #     # Removed from Polza catalog (404 as of this comment);
                #     # kept for reference in case it returns under a new slug.
                #     "model": "xiaomi/mimo-v2-omni",
                #     "token_limit": 262144,
                #     "max_tokens": 32768,
                #     "temperature": 0,
                #     "force_tools": True,
                #     "vision_support": True,
                #     "video_support": True,
                #     "audio_support": True,
                # },
            ],
            enable_chunking=True,
        ),
        # LLMProvider.MISTRAL: LLMConfig(
        #     name="Mistral AI",
        #     type_str="mistral",
        #     api_key_env="MISTRAL_API_KEY",
        #     max_history=20,
        #     tool_support=True,
        #     force_tools=True,
        #     models=[
        #         {
        #             "model": "mistral-large-latest",
        #             "token_limit": 32000,
        #             "max_tokens": 2048,
        #             "temperature": 0,
        #         },
        #         {
        #             "model": "mistral-small-latest",
        #             "token_limit": 32000,
        #             "max_tokens": 2048,
        #             "temperature": 0,
        #         },
        #         {
        #             "model": "mistral-medium-latest",
        #             "token_limit": 32000,
        #             "max_tokens": 2048,
        #             "temperature": 0,
        #         },
        #     ],
        #     token_per_minute_limit=500000,
        #     enable_chunking=False,
        # ),
        # LLMProvider.GIGACHAT: LLMConfig(
        #     name="Sber GigaChat",
        #     type_str="gigachat",
        #     api_key_env="GIGACHAT_API_KEY",
        #     scope_env="GIGACHAT_SCOPE",
        #     verify_ssl_env="GIGACHAT_VERIFY_SSL",
        #     max_history=20,
        #     tool_support=True,
        #     force_tools=True,
        #     models=[
        #         {
        #             "model": "GigaChat-2",
        #             "token_limit": 128000,
        #             "max_tokens": 2048,
        #             "temperature": 0,
        #             "top_p": 0.9,
        #             "repetition_penalty": 1.0,
        #         },
        #         {
        #             "model": "GigaChat-2-Pro",
        #             "token_limit": 128000,
        #             "max_tokens": 2048,
        #             "temperature": 0,
        #             "top_p": 0.9,
        #             "repetition_penalty": 1.0,
        #         },
        #         {
        #             "model": "GigaChat-2-Max",
        #             "token_limit": 128000,
        #             "max_tokens": 2048,
        #             "temperature": 0,
        #             "top_p": 0.9,
        #             "repetition_penalty": 1.0,
        #         },
        #     ],
        #     enable_chunking=False,
        # ),
    }
