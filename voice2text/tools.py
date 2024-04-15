import pandas as pd
import tiktoken
import openai
from IPython.display import display, Code, Markdown
import pandas as pd
import json
import requests
from .voice2text import WsParam, RecognitionWebsocket
import time
from zhipuai import ZhipuAI


class chat_with_llm:
    def __init__(self, functions_list=None, tools=None):
        """
        :param functions_list: 可选参数，默认为None，可以设置为包含全部外部函数的列表对象
        :param tools: 可选参数，默认为None，可以设置为包含全部外部函数参数解释Schema格式列表
        """
        self.functions_list = functions_list
        self.tools = tools

    def get_glm_response(self, messages, tools=None, model="glm4"):
        """
        单次GLM模型响应函数，能够正常获取模型响应，并在模型无法正常响应时暂停模型调用，\
        并在休息一分钟之后继续调用模型。最多尝试三次。
        :param messages: 必要参数，字典类型，输入到Chat模型的messages参数对象
        :param tools: 可选参数，默认为None，可以设置为包含全部外部函数参数解释Schema格式列表
        :param model: Chat模型，可选参数，默认模型为glm-4
        :return：Chat模型输出结果
        """
        attempts = 0
        max_attempts = 3

        while attempts < max_attempts:
            try:
                if model == "glm4":
                    ZhipuAI.api_key = (
                        "335590e406917fcf09df3819ca20c3db.tSewYSL13MLugE1y"
                    )
                    client = ZhipuAI(api_key=ZhipuAI.api_key)
                    response = client.chat.completions.create(
                        model="glm-4", messages=messages
                    )
                else:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=messages,  # 使用函数参数
                        tools=tools,
                    )
                return response  # 成功时返回响应
            except Exception as e:  # 捕获所有异常
                print(f"发生错误：{e}")
                attempts += 1
                if attempts < max_attempts:
                    print("等待1分钟后重试...")
                    time.sleep(60)  # 等待1分钟
                else:
                    print("尝试次数过多，停止尝试。")
                    return None  # 在所有尝试后返回 None

    def check_code_run(self, messages, model="glm4", auto_run=True):
        """
        能够自动执行外部函数调用的Chat对话模型，专门用于代码解释器的构建过程，可以通过auto_run参数设置，决定是否自动执行代码
        :param messages: 必要参数，字典类型，输入到Chat模型的messages参数对象
        :param model: Chat模型，可选参数，默认模型为glm-4
        :auto_run：在调用外部函数的情况下，是否自动进行Second Response。该参数只在外部函数存在时起作用
        :return：Chat模型输出结果
        """

        # 如果没有外部函数库，则执行普通的对话任务
        if self.tools == None:
            response = self.get_glm_response(model=model, messages=messages)
            response_message = response.choices[0].message

        # 若存在外部函数库，则需要灵活选取外部函数并进行回答
        else:

            # 创建外部函数库字典
            available_functions = {func.__name__: func for func in self.functions_list}

            # first response
            response = self.get_glm_response(
                model=model, messages=messages, tools=self.tools
            )
            response_message = response.choices[0].message

            # 判断返回结果是否存在function_call，即判断是否需要调用外部函数来回答问题
            # 若存在function_call，则执行Function calling流程
            # 需要调用外部函数，由于考虑到可能存在多次Function calling情况，这里创建While循环
            # While循环停止条件：response_message不包含function_call
            while response_message.tool_calls != None:
                print("正在调用外部函数...")

                try:
                    # 获取函数名
                    function_name = response_message.tool_calls[0].function.name
                    # 获取函数对象
                    fuction_to_call = available_functions[function_name]

                    # 获取函数参数
                    function_args = json.loads(
                        response_message.tool_calls[0].function.arguments
                    )
                    # 仅仅调用python_inter函数时使用
                    # 将当前操作空间中的全局变量添加到外部函数中
                    function_args["g"] = globals()

                    def convert_to_markdown(code, language):
                        return f"```{language}\n{code}\n```"

                    if function_args.get("py_code"):
                        code = function_args["py_code"]
                        markdown_code = convert_to_markdown(code, "python")
                        print("即将执行以下代码：")

                    else:
                        markdown_code = function_args
                    # display(Markdown(markdown_code))

                    if auto_run == False:
                        res = input(
                            "请确认是否运行上述代码（1），或者退出本次运行过程（2）"
                        )

                        if res == "2":
                            print("终止运行")
                            return None

                    print("正在执行代码，请稍后...")

                    # 将函数参数输入到函数中，获取函数计算结果
                    function_response = fuction_to_call(**function_args)

                    print("外部函数已运行完毕")

                    # messages中拼接first response消息
                    messages.append(response_message.model_dump())

                    # messages中拼接函数输出结果
                    messages.append(
                        {
                            "role": "tool",
                            "content": function_response,
                            "tool_call_id": response_message.tool_calls[0].id,
                        }
                    )

                    # 第二次调用模型
                    second_response = self.get_glm_response(
                        messages=messages, tools=self.tools, model=model
                    )

                    # 更新response_message
                    response_message = second_response.choices[0].message
                    print("更新response_message")
                except Exception as e:
                    print("json格式对象创建失败，正在重新运行")
                    # messages = check_code_run(
                    #     messages=messages,
                    #     model=model,
                    #     auto_run=auto_run,
                    # )
                    return messages

        # While条件不满足，或执行完While循环之后，提取返回结果
        final_response = response_message

        display(Markdown(final_response.content))

        # messages.append(final_response.model_dump())

        return final_response.content
