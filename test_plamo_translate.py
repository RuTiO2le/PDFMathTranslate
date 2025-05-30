# import vllm

# # max_model_len/max_num_batched_tokens can be increased when running on a GPU with substantial memory.
# # NOTE: Switch to "pfnet/plamo-2-translate-base" to try the base model.
# llm = vllm.LLM(model="pfnet/plamo-2-translate", trust_remote_code=True, max_model_len=2000, max_num_batched_tokens=2000)

# prompt = r'''<|plamo:op|>dataset
# translation
# <|plamo:op|>input lang=English
# Write the text to be translated here.
# <|plamo:op|>output lang=Japanese
# '''

# responses = llm.generate([prompt] * 1, sampling_params=vllm.SamplingParams(temperature=0, max_tokens=1024, stop=["<|plamo:op|>"]))
# # NOTE: This outputs "ここに翻訳するテキストを入力してください。".
# print(responses[0].outputs[0].text)



from mlx_lm import load, generate

# モデルのロード
stop_token = "<|plamo:op|>"
model, tokenizer = load(
    "mlx-community/plamo-2-translate",
    tokenizer_config={"eos_token": stop_token, "trust_remote_code": True},
)

source_text = "When I was a child, I loved to play outside with my friends. We would run around, climb trees, and explore the world around us. Those were some of the happiest times of my life."

# プロンプト
prompt = rf'''<|plamo:op|>dataset
translation
<|plamo:op|>input lang=English
{source_text}
<|plamo:op|>output lang=Japanese
'''
message = [{"role": "user", "content": prompt}]
prompt = tokenizer.apply_chat_template(
    message,
    add_generation_prompt=True,
)

# eos_token_id = tokenizer.convert_tokens_to_ids(stop_token)
# print(eos_token_id)
# print(tokenizer.eos_token_id)
# print(tokenizer.eos_token)


# output = generate(model, tokenizer, prompt, verbose=True)

# if stop_token in output:
#     clean_output = output.split(stop_token)[0]
# else:
#     clean_output = output

# print(clean_output.strip())


# generateを独自実装
import mlx.core as mx
import mlx.nn as nn
from mlx_lm import load

def generate_until_eos(model, tokenizer, prompt: str, eos_token_id=None, max_new_tokens=100):
    # Tokenize with encode
    input_ids = tokenizer.encode(prompt)
    generated_ids = []
    eos_reached = False

    for _ in range(max_new_tokens):
        logits = model(mx.array([input_ids[:] + generated_ids]))[0]
        next_token_logits = logits[-1]
        next_token = int(mx.argmax(next_token_logits).item())
        # print(f"Next token: {next_token} ({tokenizer.decode([next_token])})")
        
        generated_ids.append(next_token)

        if eos_token_id is not None and next_token == eos_token_id:
            eos_reached = True
            break

    output_text = tokenizer.decode(generated_ids, skip_special_tokens=True)
    return output_text, eos_reached

# EOS トークン ID を取得
eos_token_id = tokenizer.convert_tokens_to_ids("<|plamo:op|>")

# 自作 generate 関数を呼び出し
output, stopped = generate_until_eos(model, tokenizer, prompt, eos_token_id)

print("--- Output ---")
print(output)