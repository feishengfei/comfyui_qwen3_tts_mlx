# Speaker‑Cast Schema（schema.md）
> 用途
> 1. 交给大模型作为生成多角色人设YAML的强制规约，用于Qwen3‑TTS‑MLX VoiceDesign 通路；
> 2. Wrapper解析节点以此做字段校验；
> 3. **此Schema产出的角色集合，用于Instruct音色生成（VoiceDesign），不是参考音频克隆通路，与原有`SpeakerDef / SpeakerListCombine`体系互相独立，不可混用**。
>
> 约定：YAML**顶层直接为数组**，无外层包裹字典。

## 数据模型：单角色对象 SpeakerCastItem
| 字段 | 类型 | 必填 | 约束 & 说明 |
|---|---|---|---|
| `name` | string | ✅ 必填 | **程序主键，同一份YAML文档内必须全局唯一**。短标识符，英文字母小写，建议下划线，禁止空格,禁示'-'连接。对话脚本`sp`字段引用该值；用于文件命名、内部索引。例：`chenjie`、`amy` |
| `full_name` | string | ⭕可选 | 人物完整正式名称，仅用于展示、备注，**不作为程序key，允许重复，允许为空**。例：`Amy Green` |
| `lang_code` | string | ✅ 必填 | 小写自然语言单词，直接透传给TTS底层`lang_code`参数。示例：`chinese` / `english` / `japanese` |
| `instruct` | string | ✅ 必填 | **VoiceDesign音色创作指令**，直接传入节点`instruct`入参；描述年龄、性别、声线、情绪、说话习惯，用于从零生成全新音色，不是微调已有音色。 需要用中文书写音色描述|
| `note` | string | ⭕可选 | 人类阅读备注，角色背景、使用场景；**不传入TTS，程序完全忽略此字段**。 |
| `speed` | float | ⭕可选 | 【预留扩展】该角色独立语速，0.5‑2.0；如不填则使用TTS全局speed参数 |
| `temperature` | float | ⭕可选 | 【预留扩展】该角色独立生成温度，0.1‑1.0；如不填使用全局temperature |

> 说明预留字段：`speed` / `temperature` 当前不强制，AI可以不输出；后续工作流可实现“每个角色拥有独立TTS超参”。


## 📜 instruct（音色指令）编写规范（给AI的强制约束，摘自Qwen3‑TTS VoiceDesign官方文档）
> 这一段会直接粘贴给LLM，约束AI生成`instruct`的质量。

### 核心原则
1. **要具体，拒绝模糊**：使用可感知的声学描述（清亮、低沉、语速偏快），禁止“好听、普通、很棒”这类主观无效形容词。
2. **多维度组合描述，不要单维度**：只写“女生”效果很差；必须组合多个声学维度。
3. **客观描述听觉特征，不要主观喜好**：写“音调偏高、充满活力”，不要写“我最喜欢的声音”。
4. **禁止模仿特定真人、明星、演员**：模型不支持定向模仿，同时存在版权风险。只描述声音特质，不要指定人物。
5. **简洁无冗余**：不要堆砌重复同义词，避免无意义的加强词（非常非常好听）。
6. **语言匹配角色母语**：角色`lang_code: chinese`优先用中文写instruct；`lang_code: english`优先用英文写instruct，提升音色一致性。

### 建议必须覆盖的描述维度（AI生成时尽量从中选取）
| 维度 | 可选描述词汇参考 |
|---|---|
| 性别 | male / female / neutral；男性、女性、中性 |
| 年龄段 | child(5‑12)、teenager(13‑18)、young adult(19‑35)、middle‑aged(36‑55)、senior(55+)；儿童、青少年、青年、中年、老年 |
| 音调 pitch | high / medium / low / slightly high / slightly low；高音、中音、低音、略高、略低 |
| 语速 speed | fast / medium / slow / slightly fast / slightly slow；快、中等、慢、稍快、稍慢 |
| 音色质感 texture | crisp清脆，husky沙哑，mellow圆润，resonant浑厚，sweet甜美 |
| 性格/情绪基线 | cheerful活泼，gentle温柔，calm沉稳，serious严肃，lively朝气 |
| 使用场景 | 小学生课本对话、故事旁白、日常聊天、课堂朗读 |

✅ 好示例（中文）：
> 青少年女生，音调略高，音色清亮活泼，语速中等，适合小学英语课本对话朗读。

❌ 坏示例（模糊无效）：
> 一个很好听的女孩子声音。

### 长度提示
本地mlx版本没有云端500字符硬限制，但仍然建议控制在 **150字以内**，避免指令过长带来的不稳定。



## YAML 完整示例（以PEP人教版六年级英语教材为例)

 设计多角色语音时需要考虑多角色之间在各个维度上的差异性！

```yaml
- name: chenjie
  full_name: Chen Jie
  lang_code: chinese
  instruct: 儿童，女性，中等音调，音色温润柔和，语速略偏慢，气质礼貌稳重，适合小学英语课本对话朗读。
  note: 中国女生，乐于助人，大方善交流
- name: wubinbin
  full_name: Wu Binbin
  lang_code: chinese
  instruct: 儿童，男性，中等音调，音色温润干净，语速平稳，说话内敛沉静，适合小学课本朗读。
  note: 中国男生，聪明勤奋有礼貌，爱思考记录
- name: zhangpeng
  full_name: Zhang Peng
  lang_code: chinese
  instruct: 儿童，男性，中等音调，音色饱满厚实，语速稍快，语气热忱外放，充满朝气，适合课堂对话。
  note: 中国男生，高大外向热心，热爱运动
- name: sarah
  full_name: Sarah Miller
  lang_code: english
  instruct: 儿童，女性，中等音调，音色醇厚温暖，语速略慢，心思细腻待人友善，适合小学生课本对话朗读。
  note: 外国女生，善于观察，乐于体会文化差异
- name: amy
  full_name: Amy Green
  lang_code: english
  instruct: 儿童，女性，中等音调，音色柔和克制，语速适中，性格安静内敛，腼腆踏实的小学生。
  note: 外国女生，文静踏实，略带腼腆
- name: mike
  full_name: Mike Black
  lang_code: english
  instruct: 儿童，男性，中等音调，音色醇厚清亮，语速稍快，好奇心强，性格随和的小学生。
  note: 外国男孩，好奇心旺盛，喜爱户外活动
- name: john
  full_name: John Baker
  lang_code: english
  instruct: 儿童，男性，中等音调，音色松弛醇厚，语速平稳适中，性格随和豁达的小学生。
  note: 外国男孩，性格随和包容
- name: oliver
  full_name: Oliver Smith
  lang_code: english
  instruct: 儿童，男性，中等音调，音色清亮温暖，语速适中轻快，热爱运动性格开朗的小学生。
  note: 澳大利亚男孩，热爱运动，性格开朗
- name: misswhite
  full_name: Miss White
  lang_code: english
  instruct: 青年，女性，中等音调，音色醇厚温柔，语速偏慢适中，语气耐心，带有鼓励感的教师声线。
  note: 英语老师，和蔼有耐心，善于鼓励学生
- name: mrjones
  full_name: Mr Jones
  lang_code: english
  instruct: 青年，男性，中等音调，音色明亮松弛，语速适中，风趣随和的美术教师声线。
  note: 美术老师，年轻风趣
- name: mryoung
  full_name: Mr Young
  lang_code: english
  instruct: 中年，男性，中等音调，音色浑厚温和，语速略慢，诙谐和善的音乐教师声线。
  note: 音乐老师，年长幽默
- name: robin
  full_name: Robin
  lang_code: english
  instruct: 儿童，中性，中等音调，音色顺滑带有轻微金属温润感，语速均匀平稳，语气认真诚恳的机器人。
  note: 智能机器人，能干严谨，会双语，怕水
- name: zip
  full_name: Zip
  lang_code: english
  instruct: 儿童，女性，中等音调，音色清脆灵动，语速偏快，机敏狡黠的卡通松鼠角色。
  note: 松鼠，机灵反应快，善于出主意
- name: zoom
  full_name: Zoom
  lang_code: english
  instruct: 儿童，男性，中等音调，音色厚实绵软，语速略慢，憨厚天真的卡通大熊角色。
  note: 大熊，憨厚贪吃，有点粗心，喜剧角色
```


## 给到AI的完整生成提示片段（可直接复制）
```
请严格输出YAML，遵循Speaker‑Cast Schema：
1. 输出顶层直接是数组，使用 `-` 列表项，不要外层{}包裹；
2. name 必须小写、无空格，整套YAML内部name不能重复；
3. lang_code 使用小写语言单词，例如 chinese / english；
4. instruct字段严格遵守Qwen3‑TTS VoiceDesign规范：
   - 禁止模糊形容词，禁止指定模仿明星真人；
   - 组合：性别+年龄+音调+音色质感+语速+性格+使用场景；
   - lang_code为chinese用中文写instruct；lang_code为english用英文写instruct；
5. 只输出YAML正文，不要markdown代码块标记以外多余解释文字；
6. name / lang_code / instruct为必填；full_name、note、speed、temperature为可选。
```
