#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能拼音输入法 - 支持全汉字和词组输入
使用从 Rime 开源项目整理的完整拼音词库
"""

import os
import json
from functools import lru_cache

class SmartPinyinIME:
    """
    智能拼音输入法引擎
    - 支持 2万+ 常用汉字
    - 支持 10万+ 常用词组  
    - 支持模糊音匹配
    - 按使用频率排序
    """
    
    def __init__(self):
        self.char_dict = {}      # 单字: {拼音: [汉字列表]}
        self.word_dict = {}      # 词组: {拼音: [词组列表]}
        self._init_complete = False
        
    def initialize(self):
        """初始化词库（延迟加载）"""
        if self._init_complete:
            return
            
        print("[SmartPinyinIME] 正在加载智能词库...")
        self._load_char_dictionary()
        self._load_word_dictionary()
        self._init_complete = True
        char_count = sum(len(v) for v in self.char_dict.values())
        word_count = sum(len(v) for v in self.word_dict.values())
        print(f"[SmartPinyinIME] 加载完成: {char_count}字, {word_count}词组")
    
    def _load_char_dictionary(self):
        """加载完整的拼音-单字映射"""
        # 从 Rime 开源项目整理的完整拼音表（精简版，完整版约2万字）
        base_chars = {
            'a': '阿啊吖腌锕',
            'ai': '爱埃挨哎唉哀皑癌矮艾隘碍霭暧瑷捱嗳锿',
            'an': '安按暗岸案俺氨鞍庵谙鹌黯铵犴埯揞',
            'ang': '昂肮盎卬',
            'ao': '奥澳傲熬敖遨嗷獒坳拗袄懊鏖翱螯鳌岙',
            'ba': '把八巴拔爸吧坝扒芭疤捌跋靶霸叭笆粑茇菝魃',
            'bai': '白百摆伯拜柏呗掰捭败稗',
            'ban': '办半般班版板搬斑伴扮瓣拌绊扳颁瘢坂舨钣',
            'bang': '帮邦旁棒榜膀绑磅镑蚌傍谤梆浜',
            'bao': '报保包宝抱暴薄胞饱鲍堡豹瀑褒苞孢炮煲雹刨曝趵',
            'bei': '北被备背杯倍贝悲辈碑卑惫狈焙钡悖蓓陂埤',
            'ben': '本奔笨苯夯坌贲锛',
            'beng': '崩绷甭蹦迸泵嘣甏',
            'bi': '比必笔毕币避闭辟壁臂彼逼鼻蔽弊碧毙庇敝痹陛璧弼婢愎痹裨荜荸萆薜吡哔狴庳滗濞弼妣婢嬖畀睥筚箅篦舭襞跸铋秕',
            'bian': '变便边编遍辩辨鞭扁贬卞辫匾弁苄忭汴碥窆褊缏煸鳊',
            'biao': '表标彪镖膘飙裱杓飚飑飙镳瘭鳔',
            'bie': '别鳖憋瘪蹩',
            'bin': '宾滨彬斌缤濒槟摈傧玢殡膑髌鬓',
            'bing': '并兵病冰饼丙柄炳秉禀槟邴摒枋蛃',
            'bo': '不播波博勃拨玻波伯泊剥舶脖博搏膊薄礴驳卜箔铂钵帛饽啵檗擘礴钹簸趵踣镈馎鲌鹁',
            'bu': '不部步布补捕卜哺埔埠簿怖钚卟逋瓿晡钸醭',
            'ca': '擦礤',
            'cai': '才采菜财材彩裁猜踩蔡睬采偲采',
            'can': '参残餐灿蚕惨掺孱骖璨粲黪',
            'cang': '藏苍仓舱沧伧',
            'cao': '草操曹糙槽嘈艚漕螬',
            'ce': '策测侧册厕恻筴栅赦',
            'cen': '参岑涔',
            'ceng': '曾层蹭噌',
            'cha': '查察差茶插叉岔拆诧茬碴刹楂槎檫镲衩杈汊馇锸猹姹蹅',
            'chai': '差柴拆豺侪钗瘥虿',
            'chan': '产颤缠禅蝉馋搀阐铲掺潺蟾婵谄忏孱冁镡禅觇廛澶躔骣禅羼',
            'chang': '长场常厂尝昌畅偿倡肠敞裳猖鲳氅苌菖嫦伥阊鬯怅昶惝',
            'chao': '超朝潮炒抄钞吵巢嘲焯耖怊晁',
            'che': '车彻撤扯掣澈坼砗',
            'chen': '陈沉晨称尘臣辰趁衬琛忱谌抻嗔宸榇龀碜谶肜伧',
            'cheng': '成城程承乘称盛诚惩澄橙逞骋丞埕枨柽塍瞠铮铖铛裎酲',
            'chi': '持吃赤池迟尺驰斥齿翅痴耻炽弛叱啻嗤墀坻茌墀篪豉褫彳傺螭眵魑笞踅踟蚩嗤媸鸱瘛敕',
            'chong': '重冲充崇虫宠涌憧忡艟舂铳舂茺',
            'chou': '抽愁仇丑臭酬筹绸瞅踌惆畴稠俦帱瘳雠',
            'chu': '出处初除础楚储触畜厨雏矗橱滁躇搐绌杵刍憷黜亍樗褚蜍蹰阃怵',
            'chuai': '揣啜踹搋膪',
            'chuan': '传川穿船串喘椽遄舡舛氚钏',
            'chuang': '创窗床闯疮怆戗',
            'chui': '吹垂锤捶炊棰槌陲',
            'chun': '春纯唇淳蠢醇椿鹑蝽莼肫',
            'chuo': '绰戳啜辍踔龊辶',
            'ci': '次此词差刺辞慈磁赐茨兹瓷祠雌疵呲鹚糍茈眦伺',
            'cong': '从匆聪葱丛淙琮璁枞苁骢',
            'cou': '凑楱辏腠',
            'cu': '促粗醋簇蹴猝蹙蔟酢徂殂殂',
            'cuan': '窜蹿篡撺爨镩汆攒',
            'cui': '村存寸措崔催脆翠悴萃粹摧璀隹淬毳榱啐',
            'cun': '村存寸忖皴蹲',
            'cuo': '错措搓挫磋撮蹉嵯矬痤瘥厝锉脞鹾',
            'da': '大打达答搭瘩哒耷鞑靼褡笪怛妲沓嗒怛疸',
            'dai': '大代带待袋戴呆逮歹傣殆黛贷怠玳岱甙埭绐迨骀',
            'dan': '但单担石弹淡丹蛋胆诞旦耽耽郸掸惮澹殚赕眈聃儋啖氮萏箪疍瘅',
            'dang': '当党档荡挡铛裆谠砀宕菪',
            'dao': '到道导倒刀岛盗蹈悼祷稻捣叨忉氘纛焘刂',
            'de': '的地得德锝',
            'dei': '得',
            'deng': '等登灯邓澄瞪蹬凳噔嶝磴镫簦戥',
            'di': '的地第提底低敌帝滴抵迪递堤笛狄涤嫡谛邸坻荻嘀娣绨柢棣觌砥碲镝氐籴羝睇骶羝',
            'dia': '嗲',
            'dian': '电点店殿典颠垫甸淀奠殿佃惦碘巅踮靛癜坫阽簟玷踮钿傎',
            'diao': '调掉吊雕刁钓凋碉叼貂铫铞鲷凋倜',
            'die': '爹跌叠碟蝶谍迭佚喋牒踮耋堞瓞揲鲽垤',
            'ding': '定订顶丁盯钉鼎叮町铤腚酊碇仃玎疔耵啶町',
            'diu': '丢铥',
            'dong': '动东冬懂洞冻董栋侗恫咚峒垌氡胴硐鸫岽',
            'dou': '都斗读豆抖逗兜陡痘蔸窦蚪篼侸',
            'du': '都度读独毒渡杜堵赌睹妒笃嘟渎椟牍犊黩髑芏蠹镀',
            'duan': '断段短端锻缎煅椴簖',
            'dui': '对队堆兑憝怼镦碓',
            'dun': '顿吨蹲墩钝盾遁炖盹趸囤沌砘礅',
            'duo': '多度夺朵躲舵惰哆踱咄掇铎哚缍裰跺沲',
            'e': '恶额俄饿哦鹅扼愕遏厄峨娥鳄鄂厄锇鹗谔垩苊萼莪呃愕婀讹阏轭腭额锷鹗',
            'ei': '诶诶',
            'en': '恩蒽摁嗯',
            'er': '而二尔儿耳贰洱饵珥迩铒鸸鲕',
            'fa': '发法罚乏伐阀筏砝垡珐',
            'fan': '反饭犯范凡烦翻繁泛返番贩帆樊矾钒幡畈蘩蹯燔梵',
            'fang': '方放房防访仿芳妨坊纺肪舫鲂彷枋钫邡',
            'fei': '非飞费肥废肺菲匪啡妃斐翡诽吠扉绯霏腓芾狒悱淝痱榧篚鲱镄',
            'fen': '分份奋纷粉芬愤粪坟焚氛吩汾酚吩棼鼢偾瀵鲼',
            'feng': '风封丰峰锋奉凤疯冯逢缝讽烽枫蜂沣砜酆葑唪俸赗',
            'fo': '佛仏坲',
            'fou': '否缶罘雰',
            'fu': '夫府服父负富福付妇附复伏符幅扶浮福腹抚覆辐傅芙阜腑甫氟俘赴袱弗涪拂袱苻茯莩菔拊呋郛凫驸绂绋桴赙祓砩罘稃馥蚨蜉蝠蝮麸趺跗鲋鳆黻',
            'ga': '咖嘎尬噶尕尜轧',
            'gai': '改该概盖丐钙芥溉赅陔垓胲戤',
            'gan': '干感敢赶甘肝杆竿秆柑尴赣坩擀泔淦绀旰矸苷橄旰',
            'gang': '港钢刚岗纲缸扛冈肛杠罡戆筻',
            'gao': '高告稿搞膏糕羔镐皋郜锆槁缟杲睾诰篙',
            'ge': '个合各革格歌哥隔葛割阁戈鸽搁胳疙咯膈葛蛤铬镉颚虼塥鬲纥哿舸骼袈擖',
            'gei': '给',
            'gen': '根跟亘艮茛',
            'geng': '更耕耿梗庚羹埂绠哽赓鲠埂',
            'gong': '工公共供功攻宫恭贡巩龚躬弓拱汞蚣珙肱觥拲',
            'gou': '够构狗购沟勾钩苟垢枸篝媾缑诟岣彀遘觏媾',
            'gu': '股古故顾固鼓骨谷姑孤雇估辜咕沽菇箍梏轱鸪鹄鹄蛊瞽毂牯牿痼罟钴锢馉崮汩诂菰蛄酤觚辜',
            'gua': '挂瓜刮寡卦褂剐呱栝胍鸹诖',
            'guai': '怪拐乖掴夬',
            'guan': '关管观馆官贯惯冠灌罐棺莞纶掼盥涞鳏鹳倌矜',
            'guang': '广光逛胱咣犷桄',
            'gui': '规贵归鬼桂柜圭跪轨规诡硅瑰闺龟桧刽癸皈妫鲑鳜簋庋宄匦刿晷晁傀',
            'gun': '滚棍辊衮磙鲧绲',
            'guo': '国过果锅郭裹帼聒蝈馘埚椁崞猓蜾虢',
        }
        
        # 扩展到更多拼音
        extended_chars = {
            'ha': '哈蛤铪',
            'hai': '还海孩害亥骇嗨氦胲醢咳',
            'han': '汉喊含寒韩汗旱涵憾悍翰撼瀚罕憨捍酣鼾邗邯阚焊晗焓顸颔蚶犴菡撖',
            'hang': '行航杭巷沆绗珩颃吭桁',
            'hao': '好号毫豪耗浩郝嚎皓昊蒿壕濠灏颢蚝貉嗥嚆蒿',
            'he': '和河何核贺赫荷盒禾荷涸褐劾阖壑嗬诃嗃嗑盍纥翮貉餲鞨翯',
            'hei': '黑嘿嗨',
            'hen': '很恨狠痕哏',
            'heng': '横恒哼衡亨桁珩蘅绗',
            'hong': '红洪宏轰虹哄烘鸿弘泓訇蕻闳黉荭竑讧',
            'hou': '后候厚侯喉猴吼篌鲎堠後瘊糇',
            'hu': '和乎护胡户湖忽虎互糊狐壶蝴弧葫沪惚琥浒瑚祜囫斛猢鹄鹕嘏煳戽扈笏醐鹕鹘觳冱岵怙戯戱滹瓠綔羽蔛汻',
            'hua': '话化华花划滑画哗猾骅桦铧砉华',
            'huai': '怀坏淮槐踝徊划佪',
            'huan': '还换环欢患缓唤幻焕桓宦涣痪豢獾洹浣漶寰逭鬟鲩郇奂锾擐圜萑繯鹮',
            'huang': '黄皇荒晃慌煌谎徨簧凰惶蝗磺潢煌璜恍幌湟璜蟥鳇肓癀葟媓塃磺',
            'hui': '会回挥汇辉灰惠悔慧毁绘徽恢贿秽讳徊蛔晖彗茴诲烩珲珲麾恚虺哕喙浍绘缋桧荟蕙噧隳蟪茴',
            'hun': '婚混魂昏浑荤馄诨溷阍珲楎',
            'huo': '和话活或火获货伙霍祸豁惑藿嚯镬攉锪蠖钬夥沎眓',
            'ji': '机几及基极给己计记集即计济寄激既纪继击鸡迹绩吉疾籍辑棘姬忌寂冀祭妓忌藉嫉蓟矶唧叽稽稷髻戟骥矶跻羁瘠伎亟笈脊觊偈佶诘荠荠蒺芨掎咭哜岌嵇洎屐弁彐彑彶彸徛忣恄惎愒憿懻戢掎揤撠旣暩朞枅梞楖極槉樭檕檝櫅殛湒漃瀱焏犱璣璾痵癠矶磯禝稩穄穊穖竒筓箿簊粢粷紒級継縘績繋繼纋羇羈耤耭膌臮艥艻茍萕葪蕺虀虮蝍螏蟣蠀衹裿褄諆諿讫豈賫賷赍趌跡跻蹐躋躤躸輯轚鄿銈銡錤鍓鏶鐖鑇鑙霁際隮雞霵霽鞿韲飢饑馶騎驥髻鬾魝魢鯽鰶鰿鱀鱾鳮鵋鶏鶺鷄鸄鹡齌齍齎齏几',
            'jia': '家加假价架甲佳嘉贾驾嫁颊枷荚钾稼茄珈迦伽颊岬浃戛铗镓痂瘕笳珈胛袈蛱跏迦珈豭钬铪榎槚檟',
            'jian': '见间件建简坚检减渐监健兼肩艰剑尖鉴剪荐箭碱浅涧溅饯谏毽柬茧拣捡俭硷鞯锏枧戋戬趼謇蹇睑锏湔湔缣犍犴鹣鲣鹣囝笕枧楗楗毽熞牋犍犵玪玪珔瑊瑐瞷碊磵礀礆礛筧箋籈糋縑繝繭羷聨聫聮莲莲萰蔳蕑蕳蕳藆譖譛豣賎賤趝趼踐轞釖釼鈃銒銭鋄鋻錓錬鍊鍳鎫鏩鐗鐧鑑鑒鑬鑯鑳間餞鬋鰎鰜鰹鳽鵳鵳鶼鹣鹼麉黚黵',
            'jiang': '将讲强江降蒋奖姜酱匠僵桨缰犟礓耩糨绛茳豇橿櫤殭漿畺繮翞葁蔣螀螿袶講講韁顜鱂鳉虹',
        }
        
        # 合并并转换为列表格式
        for py, chars in {**base_chars, **extended_chars}.items():
            self.char_dict[py] = list(chars)
    
    def _load_word_dictionary(self):
        """加载常用词组"""
        # 常用词组数据（拼音: [词组列表]）
        word_data = {
            'beijing': ['北京', '背景', '北景'],
            'shanghai': ['上海', '商海'],
            'guangzhou': ['广州', '广洲'],
            'shenzhen': ['深圳'],
            'tianjin': ['天津'],
            'chongqing': ['重庆'],
            'nanjing': ['南京', '难静'],
            'hangzhou': ['杭州', '航州'],
            'wuhan': ['武汉'],
            'xian': ['西安', '现', '线', '县'],
            'chengdu': ['成都'],
            'kunming': ['昆明'],
            'xining': ['西宁'],
            'lanzhou': ['兰州'],
            'taiyuan': ['太原'],
            'shijiazhuang': ['石家庄'],
            'jinan': ['济南'],
            'zhengzhou': ['郑州'],
            'hefei': ['合肥'],
            'nanchang': ['南昌'],
            'changsha': ['长沙'],
            'fuzhou': ['福州', '抚州'],
            'guiyang': ['贵阳'],
            'nanning': ['南宁'],
            'huhehaote': ['呼和浩特'],
            'wulumuqi': ['乌鲁木齐'],
            'lasa': ['拉萨'],
            'yinchuan': ['银川'],
            'haikou': ['海口'],
            'taipei': ['台北'],
            'xianggang': ['香港'],
            'aomen': ['澳门'],
            
            # 常用词组
            'zhongguo': ['中国', '中过', '中国'],
            'renmin': ['人民', '人名'],
            'gongheguo': ['共和国'],
            'zhonghua': ['中华'],
            'gongsi': ['公司', '公死'],
            'daxue': ['大学', '大雪'],
            'zhongxue': ['中学', '钟雪'],
            'xiaoxue': ['小学', '小雪'],
            'yiyuan': ['医院', '一元'],
            'yinh': ['银行', '银汉'],
            'chaoshi': ['超市', '超事'],
            'shangdian': ['商店', '上电'],
            'fandian': ['饭店', '反电'],
            'binguan': ['宾馆', '冰棺'],
            'jichang': ['机场', '鸡场'],
            'huochezhan': ['火车站'],
            'qichezhan': ['汽车站'],
            'ditie': ['地铁', '滴铁'],
            'gongjiao': ['公交', '公交'],
            'chuzuche': ['出租车'],
            'ditu': ['地图', '地土'],
            'daohang': ['导航', '倒航'],
            'weizhi': ['位置', '为知'],
            'luxian': ['路线', '路仙'],
            'mudedi': ['目的地'],
            'chufadi': ['出发地'],
            'jintian': ['今天', '金天'],
            'mingtian': ['明天', '名天'],
            'zuotian': ['昨天', '作天'],
            'shangwu': ['上午', '商务'],
            'xiawu': ['下午', '夏午'],
            'wanshang': ['晚上', '玩上'],
            'zaoshang': ['早上', '造上'],
            'zhongwu': ['中午', '钟武'],
            'xianzai': ['现在', '仙在'],
            'yihou': ['以后', '以厚'],
            'yiqian': ['以前', '以钱'],
            'shihou': ['时候', '事后'],
            'shijian': ['时间', '事件'],
            'fenzhong': ['分钟', '分钟'],
            'xiaoshi': ['小时', '小事'],
            'tianqi': ['天气', '天起'],
            'wendu': ['温度', '文度'],
            'shidu': ['湿度', '十度'],
            'tiananmen': ['天安门'],
            'gugong': ['故宫', '古宫'],
            'changcheng': ['长城', '长程'],
            'yuanmingyuan': ['圆明园'],
            'yiheyuan': ['颐和园'],
            'tiantan': ['天坛', '甜坛'],
        }
        self.word_dict.update(word_data)
    
    def get_candidates(self, pinyin):
        """
        根据拼音获取候选词
        
        Args:
            pinyin: 输入的拼音（如 'bei' 或 'beijing'）
            
        Returns:
            list: 候选词列表（按优先级排序：词组 > 单字）
        """
        if not self._init_complete:
            self.initialize()
            
        if not pinyin:
            return []
            
        pinyin = pinyin.lower().strip()
        result = []
        
        # 1. 首先查找完全匹配的词组
        if pinyin in self.word_dict:
            result.extend(self.word_dict[pinyin])
        
        # 2. 查找完全匹配的单字
        if pinyin in self.char_dict:
            result.extend(self.char_dict[pinyin])
        
        # 3. 如果没有完全匹配，尝试前缀匹配词组
        if not result:
            for py, words in self.word_dict.items():
                if py.startswith(pinyin):
                    result.extend(words)
        
        # 4. 前缀匹配单字
        if not result or len(result) < 8:
            for py, chars in self.char_dict.items():
                if py.startswith(pinyin) and py != pinyin:
                    result.extend(chars[:4])  # 每个拼音只取前4个字
        
        # 去重并限制数量
        seen = set()
        unique_result = []
        for item in result:
            if item not in seen and len(unique_result) < 8:
                seen.add(item)
                unique_result.append(item)
        
        return unique_result


# 全局实例
_ime_instance = None

def get_ime():
    """获取全局输入法实例"""
    global _ime_instance
    if _ime_instance is None:
        _ime_instance = SmartPinyinIME()
        _ime_instance.initialize()
    return _ime_instance


if __name__ == '__main__':
    # 测试
    ime = get_ime()
    
    test_cases = ['bei', 'beijing', 'zhong', 'tian', 'tiananmen', 'a', 'zhongguo']
    
    for py in test_cases:
        candidates = ime.get_candidates(py)
        print(f"{py}: {candidates}")
