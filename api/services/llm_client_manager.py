import logging
import re
from openai import AzureOpenAI, APIError
from api.core_config import app_configs

logger = logging.getLogger(__name__)

azure_openai_client = None

def initialize_openai_client():
    """根据 app_configs 初始化或重新初始化全局 Azure OpenAI 客户端。"""
    global azure_openai_client
    try:
        api_key = app_configs.get("AZURE_OPENAI_API_KEY", "xxx")
        api_version = app_configs.get("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
        azure_endpoint = app_configs.get("AZURE_OPENAI_ENDPOINT", "https://aiyaya-llm-openai.openai.azure.com/")
        deployment_name = app_configs.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini")

        if not api_key or api_key == "xxxx-xxxx-xxxx-xxxx":
            logger.warning("警告: Azure OpenAI API Key 未配置或为占位符。Azure OpenAI 客户端将不会初始化。")
            azure_openai_client = None
            return
            
        if not azure_endpoint or not deployment_name:
            logger.warning("警告: Azure OpenAI 端点或部署名称未配置。Azure OpenAI 客户端将不会初始化。")
            azure_openai_client = None
            return

        logger.info(f"正在初始化 Azure OpenAI 客户端，部署: {deployment_name}")
        azure_openai_client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            azure_deployment=deployment_name
        )
        logger.info("Azure OpenAI 客户端已成功初始化/重新初始化。")
    except Exception as e:
        logger.error(f"初始化 OpenAI 客户端时出错: {e}")
        logger.error(
            "请确保通过管理面板或环境变量设置了 OpenAI API Key，并且基础 URL (如果使用) 正确。")
        azure_openai_client = None


def get_openai_client():
    """获取 Azure OpenAI 客户端实例，如果未初始化则尝试初始化。"""
    global azure_openai_client
    if azure_openai_client is None:
        logger.info("Azure OpenAI 客户端为 None，尝试初始化...")
        initialize_openai_client()
    return azure_openai_client


def execute_llm_chat_completion(client, model_name: str, system_prompt: str, user_prompt: str, context_description: str,
                                response_format_type: str = None):
    """
    执行 LLM 请求。

    :param client: Azure OpenAI 客户端实例。
    :param model_name: 要使用的模型部署名称。
    :param system_prompt: 系统提示。
    :param user_prompt: 用户原始提示。
    :param context_description: 用于 _prepare_llm_user_prompt 的上下文描述。
    :param response_format_type: 可选，响应格式类型 (例如 "json_object")。
    :return: LLM 的响应内容。
    """

    completion_params = {
        "model": model_name,  # 对于 Azure OpenAI，这应该是部署名称
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    if response_format_type:
        completion_params["response_format"] = {"type": response_format_type}

    try:
        response = client.chat.completions.create(**completion_params)
        if response and response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if message and message.content:
                # 首先获取原始响应内容
                raw_content = message.content
                # 移除 <think>...</think> 标签及其内容
                # re.DOTALL 使 . 匹配换行符
                content_after_think_tags = re.sub(r"<think>.*?</?think>", "", raw_content, flags=re.DOTALL)
                # 尝试提取被 ```...``` 包裹的内容，可选地处理语言标记如 json
                # re.DOTALL 确保 . 可以匹配换行符，处理多行 JSON
                # \s* 用于匹配 ``` 和实际内容之间，以及内容和末尾 ``` 之间的空白字符
                # (?:\w*\s*)? 是一个可选的非捕获组，匹配可选的语言名称后跟可选空格
                markdown_json_match = re.search(r"```(?:\w*\s*)?([\s\S]*?)\s*```", content_after_think_tags, re.DOTALL)

                if markdown_json_match:
                    # 如果匹配到，提取第一个捕获组的内容
                    final_content = markdown_json_match.group(1)
                    logger.info(f"从 Markdown 代码块中提取了 JSON 内容 ({context_description})。")
                else:
                    # 如果没有匹配到 Markdown 代码块，则假定内容已经是 JSON 或纯文本
                    final_content = content_after_think_tags
                    # 然后去除首尾空白
                return final_content.strip()
            else:
                logger.error(f"LLM 响应中缺少 'content' 字段 ({context_description})。响应: {response}")
                return f"Error: LLM response missing content for {context_description}."
        else:
            logger.error(f"LLM 响应无效或 choices 为空 ({context_description})。响应: {response}")
            return f"Error: Invalid LLM response or empty choices for {context_description}."
    except APIError as e:  # 使用导入的 APIError
        logger.error(f"LLM API 请求失败 ({context_description}): {e}")
        return f"Error: LLM API request failed for {context_description}: {str(e)}"
    except Exception as e:
        logger.error(f"处理 LLM 响应时发生意外错误 ({context_description}): {e}")
        return f"Error: Unexpected error during LLM processing for {context_description}: {str(e)}"
