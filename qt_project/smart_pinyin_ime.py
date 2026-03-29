#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能拼音输入法 - 基于 pypinyin 的完整汉字输入
支持分页显示候选词（每页5个）
支持全库汉字（20,000+字符）
"""

from pypinyin import pinyin, Style

class SmartPinyinIME:
    """智能拼音输入法引擎 - 支持全库汉字"""
    
    # 常用高频汉字（优先显示）
    HIGH_FREQ_CHARS = (
        "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动"
        "同工也能下过子说产种面而方后多定行学法所民得经十三之进着等部度家电力里如水化高自"
        "二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日"
        "那社义事平形相全表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变"
        "条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料象员革位入常文总"
        "次品式活设及管特件长求老头基资边流路级少图山统接知较将组见计别她手角期根论运农指"
        "几九区强放决西被干做必战先回则任取完举色"
        # 补充更多常用字
        "啊阿安岸按案暗昂傲奥澳巴八爸罢白百摆败班般板半帮邦榜棒包保报抱暴北贝备背倍被"
        "本笨比笔币必毕闭边编变便遍标表别冰兵并病波博伯播不布步部才采彩菜参餐残惨仓苍藏"
        "操草册侧测策层曾叉查茶差插柴拆产颤缠长场常厂唱超朝潮吵车彻撤陈晨沉称成城承乘程"
        "吃池持尺赤充冲虫崇抽愁仇丑臭出初除处触川穿传船串创床窗春纯唇词此次刺从匆葱聪粗"
        "促醋窜催脆翠村存寸错措达大打代带待袋丹单担但蛋当党档刀导到道倒得德灯登等邓低底"
        "地第弟电店典点掉调钓爹跌叠丁订定东冬动洞都斗抖豆读度渡独段断端对队吨蹲顿多夺朵"
        "躲俄恶饿恩儿而耳二发法罚反返饭犯范方房防放访飞非肥费分份奋愤风丰封峰锋佛否夫服"
        "父付负富府该改概盖干甘赶敢感刚岗纲钢港高搞告个各哥歌格隔给根跟更耕工公功共供宫"
        "勾沟钩狗够购古股固故顾瓜刮挂乖拐怪关观官馆管惯光广归规轨鬼贵桂滚过国果孩海害汉含"
        "寒汗行航杭好号毫浩合和河何贺黑很恨狠横恒红洪宏虹后厚候乎呼胡湖户护花华划化话画"
        "怀坏欢还环换幻黄皇荒慌回会汇辉悔惠昏婚浑混火或货获惑几机鸡积及极急集计记技际济"
        "继加甲价驾架家假间件建剑见健渐鉴江将讲奖降酱交叫教较角脚接街节结解介界今斤金仅"
        "尽进近京经精静境敬九久酒旧救就局举巨拒具据距捐卷决绝觉军君均俊开凯看刊砍康抗考"
        "靠可科客课肯坑空孔恐口扣苦库裤夸垮跨快块宽款狂况矿框亏葵困扩括拉啦落辣来赖兰蓝"
        "览烂郎狼朗浪老劳牢乐勒雷累泪类冷力历立丽利里理连联练恋链两亮量凉粮辽疗料列劣烈"
        "猎林临淋令灵岭领另六流留刘柳龙笼隆楼漏露路陆录乱卵掠略论轮罗落络骆马妈码吗麻买"
        "卖麦满慢漫忙芒盲茫毛矛茅茂冒貌没每美妹门们闷梦蒙猛米密蜜面棉免苗描秒妙灭蔑民敏"
        "名明命谬么末抹沫漠莫墨默谋某木目母亩幕慕那拿哪纳奶奈男南难脑恼闹呢内嫩能你尼泥"
        "逆年念娘酿鸟尿宁凝牛扭纽农浓弄奴努怒女暖虐诺欧偶爬怕拍排牌派盘判叛乓旁胖跑炮袍"
        "培陪配喷盆朋鹏批皮疲匹片偏骗飘票拼贫品平评凭破迫剖扑铺葡朴圃普七妻期欺漆齐其"
        "奇骑棋旗企起气汽弃妻千迁牵铅前钱潜浅欠枪强墙抢悄桥瞧巧切且窃亲侵琴禽勤青轻氢倾"
        "请庆穷秋丘求球区曲取去趣全权泉拳劝券缺却确鹊裙群然燃染嚷壤让饶扰绕热人忍认任扔"
        "仍日荣绒容肉如入软锐瑞润若弱撒洒萨塞赛三伞散桑嗓丧扫嫂色杀沙纱傻啥山衫闪扇善伤"
        "商上尚烧稍少绍蛇舍设社射射摄申深神审甚渗升生声省剩胜圣师失诗狮十石时实识史使始"
        "士世市示式事侍试视适室是释收手守首寿受兽书术束述树竖数刷衰摔甩帅双霜谁水税睡顺"
        "瞬说司丝私思死四寺似松送诵诉肃素速酸算虽随岁损笋缩所索锁他它她台太态谈潭潭谈探"
        "汤唐堂塘糖躺趟涛逃讨套特疼踢提题体替天添田填挑条跳铁听厅庭停挺突图徒涂途土吐团"
        "推腿退吞托脱拖驼妥挖瓦袜歪外弯湾丸完万汪亡王网往忘望危威微围为伟伪卫未位味胃喂"
        "温文纹稳问翁窝我握屋污无五武物务误西吸希息习席洗喜戏系细下夏先仙闲显险县现限线"
        "相香想向象像消销小效校笑些写谢心辛新信星行形型兴幸性姓凶兄胸雄休修秀袖虚需许序"
        "叙畜续宣选学穴雪血寻训讯迅压牙呀鸦鸭牙雅亚烟言严岩炎研盐眼演验央杨阳杨洋养氧样"
        "妖摇遥咬药要爷也冶野业叶夜一衣医依仪移遗疑已以矣蚁艺议亦异役抑易疫益意因音阴银"
        "引印应英婴鹰迎营影硬映永勇涌用优忧尤由油游友有又右幼诱于余鱼渔雨语育预域欲喻寓"
        "遇元园原圆员源远怨院愿约月越云运再载咱暂赞脏早造则责择泽贼怎增赠扎渣炸摘窄债沾"
        "展战站张章掌丈仗招找照罩遮折哲者这真针珍真诊阵振镇争征睁整正证郑之支只汁知织"
        "执直值职植止只旨纸指志制治质致智置中终钟种仲众周州洲舟粥轴宙昼皱朱猪诸竹逐主"
        "助住注柱祝著筑抓爪专转庄装壮状追准捉桌仔子字自宗棕总走足组祖租阻钻嘴最罪尊遵"
        "作做坐座左佐昨"
    )
    
    def __init__(self):
        self.char_dict = {}
        self.word_dict = {}
        self._init_complete = False
        self._page_size = 5
        self._full_dict_loaded = False
        
    def initialize(self):
        if self._init_complete:
            return
        print("[SmartPinyinIME] 正在加载智能词库...")
        self._load_char_dictionary()
        self._load_word_dictionary()
        self._init_complete = True
        char_count = sum(len(v) for v in self.char_dict.values())
        word_count = sum(len(v) for v in self.word_dict.values())
        print(f"[SmartPinyinIME] 加载完成: {char_count}高频字, {word_count}词组")
    
    def _load_char_dictionary(self):
        """加载高频汉字拼音映射"""
        for char in self.HIGH_FREQ_CHARS:
            try:
                py = pinyin(char, style=Style.NORMAL)[0][0]
                if py not in self.char_dict:
                    self.char_dict[py] = []
                if char not in self.char_dict[py]:
                    self.char_dict[py].append(char)
            except:
                pass
    
    def _load_full_dictionary(self):
        """按需加载全库汉字（CJK Unified Ideographs: \u4e00-\u9fff）"""
        if self._full_dict_loaded:
            return
            
        print("[SmartPinyinIME] 正在加载全库汉字...")
        # 添加所有CJK汉字（约20,000+字符）
        # 但跳过已在高频字中的，避免重复
        high_freq_set = set(self.HIGH_FREQ_CHARS)
        count = 0
        
        # CJK Unified Ideographs
        for codepoint in range(0x4e00, 0x9fff + 1):
            char = chr(codepoint)
            if char in high_freq_set:
                continue
            try:
                py = pinyin(char, style=Style.NORMAL)[0][0]
                if py not in self.char_dict:
                    self.char_dict[py] = []
                self.char_dict[py].append(char)
                count += 1
            except:
                pass
        
        self._full_dict_loaded = True
        print(f"[SmartPinyinIME] 全库加载完成: 新增{count}字")
    
    def _load_word_dictionary(self):
        """加载常用词组"""
        words = [
            ("北京", "beijing"), ("背景", "beijing"), ("上海", "shanghai"),
            ("广州", "guangzhou"), ("深圳", "shenzhen"), ("天津", "tianjin"),
            ("重庆", "chongqing"), ("南京", "nanjing"), ("杭州", "hangzhou"),
            ("武汉", "wuhan"), ("西安", "xian"), ("成都", "chengdu"),
            ("中国", "zhongguo"), ("人民", "renmin"), ("共和国", "gongheguo"),
            ("中华", "zhonghua"), ("天安门", "tiananmen"), ("故宫", "gugong"),
            ("长城", "changcheng"), ("公司", "gongsi"), ("大学", "daxue"),
            ("中学", "zhongxue"), ("小学", "xiaoxue"), ("医院", "yiyuan"),
            ("银行", "yinhang"), ("超市", "chaoshi"), ("商店", "shangdian"),
            ("饭店", "fandian"), ("机场", "jichang"), ("火车站", "huochezhan"),
            ("汽车站", "qichezhan"), ("地铁", "ditie"), ("公交", "gongjiao"),
            ("地图", "ditu"), ("导航", "daohang"), ("位置", "weizhi"),
            ("路线", "luxian"), ("目的地", "mudedi"), ("今天", "jintian"),
            ("明天", "mingtian"), ("昨天", "zuotian"), ("上午", "shangwu"),
            ("下午", "xiawu"), ("晚上", "wanshang"), ("早上", "zaoshang"),
            ("中午", "zhongwu"), ("现在", "xianzai"), ("时间", "shijian"),
            ("天气", "tianqi"), ("温度", "wendu"),
            # 添加更多词组
            ("多少", "duoshao"), ("怎么", "zenme"), ("什么", "shenme"),
            ("哪里", "nali"), ("那里", "nali"), ("这里", "zheli"),
            ("谢谢", "xiexie"), ("不客气", "bukeqi"), ("对不起", "duibuqi"),
            ("没关系", "meiguanxi"), ("你好", "nihao"), ("再见", "zaijian"),
            ("请问", "qingwen"), ("好的", "haode"), ("可以", "keyi"),
            ("不行", "buxing"), ("确定", "queding"), ("取消", "quxiao"),
            ("返回", "fanhui"), ("前进", "qianjin"), ("左转", "zuozhuan"),
            ("右转", "youzhuan"), ("直行", "zhixing"), ("掉头", "diaotou"),
            ("高速", "gaosu"), ("收费站", "shoufeizhan"), ("服务区", "fuwuqu"),
            ("出口", "chukou"), ("入口", "rukou"), ("红绿灯", "honglvdeng"),
            ("路口", "lukou"), ("环岛", "huandao"), ("匝道", "zhadao"),
        ]
        for word, py in words:
            if py not in self.word_dict:
                self.word_dict[py] = []
            self.word_dict[py].append(word)
    
    def get_candidates(self, pinyin_str, page=0, load_full=False):
        """
        根据拼音获取候选词（支持分页）
        
        Args:
            pinyin_str: 输入的拼音
            page: 页码（从0开始）
            load_full: 是否加载全库汉字（用于获取更多候选）
            
        Returns:
            dict: {
                "candidates": [当前页的候选词列表],
                "total": 总候选词数,
                "has_more": 是否有更多页,
                "page": 当前页码
            }
        """
        if not self._init_complete:
            self.initialize()
        
        # 如果需要全库加载（例如翻页时）
        if load_full and not self._full_dict_loaded:
            self._load_full_dictionary()
            
        if not pinyin_str:
            return {"candidates": [], "total": 0, "has_more": False, "page": 0}
            
        pinyin_str = pinyin_str.lower().strip()
        
        # 高频字集合（用于优先级排序）
        high_freq_set = set(self.HIGH_FREQ_CHARS)
        
        # 分类收集结果（保持优先级）
        exact_words = []      # 完全匹配的词组
        exact_chars = []      # 完全匹配的单字
        prefix_words = []     # 前缀匹配的词组
        prefix_chars = []     # 前缀匹配的单字
        
        # 1. 完全匹配的词组
        if pinyin_str in self.word_dict:
            exact_words.extend(self.word_dict[pinyin_str])
        
        # 2. 完全匹配的单字
        if pinyin_str in self.char_dict:
            exact_chars.extend(self.char_dict[pinyin_str])
        
        # 3. 前缀匹配词组
        for py, words in self.word_dict.items():
            if py.startswith(pinyin_str) and py != pinyin_str:
                prefix_words.extend(words)
        
        # 4. 前缀匹配单字
        for py, chars in self.char_dict.items():
            if py.startswith(pinyin_str) and py != pinyin_str:
                prefix_chars.extend(chars)
        
        # 合并结果：高频字在前，低频字在后
        # 顺序：完全匹配词组 > 完全匹配高频单字 > 前缀匹配高频单字 > 其他
        def prioritize(items):
            """将列表分为高频和低频两部分，保持原顺序"""
            high = [c for c in items if c in high_freq_set]
            low = [c for c in items if c not in high_freq_set]
            return high + low
        
        # 组装最终结果（去重同时保持优先级）
        seen = set()
        all_results = []
        
        # 1. 完全匹配的词组（全部保留）
        for item in exact_words:
            if item not in seen:
                seen.add(item)
                all_results.append(item)
        
        # 2. 完全匹配的单字（高频优先）
        for item in prioritize(exact_chars):
            if item not in seen:
                seen.add(item)
                all_results.append(item)
        
        # 3. 前缀匹配的词组
        for item in prefix_words:
            if item not in seen:
                seen.add(item)
                all_results.append(item)
        
        # 4. 前缀匹配的单字（高频优先）
        for item in prioritize(prefix_chars):
            if item not in seen:
                seen.add(item)
                all_results.append(item)
        
        # 分页
        total = len(all_results)
        start_idx = page * self._page_size
        end_idx = start_idx + self._page_size
        page_results = all_results[start_idx:end_idx]
        
        return {
            "candidates": page_results,
            "total": total,
            "has_more": end_idx < total,
            "page": page
        }


# 全局实例
_ime_instance = None

def get_ime():
    """获取全局输入法实例"""
    global _ime_instance
    if _ime_instance is None:
        _ime_instance = SmartPinyinIME()
        _ime_instance.initialize()
    return _ime_instance


if __name__ == "__main__":
    ime = get_ime()
    
    test_cases = ["bei", "beijing", "zhong", "tian", "tiananmen", "a"]
    
    print("=" * 50)
    print("智能拼音输入法测试 - 分页显示")
    print("=" * 50)
    
    for py in test_cases:
        print(f"\n拼音: {py}")
        result = ime.get_candidates(py, page=0)
        print(f"  第1页: {result['candidates']} (共{result['total']}个)")
        if result["has_more"]:
            result2 = ime.get_candidates(py, page=1)
            print(f"  第2页: {result2['candidates']}")
    
    # 测试全库加载
    print("\n" + "=" * 50)
    print("测试全库汉字加载（输入'yi'）")
    print("=" * 50)
    result = ime.get_candidates("yi", page=0, load_full=True)
    print(f"第1页: {result['candidates']}")
    print(f"总计: {result['total']}个候选")
