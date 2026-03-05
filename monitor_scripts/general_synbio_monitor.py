import os
import requests
import json
import re
from datetime import datetime
from duckduckgo_search import DDGS

MOONSHOT_API_KEY = os.getenv('MOONSHOT_API_KEY', '')

# 合成生物学技术全景监控
KEYWORDS = {
    # 1. 基因编辑与CRISPR技术
    "基因编辑技术-中文": [
        "CRISPR 最新技术 2024",
        "碱基编辑 先导编辑 进展",
        "基因编辑 递送系统 突破",
        "合成生物学 CRISPR 应用"
    ],
    "基因编辑技术-英文": [
        "CRISPR latest technology 2024",
        "base editing prime editing breakthrough",
        "gene editing delivery system",
        "CRISPR synthetic biology application"
    ],
    
    # 2. 代谢工程与通路设计
    "代谢工程-中文": [
        "代谢工程 动态调控 新策略",
        "模块化通路 设计 合成生物学",
        "代谢流 优化 最新进展",
        "细胞工厂 构建 突破"
    ],
    "代谢工程-英文": [
        "metabolic engineering dynamic regulation",
        "modular pathway design synthetic biology",
        "metabolic flux optimization",
        "cell factory construction breakthrough"
    ],
    
    # 3. 蛋白质工程与酶设计
    "蛋白质工程-中文": [
        "定向进化 新策略 2024",
        "AI蛋白质设计 合成生物学",
        "酶工程 改造 最新",
        "无细胞合成 蛋白质"
    ],
    "蛋白质工程-英文": [
        "directed evolution new strategy",
        "AI protein design synthetic biology",
        "enzyme engineering breakthrough",
        "cell-free protein synthesis"
    ],
    
    # 4. 合成基因组学与DNA合成
    "合成基因组-中文": [
        "DNA合成 新技术 成本降低",
        "合成基因组 全基因组合成",
        "DNA存储 合成生物学",
        "基因组合成 酵母 细菌"
    ],
    "合成基因组-英文": [
        "DNA synthesis new technology cost",
        "synthetic genome whole genome synthesis",
        "DNA data storage synthetic biology",
        "genome synthesis yeast bacteria"
    ],
    
    # 5. 自动化与生物铸造厂
    "自动化平台-中文": [
        "生物铸造厂 biofoundry 自动化",
        "高通量筛选 微流控 合成生物学",
        "实验室自动化 机器人",
        "AI生物设计 自动化平台"
    ],
    "自动化平台-英文": [
        "biofoundry automation platform",
        "high-throughput screening microfluidics",
        "lab automation robotics synthetic biology",
        "AI biological design automation"
    ],
    
    # 6. 国内外政策与产业动态
    "政策产业-中文": [
        "合成生物学 中国政策 2024",
        "合成生物学 美国 欧洲 政策对比",
        "合成生物学 投资 融资 动态",
        "合成生物学 产业化 最新"
    ],
    "政策产业-英文": [
        "synthetic biology policy China USA Europe",
        "synthetic biology investment funding 2024",
        "synthetic biology industrialization",
        "synbio market industry news"
    ],
    
    # 7. 顶级期刊突破（专门追踪Nature/Science/Cell）
    "顶刊突破-中文": [
        "Nature 合成生物学 最新论文",
        "Science 代谢工程 突破",
        "Cell 基因编辑 最新研究"
    ],
    "顶刊突破-英文": [
        "Nature synthetic biology latest paper",
        "Science metabolic engineering breakthrough",
        "Cell gene editing latest research",
        "Nature Biotechnology synbio"
    ]
}

def search_web(keyword, region="wt-wt"):
    try:
        with DDGS() as ddgs:
            results = ddgs.text(keyword, max_results=8, timelimit="m", region=region)
            items = []
            for r in results:
                title_lower = r['title'].lower()
                # 过滤无关商业内容
                if any(x in title_lower for x in ['buy', 'price', 'supplier', 'shop', 'amazon']):
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
                "source": "news",
                "date": r.get('date', 'unknown')
            } for r in results]
    except:
        return []

def search_academic(keyword):
    academic_results = []
    queries = [
        f"{keyword} site:nature.com",
        f"{keyword} site:science.org",
        f"{keyword} site:cell.com",
        f"{keyword} site:pubmed.ncbi.nlm.nih.gov"
    ]
    for query in queries[:2]:
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=3, timelimit="m")
                for r in results:
                    if any(x in r['href'] for x in ['nature.com', 'science.org', 'cell.com', 'pubmed', 'ncbi']):
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
    """提取技术指标"""
    patterns = {
        "效率提升": r'(\d+\.?\d*)\s*倍|(\d+\.?\d*)\s*-fold',
        "成本降低": r'成本.*?降低.*?(\d+\.?\d*)%|cost.*?reduced.*?(\d+\.?\d*)%',
        "产量": r'(\d+\.?\d*)\s*(mg/l|g/l|μg/ml)',
        "时间缩短": r'(\d+\.?\d*)\s*(h|d|小时|天)',
        "通量": r'(\d+\.?\d*)\s*(样本|sample)'
    }
    found = {}
    for k, p in patterns.items():
        m = re.findall(p, text, re.IGNORECASE)
        if m:
            found[k] = m[:2]
    return found

def analyze_with_kimi(category, articles):
    """智能分析"""
    if not articles:
        return "本周该方向暂无重大进展。"
    
    api_key = os.getenv('MOONSHOT_API_KEY')
    if not api_key:
        return "⚠️ 未配置 MOONSHOT_API_KEY"
    
    cn_articles = [a for a in articles if any('\u4e00' <= c <= '\u9fff' for c in a['title'])]
    en_articles = [a for a in articles if a not in cn_articles]
    
    context = f"【中文文献/新闻 {len(cn_articles)} 条】\n"
    for i, a in enumerate(cn_articles[:5]):
        context += f"{i+1}. {a['title']}\n{a['snippet'][:350]}\n\n"
    
    context += f"\n【英文文献/新闻 {len(en_articles)} 条】\n"
    for i, a in enumerate(en_articles[:5]):
        context += f"{i+1}. {a['title']}\n{a['snippet'][:350]}\n\n"
    
    data = extract_tech_data(context)
    
    # 根据类别定制Prompt
    if "基因编辑" in category:
        prompt = f"""你是合成生物学领域专家，分析【基因编辑技术】最新进展：

{context}

【技术指标】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请重点分析：
1. **技术突破点**（2-3条）
   - 新型编辑工具（碱基编辑、先导编辑、表观编辑）
   - 递送系统创新（病毒载体、纳米颗粒、RNP）
   - 编辑效率/精准度提升

2. **国内外对比**
   - 中国团队在CRISPR领域的优势与差距
   - 国外（美国、欧洲）最新技术路线
   - 专利布局差异

3. **应用前景**
   - 在合成生物学中的应用（基因组编辑、通路优化）
   - 产业化障碍与解决方案

4. **建议关注**
   - 哪些技术值得立即跟进？
   - 哪些处于概念验证阶段需谨慎评估？"""

    elif "代谢工程" in category:
        prompt = f"""你是代谢工程专家，分析【代谢工程与通路设计】最新进展：

{context}

【技术指标】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请重点分析：
1. **新策略与方法**（2-3条）
   - 动态调控系统（反馈调控、开关系统）
   - 模块化设计（ BioBrick、MoClo等标准化）
   - 多酶复合体/区室化策略

2. **底盘细胞创新**
   - 非模式生物开发（嗜热菌、极端微生物）
   - 跨界通路移植（植物酶在微生物表达）

3. **中外技术路线差异**
   - 中国：重产量优化 vs 国外：重设计自动化？
   - 技术差距与超车机会

4. **产业化应用**
   - 哪些策略已接近工业化？
   - 成本降低潜力"""

    elif "蛋白质工程" in category:
        prompt = f"""你是蛋白质工程专家，分析【蛋白质与酶工程】最新进展：

{context}

【技术指标】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请重点分析：
1. **技术突破**（2-3条）
   - 定向进化新方法（连续进化、机器学习辅助）
   - AI蛋白质设计（AlphaFold应用、RFdiffusion等）
   - 无细胞合成系统进展

2. **酶工程热点**
   - 新型酶发现（宏基因组挖掘）
   - 酶固定化与循环利用
   - 多酶级联反应优化

3. **国内外对比**
   - 中国在AI蛋白设计的进展
   - 国外优势领域（计算设计、高通量筛选）

4. **应用建议**
   - 对天然产物合成的启示
   - 值得投资的酶工程技术"""

    elif "自动化平台" in category:
        prompt = f"""你是合成生物学自动化专家，分析【自动化与生物铸造厂】最新进展：

{context}

【技术指标】：{json.dumps(data, ensure_ascii=False) if data else "无"}

请重点分析：
1. **平台技术突破**（2-3条）
   - 生物铸造厂（Biofoundry）建设进展
   - 液滴微流控高通量筛选
   - 实验室自动化机器人（云实验室）

2. **国内外平台建设**
   - 中国：深圳、天津、上海等平台动态
   - 国外：Ginkgo、Zymergen等进展
   - 技术差距与特色

3. **AI整合**
   - 机器学习在生物设计中的应用
   - 自动化实验闭环（设计-构建-测试-学习）

4. **产业化价值**
   - 通量提升与成本降低数据
   - 对中小企业可及性"""

    elif "政策产业" in category:
        prompt = f"""你是合成生物学产业分析师，分析【政策与产业动态】：

{context}

请重点分析：
1. **国内政策动态**
   - 国家部委最新政策（发改委、科技部、工信部）
   - 地方政策支持（深圳、上海、天津等）
   - 重点专项与资金支持

2. **国际政策对比**
   - 美国：NSF、DOE、DARPA资助方向
   - 欧洲：Horizon Europe、各国战略
   - 政策差异与启示

3. **投融资动态**
   - 国内外大额融资事件
   - 上市公司动态
   - 产业并购趋势

4. **产业化进展**
   - 哪些产品实现商业化？
   - 成本平价（Cost parity）进展
   - 市场接受度"""

    elif "顶刊突破" in category:
        prompt = f"""你是学术前沿追踪专家，分析【顶级期刊突破】：

{context}

请重点总结：
1. **Nature/Science/Cell亮点**（3-5条）
   - 突破点简述
   - 技术重要性评估
   - 研究团队

2. **技术趋势**
   - 当前研究热点转移
   - 新兴技术方向
   - 跨学科融合趋势

3. **对我们的启示**
   - 哪些技术可能改变行业？
   - 值得深入阅读的论文
   - 潜在合作机会"""

    else:
        prompt = f"""你是合成生物学专家，分析【{category}】方向最新进展：

{context}

请分析：
1. 技术突破点（2-3条）
2. 国内外技术对比
3. 成熟度与产业化前景
4. 对我们项目的建议"""

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
            return f"API请求失败: {resp.status_code}"
        
        result = resp.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            return f"API返回异常: {str(result)[:300]}"
            
    except Exception as e:
        return f"分析失败: {str(e)}"

def main():
    print(f"开始生成合成生物学技术情报周报...")
    print(f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    report = [
        f"# 🧬 合成生物学技术情报周报（全球视野）\n",
        f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        f"**监控范围**：基因编辑 | 代谢工程 | 蛋白质工程 | 合成基因组 | 自动化平台 | 政策产业\n",
        f"**地域覆盖**：中国 🇨🇳 | 美国 🇺🇸 | 欧洲 🇪🇺 | 全球 🌍\n",
        f"**数据来源**：顶级期刊 | 学术数据库 | 产业新闻 | 政策文件\n\n---\n"
    ]
    
    all_results = {}
    total_cn = total_en = 0
    
    # 按重要性排序
    priority_order = [
        "顶刊突破-中文", "顶刊突破-英文",
        "基因编辑技术-中文", "基因编辑技术-英文",
        "代谢工程-中文", "代谢工程-英文",
        "蛋白质工程-中文", "蛋白质工程-英文",
        "自动化平台-中文", "自动化平台-英文",
        "合成基因组-中文", "合成基因组-英文",
        "政策产业-中文", "政策产业-英文"
    ]
    
    for category in priority_order:
        if category not in KEYWORDS:
            continue
            
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
            print(f"  - {kw[:30]}...: {len(r)} 条")
        
        # 去重
        seen = set()
        unique = [r for r in category_results if not (r['url'] in seen or seen.add(r['url']))]
        
        print(f"  去重后：{len(unique)} 条")
        all_results[category] = unique
        
        if unique:
            print(f"  正在分析...")
            analysis = analyze_with_kimi(category, unique)
            
            # 添加图标
            if "顶刊" in category:
                icon = "🏆 "
            elif "基因编辑" in category:
                icon = "✂️ "
            elif "代谢工程" in category:
                icon = "⚗️ "
            elif "蛋白质" in category:
                icon = "🧪 "
            elif "自动化" in category:
                icon = "🤖 "
            elif "政策" in category:
                icon = "📊 "
            else:
                icon = "🔬 "
            
            report.append(f"\n## {icon}{category}\n{analysis}\n")
        else:
            report.append(f"\n## {category}\n*本周该方向暂无重大进展*\n")
    
    # 全局总结
    report.append(f"\n---\n## 📈 本周技术趋势总结\n")
    report.append(f"**文献统计**：中文 {total_cn} 条 | 英文 {total_en} 条\n\n")
    report.append(f"**重点关注领域**：\n")
    report.append(f"1. 基因编辑递送系统与精准度提升\n")
    report.append(f"2. AI驱动的蛋白质设计与优化\n")
    report.append(f"3. 自动化生物铸造厂平台建设\n")
    report.append(f"4. 中国合成生物学产业政策支持力度\n\n")
    
    report.append(f"**中外技术差距观察**：\n")
    report.append(f"- 中国在基因编辑应用、代谢工程优化方面进展迅速\n")
    report.append(f"- 美国在基础研究、自动化平台、AI设计工具方面仍领先\n")
    report.append(f"- 欧洲在监管框架、伦理研究方面较为完善\n")
    
    report.append(f"\n---\n## 💡 下周关注建议\n")
    report.append(f"1. 关注Nature/Science子刊的合成生物学专刊\n")
    report.append(f"2. 追踪国内合成生物学重点专项申报动态\n")
    report.append(f"3. 关注国际大型合成生物学会议（如SBx.x、SEED等）最新发布\n")
    report.append(f"4. 监测基因编辑治疗领域对合成生物学的技术溢出效应\n")
    
    # 保存
    try:
        filename = f"SynBio_Tech_Weekly_{datetime.now().strftime('%Y%m%d')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("".join(report))
        print(f"\n{'='*60}")
        print(f"✅ 合成生物学技术周报生成完成！")
        print(f"📄 文件：{filename}")
        print(f"📊 总计：中文{total_cn}条 | 英文{total_en}条")
        print(f"🌍 覆盖：基因编辑、代谢工程、蛋白工程、自动化、政策")
        print(f"{'='*60}")
    except Exception as e:
        print(f"保存失败: {e}")
        with open(f"SynBio_error_{datetime.now().strftime('%Y%m%d')}.md", "w", encoding="utf-8") as f:
            f.write(f"# 报告生成异常\n\n{str(e)}")

if __name__ == "__main__":
    main()
