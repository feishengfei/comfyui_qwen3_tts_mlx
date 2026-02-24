import os
from inspect import cleandoc

from mlx_audio.tts.generate import generate_audio
from mlx_audio.tts.utils import load_model

# =========================
# 🔹 模型加载节点（带缓存）
# =========================

class Qwen3TTSMLXLoader:
    _model_cache = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model_dir": ("STRING", {"default": "/path/to/your/qwen3tts-folder"}),
            }
        }

    RETURN_TYPES = ("QWEN3_TTS_MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "load_model_node"
    CATEGORY = "Qwen3-TTS-MLX"

    def load_model_node(self, model_dir):
        if model_dir in self._model_cache:
            return (self._model_cache[model_dir],)

        model = load_model(model_dir)
        self._model_cache[model_dir] = model
        return (model,)


# =========================
# 🔹 TTS 生成节点
# =========================

class Qwen3TTSMLXGenerate:

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("QWEN3_TTS_MODEL",),
                "text": ("STRING", {"multiline": True}),
                "ref_audio": ("STRING", {"default": ""}),
                "ref_text": ("STRING", {"default": ""}),
                "output_dir": ("STRING", {"default": "tts_output"}),
                "file_prefix": ("STRING", {"default": "tts"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("output_path",)
    FUNCTION = "generate_node"
    CATEGORY = "Qwen3-TTS-MLX"

    OUTPUT_NODE = True

    def generate_node(
        self,
        model,
        text,
        ref_audio,
        ref_text,
        output_dir,
        file_prefix,
    ):
        os.makedirs(output_dir, exist_ok=True)

        # 调用生成
        generate_audio(
            model=model,
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,
            file_prefix=file_prefix,
            output_path=output_dir,
        )

        return (output_dir,)


# =========================
# 🔹 注册
# =========================

NODE_CLASS_MAPPINGS = {
    "Qwen3TTSMLXLoader": Qwen3TTSMLXLoader,
    "Qwen3TTSMLXGenerate": Qwen3TTSMLXGenerate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Qwen3TTSMLXLoader": "Qwen3 TTS MLX Loader",
    "Qwen3TTSMLXGenerate": "Qwen3 TTS MLX Generate",
}
