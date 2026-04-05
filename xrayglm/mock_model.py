class MockXrayGLM:
    async def analyze(self, image_path: str) -> str:
        return (
            "胸部X光片分析结果：\n"
            "1. 双肺纹理增粗，右下肺野可见斑片状模糊影，考虑炎症可能。\n"
            "2. 心影大小形态未见明显异常。\n"
            "3. 双侧膈肌光滑，肋膈角锐利。\n"
            "4. 纵隔无明显增宽。\n"
            "建议结合临床症状及实验室检查进一步明确诊断。"
        )
