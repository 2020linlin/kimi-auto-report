import os
import requests
import json
import re
from datetime import datetime
from duckduckgo_search import DDGS

MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY', '')

KEYWORDS = {
    "生物合成-中文": ["藏花酸 生物合成", "藏花酸 酵母合成", "藏花酸 重组菌株", "西红花酸 微生物合成"],
    "生物合成-英文": ["Crocetin biosynthesis", "Crocetin yeast synthesis", "Crocetin synthetic biology", "Crocetin heterologous expression"],
    "合成途径-中文": ["藏花酸 合成途径", "藏花酸 类胡萝卜素", "藏花酸 CCD酶", "藏花酸 ALDH酶"],
    "合成途径-英文": ["Crocetin biosynthetic pathway", "Crocetin carotenoid pathway", "Crocetin CCD cleavage enzyme", "Crocetin ALDH enzyme"],
    "酶工程-中文": ["藏花酸 类胡萝卜素裂解双加氧酶", "藏花酸 醛脱氢酶", "藏花酸 酶催化"],
    "酶工程-英文": ["Crocetin CCD enzyme", "Crocetin carotenoid cleavage dioxygenase", "Crocetin ALDH"],
    "发酵优化-中文": ["藏花酸 发酵产量", "藏花酸 滴度", "藏花酸 发酵工艺"],
    "发酵优化-英文": ["Crocetin fermentation titer", "Crocetin yield optimization", "Crocetin bioprocess"],
    "专利-中文": ["藏花酸 合成生物学 专利", "藏花酸 制备方法", "西红花酸 专利"],
    "专利-英文": ["Crocetin biosynthesis patent", "Crocetin production patent", "Crocetin synthetic biology patent"]
}

def search_web(keyword, region="wt-wt"):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(keyword, max_results=5, timelimit="m", region=region)
            items = []
            for r in results:
                title_lower = r['title'].lower()
                if any(x in title_lower for x in ['buy', 'price', 'supplier', 'market', 'shop', 'saffron price']):
                    continue
                items.append({"title": r['title'], "url": r['href'], "snippet": r['body'][:500]})
            return items
    except:
        return []

def search_news(keyword):
    try:
        with DDGS() as ddgs:
            results = ddgs.news(keyword, max_results=3, timelimit="w")
            return [{"title": r['title'], "url": r['url'], "snippet": r['body'][:400]} for r in results]
    except:
        return []

def search_academic(keyword):
    academic_results = []
    for query in [f"{keyword} site:pubmed.ncbi.nlm.nih.gov", f"{keyword} site:scholar.google.com"]:
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=3, timelimit="m")
                for r in results:
                    if any(x in r['href'] for x in ['pubmed', 'ncbi', 'scholar.google', '.edu']):
                        academic_results.append({"title": r['title'], "url": r['href'], "snippet": r['body'][:500]})
        except:
            continue
    return academic_results

def extract_data(text):
    patterns = {"滴度": r'(\d+\.?\d*)\s*(mg/l|g/l)', "产率": r'(\d+\.?\d*)%', "时间": r'(\d+)\s*(h|d)'}
    found = {}
    for k, p in patterns.items():
        m = re.findall(p, text, re.I)
        if m:
            found[k] = m[:2]
    return found

def analyze(category, articles):
    if not articles:
        return "本周暂无新文献。"
    
    cn = [a for a in articles if any('\u4e00' <= c <= '\u9fff' for c in a['title'])]
    en = [a for a in articles if a not in cn]
    
    context = f"【中文{len(cn)}条】\n" + "\n".join([f"{i+1}. {a['title']}\n{a['snippet'][:300]}" for i, a in enumerate(cn[:5])])
    context += f"\n\n【英文{len(en)}条】\n" + "\n\n".join([f"{i+1}. {a['title']}\n{a['snippet'][:300]}" for i, a in enumerate(en[:5])])
    
    data = extract_data(context)
    
    prompt = f"""你是天然产物合成生物学专家，分析藏花酸（Crocetin）【{category}】文献：

{context}

数据：{json.dumps(data, ensure_ascii=False) if data else "无"}

请分析：
1. 中文研究进展（2-3条）
2. 国际前沿（2-3条）
3. 技术对比
4. 可操作建议

藏花酸（Crocetin）：类胡萝卜素衍生物，西红花主要活性成分，C20H24O4。
合成路径：番茄红素/β-胡萝卜素→玉米黄质→藏花酸（需CCD裂解酶+ALDH氧化酶）。
关键酶：CCD（类胡萝卜素裂解双加氧酶）、ALDH（醛脱氢酶）。
应用：抗肿瘤、抗氧化、神经保护、心血管保护。"""

    try:
        resp = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers={"Authorization": f"Bearer {MOONSHOT_API_KEY}"},
            json={"model": "moonshot-v1-32k", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
            timeout=150
        )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"分析失败: {e}"

def main():
    report = [f"# 藏花酸（Crocetin）情报周报\n**时间**：{datetime.now().strftime('%Y-%m-%d')}**\n\n---\n"]
    total_cn = total_en = 0
    
    for cat, kws in KEYWORDS.items():
        print(f"搜索：{cat}")
        results = []
        for kw in kws:
            if "英文" in cat:
                r = search_web(kw, "wt-wt") + search_academic(kw)
                total_en += len(r)
            else:
                r = search_web(kw, "cn-zh") + search_news(kw)
                total_cn += len(r)
            results.extend(r)
        
        seen = set()
        unique = [r for r in results if not (r['url'] in seen or seen.add(r['url']))]
        
        analysis = analyze(cat, unique)
        report.append(f"\n## {cat}\n{analysis}\n")
    
    report.append(f"\n---\n## 统计\n- 中文：{total_cn}条\n- 英文：{total_en}条\n")
    
    filename = f"Crocetin_report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("".join(report))
    print(f"生成：{filename}")

if __name__ == "__main__":
    main()
