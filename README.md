# BUAA-MedAgents · 多智能体医疗诊断辅助系统

一个基于多智能体协作的医疗诊断辅助系统。通过 LLM A（诊断医师）与 LLM B（质控医师）的双重博弈机制，为用户提供专业的诊断推理和证据支撑。支持医学影像分析、化验单解读、病历提取与交互式追问。

**项目来自北京航空航天大学（BUAA）。**

## ⚠️ 免责声明

**本系统不构成医疗意见，不能替代专业医师的诊断和治疗建议。**

- 本系统仅作为辅助诊断工具，用于学习和科研目的
- 系统输出的诊断结论基于大语言模型推理，可能存在错误或遗漏
- **任何医疗决策必须由持证医师根据患者的实际情况独立判断**
- 对于紧急医疗情况，请立即前往医院或拨打急救电话
- 使用本系统导致的任何健康问题，开发者不承担任何责任

**使用本系统即代表你同意上述声明。**

---

## ✨ 核心功能

### 1. 多源数据融合
- **医学影像分析**：通过 XrayGLM 自动分析胸部 X 光片
- **化验单解读**：使用视觉 LLM（Qwen-VL）提取并分析化验指标
- **病历信息提取**：自动识别既往诊断、用药、过敏史等关键信息
- **其他图片识别**：对患者上传的其他医学文档进行内容识别

### 2. 智能诊断推理
- **LLM A（诊断医师）**：基于患者主诉、检查数据进行综合分析，可主动向患者追问或请求子Agent补充分析
- **LLM B（质控医师）**：从安全性和逻辑性两个维度审核 LLM A 的诊断，确保方案的可靠性
- **博弈机制**：两个 LLM 最多进行 3 轮的诊断-审核循环，最终给出经过严格质控的诊断结论

### 3. 交互式咨询
- **补充信息采集**：LLM A 可按需向患者追问症状细节、病史等关键信息
- **后续咨询**：诊断完成后，患者可继续提问，医生给出针对性解答
- **新建咨询**：支持清空历史记录，开始新的诊断流程

### 4. 个性化患者管理
- 记录患者的性别、年龄、身高、体重
- 管理过敏史和既往病史
- 自动在诊断时融入患者基本信息

---

## 🏗️ 项目结构

```
MedAgent/
├── config.py                    # Pydantic 配置管理（API key、模型参数等）
├── main.py                      # 应用入口
├── requirements.txt             # 项目依赖
├── .env                         # 环境变量配置（gitignore）
├── .gitignore                   # Git 忽略文件
│
├── models/                      # 数据模型（Pydantic v2）
│   ├── patient.py              # 患者信息、上传文件
│   ├── agent_output.py         # 各子Agent的输出模型
│   ├── diagnosis.py            # 诊断结果模型
│   └── review.py               # 审核结果模型
│
├── agents/                      # 多个专业Agent
│   ├── base.py                 # Agent 基类
│   ├── triage.py               # 分诊Agent：文件分类、意图识别
│   ├── image_agent.py          # 影像Agent：调用 XrayGLM 分析 X 光
│   ├── lab_agent.py            # 化验Agent：使用 Qwen-VL 提取化验单
│   ├── record_agent.py         # 病历Agent：提取病历关键信息
│   ├── diagnosis_agent.py      # LLM A：综合诊断推理
│   └── review_agent.py         # LLM B：质量审核
│
├── orchestrator/
│   └── pipeline.py             # 流水线编排：协调各Agent执行顺序、数据流
│
├── llm/
│   └── openai_client.py        # OpenAI 兼容 API 客户端（支持 DeepSeek、DashScope）
│
├── xrayglm/                     # XrayGLM 集成层
│   ├── interface.py            # Protocol 抽象接口
│   ├── mock_model.py           # Mock 实现（开发测试）
│   └── local_model.py          # 本地部署实现
│
├── ui/
│   └── app.py                  # Gradio 6.x 网页界面（3列布局）
│
└── prompts/                     # LLM 提示词
    ├── triage.txt              # 分诊提示词
    ├── diagnosis.txt           # LLM A 诊断提示词
    ├── review.txt              # LLM B 审核提示词
    ├── lab_extraction.txt      # 化验提取提示词
    └── record_extraction.txt   # 病历提取提示词
```

---

## 🚀 快速开始

### 前置条件
- Python 3.8+
- 有效的 OpenAI 兼容 API 密钥（DeepSeek、DashScope 等）
- （可选）NVIDIA GPU 用于本地 XrayGLM 部署

### 安装

```bash
# 克隆仓库
git clone https://github.com/your-username/BUAA-MedAgents.git
cd BUAA-MedAgents

# 安装依赖
pip install -r requirements.txt
```

### 配置

复制 `.env.example` 到 `.env` 并填入你的 API 密钥：

```bash
cp .env.example .env
```

编辑 `.env`：
```
# 主 LLM（诊断、审核）
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_MODEL=deepseek-reasoner
OPENAI_BASE_URL=https://api.deepseek.com/v1

# 视觉 LLM（化验单、病历、其他图片识别）
VISION_API_KEY=your_dashscope_api_key
VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
VISION_MODEL=qwen-vl-plus

# XrayGLM 配置
XRAYGLM_MODE=mock          # "mock" 或 "local"
XRAYGLM_CHECKPOINT_PATH=./checkpoints/XrayGLM
XRAYGLM_PROMPT=详细描述这张胸部X光片的诊断结果

# 诊断参数
MAX_REVIEW_ROUNDS=3        # LLM A/B 的最大博弈轮数
LOG_LEVEL=INFO
```

### 运行

```bash
python main.py
```

打开浏览器访问 `http://127.0.0.1:7860`

---

## 💻 使用流程

1. **输入患者信息**
   - 在左侧边栏填入患者基本信息（性别、年龄、身高、体重、过敏史、既往病史）
   - 在中间面板输入主诉（症状描述）

2. **上传医学文件**
   - 上传 X 光片、化验单、病历等医学文件
   - 为每个文件选择合适的标签（或由系统自动分类）

3. **提交诊断请求**
   - 点击"发送"按钮
   - 系统依次执行：
     - **分诊**：文件分类、主诉分析
     - **数据提取**：各子Agent 并行处理（影像、化验、病历）
     - **LLM A 诊断**：基于提取结果进行诊断推理
     - **LLM B 审核**：质量控制
     - 必要时重复诊断-审核循环

4. **查看诊断结果**
   - 右侧面板显示实时会诊过程
   - 最终报告包含：诊断结论、置信度、证据依据、治疗建议
   - 可点击"推理详情"查看 LLM A/B 的完整对话记录

5. **后续咨询**
   - 诊断完成后，可继续在输入框提问
   - 医生会基于诊断结果给出针对性回答

6. **开始新诊断**
   - 点击"新建会诊"清空历史，开始新的诊断

---

## 🔧 配置说明

### LLM 选项

**主 LLM（诊断和审核）**
- **DeepSeek**（推荐）：`openai-reasoner` 具有强大的推理能力
  ```
  OPENAI_BASE_URL=https://api.deepseek.com/v1
  OPENAI_MODEL=deepseek-reasoner
  ```
- **OpenAI**：GPT-4o
  ```
  OPENAI_BASE_URL=https://api.openai.com/v1
  OPENAI_MODEL=gpt-4o
  ```

**视觉 LLM（图像识别）**
- **Qwen-VL**（推荐）：阿里云 DashScope
  ```
  VISION_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
  VISION_MODEL=qwen-vl-plus
  ```

### XrayGLM 部署

**开发模式（Mock）**
```
XRAYGLM_MODE=mock
```
返回虚拟的 X 光分析结果，用于测试。

**本地部署（Local）**
需要 14GB+ 显存：
```
XRAYGLM_MODE=local
```
详见 [XrayGLM 部署指南](#xrayglm-部署指南)

---

## 📊 诊断流程详解

### 分诊阶段（Triage）
- 分析患者主诉，识别诊断意图
- 对上传文件进行分类（X光、化验单、病历、其他图片）
- 合并患者的过敏史信息

### 数据提取阶段（Extraction）
并行执行以下任务：
- **ImageAgent**：调用 XrayGLM 分析 X 光片
- **LabAgent**：使用 Qwen-VL 识别化验单、提取指标
- **RecordAgent**：提取病历的关键信息（既往诊断、用药、过敏等）
- **Vision LLM**：对其他上传的医学图片进行内容提取

### 诊断阶段（Diagnosis - LLM A）
LLM A 基于以下信息进行综合诊断：
- 患者主诉和基本信息
- 所有提取的检查数据
- 之前的审核反馈（如果有驳回）

如果信息不足，LLM A 可以：
1. **向患者追问**（如：症状持续时间、加重因素等）
2. **请求子Agent补充分析**（如：要求影像Agent重点分析某个区域）

### 审核阶段（Review - LLM B）
LLM B 从两个维度进行严格审核：

**安全性审核**
- 检查治疗方案是否与患者过敏史冲突
- 验证药物相互作用和禁忌
- 评估用药剂量和给药途径的安全性

**逻辑性审核**
- 诊断结论是否有充分的检查证据支持
- 是否遗漏了重要的异常发现
- 推理过程是否逻辑自洽

如果审核不通过，LLM A 会进入下一轮修正（最多 3 轮）。

---

## 🔌 API 集成

系统使用 OpenAI 兼容 API，支持多种服务商：

```python
from llm import LLMClient
from config import Settings

settings = Settings()

# 主 LLM（推理）
llm = LLMClient(settings)

# 视觉 LLM（图像识别）
vision_llm = LLMClient(settings, use_vision_model=True)

# 使用
response = await llm.chat(messages)
json_response = await llm.chat_json(messages)  # 返回 JSON
image_text = await vision_llm.chat_with_image(
    system_prompt="...",
    user_text="...",
    image_path="..."
)
```

---

## 📝 提示词工程

系统使用外置的提示词文件（在 `prompts/` 目录），便于迭代优化：

- **diagnosis.txt**：LLM A 的诊断指令，包含信息不足时的追问规范
- **review.txt**：LLM B 的审核标准清单
- **lab_extraction.txt** 等：各子Agent的提取指令

修改这些文件可以调整模型的行为，无需重新编译代码。

---

## 🎯 关键设计

- **全异步**：所有 Agent 异步执行，提高吞吐量
- **流式 UI**：使用 Gradio 实时更新诊断进度
- **Context 持久化**：支持用户补充信息后续诊断，不丢失前面的推理
- **双重质控**：LLM A/B 博弈确保诊断的严谨性
- **模块化**：Agent 独立，便于替换或扩展（如集成新的 LLM）

---

## 📚 XrayGLM 引用

本项目使用 **XrayGLM** 进行胸部 X 光片分析。

**论文**
- Wang, R., et al. (2023). XrayGLM: Chest X-ray Interpretation with Generalist Large Language Models. [arXiv:2305.11581](https://arxiv.org/abs/2305.11581)

**模型权重**
- GitHub: [WangRongsheng/XrayGLM](https://github.com/WangRongsheng/XrayGLM)
- HuggingFace: [WangRongsheng/XrayGLM](https://huggingface.co/WangRongsheng/XrayGLM)

**部署说明**
详见项目根目录的部署文档。

### 引用格式

如果你在科研或临床决策中使用了本系统的 XrayGLM 分析结果，请引用：

```bibtex
@article{wang2023xrayglm,
  title={XrayGLM: Chest X-ray Interpretation with Generalist Large Language Models},
  author={Wang, Rongsheng and others},
  journal={arXiv preprint arXiv:2305.11581},
  year={2023}
}
```

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🤝 贡献

欢迎提交 Issue 或 Pull Request！

---

## ⚡ 常见问题

**Q: 为什么诊断结果与我的医生不同？**  
A: 本系统是 AI 辅助工具，诊断可能受限于 LLM 的知识和输入数据的质量。请始终咨询持证医师。

**Q: 支持哪些医学影像格式？**  
A: 目前支持 PNG、JPG、JPEG、BMP、TIFF。其他格式请转换后上传。

**Q: 诊断失败了怎么办？**  
A: 检查是否提供了足够的患者信息和医学文件。如果 LLM 反复追问但患者无法回答，可能表明信息真的不足，此时应咨询医生。

**Q: 可以批量处理患者吗？**  
A: 当前版本不支持批量处理。如有需求，欢迎开 Issue 讨论。

---

## 📞 联系方式

如有问题或建议，请提交 Issue 或通过邮件联系。

---

**最后提醒**：本系统仅供学习和研究使用，任何医疗决策必须由专业医师做出。祝你使用愉快！💊
