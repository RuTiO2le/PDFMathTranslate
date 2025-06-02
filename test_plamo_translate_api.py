import random
from typing import Optional
from transformers import AutoTokenizer
import os

import streamlit as st
from openai import OpenAI

# tokenizer = AutoTokenizer.from_pretrained("./tokenizer", trust_remote_code=True)

BASE_URLS = {
    "plamo2-8b-translation": os.getenv("PLAMO_TRANSLATE_BASE_URL"),
    "plamo2-8b-translation-sft": os.getenv("PLAMO_TRANSLATE_SFT_BASE_URL"),
    # "plamo-2.0-translate": os.getenv("PLAMO_TRANSLATE_BASE_URL")
}

MODEL_NAMES = {
    "plamo2-8b-translation": "plamo-2-8b-translation-32k",
    "plamo2-8b-translation-sft": "plamo-2-8b-translation-32k",
    # "plamo-2.0-translate": "plamo-2.0-translate",
}


def translate(
    text: str,
    model_name: str,
    base_url: str,
    input_lang: str = "Japanese|English",
    output_lang: str = "Japanese|English",
    temperature: float = 0.0,
    best_of: int = 1,
    type: Optional[str] = None,
    stream: bool = False,
):
    client = OpenAI(base_url=base_url, api_key="a")
    is_started = False
    output_lang_ditected = ""

    if output_lang == "Japanese|English":
        output_lang = " lang="
    else:
        output_lang_ditected = output_lang
        output_lang = f" lang={output_lang}\n"
        is_started = True
    if type is not None:
        type = f" style={type}"
    else:
        type = ""
    messages = [
        f"""<|plamo:op|>dataset
translation
<|plamo:op|>input{type} lang={input_lang}
{text}
<|plamo:op|>output{output_lang}"""
    ]
    output = ""
    # n_tokens = len(tokenizer.encode(messages[0]))
    # max_new_tokens = 30000 - n_tokens

    if stream:
        try:
            for x in client.completions.create(
                prompt=messages,  # type: ignore
                model=model_name,
                temperature=temperature,
                max_tokens=15000,
                stop=["<|plamo:op|>"],
                stream=True,
            ):
                output += x.choices[0].text
                if not is_started and "\n" in output:
                    is_started = True
                    output_lang_ditected, output = output.split("\n", 1)
                yield output, output_lang_ditected
        except Exception as e:
            print(f"Error: {e}")
            yield f"Error: {e}", ""
    else:
        try:
            response = client.completions.create(
                prompt=messages[0],
                model=model_name,
                temperature=temperature,
                max_tokens=15000,
                stop=["<|plamo:op|>"],
            )
            if "\n" in output:
                _, output = response.choices[0].text.split("\n", 1)
            return output
        except Exception as e:
            print(f"Error: {e}")
            return f"Error: {e}", ""

# 言語選択
def get_lang_choices():
    return {
        "自動": "Japanese|English",
        "日本語": "Japanese",
        "やさしい日本語": "Japanese(easy)",
        "英語": "English",
        "イギリス英語": "English(UK)",
        "フランス語": "French",
        "ドイツ語": "German",
        "スペイン語": "Spanish",
        "タイ語": "Thai",
        "ポルトガル語": "Portuguese",
        "中国語(簡体字)": "Chinese",
        "中国語(繁体字)": "Taiwanese",
        "韓国語": "Korean",
        "アラビア語": "Arabic",
        "チェコ語": "Czech",
        "デンマーク語": "Danish",
        "オランダ語": "Dutch",
        "フィンランド語": "Finnish",
        "ギリシャ語": "Greek",
        "ハンガリー語": "Hungarian",
        "インドネシア語": "Indonesian",
        "イタリア語": "Italian",
        "ノルウェー語": "Norwegian",
        "ポーランド語": "Polish",
        "ルーマニア語": "Romanian",
        "ロシア語": "Russian",
        "スウェーデン語": "Swedish",
        "トルコ語": "Turkish",
        "ウクライナ語": "Ukrainian",
        "ベトナム語": "Vietnamese",
    }

lang_dict = get_lang_choices()

def main(text: str, model_name="plamo2-8b-translation-sft", type=None):

    if "translation" not in model_name:
        types = ["None"]

    output = translate(
        text=text,
        model_name=MODEL_NAMES[model_name],
        base_url=BASE_URLS[model_name],
        type=type,
    )
    print(f"Translated text: {output}")


def main2(text, model_name="plamo2-8b-translation-sft", type=None):
    client = OpenAI(base_url=BASE_URLS[model_name], api_key="a")

    if type is not None:
        type = f" style={type}"
    else:
        type = ""

    message = f"""<|plamo:op|>dataset
translation
<|plamo:op|>input{type} lang=Japanese|English
{text}
<|plamo:op|>output lang=Japanese|English"""

    response = client.completions.create(
        prompt=message,
        model=MODEL_NAMES[model_name],
        temperature=0.,
        max_tokens=15000,
        stop=["<|plamo:op|>"],
    )
    _, output = response.choices[0].text.split("\n", 1)
    print(f"Translated text: {output}")



if __name__ == "__main__":
    types = [
        "None",
        "dialog",  # LLM conversation style
        "chat",  # Slack/Discord style
        "web",  # Web corpus
        "code",  # Programs
        "pdf",  # Texts excted from PDF files
        "news",  # News articles
        "academic",  # Academic papers
        "document",  # Technical documents
        "wikipedia",  # Wikipedia articles
        "legal",  # Laws
        "contract",  # Contracts
        "financial_summary",  # Financial summary (a.k.a. Tanshin)
    ]

    text = """1.1 Sequential decision making
Reinforcement learning or RL is a class of methods for solving various kinds of sequential decision making tasks. In such tasks, we want to design an agent that interacts with an external environment. The agent maintains an internal state zt, which it passes to its policy π to choose an action at = π(zt). The environment responds by sending back an observation ot+1, which the agent uses to update its internal state using the state-update function zt+1 = SU(zt,at,ot+1). See Figure 1.1 for an illustration.
Note that we often assume that the observation ot corresponds to the true environment or world state wt; in this case, we denote the internal agent state and external environment state by the same letter, namely st. We discuss this issue in more detail in Section 1.1.3.
RL is more complicated than supervised learning (e.g., training a classifier) or self-supervised learning (e.g., training a language model), because this framework is very general: there are many assumptions we can make about the environment and its observations ot, and many choices we can make about the form the agent’s internal state zt and policy π, as well the ways to update these things using U. We will study many different combinations in the rest of this document. The right choice ultimately depends on which real-world
application you are interested in solving.1.
"""

    # main(text)
    main2(text, type="academic")
    # main2(text, model_name="plamo2-8b-translation", type="academic")
    # main2(text, model_name="plamo-2.0-translate") # APIがないので無理
