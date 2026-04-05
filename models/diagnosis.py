from pydantic import BaseModel


class AgentRequest(BaseModel):
    """LLM A 向子Agent发起的补充数据请求。"""
    agent: str          # "xray" | "lab" | "record"
    instruction: str    # 具体指令，如"请重点分析右下肺阴影"


class DiagnosisResult(BaseModel):
    diagnosis: str = ""
    confidence: str = "medium"  # "high" | "medium" | "low"
    evidence_basis: list[str] = []
    treatment_suggestions: list[str] = []
    reasoning_trace: str = ""

    # ---- 信息请求（LLM A 认为信息不足时使用）----
    needs_more_info: bool = False
    user_questions: list[str] = []            # 需要向患者追问的问题
    agent_requests: list[AgentRequest] = []   # 需要子Agent补充的数据
