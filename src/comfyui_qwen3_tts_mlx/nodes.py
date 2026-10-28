import os
import yaml
from pathlib import Path
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


OPTION_SETTINGS = {
    "lang_code": (["auto", "english", "chinese", "japanese", "korean", "french", "german", "spanish", "portuguese", "russian", ], {"default": "auto"}),
    "play"    : ("BOOLEAN", {"default": False}),
    "verbose" : ("BOOLEAN", {"default": True}),
    "speed": ("FLOAT", {
            "default": 1.0,
            "min": 0.5,
            "max": 2.0,
            "step": 0.1
        }),
    "temperature": ("FLOAT", {
            "default": 0.7,
            "min": 0.1,
            "max": 1.0,
            "step": 0.1
        }),
    "stream"  : ("BOOLEAN", {"default": False}),
    # 新增：join_audio 透传给底层generate_audio
    "join_audio": ("BOOLEAN", {
        "default": False,
        "tooltip": "False：按换行切分，输出 prefix_000.wav、prefix_001.wav…多分片，适合单词卡，对接批量ASR；True：拼接全部片段输出单个完整wav，适合故事连续朗读"
    }),
}


# =========================
# 🔹 TTS Base 生成节点
# =========================
class Qwen3TTSBaseMLXGenerate:
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
            },
            "optional": OPTION_SETTINGS
        }
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_path", "output_parent_dir")
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
        speed,
        lang_code,
        play,
        verbose,
        stream,
        temperature,
        join_audio,
    ):
        os.makedirs(output_dir, exist_ok=True)
        generate_audio(
            model=model,
            text=text,
            ref_audio=ref_audio,
            ref_text=ref_text,
            file_prefix=file_prefix,
            output_path=output_dir,
            speed = speed,
            lang_code = lang_code,
            play=play,
            verbose=verbose,
            stream=stream,
            temperature=temperature,
            join_audio=join_audio,
        )
        abs_output_dir = str(Path(output_dir).absolute())
        abs_parent_dir = str(Path(output_dir).absolute().parent)
        return (abs_output_dir, abs_parent_dir)


# =========================
# 🔹 TTS CustomVoice 生成节点
# =========================
class Qwen3TTSCustomVoiceMLXGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("QWEN3_TTS_MODEL",),
                "text": ("STRING", {"multiline": True}),
                "voice": (["serena", "vivian", "uncle_fu", "ryan", "aiden", "ono_anna", "sohee", "eric", "dylan"], {"default": "vivian"}),
                'instruct' : ("STRING", {"multiline": True, "default": ""}),
                "output_dir": ("STRING", {"default": "tts_output"}),
                "file_prefix": ("STRING", {"default": "tts"}),
            },
            "optional": OPTION_SETTINGS
        }
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_path", "output_parent_dir")
    FUNCTION = "generate_node"
    CATEGORY = "Qwen3-TTS-MLX"
    OUTPUT_NODE = True
    def generate_node(
        self,
        model,
        text,
        voice,
        output_dir,
        file_prefix,
        instruct,
        speed,
        lang_code,
        play,
        verbose,
        stream,
        temperature,
        join_audio,
    ):
        os.makedirs(output_dir, exist_ok=True)
        generate_audio(
            model=model,
            text=text,
            voice=voice,
            file_prefix=file_prefix,
            output_path=output_dir,
            instruct=instruct,
            speed=speed,
            lang_code=lang_code,
            play=play,
            verbose=verbose,
            stream=stream,
            temperature=temperature,
            join_audio=join_audio,
        )
        abs_output_dir = str(Path(output_dir).absolute())
        abs_parent_dir = str(Path(output_dir).absolute().parent)
        return (abs_output_dir, abs_parent_dir)


# =========================
# 🔹 TTS VoiceDesign 生成节点
# =========================
class Qwen3TTSVoiceDesignMLXGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("QWEN3_TTS_MODEL",),
                "text": ("STRING", {"multiline": True}),
                "instruct": ("STRING", {"multiline": True, "default": "A cheerful young female voice with high pitch"}),
                "output_dir": ("STRING", {"default": "tts_output"}),
                "file_prefix": ("STRING", {"default": "tts"}),
            },
            "optional": OPTION_SETTINGS
        }
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_path", "output_parent_dir")
    FUNCTION = "generate_node"
    CATEGORY = "Qwen3-TTS-MLX"
    OUTPUT_NODE = True
    def generate_node(
        self,
        model,
        text,
        instruct,
        output_dir,
        file_prefix,
        speed,
        lang_code,
        play,
        verbose,
        stream,
        temperature,
        join_audio,
    ):
        os.makedirs(output_dir, exist_ok=True)
        generate_audio(
            model=model,
            text=text,
            instruct=instruct,
            file_prefix=file_prefix,
            output_path=output_dir,
            speed=speed,
            lang_code=lang_code,
            play=play,
            verbose=verbose,
            stream=stream,
            temperature=temperature,
            join_audio=join_audio,
        )
        abs_output_dir = str(Path(output_dir).absolute())
        abs_parent_dir = str(Path(output_dir).absolute().parent)
        return (abs_output_dir, abs_parent_dir)

class YamlParse:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "yaml_str": ("STRING", {"multiline": True}),
            }
        }
    RETURN_TYPES = ("ANY",)
    RETURN_NAMES = ("data",)
    OUTPUT_IS_LIST = (True,)
    FUNCTION = "parse"
    CATEGORY = "Qwen3-TTS-MLX/Utils"
    def parse(self, yaml_str):
        data = yaml.safe_load(yaml_str)
        return (data,)


class DictGet:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dict_obj": ("ANY",),
                "key": ("STRING", {"default": "en_GB"}),
                "default": ("STRING", {"default": ""}),
            }
        }
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("value",)
    FUNCTION = "get"
    CATEGORY = "Qwen3-TTS-MLX/Utils"
    def get(self, dict_obj, key, default):
        if not isinstance(dict_obj, dict):
            return (default,)
        return (dict_obj.get(key, default),)


# =========================
# 🔹 注册
# =========================
NODE_CLASS_MAPPINGS = {
    "Qwen3TTSMLXLoader": Qwen3TTSMLXLoader,
    "Qwen3TTSBaseMLXGenerate": Qwen3TTSBaseMLXGenerate,
    "Qwen3TTSCustomVoiceMLXGenerate": Qwen3TTSCustomVoiceMLXGenerate,
    "Qwen3TTSVoiceDesignMLXGenerate": Qwen3TTSVoiceDesignMLXGenerate,
    "YamlParse": YamlParse,
    "DictGet": DictGet,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "Qwen3TTSMLXLoader": "Qwen3 TTS MLX Loader",
    "Qwen3TTSBaseMLXGenerate": "Qwen3 TTS MLX Generate Base",
    "Qwen3TTSCustomVoiceMLXGenerate": "Qwen3 TTS MLX Generate CustomVoice (9 speakers)",
    "Qwen3TTSVoiceDesignMLXGenerate": "Qwen3 TTS MLX Generate VoiceDesign (by instruct)",
    "YamlParse": "YAML Parse",
    "DictGet": "Dict Get",
}
