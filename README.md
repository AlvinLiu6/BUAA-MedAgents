# BUAA-MedAgents · 多智能体健康管理与诊断系统

一个基于多智能体协作的个人健康管理 + 智能诊断系统。主界面提供九大健康模块（首页健康助手、个人信息、运动、营养、睡眠、心理、用药、健康档案、慢病管理）；诊疗系统采用 LLM A（诊断医师）与 LLM B（质控医师）的双重博弈机制，并能将诊断结果自动归档到健康档案。

---

## ⚠️ 免责声明

**本系统不构成医疗意见，不能替代专业医师的诊断和治疗建议。**

- 本系统仅作为辅助工具，用于学习和科研目的
- 系统输出的诊断和建议基于大语言模型推理，可能存在错误或遗漏
- **任何医疗决策必须由持证医师根据患者的实际情况独立判断**
- 对于紧急医疗情况，请立即前往医院或拨打急救电话
- 使用本系统导致的任何健康问题，开发者不承担任何责任

**使用本系统即代表你同意上述声明。**

---

## ✨ 核心功能

### 🏠 健康管理主门户（Portal）

主门户以左侧导航 + 右侧内容区的布局组织九个功能模块，所有数据本地持久化存储在 `~/.medagent/` 下。

#### 1. 智能健康助手（首页）
- 实时健康咨询聊天框，LLM 可读取所有模块的数据（个人信息、运动、睡眠、用药、心情、病史、慢病等）
- 会话历史在切换模块时保留，退出后清空
- 自动识别当天日期，重点关注近 1-2 周的数据，旧记录仅在用户主动询问或存在长期趋势时提及
- 首页还展示每日健康资讯与个性化提醒（服药提醒、运动打卡等）

#### 2. 个人信息
- 记录性别、年龄、身高、体重、过敏史、既往病史
- 信息自动同步至智能诊疗系统，无需重复输入

#### 3. 运动管理
- 制定个性化运动计划（由 LLM 根据个人信息生成）
- 每日打卡，支持日历视图查看打卡记录

#### 4. 营养管理
- 生成个性化膳食建议
- 依据身体数据（BMI、过敏）个性化调整

#### 5. 睡眠管理
- 记录每晚的睡眠时长与质量
- 日历可视化，支持记录删除

#### 6. 心理健康
- 每日心情打卡（1-5 分 + 备注）
- 独立的心理健康聊天助手，会话记录跨模块保留
- 心情历史以点阵概览 + 详细列表呈现，支持逐条删除

#### 7. 用药管理
- 录入常用药品（药名、剂量、服药时间、频次）
- 每日服药打卡
- 自动识别未打卡的药品并在首页提醒
- **与慢病管理联动**：从慢病同步过来的药品会带有橙色标签，展示所属慢病

#### 8. 健康档案
- 手动添加病历记录（日期、症状、诊断、治疗、医院、备注）
- **自动归档**：智能诊疗系统给出最终诊断后，会自动将其写入健康档案
- 支持编辑、删除，卡片式展示

#### 9. 慢病管理
- 管理慢性疾病：病症名称、确诊日期、关联用药、指标监测、备注
- **关联用药子表**：逐条添加（药名 / 剂量 / 频次），支持逐条删除
- **指标监测子表**：逐条添加（指标名 / 目标值 / 检测频次）
- 保存慢病时自动把关联用药同步到用药管理全局列表（带 `chronic_id` 回溯源头）

### 🩺 智能诊疗子系统（Diagnosis）

独立端口运行（默认 7861），从主门户的「智能诊疗」入口进入。

#### 多源数据融合
- **医学影像分析**：通过 XrayGLM 自动分析胸部 X 光片
- **化验单解读**：使用视觉 LLM（Qwen-VL）提取并分析化验指标
- **病历信息提取**：自动识别既往诊断、用药、过敏史等
- **其他图片识别**：对患者上传的其他医学文档进行内容识别

#### 双重博弈机制
- **LLM A（诊断医师）**：基于主诉、检查数据进行综合分析
- **LLM B（质控医师）**：从安全性与逻辑性两个维度审核 A 的诊断
- **最多 3 轮博弈**：未通过审核则 A 据反馈再诊断，直到达成共识或达上限

#### 交互式追问
- 信息不足时，LLM A 可向患者追问（标注「重要」的问题诊断必需）
- 所有「重要」问题回答后必须直接给出诊断，不再反复追问
- 也可向子 Agent 请求更细粒度分析（如要求影像 Agent 重点看右下肺野）

#### 后续咨询 & 自动归档
- 诊断完成后可继续提问，医生基于已有结论针对性作答
- 最终诊断自动写入主门户的「健康档案」

---

## 🏗️ 项目结构

```
MedAgent/
├── config.py                    # Pydantic 配置管理
├── main.py                      # 应用入口（双端口：门户 7860 / 诊疗 7861）
├── requirements.txt
├── .env                         # 环境变量（gitignore）
│
├── models/                      # Pydantic v2 数据模型
│   ├── patient.py
│   ├── agent_output.py
│   ├── diagnosis.py
│   └── review.py
│
├── agents/                      # 各专业 Agent
│   ├── base.py
│   ├── triage.py                # 分诊：文件分类、意图识别
│   ├── image_agent.py           # 影像 Agent（调用 XrayGLM）
│   ├── lab_agent.py             # 化验 Agent（Qwen-VL）
│   ├── record_agent.py          # 病历 Agent
│   ├── diagnosis_agent.py       # LLM A：诊断
│   └── review_agent.py          # LLM B：审核
│
├── orchestrator/
│   └── pipeline.py              # 流水线编排
│
├── llm/
│   └── openai_client.py         # OpenAI 兼容客户端（支持 DeepSeek / DashScope）
│
├── xrayglm/                     # XrayGLM 集成
│   ├── interface.py             # Protocol 抽象
│   ├── mock_model.py            # Mock（开发）
│   └── local_model.py           # 本地部署
│
├── ui/                          # 前端
│   ├── portal.py                # 主门户（九大模块）
│   ├── app.py                   # 诊疗子系统
│   ├── profile_store.py         # 个人信息持久化
│   └── health_store.py          # 健康数据持久化（运动/睡眠/用药/病历/慢病…）
│
└── prompts/                     # 外置提示词
    ├── triage.txt
    ├── diagnosis.txt
    ├── review.txt
    ├── lab_extraction.txt
    └── record_extraction.txt
```

### 数据存储

所有个人数据保存在用户目录下，不上传任何云端：

```
~/.medagent/
├── patient_profile.json    # 性别、年龄、身高、体重、过敏、既往史
└── health_data.json        # 运动计划、打卡、睡眠、营养、心情、用药、
                            # 服药打卡、病历、慢病
```

---

## 🚀 快速开始

### 前置条件
- Python 3.8+
- 有效的 OpenAI 兼容 API 密钥（DeepSeek、DashScope 等）
- （可选）NVIDIA GPU 用于本地 XrayGLM 部署

### 安装

```bash
git clone https://github.com/AlvinLiu6/BUAA-MedAgents.git
cd BUAA-MedAgents
pip install -r requirements.txt
```

### 配置

创建 `.env`：

```ini
# 主 LLM（诊断、审核、健康助手）
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_MODEL=deepseek-reasoner
OPENAI_BASE_URL=https://api.deepseek.com/v1

# 视觉 LLM（化验单、病历、其他图片识别）
VISION_API_KEY=your_dashscope_api_key
VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen-vl-plus

# XrayGLM 配置
XRAYGLM_MODE=mock                # mock | local
XRAYGLM_CHECKPOINT_PATH=./checkpoints/XrayGLM
XRAYGLM_PROMPT=详细描述这张胸部X光片的诊断结果

# 诊断参数
MAX_REVIEW_ROUNDS=3              # LLM A/B 最大博弈轮数
LOG_LEVEL=INFO
```

### 运行

```bash
python main.py
```

启动后：
- 主门户：<http://127.0.0.1:7860>
- 诊疗子系统：<http://127.0.0.1:7861>（由主门户内嵌进入）

---

## 💻 使用流程

### 日常健康管理
1. 在「个人信息」完善基础数据（性别、年龄、身高、体重、过敏史）
2. 在「运动 / 营养」生成个性化计划；每日在运动模块打卡
3. 睡眠、心情、用药各模块记录当日情况
4. 慢病患者在「慢病管理」录入病症、关联用药、指标；保存后用药会自动出现在用药管理中
5. 随时在首页咨询健康助手，助手能读取所有数据给出针对性建议

### 智能诊疗
1. 主门户点击「🩺 智能诊疗」进入诊疗系统
2. 左侧补充或确认患者信息，中间输入主诉并上传医学文件（X 光片、化验单、病历…）
3. 点击「发送」，系统依次执行：分诊 → 并行数据提取 → LLM A 诊断 → LLM B 审核，必要时循环
4. LLM A 若认为信息不足会追问；「重要」问题全部回答后必出诊断
5. 结论含：诊断、置信度、证据依据、治疗建议；完整会诊记录可展开查看
6. 诊断结果自动写入「健康档案」
7. 可继续在输入框追问；或点「新建会诊」清空历史

---

## 🔧 配置说明

### LLM 选项

**主 LLM（诊断、审核、健康助手）**
- **DeepSeek**（推荐，推理能力强）
  ```
  OPENAI_BASE_URL=https://api.deepseek.com/v1
  OPENAI_MODEL=deepseek-reasoner
  ```
- **OpenAI GPT-4o**
  ```
  OPENAI_BASE_URL=https://api.openai.com/v1
  OPENAI_MODEL=gpt-4o
  ```

**视觉 LLM（图像识别）**
- **Qwen-VL**（推荐，阿里云 DashScope）
  ```
  VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
  VISION_MODEL=qwen-vl-plus
  ```

### XrayGLM 部署

**开发模式（Mock）** — 返回虚拟结果，便于无 GPU 测试：
```
XRAYGLM_MODE=mock
```

**本地部署（Local）** — 需 14 GB+ 显存：
```
XRAYGLM_MODE=local
XRAYGLM_CHECKPOINT_PATH=./checkpoints/XrayGLM
```

---

## 📊 诊断流程详解

### 1. 分诊（Triage）
- 分析患者主诉，识别诊断意图
- 对上传文件进行分类（X 光 / 化验单 / 病历 / 其他图片）
- 合并患者基本信息与过敏史

### 2. 并行数据提取（Extraction）
- **ImageAgent**：XrayGLM 分析 X 光片
- **LabAgent**：Qwen-VL 识别化验单，提取指标
- **RecordAgent**：提取病历关键信息
- **Vision LLM**：其他医学图片的内容提取

### 3. 诊断（LLM A）
基于主诉 + 所有检查数据 + 既往审核反馈（如有）进行综合推理。信息不足时可：
1. 向患者追问（「重要」问题诊断必需）
2. 向子 Agent 请求补充分析

### 4. 审核（LLM B）
- **安全性**：过敏冲突、药物相互作用、剂量途径
- **逻辑性**：证据是否支持、是否遗漏异常、推理是否自洽

审核不通过时回到第 3 步，最多 3 轮。通过后进入最终归档。

### 5. 自动归档
诊断结果（诊断、置信度、治疗建议）自动写入「健康档案」，可在主门户查看和编辑。

---

## 🔌 API 集成示例

```python
from llm import LLMClient
from config import Settings

settings = Settings()

# 主 LLM
llm = LLMClient(settings)

# 视觉 LLM
vision_llm = LLMClient(settings, use_vision_model=True)

response = await llm.chat(messages)
json_response = await llm.chat_json(messages)
image_text = await vision_llm.chat_with_image(
    system_prompt="...",
    user_text="...",
    image_path="...",
)
```

---

## 📝 提示词工程

所有提示词外置于 `prompts/`，便于迭代：

- **diagnosis.txt**：LLM A 诊断指令（含追问规范、「重要」问题回答后必出诊断的硬约束）
- **review.txt**：LLM B 审核清单
- **triage.txt** / **lab_extraction.txt** / **record_extraction.txt**：各子 Agent 指令

---

## 🎯 关键设计

- **全异步**：所有 Agent 异步执行，子 Agent 用 `asyncio.gather` 并行
- **流式 UI**：Gradio 实时推送诊断进度
- **Context 持久化**：用户补充信息后续对话不丢失
- **双重质控**：LLM A/B 博弈确保诊断严谨
- **模块解耦**：Agent / XrayGLM / LLM 客户端可独立替换
- **本地优先**：所有健康数据存储在本地，隐私可控
- **慢病 ↔ 用药联动**：慢病管理中的药品自动同步到全局用药列表

---

## 📚 XrayGLM 引用

本项目使用 **XrayGLM** 进行胸部 X 光片分析。

**论文**
- Wang, R., et al. (2023). XrayGLM: Chest X-ray Interpretation with Generalist Large Language Models. [arXiv:2305.11581](https://arxiv.org/abs/2305.11581)

**模型权重**
- GitHub: [WangRongsheng/XrayGLM](https://github.com/WangRongsheng/XrayGLM)
- HuggingFace: [WangRongsheng/XrayGLM](https://huggingface.co/WangRongsheng/XrayGLM)

### 引用格式

```bibtex
@article{wang2023xrayglm,
  title={XrayGLM: Chest X-ray Interpretation with Generalist Large Language Models},
  author={Wang, Rongsheng and others},
  journal={arXiv preprint arXiv:2305.11581},
  year={2023}
}
```

---

## ⚡ 常见问题

**Q: 健康数据存储在哪里？会上传到云端吗？**
A: 所有数据存储在本地 `~/.medagent/` 下，不会上传到任何云端。

**Q: 为什么诊断结果与我的医生不同？**
A: 本系统是 AI 辅助工具，诊断可能受限于 LLM 的知识和输入数据的质量。请始终咨询持证医师。

**Q: 支持哪些医学影像格式？**
A: PNG、JPG、JPEG、BMP、TIFF。其他格式请转换后上传。

**Q: 诊断自动归档到健康档案的内容能修改吗？**
A: 可以。在「健康档案」模块点击任一记录的编辑按钮即可修改。

**Q: 慢病里的用药和「用药管理」里的是同一份吗？**
A: 保存慢病时会把关联用药同步到「用药管理」全局列表，并打上橙色标签标注所属慢病；用药打卡统一在「用药管理」进行。

**Q: 可以批量处理患者吗？**
A: 当前版本为单用户设计。如有需求，欢迎开 Issue 讨论。

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献

欢迎提交 Issue 或 Pull Request！

---

**最后提醒**：本系统仅供学习和研究使用，任何医疗决策必须由专业医师做出。祝你健康！💊
