import json
import os
import sys
import httpx

def main():
    raw_manifest = sys.stdin.read()
    if not raw_manifest.strip():
        print("No manifest found from prepare_digest.py", file=sys.stderr)
        sys.exit(1)
        
    manifest = json.loads(raw_manifest)
    payload_file = manifest.get("payload_file")
    
    if not payload_file or not os.path.exists(payload_file):
        print("Payload file not found!", file=sys.stderr)
        sys.exit(1)
        
    with open(payload_file, "r", encoding="utf-8") as f:
        payload = json.loads(f.read())
        
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY environment variable is missing.", file=sys.stderr)
        sys.exit(1)
        
    # Prepare data subset
    data_for_prompt = {
        "x": payload.get("x", []),
        "podcasts": payload.get("podcasts", []),
        "papers": payload.get("papers", []),
        "articles": payload.get("articles", [])
    }
    
    output_contract = payload.get("output_contract", {})
    
    user_prompt = f"""
请根据以下 JSON 格式的原始资讯，帮我撰写一份今天的「AI Signal 日报」。
要求：
1. 请用优美的中文排版，采用 Markdown 格式。
2. 包含适当的二级标题（如：播客精选、推特动态、最新论文等）。
3. 请为每条内容生成一段精简的中文摘要，并务必保留原始的 URL 链接。
4. 滤除掉无意义的寒暄内容。

原始配置和规则：
{json.dumps(output_contract, ensure_ascii=False)}

今日新闻原始数据：
{json.dumps(data_for_prompt, ensure_ascii=False)}
"""
    
    print("Calling Gemini API...", file=sys.stderr)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    resp = httpx.post(url, json={
        "contents": [{"parts": [{"text": user_prompt}]}],
        "systemInstruction": {"parts": [{"text": "You are a professional AI news digest writer."}]}
    }, timeout=120)
    
    if resp.is_error:
        print(f"❌ Gemini API Error: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
        
    result = resp.json()
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    
    # 清理 Gemini 输出时可能带有的 markdown 代码块符号
    if text.startswith("```markdown"):
        text = text[11:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
        
    print(text.strip())

if __name__ == "__main__":
    main()
