import os
from datetime import datetime

# log.py 路径：src/utils/log.py → 向上两级到 src → 再向上一级到项目根目录
CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_FILE_DIR, "../.."))

# 2. 日志目录固定为 项目根目录/logs
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
# 确保日志目录存在（不存在则自动创建）
os.makedirs(LOG_DIR, exist_ok=True)

# 3. 定义日志文件路径（固定路径，所有模块共用）
LOG_FILE_1 = os.path.join(LOG_DIR, "log_1.txt")
LOG_FILE_2 = os.path.join(LOG_DIR, "log_2.txt")
LOG_FILE_3 = os.path.join(LOG_DIR, "log_3.txt")

# 日志等级与文件映射（全局统一）
LEVEL_LOG_MAP = {
    1: [LOG_FILE_1, LOG_FILE_2, LOG_FILE_3],
    2: [LOG_FILE_2, LOG_FILE_3],
    3: [LOG_FILE_3]
}

# --------------------------
# 4. 日志核心函数（所有模块统一调用）
# --------------------------
def log(erro_msg, level, filename): 
    """
    项目公共日志函数
    :param erro_msg: 日志内容（str）
    :param level: 日志等级（1-3，1级最高）
    :param filename: 调用日志的文件名（用于定位错误）
    """

    level = max(1, min(level, 3))
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_msg = f"{current_time} | LEVEL-{level} | FILE-{os.path.basename(filename)} | {erro_msg}\n" 
    
    # 写入文件
    for log_file in LEVEL_LOG_MAP[level]:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_msg)
        except Exception as e:
            print(f"[日志系统错误] 写入 {os.path.basename(log_file)} 失败：{str(e)}")


# 测试代码
if __name__ == "__main__":
    # 打印日志目录，验证路径是否正确
    print(f"日志目录：{LOG_DIR}")
    # 测试不同等级日志
    log("这是1级日志（最详细）", 1, __file__)
    log("这是2级日志", 2, __file__)
    log("这是3级日志（最简略）", 3, __file__)
    log("等级超出范围（会被修正为3）", 5, __file__)