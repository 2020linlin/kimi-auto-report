import os
import requests
import json
import re
from datetime import datetime
from duckduckgo_search import DDGS

KEYWORDS = {
    "底盘细胞": ["光甘草定 重组酵母", "光甘草定 解脂耶氏酵母", "Glabridin yeast"],
    "代谢通路": ["光甘草定 异黄酮合成通路", "光甘草定 前体供应", "光甘草定 CYP"],
    "酶工程": ["光甘草定 查耳酮合酶", "光甘草定 定向进化", "光甘草定 关键酶"],
    "发酵工艺": ["光甘草定 发酵 产量", "光甘草定 滴度 g/L", "Glabridin fermentation"],
    "专利": ["光甘草定 合成生物学 专利", "Glabridin biosynthesis patent"]
}

def search_papers(keyword):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(keyword, max_results=5, timelimit="m")
            items = []
            for r in results:
                title_lower = r['title'].lower()
                if any(x in title_lower for x in ['buy', 'price', 'supplier', 'market', 'cost']):
                    continue
                items.append({
                    "title": r['title'],
                    "url": r['href'],
                    "snippet": r['body'][:400]
                })
            return items
    except:
        return []

def extract_data(text):
    patterns = {
        "滴度": r'(\d+\.?\d*)\s*(mg/l|g/l)',
        "产率": r'(\d+\.?\d*)%',
        "时间": r'(\d+)\s*(h|d)'
    }
    found = {}
    for k, p in patterns.items():
        m = re.findall(p, text, re.I)
        if m:
            found[k] = m[:2]
    return found

def analyze(category, articles):
    if not articles:
        return "本周无新进展。"
    
    api_key = os.getenv('MOONSHOT_API_KEY')
    if not api_key:
        return "API未配置"
    
    context = "\n\n".join([f"{i+1}. {a['title']}\n{a['snippet']}" for i, a in enumerate(articles[:8])])
    data = extract_data(context)
    
    prompt = f"""你是一名合成生物学专家，分析光甘草定【{category}】方向的技术情报：

{context}

提取到的数据：{json.dumps(data, ensure_ascii=False)}

请按以下格式分析：
1. 技术突破点（2-3条）
2. 关键指标（滴度、产率等）
3. 技术成熟度（🔴概念验证/🟡中试前/🟢产业化）
4. 对我们项目的建议（具体可操作的实验方向）

注意：光甘草定是异黄酮类，合成路径涉及查耳酮合酶、CYP450等，常用酵母底盘。"""
    
    try:
        resp = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "moonshot-v1-32k",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            },
            timeout=120
        )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"分析失败: {e}"

def main():
    report = [f"# 光甘草定合成生物学周报\n生成时间：{datetime.now().strftime('%Y-%m-%d')}\n"]
    
    for cat, kws in KEYWORDS.items():
        print(f"搜索：{cat}")
        all_results = []
        for kw in kws:
            all_results.extend(search_papers(kw))
        
        seen = set()
        unique = []
        for r in all_results:
            if r['url'] not in seen:
                seen.add(r['url'])
                unique.append(r)
        
        analysis = analyze(cat, unique)
        report.append(f"\n## {cat}\n{analysis}\n")
    
    filename = f"report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
    
    print(f"报告生成：{filename}")

if __name__ == "__main__":
    main()
