import os
import requests
import json
import re
from datetime import datetime
from duckduckgo_search import DDGS

MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY', '')

# 增强版关键词矩阵
KEYWORDS = {
    # 基础维度
    "底盘细胞-中文": ["人参皂苷CK 重组酵母", "人参皂苷CK 解脂耶氏酵母", "人参皂苷CK 大肠杆菌"],
    "底盘细胞-英文": ["Ginsenoside CK yeast chassis", "Ginsenoside CK Yarrowia lipolytica", "Ginsenoside CK E. coli"],
    "代谢通路-中文": ["人参皂苷CK 合成途径", "人参皂苷CK 达玛烷型", "原人参二醇 PPD CK"],
    "代谢通路-英文": ["Ginsenoside CK biosynthetic pathway", "Ginsenoside CK dammarane", "PPD to ginsenoside CK"],
    "酶工程-中文": ["人参皂苷CK 糖基转移酶", "人参皂苷CK β-葡萄糖苷酶", "人参皂苷CK UGT"],
    "酶工程-英文": ["Ginsenoside CK glycosyltransferase", "Ginsenoside CK UGT enzyme", "Ginsenoside CK β-glucosidase"],
    "发酵优化-中文": ["人参皂苷CK 发酵产量", "人参皂苷CK 滴度", "人参皂苷CK 产率"],
    "发酵优化-英文": ["Ginsenoside CK fermentation titer", "Ginsenoside CK yield", "Ginsenoside CK production"],
    "专利-中文": ["人参皂苷CK 合成生物学 专利", "人参皂苷CK 制备方法"],
    "专利-英文": ["Ginsenoside CK biosynthesis patent", "Ginsenoside CK production patent"],
    
    # 新增：最新合成途径（专门追踪新策略）
    "最新合成途径-中文": [
        "人参皂苷CK 新合成途径 2024",
        "人参皂苷CK 代谢工程 新策略",
        "人参皂苷CK 全合成 最新",
        "人参皂苷CK 异源合成 新方法",
        "达玛烷型 三萜 合成生物学 新"
    ],
    "最新合成途径-英文": [
        "Ginsenoside CK novel biosynthetic pathway",
        "Ginsenoside CK new metabolic engineering",
        "Ginsenoside CK de novo synthesis",
        "Ginsenoside CK heterologous production new",
        "Dammarane triterpene synthetic biology new"
    ],
    
    # 新增：最高产量记录（专门追踪高产研究）
    "最高产量-中文": [
        "人参皂苷CK 最高产量",
        "人参皂苷CK 最高滴度",
        "人参皂苷CK 产量突破",
        "人参皂苷CK g/L",
        "人参皂苷CK 克级"
    ],
    "最高产量-英文": [
        "Ginsenoside CK highest titer",
        "Ginsenoside CK maximum yield",
        "Ginsenoside CK production record",
        "Ginsenoside CK g/L fermentation",
        "Ginsenoside CK gram scale"
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
        "达玛烷", "dammarane", "原人参二醇", "PPD", "protopanaxadiol",
        "氧化鲨烯", "OSC", "角鲨烯", "squalene",
        "P450", "CYP", "糖基转移酶", "UGT", "glycosyltransferase"
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
        prompt = f"""你是天然产物合成生物学专家，专门分析人参皂苷CK的【最新合成途径】：

{context}

【提取的技术数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}
【提及的合成途径元件】：{', '.join(pathways) if pathways else "未明确提及"}

请重点分析：
1. **最新合成策略**（2-3条）
   - 新底盘细胞（如丝状真菌、链霉菌等非酵母系统）
   - 新代谢通路设计（如人工达玛烷途径、分支途径优化）
   - 多基因协同表达策略

2. **途径创新点**
   - 与经典途径（达玛烷骨架→PPD→CK）的差异
   - 解决的关键瓶颈（如复杂骨架合成、糖基化特异性）

3. **技术成熟度评估**
   - 🔴 概念验证（体外或单酶验证）
   - 🟡 酵母初步构建（有CK产量数据）
   - 🟢 接近应用（>100 mg/L）

4. **对我们项目的启示**
   - 哪些新途径值得借鉴？
   - 需要优先验证的关键步骤

人参皂苷CK：达玛烷型三萜，PPD→CK，关键酶OSC、P450（CYP716A53v2）、UGT。"""

    elif "最高产量" in category:
        prompt = f"""你是天然产物合成生物学专家，专门追踪人参皂苷CK的【最高产量记录】：

{context}

【提取的产量数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请重点分析：
1. **产量排行榜**（制作表格）
   | 排名 | 研究机构 | 滴度 | 底盘 | 关键策略 | 年份 |
   |------|---------|------|------|---------|------|
   （根据文献提取，CK产量通常<10 mg/L，PPD产量可达g/L级）

2. **高产策略总结**（3-5条）
   - 达玛烷骨架供应（OSC过表达、角鲨烯供应）
   - P450酶优化（CYP716A53v2表达、电子传递链）
   - 糖基化效率（UGT选择、UDP-糖供应）
   - 发酵工艺（两相发酵、补料策略）
   - 转运工程（减少产物抑制）

3. **产量瓶颈分析**
   - CK vs PPD产量差距（为什么PPD可达g/L而CK只有mg/L？）
   - 糖基化步骤的限制因素

4. **突破建议**
   - 要达到克级（g/L）CK产量，需要哪些突破？

注意：目前CK微生物合成产量普遍很低（<10 mg/L），任何突破都值得重点关注。"""

    else:
        prompt = f"""你是天然产物合成生物学专家，分析人参皂苷CK【{category}】方向的技术情报：

{context}

【提取的技术数据】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请按以下格式分析：
1. 技术突破点（2-3条）
2. 关键指标（滴度、产率等）
3. 技术成熟度（🔴概念验证/🟡中试前/🟢产业化）
4. 对我们项目的建议

人参皂苷CK：达玛烷型三萜，PPD→CK，关键酶OSC、CYP、UGT。"""

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
    print(f"开始生成人参皂苷CK增强版情报周报...")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    report = [
        f"# 🌿 人参皂苷CK合成生物学情报周报（增强版）\n",
        f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"**目标分子**：人参皂苷Compound K（达玛烷型三萜）\n",
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
            icon = "🌟 " if "最新合成途径" in category else "🏆 " if "最高产量" in category else ""
            report.append(f"\n## {icon}{category}\n{analysis}\n")
        else:
            report.append(f"\n## {category}\n*本周该方向暂无新文献*\n")
    
    # 全局统计
    pathway_results = all_results.get("最新合成途径-中文", []) + all_results.get("最新合成途径-英文", [])
    yield_results = all_results.get("最高产量-中文", []) + all_results.get("最高产量-英文", [])
    
    summary = f"""
## 📈 本周核心发现

### 1. 最新合成途径动态
- 新途径研究：{len(pathway_results)} 篇文献
- 主要创新方向：见上方详细分析

### 2. 产量突破追踪
- 高产研究：{len(yield_results)} 篇文献
- CK vs PPD产量对比：见上方排行榜

### 3. 研究热度
- 中文：{total_cn} 条 | 英文：{total_en} 条
- 监控维度：{len(KEYWORDS)} 个

---
"""
    report.insert(4, summary)
    
    # 趋势建议
    report.append(f"\n---\n## 💡 下周关注重点\n")
    report.append("1. **最新途径**：关注非酵母系统（如丝状真菌）中的达玛烷合成\n")
    report.append("2. **产量突破**：追踪CK产量是否突破50 mg/L或达到克级\n")
    report.append("3. **糖基化工程**：关注UGT酶定向进化提高CK特异性\n")
    report.append("4. **PPD→CK转化**：关注如何提高最后一步糖基化效率\n")
    
    # 保存（修复：直接保存到当前目录）
    try:
        filename = f"CK_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("".join(report))
        print(f"\n{'='*60}")
        print(f"✅ 人参皂苷CK增强版周报生成完成！")
        print(f"📄 文件：{filename}")
        print(f"📊 总计：中文{total_cn}条 | 英文{total_en}条")
        print(f"{'='*60}")
    except Exception as e:
        print(f"保存失败: {e}")
        # 保底：生成简单报告
        with open(f"CK_report_{datetime.now().strftime('%Y%m%d')}_error.md", "w", encoding="utf-8") as f:
            f.write(f"# CK报告生成异常\n\n{str(e)}")

if __name__ == "__main__":
    main()
