import logging

import gradio as gr

from models import ConsultationLog, ReviewVerdict
from orchestrator.pipeline import PipelineOrchestrator, EventType
from ui.health_store import load_health, save_health, add_medical_record, today_str

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
/* === Full-viewport, no outer scrollbar === */
html, body {
    height: 100vh !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}
/* Kill all Gradio wrapper padding/margin/gap */
.main, .app, #root, [data-testid="blocks-container"] {
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
}
/* Kill gap between any top-level flex children (header → body-row) */
[data-testid="blocks-container"] > *,
form > * {
    margin-top: 0 !important;
    margin-bottom: 0 !important;
    gap: 0 !important;
}
.gradio-container {
    margin: 0 !important;
    padding: 0 !important;
    height: 100vh !important;
    max-height: 100vh !important;
    max-width: 100vw !important;
    width: 100vw !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-start !important;
    font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif !important;
    background: #eef0f4 !important;
    box-sizing: border-box !important;
}
/* Remove ALL internal Gradio gaps between children */
.gradio-container > *,
.gradio-container > .flex,
.gradio-container > div {
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
}
/* The Gradio inner column that holds all blocks */
.gradio-container > div:first-child {
    display: flex !important;
    flex-direction: column !important;
    height: 100vh !important;
    width: 100% !important;
    gap: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Strip Gradio chrome */
.gradio-container .block,
.gradio-container .wrap,
.gradio-container .panel,
.gradio-container .gr-group {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
}

/* === Header — full width, flush to edges === */
.app-header {
    flex-shrink: 0;
    background: #2d5f9e;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 0 28px;
    height: 52px;
    margin: 0;
    border-radius: 0;
    width: 100vw !important;
    max-width: 100vw !important;
    box-sizing: border-box !important;
    user-select: none;
}
.app-header-icon { font-size: 1.4em; }
.app-header h1 {
    margin: 0;
    font-size: 1.05em;
    font-weight: 600;
    white-space: nowrap;
}
.app-header-sub {
    margin: 0;
    font-size: 0.72em;
    opacity: 0.75;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* === Three-column body === */
/* 52px header + 12px bottom padding = 64px */
.body-row {
    flex: 1 !important;
    height: calc(100vh - 64px) !important;
    max-height: calc(100vh - 64px) !important;
    min-height: 0 !important;
    overflow: hidden !important;
    align-items: stretch !important;
    gap: 0 !important;
    padding: 0 20px 12px 20px !important;   /* symmetric L/R padding + bottom space */
    margin: 0 !important;
    margin-top: 0 !important;
    width: 100vw !important;
    max-width: 100vw !important;
    box-sizing: border-box !important;
    border-radius: 0 !important;
}
/* Kill Gradio gap injected between header and body row */
.gradio-container > div:first-child > div:has(> .body-row),
.gradio-container > div:first-child > .body-row {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
/* Also reset the inner wrapper Gradio may insert around the Row */
.body-row + * { margin-top: 0 !important; }
.gradio-container > div:first-child > * + .body-row { margin-top: 0 !important; }
.body-row > * {
    min-height: 0 !important;
    height: calc(100vh - 76px) !important;   /* 64px + 12px bottom padding */
    max-height: calc(100vh - 76px) !important;
    overflow: hidden !important;
}

/* === Left sidebar === */
.left-sidebar {
    background: #e4e8ef !important;
    border-right: 1px solid #d4d9e2 !important;
    height: 100% !important;
    overflow-y: auto !important;
    padding: 16px 14px !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 0 !important;
    box-sizing: border-box !important;
    scrollbar-width: thin;
    scrollbar-color: #c5ccd8 transparent;
}

/* === Input panel (middle) === */
.input-panel {
    background: #f7f8fa !important;
    border-right: 1px solid #d4d9e2 !important;
    height: 100% !important;
    overflow-y: auto !important;
    padding: 10px 14px !important;
    box-sizing: border-box !important;
    scrollbar-width: thin;
    scrollbar-color: #c5ccd8 transparent;
}

/* === Chat panel (right) === */
.chat-col {
    background: #fff !important;
    height: calc(100vh - 76px) !important;
    max-height: calc(100vh - 76px) !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
    padding: 0 !important;
    margin: 0 !important;
}
.chat-col .chatbot-wrap {
    flex: 1 !important;
    min-height: 0 !important;
    height: 0 !important;        /* flex trick: let flex-grow take over */
    overflow: hidden !important;
}
/* The actual Gradio chatbot block — fill wrap and scroll */
.chat-col .chatbot-wrap > div,
.chat-col .chatbot-wrap .block,
.chat-col .chatbot-wrap .chatbot {
    height: 100% !important;
    max-height: 100% !important;
    overflow-y: auto !important;
}
/* Gradio internal message list container */
.chat-col .chatbot-wrap .overflow-y-auto {
    height: 100% !important;
    max-height: 100% !important;
    overflow-y: auto !important;
}

/* === Chat scrollbar === */
/* Firefox */
.chat-col .chatbot-wrap,
.chat-col .chatbot-wrap *,
.chat-col [data-testid="bot"] {
    scrollbar-width: thin !important;
    scrollbar-color: #9aafc8 #edf0f5 !important;
}
/* WebKit (Chrome / Edge) */
.chat-col ::-webkit-scrollbar {
    width: 7px !important;
}
.chat-col ::-webkit-scrollbar-track {
    background: #edf0f5 !important;
    border-radius: 4px !important;
}
.chat-col ::-webkit-scrollbar-thumb {
    background: #9aafc8 !important;
    border-radius: 4px !important;
    border: 1px solid #edf0f5 !important;
}
.chat-col ::-webkit-scrollbar-thumb:hover {
    background: #6b8fb5 !important;
}

/* === Section heading === */
.sec-head {
    font-size: 0.7em;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: #7a8698;
    margin: 0 0 4px;
    padding: 0;
}

/* === Sidebar action buttons === */
.sidebar-btn {
    width: 100% !important;
    border-radius: 8px !important;
    font-size: 0.88em !important;
    font-weight: 550 !important;
    padding: 8px 0 !important;
    cursor: pointer !important;
    transition: all 0.15s !important;
    margin-bottom: 8px !important;
}
.btn-new-consult {
    background: #2d5f9e !important;
    color: #fff !important;
    border: none !important;
}
.btn-new-consult:hover { background: #245089 !important; }
.btn-back {
    background: transparent !important;
    color: #2d5f9e !important;
    border: 1px solid #b0c4de !important;
}
.btn-back:hover { background: #eef3ff !important; border-color: #2d5f9e !important; }

/* === Personal info inputs === */
.info-input input,
.info-input select,
.info-input textarea {
    border: 1px solid #ccd2db !important;
    border-radius: 6px !important;
    background: #fff !important;
    font-size: 0.84em !important;
    padding: 5px 8px !important;
}
.info-input input:focus,
.info-input textarea:focus {
    border-color: #4a7fc1 !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(74,127,193,0.12) !important;
}
/* Make gender radio compact */
.gender-radio label {
    font-size: 0.84em !important;
    padding: 4px 12px !important;
    border: 1px solid #ccd2db !important;
    border-radius: 6px !important;
    background: #fff !important;
    cursor: pointer !important;
    transition: all 0.12s !important;
}
.gender-radio label:has(input:checked) {
    background: #2d5f9e !important;
    color: #fff !important;
    border-color: #2d5f9e !important;
}
.gender-radio input[type="radio"]:checked::after {
    content: "" !important;
    width: 8px !important;
    height: 8px !important;
    background: #2d5f9e ;
    position: absolute !important;
    top: 50% !important;
    left: 50% !important;
    transform: translate(-50%, -50%) !important;
    border-radius: 50% !important;
}
.gender-radio .wrap { gap: 6px !important; flex-wrap: nowrap !important; }



/* === Upload zone === */
.upload-zone .file-preview-holder,
.upload-zone .upload-btn {
    border: 1px dashed #b0bac8 !important;
    border-radius: 8px !important;
    background: #fff !important;
}

/* === File tag radio === */
.tag-radio .wrap { gap: 5px !important; flex-wrap: wrap !important; }
.tag-radio label {
    border: 1px solid #ccd2db !important;
    border-radius: 14px !important;
    padding: 3px 11px !important;
    font-size: 0.8em !important;
    cursor: pointer !important;
    transition: all 0.12s !important;
    background: #fff !important;
    color: #5a6475 !important;
}
.tag-radio label:has(input:checked) {
    background: #2d5f9e !important;
    border-color: #2d5f9e !important;
    color: #fff !important;
}

/* === Text input === */
.text-input-wrap textarea {
    border: 1px solid #ccd2db !important;
    border-radius: 8px !important;
    background: #fff !important;
    font-size: 0.9em !important;
    resize: none !important;
    transition: border 0.15s !important;
    min-height: 80px !important;
}
.text-input-wrap textarea:focus {
    border-color: #4a7fc1 !important;
    box-shadow: 0 0 0 2px rgba(74,127,193,0.12) !important;
}

/* === Send button === */
.btn-send {
    width: 100% !important;
    background: #2d5f9e !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-size: 0.92em !important;
    font-weight: 550 !important;
    padding: 9px 0 !important;
    cursor: pointer !important;
    transition: background 0.15s !important;
    margin-top: 4px !important;
}
.btn-send:hover { background: #245089 !important; }

/* === Disclaimer (inside bottom margin area) === */
.disclaimer-bar {
    flex-shrink: 0;
    text-align: center;
    color: #b0b8c6;
    font-size: 0.68em;
    padding: 0;
    margin: 0;
    height: 0;
    overflow: visible;
    position: relative;
    top: 2px;
    background: transparent;
    border: none;
}

/* === Divider === */
.sep { height: 1px; background: #d0d5de; margin: 8px 0; }

/* === Step badges === */
.step-badge {
    display: inline-block;
    font-size: 0.68em;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 600;
    margin-right: 4px;
    vertical-align: middle;
}
.step-badge.triage   { background: #ddeeff; color: #1a5a9e; }
.step-badge.extract  { background: #fff3d8; color: #8a5e10; }
.step-badge.diag     { background: #edeaff; color: #4e30b0; }
.step-badge.review   { background: #dff6eb; color: #1a6e42; }

/* === Thinking animation === */
@keyframes medpulse {
    0%,80%,100% { opacity:.2; transform:scale(.75); }
    40%          { opacity:1;  transform:scale(1); }
}
.thinking-dots span {
    display:inline-block; width:7px; height:7px;
    margin:0 2px; border-radius:50%;
    background:#2d5f9e;
    animation: medpulse 1.4s infinite ease-in-out;
}
.thinking-dots span:nth-child(2) { animation-delay:.18s; }
.thinking-dots span:nth-child(3) { animation-delay:.36s; }
"""

# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

STEP_LABELS = {
    "triage":        ("分诊", "triage"),
    "extraction":    ("提取", "extract"),
    "xray":          ("影像", "extract"),
    "lab":           ("化验", "extract"),
    "record":        ("病历", "extract"),
    "diagnosis":     ("诊断", "diag"),
    "review":        ("审核", "review"),
    "review_pass":   ("审核", "review"),
    "review_reject": ("审核", "review"),
    "retry":         ("重诊", "diag"),
    "max_rounds":    ("终止", "review"),
}

def _badge(step: str) -> str:
    label, cls = STEP_LABELS.get(step, ("处理", "triage"))
    return f'<span class="step-badge {cls}">{label}</span>'

def format_thinking(step: str, msg: str) -> str:
    return (f'{_badge(step)} {msg}\n\n'
            '<div class="thinking-dots"><span></span><span></span><span></span></div>')

def format_step(step: str, msg: str) -> str:
    return f'{_badge(step)} {msg}'

def format_final_report(log: ConsultationLog) -> str:
    d = log.final_diagnosis
    icon = "✅" if log.approved else "⚠️"
    status = "审核通过" if log.approved else "未通过审核（已达最大博弈轮数）"
    conf = {"high": "🟢 高", "medium": "🟡 中", "low": "🔴 低"}.get(d.confidence, d.confidence)
    evidence  = "\n".join(f"- {e}" for e in d.evidence_basis)
    treatment = "\n".join(f"- {s}" for s in d.treatment_suggestions)
    return (
        f"---\n### {icon} 诊断报告 · {status}\n\n"
        f"**诊断结论**\n{d.diagnosis}\n\n"
        f"**置信度**　{conf}\n\n"
        f"**诊断依据**\n{evidence}\n\n"
        f"**治疗建议**\n{treatment}\n\n---\n"
    )

def format_reasoning_details(log: ConsultationLog) -> str:
    d = log.final_diagnosis
    lines = []
    for i, r in enumerate(log.rounds, 1):
        v = "✅ 通过" if r.review.verdict == ReviewVerdict.APPROVED else "❌ 驳回"
        lines += [f"**第{i}轮**",
                  f"- **LLM A 诊断：** {r.diagnosis.diagnosis}",
                  f"- **LLM A 置信度：** {r.diagnosis.confidence}"]
        if r.diagnosis.treatment_suggestions:
            lines.append("- **LLM A 治疗建议：** " + "；".join(r.diagnosis.treatment_suggestions))
        lines += [f"- **LLM B 审核：** {v}", f"- **审核意见：** {r.review.comments}"]
        if r.review.safety_issues:
            lines.append(f"- **安全性：** {'; '.join(r.review.safety_issues)}")
        if r.review.logic_issues:
            lines.append(f"- **逻辑：** {'; '.join(r.review.logic_issues)}")
        lines.append("")
    return (
        f"<details>\n<summary>📖 推理详情（{log.total_rounds} 轮会诊）· 点击展开</summary>\n\n"
        f"#### 诊断推理过程\n{d.reasoning_trace}\n\n---\n\n"
        f"#### LLM A / LLM B 会诊记录\n\n" + "\n".join(lines) + "\n</details>"
    )

def _replace_or_append(msgs: list, msg: dict) -> None:
    if (msgs and msgs[-1]["role"] == "assistant"
            and "thinking-dots" in msgs[-1].get("content", "")):
        msgs[-1] = msg
    else:
        msgs.append(msg)

def build_allergy_context(allergy: str, past_history: str) -> str:
    parts = []
    if allergy:
        parts.append(f"过敏史：{allergy}")
    if past_history:
        parts.append(f"既往病史：{past_history}")
    return "；".join(parts)

TAG_MAP = {
    "X光片":   "xray",
    "化验单":  "lab_report",
    "病历":    "medical_record",
    "其他图片": "other_image",
}

# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def get_diagnosis_css() -> str:
    """Return the CSS for the diagnosis UI (needed for Gradio 6 launch())."""
    return CUSTOM_CSS


def create_ui(orchestrator: PipelineOrchestrator,
              patient_profile: dict | None = None,
              portal_port: int = 7860) -> gr.Blocks:

    with gr.Blocks(title="MedAgent - 智能医疗辅助诊断") as app:

        # ── Header bar ──────────────────────────────────────────────────
        gr.HTML("""
        <div class="app-header">
          <span class="app-header-icon">🏥</span>
          <div>
            <h1>BUAA-MedAgents · 智能医疗辅助诊断系统</h1>
            <p class="app-header-sub">多智能体协作 · XrayGLM · Qwen-VL · LLM A/B 双重博弈</p>
          </div>
        </div>""")

        # ── Body row (three columns) ─────────────────────────────────────
        with gr.Row(elem_classes=["body-row"], equal_height=True):

            # ======= LEFT SIDEBAR (18%) =======
            with gr.Column(scale=18, min_width=200, elem_classes=["left-sidebar"]):

                # New consultation
                new_btn = gr.Button("＋ 新建会诊",
                                    elem_classes=["sidebar-btn", "btn-new-consult"])

                gr.HTML('<div class="sep"></div>')

                # Personal info
                gr.HTML('<p class="sec-head">个人信息</p>')

                gender = gr.Radio(
                    choices=["男", "女"],
                    value=None,
                    label="性别",
                    elem_classes=["gender-radio", "info-input"],
                )
                age = gr.Number(
                    label="年龄（岁）",
                    minimum=0, maximum=150,
                    value=None,
                    elem_classes=["info-input"],
                )
                height_cm = gr.Number(
                    label="身高（cm）",
                    minimum=0, maximum=300,
                    value=None,
                    elem_classes=["info-input"],
                )
                weight_kg = gr.Number(
                    label="体重（kg）",
                    minimum=0, maximum=500,
                    value=None,
                    elem_classes=["info-input"],
                )
                allergy_input = gr.Textbox(
                    label="过敏史",
                    placeholder="如：青霉素、磺胺类",
                    lines=2, max_lines=3,
                    elem_classes=["info-input"],
                )
                past_history = gr.Textbox(
                    label="既往病史",
                    placeholder="如：高血压、糖尿病",
                    lines=2, max_lines=3,
                    elem_classes=["info-input"],
                )

                gr.HTML('<div style="flex:1"></div>')  # spacer
                gr.HTML('<div class="sep"></div>')

                # Back to portal
                back_btn = gr.Button("← 返回主菜单",
                                     elem_classes=["sidebar-btn", "btn-back"])

            # ======= INPUT PANEL (28%) =======
            with gr.Column(scale=28, min_width=240, elem_classes=["input-panel"]):

                gr.HTML('<p class="sec-head">上传文件</p>')
                file_upload = gr.File(
                    file_types=["image", ".pdf", ".txt"],
                    file_count="multiple",
                    show_label=False,
                    elem_classes=["upload-zone"],
                    height=100,
                )
                gr.HTML('<p class="sec-head" style="margin-top:6px">文件类型标签</p>')
                file_tag = gr.Radio(
                    choices=["X光片", "化验单", "病历", "其他图片"],
                    value="其他图片",
                    show_label=False,
                    elem_classes=["tag-radio"],
                )

                gr.HTML('<div class="sep"></div>')

                gr.HTML('<p class="sec-head">症状描述 / 提问</p>')
                text_input = gr.Textbox(
                    placeholder="请描述症状，或在诊断后继续提问…",
                    lines=4,
                    max_lines=10,
                    show_label=False,
                    elem_classes=["text-input-wrap"],
                )
                send_btn = gr.Button("发 送", elem_classes=["btn-send"])
                gr.HTML('<div style="height:20px"></div>')

            # ======= CHAT PANEL (54%) =======
            with gr.Column(scale=54, min_width=360, elem_classes=["chat-col"]):
                with gr.Column(elem_classes=["chatbot-wrap"]):
                    chatbot = gr.Chatbot(
                        show_label=False,
                        height=4000,   # CSS max-height on .chat-col overrides this
                        elem_classes=["chatbot"],
                    )

        # ── Disclaimer ──────────────────────────────────────────────────
        # Bottom space is provided by body-row's padding-bottom

        # ── State ───────────────────────────────────────────────────────
        context_state = gr.State({
            "complaint":        "",
            "file_paths":       [],
            "file_tags":        {},
            "allergy":          "",
            "waiting_followup": False,
            "mode":             "idle",
            "log":              None,
            "patient":          None,
            "resume_state":     None,
        })

        # ----------------------------------------------------------------
        # Helpers to build patient context string
        # ----------------------------------------------------------------
        def _patient_context(gender_v, age_v, height_v, weight_v, allergy_v, history_v) -> str:
            parts = []
            if gender_v:
                parts.append(f"性别：{gender_v}")
            if age_v:
                parts.append(f"年龄：{int(age_v)}岁")
            if height_v:
                parts.append(f"身高：{int(height_v)}cm")
            if weight_v:
                parts.append(f"体重：{int(weight_v)}kg")
            if allergy_v:
                parts.append(f"过敏史：{allergy_v}")
            if history_v:
                parts.append(f"既往病史：{history_v}")
            return "；".join(parts)

        # ----------------------------------------------------------------
        # Submit handler
        # ----------------------------------------------------------------
        async def on_submit(
            text, files, tag_choice, history, ctx,
            gender_v, age_v, height_v, weight_v, allergy_v, history_v,
        ):
            text = (text or "").strip()
            file_paths = []
            if files:
                for f in files:
                    file_paths.append(f.name if hasattr(f, "name") else str(f))

            if not text and not file_paths:
                yield history, ctx, "", None
                return

            messages = list(history)

            # User bubble
            user_display = text
            if file_paths:
                names = ", ".join(p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for p in file_paths)
                user_display += f"\n📎 {names}（{tag_choice}）"
            messages.append({"role": "user", "content": user_display})
            yield messages, ctx, "", None

            # ── Post-diagnosis Q&A mode ──
            if ctx.get("mode") == "post_diagnosis" and ctx.get("log") and text:
                messages.append({"role": "assistant",
                                  "content": format_thinking("diagnosis", "医生正在思考您的问题...")})
                yield messages, ctx, "", None
                answer = await orchestrator.answer_followup(
                    question=text, log=ctx["log"], patient=ctx["patient"])
                messages[-1] = {"role": "assistant", "content": answer}
                yield messages, ctx, "", None
                return

            # ── Build file tags ──
            tag_str = TAG_MAP.get(tag_choice, "other_image")
            new_tags = {fp: tag_str for fp in file_paths}

            # ── Build allergy string from personal info ──
            allergy_combined = "; ".join(
                x for x in [allergy_v, history_v] if x
            )

            # ── Follow-up or fresh start ──
            if ctx.get("waiting_followup"):
                resume = ctx.get("resume_state")
                if resume and (text or file_paths):
                    # LLM A was asking — append user answer to supplementary_info
                    # and resume from diagnosis (skip triage+extraction)
                    prev_sup = resume.get("supplementary_info", "")
                    new_sup = prev_sup
                    if text:
                        new_sup = (f"{new_sup}\n\n【患者补充说明】{text}"
                                   if new_sup else f"【患者补充说明】{text}")
                    resume = {**resume,
                              "supplementary_info": new_sup,
                              "new_file_paths": file_paths,
                              "new_file_tags": new_tags}
                    ctx = {**ctx,
                           "resume_state":     resume,
                           "waiting_followup": False,
                           "mode":             "consulting"}
                else:
                    # Triage was asking (or no resume state) — append to complaint
                    ctx = {**ctx,
                           "complaint":        f"{ctx['complaint']}\n\n补充信息：{text}",
                           "file_paths":       ctx["file_paths"] + file_paths,
                           "file_tags":        {**ctx.get("file_tags", {}), **new_tags},
                           "resume_state":     None,
                           "waiting_followup": False,
                           "mode":             "consulting"}
            else:
                patient_ctx = _patient_context(gender_v, age_v, height_v, weight_v, allergy_v, history_v)
                complaint_with_ctx = (f"【患者基本信息】{patient_ctx}\n\n【主诉】{text}"
                                      if patient_ctx else text)
                ctx = {
                    "complaint":        complaint_with_ctx,
                    "file_paths":       file_paths,
                    "file_tags":        new_tags,
                    "allergy":          allergy_combined,
                    "waiting_followup": False,
                    "mode":             "consulting",
                    "log":              None,
                    "patient":          None,
                    "resume_state":     None,
                }

            # ── Run pipeline ──
            async for event in orchestrator.run(
                chief_complaint=ctx["complaint"],
                file_paths=ctx["file_paths"],
                allergy_history=ctx.get("allergy", ""),
                file_tags=ctx.get("file_tags"),
                resume_state=ctx.get("resume_state"),
            ):
                if event.type == EventType.THINKING:
                    _replace_or_append(messages, {
                        "role": "assistant",
                        "content": format_thinking(event.step_name, event.message),
                    })
                    yield messages, ctx, "", None

                elif event.type == EventType.STEP_COMPLETE:
                    _replace_or_append(messages, {
                        "role": "assistant",
                        "content": format_step(event.step_name, event.message),
                    })
                    yield messages, ctx, "", None

                elif event.type == EventType.QUESTION:
                    _replace_or_append(messages, {
                        "role": "assistant",
                        "content": f"🩺 {event.message}\n\n*请在输入框补充信息后发送。*",
                    })
                    ctx["waiting_followup"] = True
                    ctx["resume_state"] = event.data.get("resume_state")
                    yield messages, ctx, "", None
                    return

                elif event.type == EventType.COMPLETE:
                    log: ConsultationLog = event.data["log"]
                    patient_obj = event.data.get("patient")
                    _replace_or_append(messages, {
                        "role": "assistant",
                        "content": format_final_report(log),
                    })
                    messages.append({"role": "assistant",
                                     "content": format_reasoning_details(log)})
                    messages.append({"role": "assistant",
                                     "content": "💬 诊断完成。如有疑问可继续提问，或点击「新建会诊」开始新的诊断。"})
                    ctx = {**ctx, "mode": "post_diagnosis", "log": log,
                           "patient": patient_obj, "resume_state": None}

                    # Auto-save diagnosis to health records
                    try:
                        d = log.final_diagnosis
                        chief = patient_obj.chief_complaint if patient_obj else ctx.get("complaint", "")
                        symptom = chief
                        if "【主诉】" in symptom:
                            symptom = symptom.split("【主诉】", 1)[1].strip()
                        health = load_health()
                        add_medical_record(
                            health,
                            record_date=today_str(),
                            symptom=symptom[:200],
                            diagnosis=d.diagnosis,
                            treatment="；".join(d.treatment_suggestions),
                            note=f"置信度：{d.confidence}",
                            source="diagnosis",
                        )
                        save_health(health)
                        messages.append({"role": "assistant",
                                         "content": "📋 已自动保存至「健康档案」，可在主界面查看和编辑。"})
                    except Exception as e:
                        logger.warning("Failed to auto-save medical record: %s", e)

                    yield messages, ctx, "", None

        # ----------------------------------------------------------------
        # New consultation — resets chat & state, keeps personal info
        # ----------------------------------------------------------------
        def on_new():
            empty_ctx = {
                "complaint":"","file_paths":[],"file_tags":{},"allergy":"",
                "waiting_followup":False,"mode":"idle","log":None,"patient":None,
                "resume_state":None,
            }
            return [], empty_ctx, "", None

        # ----------------------------------------------------------------
        # Back to portal
        # ----------------------------------------------------------------
        def on_back():
            return None  # JS handles navigation

        # ── Wire events ─────────────────────────────────────────────────
        personal_inputs = [gender, age, height_cm, weight_kg, allergy_input, past_history]
        submit_inputs   = [text_input, file_upload, file_tag, chatbot, context_state] + personal_inputs
        submit_outputs  = [chatbot, context_state, text_input, file_upload]

        send_btn.click(fn=on_submit, inputs=submit_inputs, outputs=submit_outputs)
        text_input.submit(fn=on_submit, inputs=submit_inputs, outputs=submit_outputs)

        new_btn.click(
            fn=on_new, inputs=[],
            outputs=[chatbot, context_state, text_input, file_upload],
        )
        back_btn.click(
            fn=on_back, inputs=[], outputs=[],
            js=f"() => {{ window.location.href = 'http://127.0.0.1:{portal_port}'; }}",
        )

        # ── Load shared profile on page open ──
        def load_profile():
            if not patient_profile:
                return [gr.update()] * 6
            return [
                gr.update(value=patient_profile.get("gender")),
                gr.update(value=patient_profile.get("age")),
                gr.update(value=patient_profile.get("height")),
                gr.update(value=patient_profile.get("weight")),
                gr.update(value=patient_profile.get("allergy", "")),
                gr.update(value=patient_profile.get("past_history", "")),
            ]

        app.load(fn=load_profile, inputs=[], outputs=personal_inputs)

    return app
