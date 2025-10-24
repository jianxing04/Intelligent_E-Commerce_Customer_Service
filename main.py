import sys
import os

# 确保 src 目录在 Python 路径中
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.engines.workflow import WorkflowEngine

def run_chat_loop():
    """
    运行一个简单的命令行聊天循环
    """

    # 初始化工作流引擎
    engine = WorkflowEngine()
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
        response = engine.process_message(user_input)
        
        # 3. 打印回复
        print(f"机器人: {response}")

if __name__ == "__main__":
    # 运行
    run_chat_loop()
