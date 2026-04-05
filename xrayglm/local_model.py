import asyncio


class LocalXrayGLM:
    """本地部署的XrayGLM模型。

    需要安装: SwissArmyTransformer>=0.3.6, torch, transformers
    """

    def __init__(self, checkpoint_path: str, prompt: str):
        self.checkpoint_path = checkpoint_path
        self.prompt = prompt
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        # TODO: 加载VisualGLM + LoRA checkpoint
        # from sat.model import AutoModel
        # self.model, self.tokenizer = AutoModel.from_pretrained(...)
        raise NotImplementedError(
            f"请先下载XrayGLM模型到 {self.checkpoint_path}，"
            "并安装相关依赖：pip install SwissArmyTransformer torch transformers"
        )

    def _inference(self, image_path: str) -> str:
        # TODO: 实际推理逻辑
        raise NotImplementedError

    async def analyze(self, image_path: str) -> str:
        return await asyncio.to_thread(self._inference, image_path)
