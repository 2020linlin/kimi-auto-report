import os
import requests
import json
import re
from datetime import datetime
from duckduckgo_search import DDGS

MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY', '')

# 增强版关键词矩阵
KEYWORDS = {
    # 原有维度
    "底盘细胞-中文": ["光甘草定 重组酵母", "光甘草定 解脂耶氏酵母"],
    "底盘细胞-英文": ["Glabridin yeast chassis", "Glabridin Yarrowia lipolytica"],
    "代谢通路-中文": ["光甘草定 异黄酮合成通路", "光甘草定 CYP450"],
    "代谢通路-英文": ["Glabridin isoflavone biosynthesis", "Glabridin P450 enzyme"],
    "酶工程-中文": ["光甘草定 查耳酮合酶", "光甘草定 定向进化"],
    "酶工程-英文": ["Glabridin chalcone synthase", "Glabridin directed evolution"],
    "发酵优化-中文": ["光甘草定 发酵产量", "光甘草定 滴度"],
    "发酵优化-英文": ["Glabridin fermentation titer", "Glabridin yield optimization"],
    "专利-中文": ["光甘草定 合成生物学 专利"],
    "专利-英文": ["Glabridin biosynthesis patent"],
    
    # 新增：最新合成途径（专门追踪新策略）
    "最新合成途径-中文": [
        "光甘草定 新合成途径 2024",
        "光甘草定 代谢工程 新策略",
        "光甘草定 全合成 最新",
        "光甘草定 异源合成 新方法"
    ],
    "最新合成途径-英文": [
        "Glabridin novel biosynthetic pathway",
        "Glabridin new metabolic engineering strategy",
        "Glabridin de novo synthesis",
        "Glabridin heterologous production new"
    ],
    
    # 新增：最高产量记录（专门追踪高产研究）
    "最高产量-中文": [
        "光甘草定 最高产量",
        "光甘草定 最高滴度",
        "光甘草定 产量突破",
        "光甘草定 g/L"
    ],
    "最高产量-英文": [
        "Glabridin highest titer",
        "Glabridin maximum yield",
        "Glabridin production record",
        "Glabridin g/L fermentation"
    ]
}

def search_web(keyword, region="wt-wt"):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(keyword, max_results=8, timelimit="m", region=region)
            items = []
            for r in results:
                title_lower = r['title'].lower()
                if any(x in title_lower for x in ['buy', 'price', 'supplier', 'market', 'shop']):
                    continue
                items.append({
                    "title": r['title'],
                    "url": r['href'],
                    "snippet": r['body'][:600],
                    "source": "web",
                    "date": datetime.now().strftime('%Y-%m')
                })
            return items
    except Exception as e:
        print(f"搜索失败 [{keyword}]: {e}")
        return []

def search_news(keyword):
    try:
        with DDGS() as ddgs:
            results = ddgs.news(keyword, max_results=5, timelimit="w")
            return [{
                "title": r['title'],
                "url": r['url'],
                "snippet": r['body'][:400],
                "source": "news",
                "date": r.get('date', 'unknown')
            } for r in results]
    except:
        return []

def search_academic(keyword):
    academic_results = []
    queries = [
        f"{keyword} site:pubmed.ncbi.nlm.nih.gov",
        f"{keyword} site:scholar.google.com",
    ]
    for query in queries:
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=5, timelimit="m")
                for r in results:
                    if any(x in r['href'] for x in ['pubmed', 'ncbi', 'scholar.google', '.edu']):
                        academic_results.append({
                            "title": r['title'],
                            "url": r['href'],
                            "snippet": r['body'][:600],
                            "source": "academic"
                        })
        except:
            continue
    return academic_results

def extract_tech_data(text):
    """增强版数据提取"""
    patterns = {
        "滴度": r'(\d+\.?\d*)\s*(mg/l|g/l|μg/ml|ug/ml)',
        "产量": r'(\d+\.?\d*)\s*(mg|g|μg)\s*/\s*(L|l)',
        "产率": r'(\d+\.?\d*)%',
        "转化率": r'conversion\s*(\d+\.?\d*)%',
        "发酵时间": r'(\d+)\s*(h|hours|小时|天|d)',
        "纯度": r'purity\s*(\d+\.?\d*)%|纯度\s*(\d+\.?\d*)%',
        "底物浓度": r'(glucose|甘油|葡萄糖).{0,15}(\d+\.?\d*)\s*(g/l|mM)',
        "OD值": r'OD\d+\s*(\d+\.?\d*)'
    }
    found = {}
    for k, p in patterns.items():
        m = re.findall(p, text, re.IGNORECASE)
        if m:
            found[k] = m[:3]
    return found

def extract_pathway_info(text):
    """提取合成途径信息"""
    pathway_keywords = [
        "查耳酮", "chalcone", "甘草素", "liquiritigenin", 
        "异黄酮", "isoflavone", "CYP", "P450",
        "糖基化", "glycosylation", "糖基转移酶", "UGT"
    ]
    found_pathways = []
    for kw in pathway_keywords:
        if kw.lower() in text.lower():
            found_pathways.append(kw)
    return list(set(found_pathways))

def analyze_with_kimi(category, articles):
    """增强版分析"""
    if not articles:
        return "本周该方向暂无新文献。"
    
    api_key = os.getenv('MOONSHOT_API_KEY')
    if not api_key:
        return "⚠️ 未配置 MOONSHOT_API_KEY"
    
    cn_articles = [a for a in articles if any('\u4e00' <= c <= '\u9fff' for c in a['title'])]
    en_articles = [a for a in articles if a not in cn_articles]
    
    context = f"【中文文献 {len(cn_articles)} 条】\n"
    for i, a in enumerate(cn_articles[:6]):
        context += f"{i+1}. {a['title']}\n{a['snippet'][:400]}\n\n"
    
    context += f"\n【英文文献 {len(en_articles)} 条】\n"
    for i, a in enumerate(en_articles[:6]):
        context += f"{i+1}. {a['title']}\n{a['snippet'][:400]}\n\n"
    
    data = extract_tech_data(context)
    pathways = extract_pathway_info(context)
    
    # 根据类别定制Prompt
    if "最新合成途径" in category:
        prompt = f"""你是一名合成生物学专家，专门分析光甘草定的【最新合成途径】：

{context}

【提取的技术数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}
【提及的合成途径元件】：{', '.join(pathways) if pathways else "未明确提及"}

请重点分析：
1. **最新合成策略**（2-3条）
   - 新底盘细胞（如非模式酵母、丝状真菌）
   - 新代谢通路设计（如人工途径、分支途径优化）
   - 新酶发现或酶工程改造

2. **途径创新点**
   - 与经典途径（苯丙氨酸→查耳酮→甘草素→光甘草定）的差异
   - 解决的关键瓶颈（如中间产物毒性、碳流分配）

3. **技术成熟度评估**
   - 🔴 概念验证（体外或大肠杆菌验证）
   - 🟡 酵母初步构建（有产量数据）
   - 🟢 接近应用（>100 mg/L）

4. **对我们项目的启示**
   - 哪些新途径值得借鉴？
   - 需要验证的关键步骤

注意：光甘草定经典合成途径为：苯丙氨酸 → 查耳酮 → 甘草素（Liquiritigenin）→ 光甘草定（Glabridin），关键酶包括CHS、CHR、IFS、CYP450、UGT。"""

    elif "最高产量" in category:
        prompt = f"""你是一名合成生物学专家，专门追踪光甘草定的【最高产量记录】：

{context}

【提取的产量数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请重点分析：
1. **产量排行榜**（制作表格）
   | 排名 | 研究机构/公司 | 滴度 | 底盘细胞 | 关键策略 | 年份 |
   |------|-------------|------|---------|---------|------|
   （根据文献提取，如数据不全可留空）

2. **高产策略总结**（3-5条）
   - 前体供应强化（如苯丙氨酸/酪氨酸模块）
   - 竞争途径敲除（如黄酮醇分支）
   - 酶表达优化（如拷贝数、启动子强度）
   - 发酵工艺优化（如两相发酵、补料策略）
   - 转运工程（如ABC转运蛋白过表达）

3. **产量瓶颈分析**
   - 当前最高产量是多少？（mg/L 或 g/L）
   - 限制因素是什么？（酶活性、前体、毒性、稳定性）

4. **突破建议**
   - 要达到克级（g/L）产量，还需要哪些技术突破？
   - 建议优先尝试的高产策略

注意：目前文献报道的光甘草定微生物合成产量普遍较低（<10 mg/L），任何突破都值得重点关注。"""

    else:
        prompt = f"""你是一名合成生物学专家，分析光甘草定【{category}】方向的技术情报：

{context}

【提取的技术数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}

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
                "temperature": 0.2
            },
            timeout=150
        )
        
        if resp.status_code != 200:
            return f"API请求失败，状态码: {resp.status_code}, 内容: {resp.text[:500]}"
        
        result = resp.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        elif "error" in result:
            return f"API错误: {result['error'].get('message', '未知错误')}"
        else:
            return f"API返回异常: {str(result)[:500]}"
            
    except Exception as e:
        return f"分析失败: {str(e)}"

def generate_summary(all_results):
    """生成全局摘要"""
    # 统计各维度
    pathway_results = all_results.get("最新合成途径-中文", []) + all_results.get("最新合成途径-英文", [])
    yield_results = all_results.get("最高产量-中文", []) + all_results.get("最高产量-英文", [])
    
    summary = f"""
## 📈 本周核心发现

### 1. 最新合成途径动态
- 新途径研究：{len(pathway_results)} 篇文献
- 主要创新方向：（见下方详细分析）

### 2. 产量突破追踪
- 高产研究：{len(yield_results)} 篇文献
- 最高产量记录：（见下方排行榜）

### 3. 研究热度趋势
- 中文研究：{sum(len(v) for k,v in all_results.items() if '中文' in k)} 篇
- 英文研究：{sum(len(v) for k,v in all_results.items() if '英文' in k)} 篇

---
"""
    return summary

def main():
    print(f"开始生成光甘草定增强版情报周报...")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    report = [
        f"# 🧬 光甘草定合成生物学情报周报（增强版）\n",
        f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"**特别追踪**：✨ 最新合成途径 | 🏆 最高产量记录\n",
        f"**数据来源**：Web搜索 | PubMed | Google Scholar | 专利库\n\n---\n"
    ]
    
    all_results = {}
    total_cn = total_en = 0
    
    # 优先分析新增维度
    priority_categories = [
        "最新合成途径-中文", "最新合成途径-英文",
        "最高产量-中文", "最高产量-英文"
    ]
    other_categories = [k for k in KEYWORDS.keys() if k not in priority_categories]
    
    # 按优先级排序
    sorted_categories = priority_categories + other_categories
    
    for category in sorted_categories:
        kws = KEYWORDS[category]
        print(f"\n🔍 正在检索：{category}...")
        
        category_results = []
        for kw in kws:
            if "英文" in category:
                r = search_web(kw, "wt-wt") + search_academic(kw)
                total_en += len(r)
            else:
                r = search_web(kw, "cn-zh") + search_news(kw)
                total_cn += len(r)
            category_results.extend(r)
            print(f"  - {kw[:25]}...: {len(r)} 条")
        
        # 去重
        seen = set()
        unique = [r for r in category_results if not (r['url'] in seen or seen.add(r['url']))]
        
        print(f"  去重后：{len(unique)} 条")
        
        all_results[category] = unique
        
        if unique:
            print(f"  正在调用Kimi分析...")
            analysis = analyze_with_kimi(category, unique)
            report.append(f"\n## {'🌟 ' if '最新合成途径' in category else '🏆 ' if '最高产量' in category else ''}{category}\n{analysis}\n")
        else:
            report.append(f"\n## {category}\n*本周该方向暂无新文献*\n")
    
    # 插入全局摘要（在报告开头）
    summary = generate_summary(all_results)
    report.insert(4, summary)  # 插入到标题后面
    
    # 统计
    report.append(f"\n---\n## 📊 本周文献统计\n")
    report.append(f"- 中文文献：{total_cn} 条\n")
    report.append(f"- 英文文献：{total_en} 条\n")
    report.append(f"- 监控维度：{len(KEYWORDS)} 个（含2个新增追踪维度）\n")
    
    # 趋势建议
    report.append(f"\n---\n## 💡 下周重点关注\n")
    report.append("1. **最新途径**：关注非模式生物（如链霉菌、蓝藻）中的光甘草定合成尝试\n")
    report.append("2. **产量突破**：追踪是否有研究突破100 mg/L或达到克级（g/L）\n")
    report.append("3. **酶工程**：关注CYP450家族新成员的发现和定向进化进展\n")
    report.append("4. **产业化**：关注是否有中试规模发酵的报道\n")
    
    # 保存
    filename = f"Glabridin_report_{datetime.now().strftime('%Y%m%d')}.md"
    filepath = os.path.join(os.path.dirname(__file__), filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("".join(report))
    
    print(f"\n{'='*60}")
    print(f"✅ 增强版周报生成完成！")
    print(f"📄 文件路径：{filepath}")
    print(f"📊 总计：中文{total_cn}条 | 英文{total_en}条")
    print(f"🌟 新增：最新合成途径 + 最高产量追踪")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
