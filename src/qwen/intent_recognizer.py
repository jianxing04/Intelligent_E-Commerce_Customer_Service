import os
import json
from typing import Optional
from dashscope import Generation
from src.utils.log import log


def recognize_intent(user_input: str, intent_dict: dict) -> Optional[str]:
    """
    识别用户输入的意图（从意图字典中选择最匹配的标签）
    
    参数:
        user_input: 用户输入的文本
        intent_dict: 意图字典，包含意图标签和描述（格式：{标签: 描述, ...}）
    返回:
        意图标签（字符串），仅在自身逻辑异常时返回None；第三方/未知异常直接抛出
    """
    # 1. 输入合法性验证（自身逻辑异常：主动处理）
    if not isinstance(user_input, str) or not user_input.strip():
        log("用户输入为空或非字符串类型", 2, __file__)
        return None
    if not isinstance(intent_dict, dict) or not intent_dict:
        log("意图字典为空或非字典类型", 2, __file__)
        return None

    # 2. 意图字典JSON序列化（自身逻辑异常：主动处理）
    try:
        intent_json_str = json.dumps(intent_dict, ensure_ascii=False, indent=2)
    except json.JSONEncodeError as e:
        log(f"意图字典JSON序列化失败：{str(e)}，字典内容：{intent_dict}", 1, __file__)
        return None

    # 3. 构建系统提示和对话消息（无异常风险，不处理）
    system_prompt = f"""你是意图识别工具，需从以下意图标签中选择最匹配的一个：
{intent_json_str}
仅返回标签本身，不添加任何额外内容。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input.strip()}
    ]

    # 4. API密钥验证（自身逻辑异常：主动处理）
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        log("环境变量DASHSCOPE_API_KEY未设置或为空", 1, __file__)
        return None
    if not isinstance(api_key, str) or not api_key.strip():
        log("环境变量DASHSCOPE_API_KEY的值无效（非字符串或空）", 1, __file__)
        return None

    # 5. 调用通义千问API（第三方异常：不捕获，直接抛出）
    response = Generation.call(
        api_key=api_key,
        model="tongyi-intent-detect-v3",
        messages=messages,
        result_format="message",
    )

    # 6. 解析API响应（第三方响应格式异常：不捕获，直接抛出）
    # 检查响应结构完整性
    if not hasattr(response, "output"):
        raise AttributeError("API响应缺少output字段")
    if not response.output.choices:
        raise IndexError("API响应的choices列表为空")
    
    detected_intent = response.output.choices[0].message.content.strip()
    
    # 验证结果是否在意图字典中（自身逻辑校验：主动处理）
    if detected_intent not in intent_dict:
        log(f"API返回的意图不在字典中：{detected_intent}，可选意图：{list(intent_dict.keys())}", 1, __file__)
        return None

    return detected_intent