# intention_recognizer.py
import os
import json
from tarfile import NUL
import yaml
from dashscope import Generation

def load_intent_config() -> dict:
    """从 YAML 文件加载意图配置"""
    # 获取当前脚本所在目录的绝对路径
    current_script_dir = os.path.dirname(__file__)

    # 拼接配置文件路径：从当前脚本目录回退2级到项目根目录，再进入config文件夹找目标文件
    config_path = os.path.join(
        current_script_dir,  # 起点：当前脚本所在目录（src/qwen）
        "../../",            # 回退2级到项目根目录
        "config",            # 进入config文件夹
        "intention_config.yaml"  # 目标文件名（注意你的文件名是intention，不是intent）
    )
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"意图配置文件不存在：{config_path}")
    
    # 读取 YAML 文件并解析为字典
    with open(config_path, "r", encoding="utf-8") as f:
        try:
            intent_dict = yaml.safe_load(f)  # safe_load 避免安全风险
            if not isinstance(intent_dict, dict):
                raise ValueError("YAML 文件格式错误，需为键值对结构")
            return intent_dict
        except yaml.YAMLError as e:
            raise ValueError(f"解析 YAML 文件失败：{str(e)}")

def recognize_intent(user_input: str) -> str:
    """
    识别用户输入的意图（从 YAML 加载配置，序列化后调用 API）
    
    参数:
        user_input: 用户输入的文本
        
    返回:
        意图标签（字符串），如果未识别则返回 "UNKNOWN"
    """
    try:
        # 1. 加载 YAML 中的意图配置
        intent_dict = load_intent_config()
        
        # 2. 将意图字典序列化为 JSON 字符串（发给通义千问）
        # 注意：ensure_ascii=False 保证中文正常显示（API 需正确识别中文描述）
        intent_json_str = json.dumps(intent_dict, ensure_ascii=False, indent=2)
        
        # 3. 构建系统提示（告知模型可选意图范围）
        system_prompt = f"""You are Qwen, created by Alibaba Cloud. You are a helpful assistant. 
You should choose one tag from the tag list:
{intent_json_str}
Just reply with the chosen tag."""

        # 4. 构造对话消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ]
        
        # 5. 调用通义千问 API
        response = Generation.call(
            api_key=os.getenv("DASHSCOPE_API_KEY"),  # 从环境变量获取 API 密钥
            model="tongyi-intent-detect-v3",
            messages=messages,
            result_format="message",
        )
        
        # 6. 解析返回结果
        intent_tag = response.output.choices[0].message.content.strip()
        
        # 验证标签是否在配置中
        if intent_tag in intent_dict:
            return intent_tag
        # 7. 如果标签不在配置中，返回 UNKNOWN，避免同义自身出问题
        else: 
            return "UNKNOWN"
            
    except Exception as e:
        return None

# 测试
if __name__ == "__main__":
    test_input = "hello!"
    print(recognize_intent(test_input))  # 预期输出: TRAIN_TICKET
