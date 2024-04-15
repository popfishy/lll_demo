import pandas as pd
import tiktoken
import openai
from IPython.display import display
from IPython.core.display import Markdown
import pandas as pd
import json
import requests
from voice2text.voice2text import *
from voice2text.tools import *
from pynput import keyboard
from zhipuai import ZhipuAI
import keyboard
import threading


# **************************** tools**********************************
def python_inter(py_code, g="globals()"):
    """
    专门用于执行非绘图类python代码，并获取最终查询或处理结果。若是设计绘图操作的Python代码，则需要调用fig_inter函数来执行。
    :param py_code: 字符串形式的Python代码，用于执行对telco_db数据库中各张数据表进行操作
    :param g: g，字符串形式变量，表示环境变量，无需设置，保持默认参数即可
    :return：代码运行的最终结果
    """

    global_vars_before = set(g.keys())
    try:
        exec(py_code, g)
    except Exception as e:
        return f"代码执行时报错{e}"
    global_vars_after = set(g.keys())
    new_vars = global_vars_after - global_vars_before
    # 若存在新变量
    if new_vars:
        result = {var: g[var] for var in new_vars}
        return str(result)
    # 若不存在新变量，即有可能是代码是表达式，也有可能代码对相同变量重复赋值
    else:
        try:
            # 尝试如果是表达式，则返回表达式运行结果
            return str(eval(py_code, g))
        # 若报错，则先测试是否是对相同变量重复赋值
        except Exception as e:
            try:
                exec(py_code, g)
                return "已经顺利执行代码"
            except Exception as e:
                pass
            # 若不是重复赋值，则报错
            return f"代码执行时报错{e}"


python_inter_function_info = {
    "name": "python_inter",
    "description": "专门用于python代码，并获取最终查询或处理结果。",
    "parameters": {
        "type": "object",
        "properties": {
            "py_code": {
                "type": "string",
                "description": "用于执行在本地环境运行的python代码",
            },
            "g": {
                "type": "string",
                "description": "环境变量，可选参数，保持默认参数即可",
            },
        },
        "required": ["py_code"],
    },
}

tools = [
    {"type": "function", "function": python_inter_function_info},
]

functions_list = [python_inter]
# **************************** tools**********************************

if __name__ == "__main__":
    # 创建OpenAI API客户端
    openai.api_base = "https://api.chatanywhere.tech"
    openai.api_key = "sk-WBjBmhlh9parwwZaUTSOs8ZyYi064EHEwGXdcBi2ku8oj56q"
    ZhipuAI.api_key = "335590e406917fcf09df3819ca20c3db.tSewYSL13MLugE1y"
    Q1 = "假设当前数据为：当domains=0时，type为1的有10个，type为2的有10个，type为3的有6个，type为4的有3个；当domains=1时,type为1的有10个，type为2的有15个.\
    请问现在草原上每类生物和Agent的数量分别是多少？"
    A1 = "根据提供的仿真输出数据，当domains=0时，1代表牛，2代表羊，3代表车辆，4代表野猪；当domains=1时，1代表侦察无人机，2代表攻击无人机。\
    domains=0时,通过观察数据，我们可以发现type为1的有10个，type为2的有10个，type为3的有6个，type为4的有3个；当domains=1时，type为1的有10个，type为2的有15个。\
    因此侦察无人机的数量为：10,攻击无人机的数量为：15，牛的数量为：10,羊的数量为：10,车辆的数量为：6,野猪的数量为3."
    Q2 = "假设当前数据为：\
          NO.48号野猪的'distance'为400,'nearest_Uav'编号为6,'nearest_next_Uav'标号为15,'nearest_Car'编号为25,'nearest_next_Car'编号为35;\
          NO.41号野猪的'distance'为150,'nearest_Uav'编号为3,'nearest_next_Uav'标号为13,'nearest_Car'编号为20,'nearest_next_Car'编号为22;\
          NO.45号野猪的'distance'为1200,'nearest_Uav'编号为7,'nearest_next_Uav'标号为1,'nearest_Car'编号为24,'nearest_next_Car'编号为48;\
          NO.42号野猪的'distance'为250,'nearest_Uav'编号为4,'nearest_next_Uav'标号为8,'nearest_Car'编号为27,'nearest_next_Car'编号为46;\
          请你分析草原上的整体态势并给出建议？"
    A2 = "从数据中我们可以看到四只野猪的 'distance' 值分别是 400、150、1200和250。NO.41号野猪的 'distance'为150,小于200，处于“危险”状态；\
          NO.42号野猪的'distance'为250,NO.48号野猪的 'distance'为400,均大于200小于500,处于“有一定危险”状态；NO.45号野猪的 'distance'为1200,大于500,处于“无危险”状态。\
          根据相关规则，优先分析处于“危险”状态的野猪，其次分析处于“有一定危险”状态的野猪，最后分析“无危险”状态的野猪。\
          NO.41野猪处于“危险”状态，其'nearest_Uav'编号为3,'nearest_next_Uav'标号为13,'nearest_Car'编号为20,'nearest_next_Car'编号为22，应该派遣\
          距离该野猪最近的NO.3号无人机进行监视，距离该野猪最近的NO.20和NO.22号车辆进行驱逐。NO.42号野猪和NO.48号野猪处于“有一定危险”状态：对于NO.42号野猪，\
          其'nearest_Uav'编号为4,'nearest_next_Uav'标号为8,'nearest_Car'编号为27,'nearest_next_Car'编号为46，应该派遣距离该野猪最近的NO.4号无人机\
          进行监视，距离该野猪最近的NO.27号车辆进行驱逐；对于NO.48号野猪，'nearest_Uav'编号为6,'nearest_next_Uav'标号为15,'nearest_Car'编号为25,'nearest_next_Car'编号为35，\
          应该派遣距离该野猪最近的NO.6号无人机进行监视，距离该野猪最近的NO.25号车辆进行驱逐。NO.45野猪处于“无危险”状态，其'nearest_Uav'编号为7,'nearest_next_Uav'标号为1,'nearest_Car'编号为24,'nearest_next_Car'编号为48\
          应该派遣距离该野猪最近的NO.1号无人机进行监视。因此给出的建议是：\
        | 野猪编号 |    状态    | distance | nearest_Uav | nearest_next_Uav | nearest_Car | nearest_next_Car |                         建议                         |\
        | :------: | :--------: | :------: | :---------: | :--------------: | :---------: | :--------------: | :--------------------------------------------------: |\
        |  NO.41   |    危险    |   150    |    NO.3     |      NO.13       |    NO.20    |      NO.22       | 派遣NO.3号无人机进行监视，NO.20和NO.22号车辆进行驱逐 |\
        |  NO.42   | 有一定危险 |   250    |    NO.4     |       NO.8       |    NO.27    |      NO.46       |    派遣NO.4号无人机进行监视，NO.27号车辆进行驱逐     |\
        |  NO.48   | 有一定危险 |   400    |    NO.6     |      NO.15       |    NO.25    |      NO.35       |    派遣NO.6号无人机进行监视，NO.25号车辆进行驱逐     |\
        |  NO.45   |   无危险   |   1200   |    NO.7     |       NO.1       |    NO.24    |      NO.48       |               派遣NO.1号无人机进行监视               |\
         "
    Q3 = ""
    A3 = ""

    with open("voice2text/overall_data.csv", "r", encoding="utf-8") as f:
        dataset = f.read()
    dataset = (
        "以上数据均为虚拟数据，现在重新提供畜牧养殖仿真模型真实数据，请你根据真实数据进行分析："
        + dataset
    )
    pd.set_option("max_colwidth", 200)
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    # 打开并读取Markdown文件
    with open("voice2text/simulation_output_dictionary.md", "r", encoding="utf-8") as f:
        simulation_output = f.read()
    print(simulation_output)
    messages = [
        {"role": "system", "content": simulation_output},
        {"role": "user", "content": Q1},
        {"role": "assistant", "content": A1},
        {"role": "user", "content": Q2},
        {"role": "assistant", "content": A2},
        {"role": "user", "content": dataset},
        # {"role": "user", "content": Q3},
        # {"role": "assistant", "content": A3},
    ]
    my_llm = chat_with_llm(functions_list=functions_list, tools=tools)
    content = my_llm.check_code_run(messages=messages, model="glm4")
    print(content)

    command_key = ""

    def get_command():
        print("请按下s键开始录音,q退出程序。")
        global command_key  # 因为后续要对这个command_key 进行修改，所以这里需要声明成global
        command_key = input()  # 获取输入的命令

    while True:
        get_command()
        if command_key == "s":
            user_input = get_voice2text()
            print("用户语音识别结果： " + user_input)
            user_input = user_input + "请一步步思考并解决问题。"
            messages.append({"role": "user", "content": user_input})
            content = my_llm.check_code_run(messages=messages, model="glm4")
            # display(Markdown(content))
            print(content)
        elif command_key == "q":
            break
        else:
            continue
