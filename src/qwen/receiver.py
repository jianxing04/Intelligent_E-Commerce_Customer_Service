import yaml
from pathlib import Path
from src.utils.log import log
from src.qwen import worker

class Receiver:
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
            self.intent_actions_map = self._extract_actions_for_nlp()
                
        except FileNotFoundError:
            log(f"Error: intentions.yaml file not found in {intentsFilePath}", 1, str(current_file_path))
            self.intents = {}

        #记录用户相关信息
        self.phone_number=None

        #意图行为字典
        self.action_handlers = {
            "greet": self._greet,
            "check_phone_number": self._check_phone_number,
            "get_order_info": self._get_order_info
        }

    def _extract_intents_for_nlp(self):
        """
        从DSL数据中提取意图名称和描述，用于大模型意图识别
        """
        intents_map = {}

        for key, value in self.intents.items():
            if isinstance(value, dict) and 'description' in value:
                description = value['description']
                # 格式：意图名称:描述
                intents_map[key] = description
            else:
                log(f"意图文件配置格式出错！{key}缺少描述(description)字段！",2,__file__)
                continue

        return intents_map
    
    def _extract_actions_for_nlp(self):
        """
        从DSL数据中提取意图名称和对应动作，用于大模型意图识别
        """
        actions_map = {}
        
        for key, value in self.intents.items():
            if isinstance(value, dict) and 'actions' in value:
                actions = value['actions']
                # 格式：意图名称:操作列表
                actions_map[key] = actions
            else:
                log(f"意图文件配置格式出错！{key}缺少操作(actions)字段！",2,__file__)
                continue

        return actions_map

    def execute(self):
        while True:
            user_input=input("您: ").strip()
            if user_input.lower() == 'exit':
                print("机器人: 再见！")
                break
            if not user_input:
                continue
            user_intent = worker.recognize_intent(user_input, self.intents_type)
            if user_intent is None:
                print("==========程序意图识别出错，请联系开发者==========")
                continue
            self.handle_intent(user_intent)
            
    def handle_intent(self, intent: str):
        actions = self.intent_actions_map.get(intent)
        if not actions:
            log(f"未找到意图 '{intent}' 的对应动作。", 2, __file__)
            return
        for action in actions:
            func=self.action_handlers.get(action)
            log(f"意图: {intent}, 动作: {action}, 函数: {func}", 2, __file__)
            if func:
                func()
            else:
                log(f"未找到动作处理函数 '{action}'。", 2, __file__)
                print(f"机器人: 抱歉，我无法执行动作 '{action}'。")

    def _greet(self):
        print("Hello! How can I assist you today?")

    def _check_phone_number(self):
        self.phone_number=None
        while not self.phone_number:
            print("机器人: 请提供您的手机号码以继续查询订单。")
            phone = input("您（请输入手机号码）: ").strip()
            res=worker.pharse_phone_number(phone).strip()
            if res and res.isdigit() and len(res) == 11:
                self.phone_number=res
                print(f"机器人: 已记录您的手机号码：{self.phone_number}")
            else:
                print("机器人: 抱歉，未能识别有效的手机号码。请重试。")
                
    def _get_order_info(self):
        order_info = worker.get_order_info(self.phone_number)
        if order_info:
            print(f"机器人: 您的订单信息如下：")
            print(f"用户名：{order_info['user_name']}")
            print(f"订单状态：{order_info['order_status']}")
        else:
            print("机器人: 抱歉，未能获取到您的订单信息。")