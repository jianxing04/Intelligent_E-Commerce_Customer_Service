import yaml
from pathlib import Path
from src.utils.log import log
from src.qwen.intent_recognizer import recognize_intent
from typing import Optional

class QwenReceiver:
    def __init__(self):
        # 1. 获取当前文件的 Path 对象
        current_file_path = Path(__file__) # .../src/qwen/receiver.py
        log("QwenReceiver init", 3, str(current_file_path))

        # 2. 获取当前文件所在的目录
        self.work_dir = current_file_path.parent # .../src/qwen
        
        # 3. 获取项目根目录 (祖父目录)
        #    .parent -> .../src
        #    .parent -> .../ (项目根目录)
        project_root = self.work_dir.parent.parent 
        
        try:
            # 4. 使用 / 运算符拼接路径 (pathlib 的特性)
            intentsFilePath = project_root / 'config' / 'intents.yaml'
            
            with open(intentsFilePath, 'r') as file:
                self.intents = yaml.safe_load(file)

            self.intents_type = self._extract_intents_for_nlp()
                
        except FileNotFoundError:
            log(f"Error: intentions.yaml file not found in {intentsFilePath}", 1, str(current_file_path))
            self.intents = {}

    def _extract_intents_for_nlp(self):
        """
        从DSL数据中提取意图名称和描述，用于大模型意图识别
        """
        intents_map = {}
        
        for intent_name, intent_config in self.intents.items():
            if isinstance(intent_config, dict) and 'description' in intent_config:
                description = intent_config['description']
                # 格式：意图名称:描述
                intents_map[intent_name] = description
            else:
                log("意图文件配置格式出错！",1,__file__)
                return {}
        
        return intents_map

    def intent_recognize(self, user_input: str) -> Optional[str]:
        """
        从用户输入中识别意图
        
        参数:
            user_input: 用户输入的文本
            
        返回:
            识别到的意图字符串；异常时返回None
        """
        try:
            return recognize_intent(user_input, self.intents_type)
        except (AttributeError, IndexError, Exception) as e:
            # 标记为第三方异常（API调用或响应解析问题）
            log(f"第三方异常导致意图识别失败：{str(e)}", 1, __file__)
            return None