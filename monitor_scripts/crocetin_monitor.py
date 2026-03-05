import os
import requests
import json
import re
from datetime import datetime
from duckduckgo_search import DDGS

MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY', '')

# 更新后的关键词矩阵（删除发酵优化，增加高产菌株策略差异）
KEYWORDS = {
    # 基础维度
    "底盘细胞-中文": ["藏花酸 重组酵母", "藏花酸 大肠杆菌", "藏花酸 蓝藻"],
    "底盘细胞-英文": ["Crocetin yeast chassis", "Crocetin E. coli", "Crocetin cyanobacteria"],
    "合成途径-中文": ["藏花酸 合成途径", "藏花酸 类胡萝卜素", "藏花酸 CCD酶"],
    "合成途径-英文": ["Crocetin biosynthetic pathway", "Crocetin carotenoid pathway", "Crocetin CCD enzyme"],
    "酶工程-中文": ["藏花酸 类胡萝卜素裂解酶", "藏花酸 CCD", "藏花酸 醛脱氢酶"],
    "酶工程-英文": ["Crocetin CCD enzyme", "Crocetin carotenoid cleavage dioxygenase", "Crocetin ALDH"],
    
    # 新增：国内外高产菌株构建策略差异（替代原来的发酵优化）
    "高产菌株策略-中文": [
        "藏花酸 高产菌株 构建策略",
        "藏花酸 国内外 技术路线 差异",
        "藏花酸 中国 美国 日本 研究对比",
        "藏花酸 代谢工程 策略比较",
        "藏花酸 合成生物学 中外差异"
    ],
    "高产菌株策略-英文": [
        "Crocetin high-yield strain construction strategy",
        "Crocetin China vs USA vs Japan research",
        "Crocetin metabolic engineering comparison",
        "Crocetin synthetic biology strategy difference",
        "Crocetin international research comparison"
    ],
    
    "专利-中文": ["藏花酸 合成生物学 专利", "西红花酸 制备方法"],
    "专利-英文": ["Crocetin biosynthesis patent", "Crocetin production patent"],
    
    # 最新合成途径
    "最新合成途径-中文": [
        "藏花酸 新合成途径 2024",
        "藏花酸 代谢工程 新策略",
        "藏花酸 全合成 最新",
        "类胡萝卜素 裂解 新酶"
    ],
    "最新合成途径-英文": [
        "Crocetin novel biosynthetic pathway",
        "Crocetin new metabolic engineering",
        "Crocetin de novo synthesis",
        "Carotenoid cleavage new enzyme"
    ],
    
    # 最高产量
    "最高产量-中文": [
        "藏花酸 最高产量",
        "藏花酸 最高滴度",
        "藏花酸 产量突破",
        "藏花酸 g/L",
        "西红花素 crocin 产量"
    ],
    "最高产量-英文": [
        "Crocetin highest titer",
        "Crocetin maximum yield",
        "Crocetin production record",
        "Crocetin g/L fermentation",
        "Crocin yield"
    ]
}

def search_web(keyword, region="wt-wt"):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(keyword, max_results=8, timelimit="m", region=region)
            items = []
            for r in results:
                title_lower = r['title'].lower()
                if any(x in title_lower for x in ['buy', 'price', 'supplier', 'market', 'shop', 'saffron price']):
                    continue
                items.append({
                    "title": r['title'],
                    "url": r['href'],
                    "snippet": r['body'][:600],
                    "source": "web"
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
                "source": "news"
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
        "滴度": r'(\d+\.?\d*)\s*(mg/l|g/l|μg/ml)',
        "产量": r'(\d+\.?\d*)\s*(mg|g|μg)\s*/\s*(L|l)',
        "产率": r'(\d+\.?\d*)%',
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

def extract_pathway_info(text):
    """提取合成途径信息"""
    pathway_keywords = [
        "类胡萝卜素", "carotenoid", "番茄红素", "lycopene",
        "玉米黄质", "zeaxanthin", "CCD", "裂解酶",
        "醛脱氢酶", "ALDH", "氧化", "oxidation"
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
    
    if "最新合成途径" in category:
        prompt = f"""你是天然产物合成生物学专家，专门分析藏花酸的【最新合成途径】：

{context}

【提取的技术数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}
【提及的合成途径元件】：{', '.join(pathways) if pathways else "未明确提及"}

请重点分析：
1. **最新合成策略**（2-3条）
   - 新底盘细胞（如蓝藻、光合细菌）
   - 新酶发现（如新型CCD、ALDH）
   - 无细胞合成（Cell-free）尝试

2. **途径创新点**
   - 与经典途径（类胡萝卜素→玉米黄质→藏花酸）的差异
   - 解决的关键瓶颈（如CCD酶活性、底物特异性）

3. **技术成熟度评估**
   - 🔴 概念验证（单酶或体外验证）
   - 🟡 微生物构建（有产量数据）
   - 🟢 接近应用（>100 mg/L）

4. **对我们项目的启示**
   - 哪些新途径值得借鉴？
   - 藏花酸 vs 藏红花素（Crocin）合成策略对比

藏花酸（Crocetin）：类胡萝卜素衍生物，C20H24O4，合成路径：类胡萝卜素→CCD裂解→ALDH氧化。"""

    elif "最高产量" in category:
        prompt = f"""你是天然产物合成生物学专家，专门追踪藏花酸的【最高产量记录】：

{context}

【提取的产量数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请重点分析：
1. **产量排行榜**（制作表格）
   | 排名 | 研究机构 | 滴度 | 底盘 | 关键策略 | 年份 |
   |------|---------|------|------|---------|------|
   （藏花酸产量通常<50 mg/L，远低于番茄红素g/L级）

2. **高产策略总结**（3-5条）
   - 类胡萝卜素前体供应（番茄红素/玉米黄质积累）
   - CCD酶优化（来源选择、定向进化）
   - ALDH酶优化（氧化效率）
   - 两相发酵（减少产物抑制）
   - 动态调控（避免代谢负担）

3. **产量瓶颈分析**
   - CCD酶是限速步骤（裂解效率低）
   - 藏花酸的水溶性问题（影响提取和检测）
   - 与藏红花素（Crocin）的转化关系

4. **突破建议**
   - 如何提高CCD酶活性？
   - 是否需要与糖基化（生成Crocin）结合提高产量？

注意：藏花酸合成需要先有类胡萝卜素（番茄红素/玉米黄质），再经CCD裂解和ALDH氧化，步骤较多导致产量普遍较低。"""

    elif "高产菌株策略" in category:
        prompt = f"""你是天然产物合成生物学专家，专门分析藏花酸【国内外高产菌株构建策略差异】：

{context}

【提取的技术数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请重点对比分析：

1. **中国研究策略特点**
   - 主要技术路线（如：重酶挖掘 vs 重底盘优化）
   - 高产菌株构建方法（CRISPR、启动子工程、拷贝数优化等）
   - 特色技术（如多基因协同表达、动态调控等）
   - 代表性研究机构及成果

2. **国外（美国/日本/欧洲）研究策略特点**
   - 主要技术路线差异（如：重计算设计 vs 重实验筛选）
   - 底盘细胞选择偏好（酵母 vs 大肠杆菌 vs 其他）
   - 特色技术（如蛋白质工程、无细胞合成等）
   - 代表性研究机构及成果

3. **技术策略对比表**
   | 维度 | 中国 | 国外 | 优劣分析 |
   |------|------|------|---------|
   | 底盘选择 | ... | ... | ... |
   | 酶工程策略 | ... | ... | ... |
   | 代谢调控 | ... | ... | ... |
   | 产量水平 | ... | ... | ... |

4. **可借鉴策略**
   - 国外哪些技术值得国内学习？
   - 国内哪些优势可以进一步强化？
   - 对我们项目的具体建议（应优先采用哪种策略？）

注意：藏花酸合成涉及类胡萝卜素→CCD→ALDH多步反应，不同国家可能在不同步骤有技术优势。"""

    else:
        prompt = f"""你是天然产物合成生物学专家，分析藏花酸【{category}】方向的技术情报：

{context}

【提取的技术数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请按以下格式分析：
1. 技术突破点（2-3条）
2. 关键指标（滴度、产率等）
3. 技术成熟度（🔴概念验证/🟡中试前/🟢产业化）
4. 对我们项目的建议

藏花酸（Crocetin）：类胡萝卜素衍生物，合成路径：类胡萝卜素→CCD→ALDH→藏花酸。"""

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

def main():
    print(f"开始生成藏花酸增强版情报周报...")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    report = [
        f"# 🌺 藏花酸（Crocetin）合成生物学情报周报（增强版）\n",
        f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"**目标分子**：藏花酸（Crocetin，C20H24O4）/ 藏红花素（Crocin）\n",
        f"**特别追踪**：✨ 最新合成途径 | 🏆 最高产量记录 | 🌏 国内外策略差异\n",
        f"**数据来源**：Web搜索 | PubMed | Google Scholar | 专利库\n\n---\n"
    ]
    
    all_results = {}
    total_cn = total_en = 0
    
    # 优先分析新增维度
    priority_categories = [
        "最新合成途径-中文", "最新合成途径-英文",
        "最高产量-中文", "最高产量-英文",
        "高产菌株策略-中文", "高产菌株策略-英文"  # 新增优先级
    ]
    other_categories = [k for k in KEYWORDS.keys() if k not in priority_categories]
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
            # 根据类别添加不同图标
            if "最新合成途径" in category:
                icon = "🌟 "
            elif "最高产量" in category:
                icon = "🏆 "
            elif "高产菌株策略" in category:
                icon = "🌏 "
            else:
                icon = ""
            report.append(f"\n## {icon}{category}\n{analysis}\n")
        else:
            report.append(f"\n## {category}\n*本周该方向暂无新文献*\n")
    
    # 全局统计
    pathway_results = all_results.get("最新合成途径-中文", []) + all_results.get("最新合成途径-英文", [])
    yield_results = all_results.get("最高产量-中文", []) + all_results.get("最高产量-英文", [])
    strategy_results = all_results.get("高产菌株策略-中文", []) + all_results.get("高产菌株策略-英文", [])
    
    summary = f"""
## 📈 本周核心发现

### 1. 最新合成途径动态
- 新途径研究：{len(pathway_results)} 篇文献
- CCD酶新发现：见上方详细分析

### 2. 产量突破追踪
- 高产研究：{len(yield_results)} 篇文献
- 藏花酸 vs 藏红花素产量对比：见上方排行榜

### 3. 国内外策略差异
- 策略对比文献：{len(strategy_results)} 篇
- 中外技术路线差异：见上方对比分析

### 4. 研究热度
- 中文：{total_cn} 条 | 英文：{total_en} 条
- 监控维度：{len(KEYWORDS)} 个

---
"""
    report.insert(4, summary)
    
    # 趋势建议
    report.append(f"\n---\n## 💡 下周关注重点\n")
    report.append("1. **最新途径**：关注蓝藻/光合细菌中的光合驱动合成\n")
    report.append("2. **酶工程**：关注新型CCD酶的挖掘和定向进化\n")
    report.append("3. **产量突破**：追踪藏花酸是否突破100 mg/L或达到克级\n")
    report.append("4. **国际对比**：关注日本（西红花传统产地）的最新研究策略\n")
    report.append("5. **策略借鉴**：评估国外蛋白质工程策略在国内的可行性\n")
    
    # 保存（修复：直接保存到当前目录）
    try:
        filename = f"Crocetin_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("".join(report))
        print(f"\n{'='*60}")
        print(f"✅ 藏花酸增强版周报生成完成！")
        print(f"📄 文件：{filename}")
        print(f"📊 总计：中文{total_cn}条 | 英文{total_en}条")
        print(f"🌏 新增：国内外高产菌株策略差异分析")
        print(f"{'='*60}")
    except Exception as e:
        print(f"保存失败: {e}")
        with open(f"Crocetin_report_{datetime.now().strftime('%Y%m%d')}_error.md", "w", encoding="utf-8") as f:
            f.write(f"# Crocetin报告生成异常\n\n{str(e)}")

if __name__ == "__main__":
    main()
