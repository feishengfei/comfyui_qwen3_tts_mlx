import os
import wave
import yaml
import numpy as np
from pathlib import Path
from inspect import cleandoc
from mlx_audio.tts.generate import generate_audio
from mlx_audio.tts.utils import load_model

MAX_SPEAKER_INPUTS = 50
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
    "lang_code": ("STRING", {"default": "auto"}),
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
    # 新增trigger：仅用于DAG执行依赖，业务逻辑不消费此参数
    "trigger": ("*", {"default": None, "tooltip":"仅做执行依赖接线，不参与生成逻辑，接上游节点输出实现串行排队"}),
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
        trigger=None,
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
        trigger=None,
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
        trigger=None,
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

class YamlParseRaw:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "yaml_str": ("STRING", {"multiline": True}),
            }
        }
    RETURN_TYPES = ("ANY",)
    RETURN_NAMES = ("data",)
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

class ListGet:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list_data": ("ANY",),
                "index": ("INT", {"default":0, "min":-10000}),
            },
            "optional": {
                "default": ("ANY",),
            }
        }
    RETURN_TYPES = ("ANY",)
    RETURN_NAMES = ("item",)
    FUNCTION = "get_item"
    CATEGORY = "Qwen3-TTS-MLX/Utils"
    def get_item(self, list_data, index, default=None):
        if not isinstance(list_data, list):
            print(f'felix not isinstance:{list}')
            return (default,)
        try:
            return (list_data[index],)
        except (IndexError, TypeError):
            return (default,)

class GetListLength:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "list_data": ("ANY",),
            }
        }
    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("length",)
    FUNCTION = "get_len"
    CATEGORY = "Qwen3-TTS-MLX/Utils"
    def get_len(self, list_data):
        if not isinstance(list_data, list):
            return (0,)
        return (len(list_data),)

def make_silence_wav(sample_rate: int, duration_sec: float, out_path: Path):
    """生成一段单声道静音wav，用于gap停顿"""
    n_samples = int(sample_rate * duration_sec)
    silence = np.zeros(n_samples, dtype=np.float32)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes((silence * 32767).astype(np.int16).tobytes())

def concat_wav_files(file_list: list[Path], output_path: Path):
    """按顺序拼接一组单声道wav文件；要求全部采样率一致"""
    if not file_list:
        raise ValueError("concat_wav_files: empty file list")
    data_frames = []
    sr = None
    for fpath in file_list:
        with wave.open(str(fpath), "rb") as wf:
            if sr is None:
                sr = wf.getframerate()
            else:
                if wf.getframerate() != sr:
                    raise RuntimeError(f"Sample rate mismatch in file: {fpath}")
            frames = wf.readframes(wf.getnframes())
            data_frames.append(frames)
    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for fr in data_frames:
            wf.writeframes(fr)


# =========================
# 🔹 SpeakerDef：单角色定义节点
# =========================
class SpeakerDef:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "name": ("STRING", {"default": "child_girl", "tooltip": "角色标识，匹配pd内sp字段"}),
                "ref_audio": ("STRING", {"default": "", "tooltip": "参考音频文件路径"}),
                "ref_text": ("STRING", {"multiline": True, "default": "", "tooltip": "参考音频对应文本"}),
                "lang_code": ("STRING", {"default": "auto", "tooltip": "该角色使用的语言码"}),
            }
        }
    RETURN_TYPES = ("*",)
    RETURN_NAMES = ("speaker_item",)
    FUNCTION = "emit"
    CATEGORY = "Qwen3-TTS-MLX/Speaker"
    def emit(self, name, ref_audio, ref_text, lang_code):
        item = {
            "name": name,
            "ref_audio": ref_audio,
            "ref_text": ref_text,
            "lang_code": lang_code
        }
        return (item,)

# =========================
# 🔹 SpeakerListCombine：预生成最多50路sp输入，参考JkForEachOpen实现，全版本ComfyUI兼容
# =========================
class SpeakerListCombine:
    @classmethod
    def INPUT_TYPES(cls):
        optional = {}
        for k in range(MAX_SPEAKER_INPUTS):
            optional[f"sp{k}"] = ("*", {})
        return {
            "optional": optional
        }
    RETURN_TYPES = ("*", "STRING")
    RETURN_NAMES = ("speaker_bundle", "speaker_map_yaml")
    FUNCTION = "combine"
    CATEGORY = "Qwen3-TTS-MLX/Speaker"
    def combine(self, **kwargs):
        bundle = []
        for k in range(MAX_SPEAKER_INPUTS):
            key = f"sp{k}"
            val = kwargs.get(key)
            if val is not None:
                bundle.append(val)
        # build map: later item overwrite earlier by name
        sp_map = {}
        for sp_item in bundle:
            if isinstance(sp_item, dict) and "name" in sp_item:
                sp_map[sp_item["name"]] = sp_item
        # dump yaml for debug preview，保留unicode不转义，不排序key
        yaml_str = yaml.safe_dump(sp_map, sort_keys=False, allow_unicode=True, indent=2)
        return (bundle, yaml_str)

# =========================
# 🔹 Qwen3TTSBaseMLXDialogGenerate 对话主生成节点
# =========================
class Qwen3TTSBaseMLXDialogGenerate:
    @classmethod
    def INPUT_TYPES(cls):
        # filter unused keys from global OPTION_SETTINGS
        filtered_opts = {
            k: v for k, v in OPTION_SETTINGS.items()
            if k not in {"join_audio", "file_prefix",  "lang_code"}
        }
        return {
            "required": {
                "model": ("QWEN3_TTS_MODEL",),
                "pd": ("*",),
                "speaker_bundle": ("*",),
                "file_prefix": ("STRING", {"default": "dialog"}),
                "output_dir": ("STRING", {"default": "tts_output"}),
            },
            "optional": {
                "global_gap": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 5.0, "step": 0.1}),
                **filtered_opts
            }
        }
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("output_wav_path", "output_parent_dir")
    FUNCTION = "dialog_generate"
    CATEGORY = "Qwen3-TTS-MLX/Dialog"
    OUTPUT_NODE = True
    def dialog_generate(
        self,
        model,
        pd,
        speaker_bundle,
        file_prefix,
        output_dir,
        global_gap,
        trigger=None,
        **kwargs
    ):
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        final_wav = out_dir / f"{file_prefix}.wav"
        tmp_dir = out_dir / ".tmp_dialog_audio"
        tmp_dir.mkdir(exist_ok=True)
        try:
            # 1. validate speaker_bundle
            if not isinstance(speaker_bundle, list):
                raise ValueError(f"speaker_bundle expected list, got {type(speaker_bundle)}")
            # build sp_map & pre‑check each speaker definition
            sp_map = {}
            for sp_item in speaker_bundle:
                if not isinstance(sp_item, dict) or "name" not in sp_item:
                    continue
                name = sp_item["name"]
                ra = Path(sp_item.get("ref_audio", ""))
                rt = sp_item.get("ref_text", "").strip()
                if not ra.exists():
                    raise FileNotFoundError(f"Speaker[{name}] ref_audio not found: {ra}")
                if not rt:
                    raise ValueError(f"Speaker[{name}] ref_text is empty after trim")
                sp_map[name] = sp_item
            # 2. normalize pd: dict -> single‑item list
            if isinstance(pd, dict):
                dialog_list = [pd]
            elif isinstance(pd, list):
                dialog_list = pd
            else:
                print(f"[Qwen3‑Dialog] pd invalid type {type(pd)}, empty dialog list")
                dialog_list = []
            concat_list = []
            # 3. iterate dialog items
            for idx, item in enumerate(dialog_list):
                txt = item.get("txt", "").strip()
                sp_key = item.get("sp")
                item_gap = float(item.get("gap", global_gap))
                item_gap = max(0.0, item_gap)
                if not txt or not sp_key:
                    print(f"[Qwen3‑Dialog] skip idx={idx}: missing txt or sp")
                    continue
                if sp_key not in sp_map:
                    print(f"[Qwen3‑Dialog] skip idx={idx}: sp key '{sp_key}' not in speaker map")
                    continue
                speaker_cfg = sp_map[sp_key]
                seg_path = tmp_dir / f"seg_{idx}.wav"
                generate_audio(
                    model=model,
                    text=txt,
                    ref_audio=speaker_cfg["ref_audio"],
                    ref_text=speaker_cfg["ref_text"],
                    lang_code=speaker_cfg["lang_code"],
                    output_path=str(tmp_dir),
                    file_prefix=f"seg_{idx}",
                    join_audio=True, # 强制！禁止底层按换行拆分、禁止追加_000后缀
                    **kwargs
                )
                concat_list.append(seg_path)
                if item_gap > 1e-6:
                    gap_path = tmp_dir / f"gap_{idx}.wav"
                    with wave.open(str(seg_path), "rb") as wf:
                        sr = wf.getframerate()
                    make_silence_wav(sr, item_gap, gap_path)
                    concat_list.append(gap_path)
            # 4. defense: all items skipped → output global_gap silence wav
            if not concat_list:
                gap_only_path = tmp_dir / "_defense_silence.wav"
                sr_fallback = 24000
                make_silence_wav(sr_fallback, global_gap, gap_only_path)
                concat_list.append(gap_only_path)
            concat_wav_files(concat_list, final_wav)
            abs_wav = str(final_wav.absolute())
            abs_parent = str(out_dir.absolute())
            return (abs_wav, abs_parent)
        finally:
            # clean temp files whatever success/fail
            for f in tmp_dir.glob("*.wav"):
                try:
                    f.unlink()
                except Exception:
                    pass
            try:
                tmp_dir.rmdir()
            except Exception:
                pass



# =========================
# 🔹 注册
# =========================
NODE_CLASS_MAPPINGS = {
    "Qwen3TTSMLXLoader": Qwen3TTSMLXLoader,
    "Qwen3TTSBaseMLXGenerate": Qwen3TTSBaseMLXGenerate,
    "Qwen3TTSCustomVoiceMLXGenerate": Qwen3TTSCustomVoiceMLXGenerate,
    "Qwen3TTSVoiceDesignMLXGenerate": Qwen3TTSVoiceDesignMLXGenerate,
    "YamlParseRaw": YamlParseRaw,
    "DictGet": DictGet,
    "ListGet": ListGet,
    "GetListLength": GetListLength,

    # multi user Dialog
    "SpeakerDef": SpeakerDef,
    "SpeakerListCombine": SpeakerListCombine,
    "Qwen3TTSBaseMLXDialogGenerate": Qwen3TTSBaseMLXDialogGenerate,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Qwen3TTSMLXLoader": "Qwen3 TTS MLX Loader",
    "Qwen3TTSBaseMLXGenerate": "Qwen3 TTS MLX Generate Base",
    "Qwen3TTSCustomVoiceMLXGenerate": "Qwen3 TTS MLX Generate CustomVoice (9 speakers)",
    "Qwen3TTSVoiceDesignMLXGenerate": "Qwen3 TTS MLX Generate VoiceDesign (by instruct)",
    "YamlParseRaw": "YAML Parse Raw(不展开Batch)",
    "DictGet": "Dict Get",
    "ListGet": "List Get",
    "GetListLength": "Get List Length",

    # multi user Dialog
    "SpeakerDef": "Speaker Def (Base‑TTS reference voice)",
    "SpeakerListCombine": "Speaker List Combine",
    "Qwen3TTSBaseMLXDialogGenerate": "Qwen3‑TTS Base MLX Dialog Generate (pd dict/list)",
}
