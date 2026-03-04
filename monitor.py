import os
import requests
import json
import re
from datetime import datetime
from duckduckgo_search import DDGS

# 中英文双语关键词配置
KEYWORDS = {
    "底盘细胞-中文": ["光甘草定 重组酵母", "光甘草定 解脂耶氏酵母"],
    "底盘细胞-英文": ["Glabridin yeast chassis", "Glabridin Yarrowia lipolytica", "Glabridin Saccharomyces cerevisiae"],
    
    "代谢通路-中文": ["光甘草定 异黄酮合成通路", "光甘草定 前体供应", "光甘草定 CYP450"],
    "代谢通路-英文": ["Glabridin isoflavone biosynthesis pathway", "Glabridin precursor supply", "Glabridin P450 enzyme"],
    
    "酶工程-中文": ["光甘草定 查耳酮合酶", "光甘草定 定向进化", "光甘草定 关键酶"],
    "酶工程-英文": ["Glabridin chalcone synthase", "Glabridin directed evolution", "Glabridin key enzyme engineering"],
    
    "发酵工艺-中文": ["光甘草定 发酵 产量", "光甘草定 滴度 g/L"],
    "发酵工艺-英文": ["Glabridin fermentation titer", "Glabridin yield optimization", "Glabridin bioprocess"],
    
    "专利-中文": ["光甘草定 合成生物学 专利", "光甘草定 微生物合成 发明"],
    "专利-英文": ["Glabridin biosynthesis patent", "Glabridin synthetic biology patent", "Glabridin microbial production patent"]
}

# 学术数据库搜索配置
ACADEMIC_SOURCES = {
    "PubMed": "https://pubmed.ncbi.nlm.nih.gov/?term=",
    "Google Scholar": "https://scholar.google.com/scholar?q=",
    "CNKI": "https://www.cnki.net/",
    "万方": "https://www.wanfangdata.com.cn/"
}

def search_web(keyword, region="wt-wt"):
    """通用网页搜索"""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(keyword, max_results=5, timelimit="m", region=region)
            items = []
            for r in results:
                title_lower = r['title'].lower()
                # 过滤商业内容
                if any(x in title_lower for x in ['buy', 'price', 'supplier', 'vendor', 'market', 'shop', 'amazon', 'ebay']):
                    continue
                items.append({
                    "title": r['title'],
                    "url": r['href'],
                    "snippet": r['body'][:500],
                    "source": "web"
                })
            return items
    except Exception as e:
        print(f"搜索失败 [{keyword}]: {e}")
        return []

def search_news(keyword):
    """新闻搜索（适合最新动态）"""
    try:
        with DDGS() as ddgs:
            results = ddgs.news(keyword, max_results=3, timelimit="w")
            items = []
            for r in results:
                items.append({
                    "title": r['title'],
                    "url": r['url'],
                    "snippet": r['body'][:400],
                    "source": "news",
                    "date": r.get('date', 'unknown')
                })
            return items
    except:
        return []

def search_academic(keyword):
    """学术文献搜索（优先Google Scholar和PubMed）"""
    academic_results = []
    
    # 通过特定site搜索学术资源
    academic_queries = [
        f"{keyword} site:pubmed.ncbi.nlm.nih.gov",
        f"{keyword} site:scholar.google.com",
        f"{keyword} filetype:pdf"
    ]
    
    for query in academic_queries[:2]:  # 取前2个
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=3, timelimit="m")
                for r in results:
                    if any(x in r['href'] for x in ['pubmed', 'ncbi', 'scholar.google', '.edu', '.ac.cn']):
                        academic_results.append({
                            "title": r['title'],
                            "url": r['href'],
                            "snippet": r['body'][:500],
                            "source": "academic"
                        })
        except:
            continue
    
    return academic_results

def extract_tech_data(text):
    """提取技术指标"""
    patterns = {
        "滴度": r'(\d+\.?\d*)\s*(mg/l|g/l|μg/ml|ug/ml)',
        "产率": r'(\d+\.?\d*)\s*%',
        "转化率": r'conversion\s*(\d+\.?\d*)%',
        "发酵时间": r'(\d+)\s*(h|hours|小时|天|d)',
        "纯度": r'purity\s*(\d+\.?\d*)%|纯度\s*(\d+\.?\d*)%'
    }
    found = {}
    for k, p in patterns.items():
        m = re.findall(p, text, re.IGNORECASE)
        if m:
            found[k] = m[:3]
    return found

def analyze_with_kimi(category, articles):
    """Kimi智能分析"""
    if not articles:
        return "本周该方向暂无新文献。"
    
    api_key = os.getenv('MOONSHOT_API_KEY')
    if not api_key:
        return "⚠️ 未配置 MOONSHOT_API_KEY"
    
    # 区分中英文来源
    cn_articles = [a for a in articles if any('\u4e00' <= c <= '\u9fff' for c in a['title'])]
    en_articles = [a for a in articles if a not in cn_articles]
    
    context = f"【中文文献 {len(cn_articles)} 条】\n"
    for i, a in enumerate(cn_articles[:5]):
        context += f"{i+1}. {a['title']}\n{a['snippet'][:300]}\n\n"
    
    context += f"\n【英文文献 {len(en_articles)} 条】\n"
    for i, a in enumerate(en_articles[:5]):
        context += f"{i+1}. {a['title']}\n{a['snippet'][:300]}\n\n"
    
    data = extract_tech_data(context)
    
    prompt = f"""你是一名合成生物学研发专家，请对以下【{category}】方向的中英文文献进行综合分析：

{context}

【提取的技术数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}

【分析要求】：
1. **中文研究进展**（2-3条）
   - 国内高校/研究所的最新成果
   - 专利布局情况

2. **国际研究前沿**（2-3条）
   - 国外顶级期刊（Nature/Science/Metabolic Engineering等）相关研究
   - 国际团队的技术突破

3. **技术对比分析**
   - 中外技术路线差异（如：国内重发酵优化 vs 国外重通路设计）
   - 关键性能指标对比（滴度、产率、纯度）

4. **可操作建议**
   - 哪些中文技术容易快速跟进？
   - 哪些国外前沿值得长期布局？
   - 建议阅读的3篇核心文献（附链接）

【专业提示】：
- 光甘草定（Glabridin, CAS 59870-68-7）为异黄酮类化合物
- 关键合成路径：苯丙氨酸→查耳酮→甘草素→光甘草定
- 常用底盘：酿酒酵母（S. cerevisiae）、解脂耶氏酵母（Y. lipolytica）
- 关键酶：CHS（查耳酮合酶）、CHR（查耳酮还原酶）、IFS（异黄酮合酶）、CYP450

输出格式：Markdown，专业术语准确，中英文文献分开总结。"""

    try:
        resp = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "moonshot-v1-32k",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2
            },
            timeout=150
        )
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"分析失败: {e}"

def main():
    report = [
        f"# 🧬 光甘草定合成生物学情报周报（中英双语）\n",
        f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"**数据来源**：Web搜索 | 学术数据库 | 专利库\n",
        f"**监控范围**：中文文献（知网/万方/专利）| 英文文献（PubMed/Google Scholar）\n\n---\n"
    ]
    
    total_cn = 0
    total_en = 0
    
    for category, keywords in KEYWORDS.items():
        print(f"🔍 检索：{category}")
        
        all_results = []
        for kw in keywords:
            if "英文" in category:
                # 英文搜索
                results = search_web(kw, region="wt-wt")
                results += search_academic(kw)
                total_en += len(results)
            else:
                # 中文搜索
                results = search_web(kw, region="cn-zh")
                results += search_news(kw)
                total_cn += len(results)
            
            all_results.extend(results)
        
        # 去重
        seen = set()
        unique = []
        for r in all_results:
            if r['url'] not in seen:
                seen.add(r['url'])
                unique.append(r)
        
        if unique:
            analysis = analyze_with_kimi(category, unique)
            report.append(f"\n## {category}\n{analysis}\n")
        else:
            report.append(f"\n## {category}\n*本周该方向暂无新文献*\n")
    
    # 统计汇总
    report.append(f"\n---\n## 📊 本周文献统计\n")
    report.append(f"- 中文文献来源：{total_cn} 条\n")
    report.append(f"- 英文文献来源：{total_en} 条\n")
    report.append(f"- 总监控关键词：{len(KEYWORDS)} 个维度\n")
    
    # 研究趋势建议
    report.append(f"\n---\n## 💡 下周研究建议\n")
    report.append("1. 关注国内外高产菌株构建策略的差异\n")
    report.append("2. 跟踪CYP450酶工程改造的最新进展\n")
    report.append("3. 评估新出现的代谢流调控工具（如CRISPRi）在光甘草定合成中的应用潜力\n")
    
    # 保存
    filename = f"report_{datetime.now().strftime('%Y%m%d')}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("".join(report))
    
    print(f"\n✅ 双语周报生成：{filename}")
    print(f"📊 中文：{total_cn} 条 | 英文：{total_en} 条")

if __name__ == "__main__":
    main()
