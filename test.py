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
    # 创建ZhipuAI 客户端
    ZhipuAI.api_key = ""

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
        {"role": "user", "content": dataset},
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
            print(content)
        elif command_key == "q":
            break
        else:
            continue
