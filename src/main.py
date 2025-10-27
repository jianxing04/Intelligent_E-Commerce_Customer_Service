import sys
import os
# --------------------------
# 关键：将项目根目录加入 Python 搜索路径
# --------------------------
# main.py 路径：src/main.py → 向上一级到项目根目录
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# 若项目根目录未在搜索路径中，则添加（避免重复添加）
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
from src.utils.log import log
log("项目根目录已加入 Python 搜索路径", 1, __file__)

# --------------------------
# 后续所有模块都能直接绝对导入
# --------------------------
# 1. 导入业务模块（如 qwen 的 receiver）
from src.qwen.receiver import QwenReceiver  

def run_chat_loop():
    """
    运行一个简单的命令行聊天循环
    """
    acceptant = QwenReceiver()
    print("聊天机器人已启动。(输入 'exit' 退出)")
    
    while True:
        # 1. 获取用户输入
        user_input = input("你: ").strip()
        
        if user_input.lower() == 'exit':
            print("机器人: 再见！")
            break
        
        if not user_input:
            continue
            
        # 2. 交给引擎处理
        response = acceptant.intent_recognize(user_input)
        
        if response is None:
            print("==========程序意图识别出错，请联系开发者==========")
            continue
        
        # 3. 打印回复
        print(f"机器人: {response}")

if __name__ == "__main__":
    # 运行
    run_chat_loop()