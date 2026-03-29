#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于QWebEngineView的高德地图组件 - 右侧半透明键盘"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QObject, pyqtSlot
from PyQt5.QtWebChannel import QWebChannel
import os
import urllib.request
import urllib.parse
import json

# 导入智能拼音输入法
try:
    # 尝试相对导入（作为包的一部分）
    from .smart_pinyin_ime import get_ime
    _HAS_SMART_IME = True
except ImportError:
    try:
        # 尝试绝对导入（直接运行）
        from smart_pinyin_ime import get_ime
        _HAS_SMART_IME = True
    except ImportError:
        _HAS_SMART_IME = False
        print("[警告] 智能拼音输入法加载失败，使用基础词典")


class AMapAPIHandler(QObject):
    """高德地图 WebService API 处理后端"""
    
    def __init__(self, amap_key, parent=None):
        super().__init__(parent)
        self.amap_key = amap_key
        self.base_url = "https://restapi.amap.com/v3"
    
    @pyqtSlot(str, result=str)
    def geocode_regeo(self, location):
        """逆地理编码：根据经纬度获取地址
        
        Args:
            location: "lng,lat" 格式的字符串
        Returns:
            JSON 字符串
        """
        try:
            url = f"{self.base_url}/geocode/regeo"
            params = {
                'key': self.amap_key,
                'location': location,
                'extensions': 'all',
                'output': 'json'
            }
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            
            print(f"[AMapAPI] 逆地理编码请求: {location}")
            
            with urllib.request.urlopen(full_url, timeout=5) as response:
                data = response.read().decode('utf-8')
                print(f"[AMapAPI] 逆地理编码响应: {data[:200]}")
                return data
        except Exception as e:
            print(f"[AMapAPI] 逆地理编码失败: {e}")
            return json.dumps({'status': '0', 'info': str(e)})
    
    @pyqtSlot(str, str, result=str)
    def input_tips(self, keywords, city="全国"):
        """输入提示：根据关键词获取地点候选
        
        Args:
            keywords: 输入的关键词
            city: 城市（默认全国）
        Returns:
            JSON 字符串
        """
        try:
            url = f"{self.base_url}/assistant/inputtips"
            params = {
                'key': self.amap_key,
                'keywords': keywords,
                'city': city,
                'datatype': 'all',
                'output': 'json'
            }
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            
            print(f"[AMapAPI] 输入提示请求: {keywords}")
            
            with urllib.request.urlopen(full_url, timeout=5) as response:
                data = response.read().decode('utf-8')
                print(f"[AMapAPI] 输入提示响应: {data[:200]}")
                return data
        except Exception as e:
            print(f"[AMapAPI] 输入提示失败: {e}")
            return json.dumps({'status': '0', 'info': str(e)})
    
    @pyqtSlot(str, str, result=str)
    def place_search(self, keywords, city="全国"):
        """地点搜索
        
        Args:
            keywords: 搜索关键词
            city: 城市
        Returns:
            JSON 字符串
        """
        try:
            url = f"{self.base_url}/place/text"
            params = {
                'key': self.amap_key,
                'keywords': keywords,
                'city': city,
                'extensions': 'all',
                'offset': 10,
                'page': 1,
                'output': 'json'
            }
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            
            print(f"[AMapAPI] 地点搜索请求: {keywords}")
            
            with urllib.request.urlopen(full_url, timeout=5) as response:
                data = response.read().decode('utf-8')
                return data
        except Exception as e:
            print(f"[AMapAPI] 地点搜索失败: {e}")
            return json.dumps({'status': '0', 'info': str(e)})


class PinyinHandler(QObject):
    """拼音处理后端 - 使用智能拼音输入法，支持分页"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ime = None
        if _HAS_SMART_IME:
            try:
                self._ime = get_ime()
                print("[PinyinHandler] 智能拼音输入法初始化成功")
            except Exception as e:
                print(f"[PinyinHandler] 智能输入法初始化失败: {e}")
        self._page_size = 5  # 每页5个候选词
        
    @pyqtSlot(str, int, result='QVariantMap')
    def get_candidates(self, pinyin, page=0):
        """
        根据拼音获取候选汉字/词组（支持分页）
        
        Args:
            pinyin: 输入的拼音
            page: 页码（从0开始）
            
        Returns:
            dict: {
                "candidates": [当前页的候选词列表],
                "total": 总候选词数,
                "has_more": 是否有更多页,
                "page": 当前页码
            }
        """
        if not pinyin:
            return {"candidates": [], "total": 0, "has_more": False, "page": 0}
        
        pinyin = pinyin.lower().strip()
        
        # 使用智能输入法（如果可用）
        if self._ime:
            try:
                # 当翻页时，加载全库汉字以获取更多候选
                result = self._ime.get_candidates(pinyin, page, load_full=(page > 0))
                return result
            except Exception as e:
                print(f"[PinyinHandler] 智能输入法查询失败: {e}")
        
        # 回退到基础词典（不分页）
        candidates = self._get_basic_candidates(pinyin)
        return {
            "candidates": candidates,
            "total": len(candidates),
            "has_more": False,
            "page": 0
        }
    
    def _get_basic_candidates(self, pinyin):
        """基础词典（作为备用）"""
        basic_dict = {
            'a': ['阿','啊','安','岸','按','案','暗'],
            'ai': ['哀','埃','挨','爱'],
            'an': ['安','岸','按','案','暗'],
            'ang': ['昂'],
            'ao': ['傲','奥','澳'],
            'ba': ['八','巴','把','爸','罢'],
            'bai': ['白','百','摆','败'],
            'ban': ['班','般','板','办','半'],
            'bang': ['帮','邦','榜','棒'],
            'bao': ['包','保','报','抱','暴'],
            'bei': ['北','贝','备','背','倍','被'],
            'ben': ['本','笨'],
            'bi': ['比','笔','币','必','毕','闭'],
            'bian': ['边','编','变','便','遍'],
            'biao': ['标','表'],
            'bie': ['别'],
            'bing': ['冰','兵','并','病'],
            'bo': ['波','博','伯','播'],
            'bu': ['不','布','步','部'],
            'cai': ['才','采','彩','菜'],
            'can': ['参','餐','残','惨'],
            'cang': ['仓','苍','藏'],
            'cao': ['操','草'],
            'ce': ['册','侧','测','策'],
            'ceng': ['层','曾'],
            'cha': ['叉','查','茶','差','插'],
            'chai': ['柴','拆'],
            'chan': ['产','颤','缠'],
            'chang': ['长','场','常','厂','唱'],
            'chao': ['超','朝','潮','吵'],
            'che': ['车','彻','撤'],
            'chen': ['陈','晨','沉','称'],
            'cheng': ['成','城','承','乘','程'],
            'chi': ['吃','池','持','尺','赤'],
            'chong': ['充','冲','虫','崇'],
            'chou': ['抽','愁','仇','丑','臭'],
            'chu': ['出','初','除','处','触'],
            'chuan': ['川','穿','传','船','串'],
            'chuang': ['创','床','窗'],
            'chun': ['春','纯','唇'],
            'ci': ['词','此','次','刺'],
            'cong': ['从','匆','葱','聪'],
            'cu': ['粗','促','醋'],
            'cuan': ['窜'],
            'cui': ['催','脆','翠'],
            'cun': ['村','存','寸'],
            'cuo': ['错','措'],
            'da': ['大','打','达'],
            'dai': ['代','带','待','袋'],
            'dan': ['丹','单','担','但','蛋'],
            'dang': ['当','党','档'],
            'dao': ['刀','导','到','道','倒'],
            'de': ['得','的','德'],
            'deng': ['灯','登','等','邓'],
            'di': ['低','底','地','第','弟'],
            'dian': ['电','店','典','点'],
            'diao': ['掉','调','钓'],
            'die': ['爹','跌','叠'],
            'ding': ['丁','订','定'],
            'diu': ['丢'],
            'dong': ['东','冬','动','洞'],
            'dou': ['都','斗','抖','豆'],
            'du': ['都','读','度','渡','独'],
            'duan': ['段','断','端'],
            'dui': ['对','队'],
            'dun': ['吨','蹲','顿'],
            'duo': ['多','夺','朵','躲'],
            'e': ['俄','恶','饿','恩'],
            'er': ['儿','而','耳','二'],
            'fa': ['发','法','罚'],
            'fan': ['反','返','饭','犯','范'],
            'fang': ['方','房','防','放','访'],
            'fei': ['飞','非','肥','费'],
            'fen': ['分','份','奋','愤'],
            'feng': ['风','丰','封','峰','锋'],
            'fo': ['佛'],
            'fou': ['否'],
            'fu': ['夫','服','父','付','负','富','府'],
            'gai': ['该','改','概','盖'],
            'gan': ['干','甘','赶','敢','感'],
            'gang': ['刚','岗','纲','钢','港'],
            'gao': ['高','搞','告'],
            'ge': ['个','各','哥','歌','格','隔'],
            'gei': ['给'],
            'gen': ['根','跟'],
            'geng': ['更','耕'],
            'gong': ['工','公','功','共','供','宫'],
            'gou': ['勾','沟','钩','狗','够','购'],
            'gu': ['古','股','固','故','顾'],
            'gua': ['瓜','刮','挂'],
            'guai': ['乖','拐','怪'],
            'guan': ['关','观','官','馆','管','惯'],
            'guang': ['光','广'],
            'gui': ['归','规','轨','鬼','贵','桂'],
            'gun': ['滚'],
            'guo': ['过','国','果'],
            'hai': ['还','孩','海','害'],
            'han': ['汉','含','寒','汗'],
            'hang': ['行','航','杭'],
            'hao': ['好','号','毫','浩'],
            'he': ['合','和','河','何','贺'],
            'hei': ['黑'],
            'hen': ['很','恨','狠'],
            'heng': ['横','恒'],
            'hong': ['红','洪','宏','虹'],
            'hou': ['后','厚','候'],
            'hu': ['乎','呼','胡','湖','户','护'],
            'hua': ['花','华','划','化','话','画'],
            'huai': ['怀','坏'],
            'huan': ['欢','还','环','换','幻'],
            'huang': ['黄','皇','荒','慌'],
            'hui': ['回','会','汇','辉','悔','惠'],
            'hun': ['昏','婚','浑','混'],
            'huo': ['火','或','货','获','惑'],
            'ji': ['几','机','鸡','积','及','极','急','集','计','记','技','际','济','继'],
            'jia': ['加','甲','价','驾','架','家','假'],
            'jian': ['间','件','建','剑','见','健','渐','鉴'],
            'jiang': ['江','将','讲','奖','降','酱'],
            'jiao': ['交','叫','教','较','角','脚'],
            'jie': ['接','街','节','结','解','介','界'],
            'jin': ['今','斤','金','仅','尽','进','近'],
            'jing': ['京','经','精','静','境','敬'],
            'jiu': ['九','久','酒','旧','救','就'],
            'ju': ['局','举','巨','拒','具','据','距'],
            'juan': ['捐','卷'],
            'jue': ['决','绝','觉'],
            'jun': ['军','君','均','俊'],
            'kai': ['开','凯'],
            'kan': ['看','刊','砍'],
            'kang': ['康','抗'],
            'kao': ['考','靠'],
            'ke': ['可','科','客','课'],
            'ken': ['肯'],
            'keng': ['坑'],
            'kong': ['空','孔','恐'],
            'kou': ['口','扣'],
            'ku': ['苦','库','裤'],
            'kua': ['夸','垮','跨'],
            'kuai': ['快','块'],
            'kuan': ['宽','款'],
            'kuang': ['狂','况','矿','框'],
            'kui': ['亏','葵'],
            'kun': ['困'],
            'kuo': ['扩','括'],
            'la': ['拉','啦','落','辣'],
            'lai': ['来','赖'],
            'lan': ['兰','蓝','览','烂'],
            'lang': ['郎','狼','朗','浪'],
            'lao': ['老','劳','牢'],
            'le': ['乐','勒'],
            'lei': ['雷','累','泪','类'],
            'leng': ['冷'],
            'li': ['力','历','立','丽','利','里','理'],
            'lia': ['俩'],
            'lian': ['连','联','练','恋','链'],
            'liang': ['两','亮','量','凉','粮'],
            'liao': ['辽','疗','料'],
            'lie': ['列','劣','烈','猎'],
            'lin': ['林','临','淋'],
            'ling': ['令','灵','岭','领','另'],
            'liu': ['六','流','留','刘','柳'],
            'long': ['龙','笼','隆'],
            'lou': ['楼','漏','露'],
            'lu': ['路','陆','录'],
            'luan': ['乱','卵'],
            'lue': ['掠','略'],
            'lun': ['论','轮'],
            'luo': ['罗','落','络','骆'],
            'ma': ['马','妈','码','吗','麻'],
            'mai': ['买','卖','麦'],
            'man': ['满','慢','漫','忙'],
            'mang': ['忙','芒','盲','茫'],
            'mao': ['毛','矛','茅','茂','冒','貌'],
            'mei': ['没','每','美','妹'],
            'men': ['门','们','闷'],
            'meng': ['梦','蒙','猛'],
            'mi': ['米','密','蜜'],
            'mian': ['面','棉','免'],
            'miao': ['苗','描','秒','妙'],
            'mie': ['灭','蔑'],
            'min': ['民','敏'],
            'ming': ['名','明','命'],
            'miu': ['谬'],
            'mo': ['么','末','抹','沫','漠','莫','墨','默'],
            'mou': ['谋','某'],
            'mu': ['木','目','母','亩','幕','慕'],
            'na': ['那','拿','哪','纳'],
            'nai': ['奶','奈'],
            'nan': ['男','南','难'],
            'nao': ['脑','恼','闹'],
            'ne': ['呢'],
            'nei': ['内'],
            'nen': ['嫩'],
            'neng': ['能'],
            'ni': ['你','尼','泥','逆'],
            'nian': ['年','念'],
            'niang': ['娘'],
            'niao': ['鸟','尿'],
            'nie': ['捏','聂'],
            'nin': ['您'],
            'ning': ['宁','凝'],
            'niu': ['牛','扭','纽'],
            'nong': ['农','浓','弄'],
            'nu': ['努','怒'],
            'nuan': ['暖'],
            'nue': ['虐'],
            'nuo': ['挪','懦'],
            'o': ['哦'],
            'ou': ['欧','偶'],
            'pa': ['怕','爬','帕'],
            'pai': ['拍','排','派'],
            'pan': ['盘','判','叛','盼'],
            'pang': ['旁','胖'],
            'pao': ['跑','炮','泡'],
            'pei': ['配','陪','培','赔'],
            'pen': ['喷','盆'],
            'peng': ['朋','鹏','碰'],
            'pi': ['皮','疲','匹'],
            'pian': ['片','偏','篇','骗'],
            'piao': ['漂','飘','票'],
            'pie': ['撇'],
            'pin': ['拼','品','聘'],
            'ping': ['平','评','苹','瓶'],
            'po': ['坡','泼','婆','迫','破'],
            'pou': ['剖'],
            'pu': ['扑','铺','葡','朴','普'],
            'qi': ['七','奇','齐','起','气','汽'],
            'qia': ['恰'],
            'qian': ['千','前','钱','签','浅','欠'],
            'qiang': ['强','墙','抢'],
            'qiao': ['桥','巧','悄'],
            'qie': ['且','切','窃'],
            'qin': ['亲','琴','勤'],
            'qing': ['青','轻','清','情','晴','请'],
            'qiong': ['穷'],
            'qiu': ['秋','求','球'],
            'qu': ['区','取','去','趣'],
            'quan': ['全','权','泉','拳'],
            'que': ['却','缺','确'],
            'qun': ['群'],
            'ran': ['然','燃','染'],
            'rang': ['让'],
            'rao': ['饶','扰','绕'],
            're': ['热'],
            'ren': ['人','认','任','忍','仁'],
            'reng': ['仍'],
            'ri': ['日'],
            'rong': ['容','融','荣'],
            'rou': ['肉','柔','揉'],
            'ru': ['如','入','儒'],
            'ruan': ['软'],
            'rui': ['锐','瑞'],
            'run': ['润'],
            'ruo': ['若','弱'],
            'sa': ['洒','萨'],
            'sai': ['塞','赛'],
            'san': ['三','散','伞'],
            'sang': ['丧','桑'],
            'sao': ['扫','嫂'],
            'se': ['色','涩'],
            'sen': ['森'],
            'sha': ['杀','沙','纱','傻'],
            'shai': ['晒'],
            'shan': ['山','闪','扇','善','衫'],
            'shang': ['上','商','伤'],
            'shao': ['少','绍','烧'],
            'she': ['社','设','射','舍'],
            'shei': ['谁'],
            'shen': ['身','深','神','什','甚','审','肾'],
            'sheng': ['生','声','升','省','圣','剩'],
            'shi': ['十','什','石','时','识','实','拾','食','史','使','始','士','氏','世','市','示','式','事','势','视','试','是','适','室','释'],
            'shou': ['手','守','首','受','售','瘦'],
            'shu': ['书','叔','殊','梳','输','熟','暑','属','术','束','述','树','数'],
            'shua': ['刷'],
            'shuai': ['衰','摔','甩','帅'],
            'shuan': ['拴'],
            'shuang': ['双','霜','爽'],
            'shui': ['谁','水','税'],
            'shun': ['顺','瞬'],
            'shuo': ['说','硕'],
            'si': ['四','死','丝','司','私','思'],
            'song': ['松','送','宋'],
            'sou': ['搜','艘'],
            'su': ['苏','诉','素','速','塑'],
            'suan': ['酸','算'],
            'sui': ['虽','随','岁','碎'],
            'sun': ['孙','损','笋'],
            'suo': ['所','索','锁','缩'],
            'ta': ['他','她','它','塔'],
            'tai': ['太','台','态','泰'],
            'tan': ['谈','探','叹','炭','碳'],
            'tang': ['堂','唐','糖','躺','汤'],
            'tao': ['讨','逃','桃','陶'],
            'te': ['特'],
            'teng': ['疼','腾','藤'],
            'ti': ['体','提','题','替'],
            'tian': ['天','田','填'],
            'tiao': ['条','跳','调'],
            'tie': ['铁','贴'],
            'ting': ['听','停','庭','厅'],
            'tong': ['同','通','统','痛','童'],
            'tou': ['头','投','透'],
            'tu': ['土','图','徒','途','涂'],
            'tuan': ['团'],
            'tui': ['推','腿','退'],
            'tun': ['吞','屯','臀'],
            'tuo': ['托','拖','脱'],
            'wa': ['瓦','娃'],
            'wai': ['外'],
            'wan': ['万','完','玩','晚','碗'],
            'wang': ['王','网','往','忘','望'],
            'wei': ['为','位','卫','危','威','微','围','伟','味','畏','胃','喂','慰'],
            'wen': ['文','纹','闻','稳','问'],
            'weng': ['翁'],
            'wo': ['我','握','沃'],
            'wu': ['无','五','午','武','务','物','误','屋'],
            'xi': ['西','吸','希','息','席','习','喜','系','细'],
            'xia': ['下','夏','吓'],
            'xian': ['先','现','线','县','显','险','鲜'],
            'xiang': ['向','相','香','乡','象','像','响'],
            'xiao': ['小','笑','校','效','消'],
            'xie': ['写','谢','鞋','邪','协','胁'],
            'xin': ['心','新','信','辛'],
            'xing': ['行','星','型','形','性','姓','兴'],
            'xiong': ['兄','雄','胸','熊'],
            'xiu': ['休','修','秀','袖','锈'],
            'xu': ['须','需','许','序','续','徐'],
            'xuan': ['选','宣','悬','旋'],
            'xue': ['学','雪','血'],
            'xun': ['寻','训','讯','迅'],
            'ya': ['压','牙','亚','雅','呀','鸭'],
            'yan': ['言','严','岩','炎','沿','研','盐','颜','眼','演','验','燕'],
            'yang': ['阳','杨','扬','洋','仰','养'],
            'yao': ['要','药','摇','咬'],
            'ye': ['也','业','叶','夜','液'],
            'yi': ['一','以','已','义','亿','艺','忆','议','亦','异','役','译','易','疫','益','谊','意','翼'],
            'yin': ['因','阴','音','银','引','饮','隐','印'],
            'ying': ['应','英','迎','影','映','硬'],
            'yo': ['哟'],
            'yong': ['用','永','泳','勇','涌'],
            'you': ['又','由','油','游','友','有','右','幼'],
            'yu': ['于','与','予','玉','宇','羽','雨','语','育','郁','狱','浴','预','域','欲','遇','愈'],
            'yuan': ['元','园','员','原','圆','远','院','愿'],
            'yue': ['月','越','约','乐','岳','悦','阅'],
            'yun': ['云','运','允'],
            'za': ['杂','砸'],
            'zai': ['在','再','载','灾','栽'],
            'zan': ['赞','暂'],
            'zang': ['脏','葬'],
            'zao': ['早','造','遭','糟','澡','灶','燥','躁'],
            'ze': ['则','责','择','泽'],
            'zei': ['贼'],
            'zen': ['怎'],
            'zeng': ['增','赠','憎'],
            'zha': ['扎','炸','诈','榨','闸'],
            'zhai': ['摘','窄','债','宅'],
            'zhan': ['占','战','站','展','颤'],
            'zhang': ['张','章','掌','丈','帐','账','胀','障'],
            'zhao': ['找','召','照','罩','赵','兆'],
            'zhe': ['这','着','者','哲','浙'],
            'zhei': ['这'],
            'zhen': ['真','针','珍','诊','阵','振','镇','震'],
            'zheng': ['正','整','证','政','争','征','症'],
            'zhi': ['之','支','只','汁','芝','枝','知','织','执','直','值','职','植','止','址','纸','指','至','志','制','治','质','致','智','置','秩','稚'],
            'zhong': ['中','种','重','众','终','钟','仲','肿'],
            'zhou': ['州','舟','周','洲','粥','宙','昼','皱','骤'],
            'zhu': ['主','住','注','助','著','筑','铸','祝','珠','诸','猪','竹','烛','逐','柱','株','朱'],
            'zhua': ['抓'],
            'zhuai': ['拽'],
            'zhuan': ['专','转','赚','砖'],
            'zhuang': ['庄','装','壮','状','撞'],
            'zhui': ['追','准','锥'],
            'zhun': ['准'],
            'zhuo': ['捉','桌','卓','啄','浊'],
            'zi': ['子','字','自','资','姿','滋','紫','仔','籽'],
            'zong': ['总','宗','踪','纵','粽'],
            'zou': ['走','奏','邹'],
            'zu': ['足','组','族','祖','租','阻'],
            'zuan': ['钻','赚'],
            'zui': ['最','罪','嘴','醉'],
            'zun': ['尊','遵'],
            'zuo': ['作','做','坐','座','左','佐','昨']
        }
        
        result = basic_dict.get(pinyin.lower(), [])
        if result:
            return result[:5]  # 最多返回5个
            
        matches = []
        for key, chars in basic_dict.items():
            if key.startswith(pinyin.lower()) and key != pinyin.lower():
                matches.extend(chars[:2])
        return matches[:5]  # 最多返回5个


class MapWidget(QWidget):
    """高德地图组件 - 右侧半透明键盘"""
    
    nav_status_changed = pyqtSignal(str)
    nav_instruction = pyqtSignal(str)

    def __init__(self, amap_key="8b657a470f4b69e82bf81f72b3a2b3c0", parent=None):
        super().__init__(parent)
        self.amap_key = amap_key  # 高德地图 WebService API Key
        self.current_lat = None
        self.current_lon = None
        
        self.pinyin_handler = PinyinHandler(self)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.web_view = QWebEngineView()
        
        # 配置 WebEngine
        from PyQt5.QtWebEngineWidgets import QWebEngineSettings, QWebEngineProfile
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.FocusOnNavigationEnabled, False)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        
        # 配置页面禁用缓存（开发调试用）
        self.web_view.page().profile().setHttpCacheType(QWebEngineProfile.NoCache)
        
        self.channel = QWebChannel()
        self.channel.registerObject('pinyinHandler', self.pinyin_handler)
        
        # 注册高德地图 API 处理后端
        self.amap_api_handler = AMapAPIHandler(self.amap_key, self)
        self.channel.registerObject('amapAPI', self.amap_api_handler)
        
        self.web_view.page().setWebChannel(self.channel)
        
        main_layout.addWidget(self.web_view)
        self.load_amap()
        
        self.nav_timer = QTimer(self)
        self.nav_timer.timeout.connect(self.check_navigation_status)
        self.nav_timer.start(1000)

    def load_amap(self):
        """加载高德地图"""
        html_content = self.generate_amap_html()
        self.web_view.setHtml(html_content)

    def generate_amap_html(self):
        """生成地图 HTML - 右侧半透明键盘"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>高德骑行地图</title>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #1a1a1a; 
            overflow: hidden;
        }}
        #container {{ 
            width: 100%; 
            height: 100vh; 
            position: relative;
        }}
        
        /* ========== 顶部搜索栏 ========== */
        .search-panel {{
            position: absolute;
            top: 8px;
            left: 8px;
            right: 8px;
            background: rgba(30, 30, 30, 0.98);
            border-radius: 12px;
            padding: 10px;
            z-index: 2000;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }}
        
        .input-row {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        
        .search-input {{
            flex: 1;
            background: #2a2a2a;
            color: #fff;
            border: 2px solid #4DB8FF;
            border-radius: 10px;
            padding: 12px 15px;
            font-size: 16px;
            outline: none;
            height: 48px;
        }}
        
        .btn {{
            background: linear-gradient(135deg, #4DB8FF, #3A9FE0);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            height: 48px;
            transition: all 0.1s;
        }}
        
        .btn:active {{ transform: scale(0.95); }}
        .btn-keyboard {{ background: linear-gradient(135deg, #f39c12, #e67e22); font-size: 18px; padding: 12px; }}
        .btn-keyboard:hover::after {{ content: '键盘'; position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.8); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; z-index: 10000; }}
        .btn-nav {{ background: linear-gradient(135deg, #2ecc71, #27ae60); }}
        .btn-nav:hover::after {{ content: '开始导航'; position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.8); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; z-index: 10000; }}
        .btn-stop {{ background: linear-gradient(135deg, #e74c3c, #c0392b); padding: 12px; }}
        .btn-stop:hover::after {{ content: '停止导航'; position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.8); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; z-index: 10000; }}
        .btn-clear {{ background: linear-gradient(135deg, #666, #555); padding: 12px; }}
        .btn-clear:hover::after {{ content: '清除所有'; position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.8); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; z-index: 10000; }}
        
        /* 地图控制按钮（右上角） */
        /* 地图缩放按钮（右侧中间） */
        .zoom-controls {{
            position: absolute;
            top: 50%;
            right: 10px;
            transform: translateY(-50%);
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 1000;
        }}
        .btn-zoom {{
            width: 50px;
            height: 50px;
            border-radius: 10px;
            background: rgba(30, 30, 30, 0.95);
            border: 2px solid #4DB8FF;
            color: #4DB8FF;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }}
        .btn-zoom:active {{ 
            background: #4DB8FF; 
            color: white; 
            transform: scale(0.95);
        }}
        
        /* 位置信息 */
        .location-info {{
            position: absolute;
            top: 75px;
            left: 8px;
            background: rgba(30, 30, 30, 0.95);
            color: #4DB8FF;
            padding: 8px 12px;
            border-radius: 8px;
            border: 1.5px solid #4DB8FF;
            font-size: 12px;
            z-index: 1000;
        }}
        
        /* 触摸手势提示 */
        .touch-hint {{
            position: absolute;
            bottom: 180px;
            left: 8px;
            background: rgba(0, 0, 0, 0.7);
            color: #ccc;
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 11px;
            z-index: 1000;
            max-width: 200px;
            line-height: 1.6;
        }}
        
        /* 导航面板 - 键盘左侧 */
        .nav-panel {{
            position: absolute;
            bottom: 20px;
            left: 8px;
            right: 420px;
            background: rgba(46, 204, 113, 0.95);
            color: white;
            padding: 12px 15px;
            border-radius: 12px;
            z-index: 2500;
            display: none;
        }}
        
        .nav-instruction {{ font-size: 17px; font-weight: 600; margin-bottom: 4px; }}
        .nav-detail {{ font-size: 12px; opacity: 0.9; }}
        
        /* ========== 右侧半透明键盘 ========== */
        .keyboard-wrapper {{
            position: fixed;
            bottom: 15px;
            right: 10px;
            width: 400px;
            z-index: 3000;
            display: none;
        }}
        
        .keyboard-wrapper.active {{ display: block; }}
        
        /* 候选区 - 半透明灰色背景 */
        .candidates-area {{
            background: rgba(80, 80, 80, 0.5);
            backdrop-filter: blur(4px);
            border-radius: 12px 12px 0 0;
            border: 1px solid rgba(255,255,255,0.1);
            border-bottom: none;
            padding: 10px 12px;
            margin-bottom: 0;
        }}
        
        .pinyin-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 6px;
        }}
        
        .pinyin-label {{
            color: #aaa;
            font-size: 10px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .pinyin-text {{
            color: #4DB8FF;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }}
        
        .candidates-row {{
            display: flex;
            gap: 6px;
            overflow-x: auto;
            scrollbar-width: none;
            padding-bottom: 2px;
        }}
        
        .candidates-row::-webkit-scrollbar {{ display: none; }}
        
        .candidate-item {{
            background: rgba(100, 100, 100, 0.7);
            color: #fff;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 6px;
            padding: 6px 12px;
            font-size: 16px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.1s;
            min-width: 36px;
            text-align: center;
        }}
        
        .candidate-item:hover {{ 
            background: rgba(77, 184, 255, 0.8);
            border-color: #4DB8FF;
        }}
        .candidate-item:active {{ transform: scale(0.95); }}
        
        /* 翻页按钮样式 */
        .more-btn {{
            background: #4DB8FF !important;
            color: #fff !important;
            font-weight: bold;
            min-width: 40px;
        }}
        .more-btn:hover {{
            background: #3AA8F0 !important;
        }}
        
        /* 键盘主体 - 半透明灰色背景 */
        .keyboard-main {{
            background: rgba(70, 70, 70, 0.5);
            backdrop-filter: blur(4px);
            border-radius: 0 0 12px 12px;
            border: 1px solid rgba(255,255,255,0.1);
            border-top: 1px solid rgba(255,255,255,0.05);
            padding: 10px 8px 12px 8px;
        }}
        
        .kb-row {{
            display: flex;
            gap: 5px;
            margin-bottom: 6px;
            justify-content: center;
        }}
        
        /* 按键样式 - 半透明 */
        .key {{
            background: rgba(120, 120, 120, 0.6);
            color: white;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 6px;
            padding: 0;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.08s;
            flex: 1;
            max-width: 38px;
        }}
        
        .key:hover {{
            background: rgba(140, 140, 140, 0.7);
        }}
        
        .key:active {{
            background: rgba(100, 100, 100, 0.8);
            transform: scale(0.96);
        }}
        
        /* 特殊按键 */
        .key-shift {{ 
            flex: 1.3;
            max-width: 50px;
            background: rgba(100, 100, 100, 0.65);
            font-size: 14px;
        }}
        .key-back {{ 
            flex: 1.3;
            max-width: 50px;
            background: rgba(110, 110, 110, 0.65);
            font-size: 14px;
        }}
        .key-space {{ 
            flex: 4;
            max-width: 180px;
            font-size: 14px;
            background: rgba(120, 120, 120, 0.6);
        }}
        .key-enter {{ 
            flex: 1.4;
            max-width: 65px;
            background: rgba(46, 204, 113, 0.7);
            font-size: 14px;
            color: white;
            font-weight: 600;
        }}
        .key-enter:hover {{ 
            background: rgba(46, 204, 113, 0.85);
        }}
        .key-enter:active {{ 
            background: rgba(39, 174, 96, 0.9);
        }}
        
        /* 行缩进 */
        .row-qwerty {{ padding-left: 15px; padding-right: 15px; }}
        .row-asdf {{ padding-left: 25px; padding-right: 25px; }}
        .row-zxcv {{ padding-left: 10px; padding-right: 10px; }}
        .row-space {{ padding-left: 20px; padding-right: 20px; }}
        
        /* 高德建议列表 */
        .suggestions-list {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: rgba(30, 30, 30, 0.98);
            border: 1px solid #333;
            border-top: none;
            border-radius: 0 0 10px 10px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 2001;
            display: none;
            margin-top: 4px;
        }}
        
        .suggestion-item {{
            padding: 12px 15px;
            color: #fff;
            cursor: pointer;
            border-bottom: 1px solid #333;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .suggestion-item:hover {{ background: #4DB8FF; }}
        .suggestion-addr {{ color: #888; font-size: 11px; margin-left: auto; }}
    </style>
</head>
<body>
    <div id="container"></div>
    
    <!-- 搜索面板 -->
    <div class="search-panel">
        <div style="position: relative;">
            <div class="input-row">
                <input type="text" id="searchInput" class="search-input" placeholder="点击键盘输入或点击地图选择位置..." readonly>
                <button class="btn btn-keyboard" onclick="toggleKeyboard()" title="键盘">⌨️</button>
                <button class="btn btn-nav" onclick="startNavigation()">🧭 导航</button>
                <button class="btn btn-stop" onclick="stopNavigation()">⏹️</button>
                <button class="btn btn-clear" onclick="clearAll()">🗑️</button>
            </div>
            <div id="suggestionsList" class="suggestions-list"></div>
        </div>
    </div>
    
    <!-- 位置信息 -->
    <div class="location-info" id="locationInfo">📍 等待GPS...</div>
    
    <!-- 地图缩放按钮（右侧中间） -->
    <div class="zoom-controls">
        <button class="btn-zoom" onclick="zoomIn()" title="放大">+</button>
        <button class="btn-zoom" onclick="zoomOut()" title="缩小">−</button>
    </div>
    
    <!-- 导航面板 - 键盘左侧 -->
    <div class="nav-panel" id="navPanel">
        <div class="nav-instruction" id="navInstruction">准备出发</div>
        <div class="nav-detail" id="navDetail">--</div>
    </div>
    
    <!-- ========== 右侧半透明键盘 ========== -->
    <div class="keyboard-wrapper" id="keyboard">
        <!-- 候选区 -->
        <div class="candidates-area">
            <div class="pinyin-row">
                <span class="pinyin-label">拼音</span>
                <span id="pinyinText" class="pinyin-text"></span>
            </div>
            <div id="candidatesContainer" class="candidates-row"></div>
        </div>
        
        <!-- 键盘按键区 -->
        <div class="keyboard-main">
            <!-- 第1行：数字 -->
            <div class="kb-row">
                <button class="key" onclick="inputChar('1')">1</button>
                <button class="key" onclick="inputChar('2')">2</button>
                <button class="key" onclick="inputChar('3')">3</button>
                <button class="key" onclick="inputChar('4')">4</button>
                <button class="key" onclick="inputChar('5')">5</button>
                <button class="key" onclick="inputChar('6')">6</button>
                <button class="key" onclick="inputChar('7')">7</button>
                <button class="key" onclick="inputChar('8')">8</button>
                <button class="key" onclick="inputChar('9')">9</button>
                <button class="key" onclick="inputChar('0')">0</button>
            </div>
            
            <!-- 第2行：QWERTY -->
            <div class="kb-row row-qwerty">
                <button class="key" onclick="inputChar('q')">Q</button>
                <button class="key" onclick="inputChar('w')">W</button>
                <button class="key" onclick="inputChar('e')">E</button>
                <button class="key" onclick="inputChar('r')">R</button>
                <button class="key" onclick="inputChar('t')">T</button>
                <button class="key" onclick="inputChar('y')">Y</button>
                <button class="key" onclick="inputChar('u')">U</button>
                <button class="key" onclick="inputChar('i')">I</button>
                <button class="key" onclick="inputChar('o')">O</button>
                <button class="key" onclick="inputChar('p')">P</button>
            </div>
            
            <!-- 第3行：ASDF -->
            <div class="kb-row row-asdf">
                <button class="key" onclick="inputChar('a')">A</button>
                <button class="key" onclick="inputChar('s')">S</button>
                <button class="key" onclick="inputChar('d')">D</button>
                <button class="key" onclick="inputChar('f')">F</button>
                <button class="key" onclick="inputChar('g')">G</button>
                <button class="key" onclick="inputChar('h')">H</button>
                <button class="key" onclick="inputChar('j')">J</button>
                <button class="key" onclick="inputChar('k')">K</button>
                <button class="key" onclick="inputChar('l')">L</button>
            </div>
            
            <!-- 第4行：ZXCV -->
            <div class="kb-row row-zxcv">
                <button class="key key-shift" onclick="toggleShift()">⇧</button>
                <button class="key" onclick="inputChar('z')">Z</button>
                <button class="key" onclick="inputChar('x')">X</button>
                <button class="key" onclick="inputChar('c')">C</button>
                <button class="key" onclick="inputChar('v')">V</button>
                <button class="key" onclick="inputChar('b')">B</button>
                <button class="key" onclick="inputChar('n')">N</button>
                <button class="key" onclick="inputChar('m')">M</button>
                <button class="key key-back" onclick="handleBackspace()">⌫</button>
            </div>
            
            <!-- 第5行：功能键 -->
            <div class="kb-row row-space">
                <button class="key key-space" onclick="inputChar(' ')">空格</button>
                <button class="key key-enter" onclick="confirmInput()">确定</button>
            </div>
        </div>
    </div>

    <script>
        window._AMapSecurityConfig = {{
            securityJsCode: '2355cb366c87c99e9733d5266db19854'
        }};
    </script>
    <script src="https://webapi.amap.com/maps?v=2.0&key={self.amap_key}&plugin=AMap.Driving,AMap.Scale"></script>
    
    <script>
        // 全局变量
        var map, currentPos, destPos, currentMarker, destMarker, trackLine;
        var driving;
        var isNavigating = false, routeInfo = null, trackPoints = [];
        var pinyinBuffer = "";
        var isShiftOn = false;
        var amapAPI = null;
        var pinyinHandler = null;
        var isMapInitialized = false;
        
        // DOM 加载完成后初始化
        document.addEventListener("DOMContentLoaded", function() {{
            console.log('DOM 加载完成');
            
            // 先初始化地图
            initMap();
            
            // 连接 QWebChannel
            if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    amapAPI = channel.objects.amapAPI;
                    pinyinHandler = channel.objects.pinyinHandler;
                    console.log('QWebChannel 连接成功, amapAPI:', amapAPI ? '可用' : '不可用');
                    
                    // 绑定需要 API 的地图事件
                    bindMapEvents();
                }});
            }} else {{
                console.error('QWebChannel 未就绪');
                document.getElementById('locationInfo').innerHTML = '⚠️ API未连接';
            }}
        }});
        
        // 初始化地图（不依赖 API）
        function initMap() {{
            if (isMapInitialized) return;
            
            map = new AMap.Map('container', {{
                zoom: 16,
                center: [114.057868, 22.543099],
                viewMode: '2D',
                mapStyle: 'amap://styles/dark'
            }});
            
            map.addControl(new AMap.Scale({{position: 'LB'}}));
            
            // 监听缩放事件
            map.on('zoomchange', function() {{
                console.log('地图缩放级别变化:', map.getZoom());
            }});
            
            // 初始化路径规划
            initDriving();
            
            isMapInitialized = true;
            console.log('地图初始化完成');
            console.log('当前缩放级别:', map.getZoom());
        }}
        
        // 绑定地图事件（需要 amapAPI 连接后）
        function bindMapEvents() {{
            if (!amapAPI) {{
                console.error('amapAPI 不可用');
                return;
            }}
            
            console.log('绑定地图事件...');
            
            // 点击地图获取地址
            map.on('click', function(e) {{
                var lng = e.lnglat.getLng();
                var lat = e.lnglat.getLat();
                var location = lng + ',' + lat;
                
                console.log('点击位置:', location);
                document.getElementById('locationInfo').innerHTML = '📍 正在获取地址...';
                
                // QWebChannel 返回 Promise
                amapAPI.geocode_regeo(location).then(function(result) {{
                    try {{
                        var data = JSON.parse(result);
                        console.log('逆地理编码结果:', data);
                        
                        if (data.status === '1' && data.regeocode) {{
                            var address = data.regeocode.formatted_address;
                            var comp = data.regeocode.addressComponent;
                            var district = comp.district || '';
                            var street = comp.street || '';
                            var number = comp.streetNumber || '';
                            var shortAddress = district + street + number;
                            if (!shortAddress) shortAddress = address;
                            
                            document.getElementById('locationInfo').innerHTML = 
                                '📍 ' + shortAddress + '<br>' +
                                lng.toFixed(5) + ',' + lat.toFixed(5);
                            
                            addTempMarker(e.lnglat, shortAddress);
                            document.getElementById('searchInput').value = shortAddress;
                        }} else {{
                            document.getElementById('locationInfo').innerHTML = 
                                '📍 无法获取地址<br>' + lng.toFixed(5) + ',' + lat.toFixed(5);
                        }}
                    }} catch(e) {{
                        console.error('解析失败:', e);
                        document.getElementById('locationInfo').innerHTML = 
                            '📍 解析失败<br>' + lng.toFixed(5) + ',' + lat.toFixed(5);
                    }}
                }}).catch(function(err) {{
                    console.error('请求失败:', err);
                    document.getElementById('locationInfo').innerHTML = 
                        '📍 请求失败<br>' + lng.toFixed(5) + ',' + lat.toFixed(5);
                }});
                
                hideKeyboard();
            }});
            
            console.log('地图事件绑定完成');
        }}
        
        // 输入提示
        window.fetchInputTips = function(keywords) {{
            console.log('fetchInputTips:', keywords);
            if (!amapAPI) {{
                console.error('amapAPI 未连接');
                return;
            }}
            if (!keywords || keywords.length < 2) {{
                document.getElementById('suggestionsList').style.display = 'none';
                return;
            }}
            
            console.log('输入提示请求:', keywords);
            amapAPI.input_tips(keywords, '全国').then(function(result) {{
                try {{
                    var data = JSON.parse(result);
                    console.log('输入提示结果:', data);
                    if (data.status === '1' && data.tips) {{
                        showSuggestions(data.tips);
                    }} else {{
                        document.getElementById('suggestionsList').style.display = 'none';
                    }}
                }} catch(e) {{
                    console.error('输入提示解析失败:', e);
                }}
            }}).catch(function(err) {{
                console.error('输入提示请求失败:', err);
            }});
        }};
        
        // 初始化路径规划
        function initDriving() {{
            driving = new AMap.Driving({{
                map: map,
                policy: AMap.DrivingPolicy.LEAST_DISTANCE,
                hideMarkers: true
            }});
            
            driving.on('complete', onRouteComplete);
        }}
        
        // 临时标记（点击地图时显示）
        var tempMarker = null;
        window.addTempMarker = function(position, title) {{
            if (tempMarker) {{
                map.remove(tempMarker);
            }}
            tempMarker = new AMap.Marker({{
                position: position,
                map: map,
                title: title,
                animation: 'AMAP_ANIMATION_DROP',
                label: {{
                    content: title,
                    offset: new AMap.Pixel(0, -30)
                }}
            }});
            
            // 5秒后移除临时标记
            setTimeout(function() {{
                if (tempMarker) {{
                    map.remove(tempMarker);
                    tempMarker = null;
                }}
            }}, 5000);
        }};
        
        // 地图缩放控制函数
        window.zoomIn = function() {{
            try {{
                var currentZoom = map.getZoom();
                map.setZoom(currentZoom + 1);
                console.log('放大到:', currentZoom + 1);
            }} catch(e) {{ console.error('放大失败:', e); }}
        }};
        window.zoomOut = function() {{
            try {{
                var currentZoom = map.getZoom();
                map.setZoom(currentZoom - 1);
                console.log('缩小到:', currentZoom - 1);
            }} catch(e) {{ console.error('缩小失败:', e); }}
        }}
        
        // 拼音输入处理
        function inputChar(char) {{
            var input = document.getElementById('searchInput');
            
            if (isShiftOn && char >= 'a' && char <= 'z') {{
                char = char.toUpperCase();
            }}
            
            if (char >= 'a' && char <= 'z') {{
                pinyinBuffer += char;
                updatePinyinDisplay();
                fetchCandidates();
            }} else {{
                input.value += char;
                clearPinyinState();
            }}
        }}
        
        function updatePinyinDisplay() {{
            var text = document.getElementById('pinyinText');
            if (pinyinBuffer.length > 0) {{
                text.textContent = pinyinBuffer;
            }} else {{
                text.textContent = '';
            }}
        }}
        
        var currentCandidatePage = 0;  // 当前候选词页码
        
        function fetchCandidates(page) {{
            if (page === undefined) page = 0;
            currentCandidatePage = page;
            getCandidatesFromDict(pinyinBuffer, page);
        }}
        
        function getCandidatesFromDict(py, page) {{
            if (pinyinHandler) {{
                pinyinHandler.get_candidates(py, page).then(function(result) {{
                    showCandidates(result);
                }}).catch(function(err) {{
                    console.error('获取候选词失败:', err);
                }});
            }} else {{
                // 备用词典（不分页）
                var dict = {{
                'a': ['阿','啊','安','岸','按','案','暗'],
                'ai': ['哀','埃','挨','爱'],
                'an': ['安','岸','按','案','暗'],
                'ang': ['昂'],
                'ao': ['傲','奥','澳'],
                'ba': ['八','巴','把','爸','罢'],
                'bai': ['白','百','摆','败'],
                'ban': ['班','般','板','办','半'],
                'bang': ['帮','邦','榜','棒'],
                'bao': ['包','保','报','抱','暴'],
                'bei': ['北','贝','备','背','倍','被'],
                'ben': ['本','笨'],
                'bi': ['比','笔','币','必','毕','闭'],
                'bian': ['边','编','变','便','遍'],
                'biao': ['标','表'],
                'bie': ['别'],
                'bing': ['冰','兵','并','病'],
                'bo': ['波','博','伯','播'],
                'bu': ['不','布','步','部'],
                'cai': ['才','采','彩','菜'],
                'can': ['参','餐','残','惨'],
                'cang': ['仓','苍','藏'],
                'cao': ['操','草'],
                'ce': ['册','侧','测','策'],
                'ceng': ['层','曾'],
                'cha': ['叉','查','茶','差','插'],
                'chai': ['柴','拆'],
                'chan': ['产','颤','缠'],
                'chang': ['长','场','常','厂','唱'],
                'chao': ['超','朝','潮','吵'],
                'che': ['车','彻','撤'],
                'chen': ['陈','晨','沉','称'],
                'cheng': ['成','城','承','乘','程'],
                'chi': ['吃','池','持','尺','赤'],
                'chong': ['充','冲','虫','崇'],
                'chou': ['抽','愁','仇','丑','臭'],
                'chu': ['出','初','除','处','触'],
                'chuan': ['川','穿','传','船','串'],
                'chuang': ['创','床','窗'],
                'chun': ['春','纯','唇'],
                'ci': ['词','此','次','刺'],
                'cong': ['从','匆','葱','聪'],
                'cu': ['粗','促','醋'],
                'cuan': ['窜'],
                'cui': ['催','脆','翠'],
                'cun': ['村','存','寸'],
                'cuo': ['错','措'],
                'da': ['大','打','达'],
                'dai': ['代','带','待','袋'],
                'dan': ['丹','单','担','但','蛋'],
                'dang': ['当','党','档'],
                'dao': ['刀','导','到','道','倒'],
                'de': ['得','的','德'],
                'deng': ['灯','登','等','邓'],
                'di': ['低','底','地','第','弟'],
                'dian': ['电','店','典','点'],
                'diao': ['掉','调','钓'],
                'die': ['爹','跌','叠'],
                'ding': ['丁','订','定'],
                'diu': ['丢'],
                'dong': ['东','冬','动','洞'],
                'dou': ['都','斗','抖','豆'],
                'du': ['都','读','度','渡','独'],
                'duan': ['段','断','端'],
                'dui': ['对','队'],
                'dun': ['吨','蹲','顿'],
                'duo': ['多','夺','朵','躲'],
                'e': ['俄','恶','饿','恩'],
                'er': ['儿','而','耳','二'],
                'fa': ['发','法','罚'],
                'fan': ['反','返','饭','犯','范'],
                'fang': ['方','房','防','放','访'],
                'fei': ['飞','非','肥','费'],
                'fen': ['分','份','奋','愤'],
                'feng': ['风','丰','封','峰','锋'],
                'fo': ['佛'],
                'fou': ['否'],
                'fu': ['夫','服','父','付','负','富','府'],
                'gai': ['该','改','概','盖'],
                'gan': ['干','甘','赶','敢','感'],
                'gang': ['刚','岗','纲','钢','港'],
                'gao': ['高','搞','告'],
                'ge': ['个','各','哥','歌','格','隔'],
                'gei': ['给'],
                'gen': ['根','跟'],
                'geng': ['更','耕'],
                'gong': ['工','公','功','共','供','宫'],
                'gou': ['勾','沟','钩','狗','够','购'],
                'gu': ['古','股','固','故','顾'],
                'gua': ['瓜','刮','挂'],
                'guai': ['乖','拐','怪'],
                'guan': ['关','观','官','馆','管','惯'],
                'guang': ['光','广'],
                'gui': ['归','规','轨','鬼','贵','桂'],
                'gun': ['滚'],
                'guo': ['过','国','果'],
                'hai': ['还','孩','海','害'],
                'han': ['汉','含','寒','汗'],
                'hang': ['行','航','杭'],
                'hao': ['好','号','毫','浩'],
                'he': ['合','和','河','何','贺'],
                'hei': ['黑'],
                'hen': ['很','恨','狠'],
                'heng': ['横','恒'],
                'hong': ['红','洪','宏','虹'],
                'hou': ['后','厚','候'],
                'hu': ['乎','呼','胡','湖','户','护'],
                'hua': ['花','华','划','化','话','画'],
                'huai': ['怀','坏'],
                'huan': ['欢','还','环','换','幻'],
                'huang': ['黄','皇','荒','慌'],
                'hui': ['回','会','汇','辉','悔','惠'],
                'hun': ['昏','婚','浑','混'],
                'huo': ['火','或','货','获','惑'],
                'ji': ['几','机','鸡','积','及','极','急','集','计','记','技','际','济','继'],
                'jia': ['加','甲','价','驾','架','家','假'],
                'jian': ['间','件','建','剑','见','健','渐','鉴'],
                'jiang': ['江','将','讲','奖','降','酱'],
                'jiao': ['交','叫','教','较','角','脚'],
                'jie': ['接','街','节','结','解','介','界'],
                'jin': ['今','斤','金','仅','尽','进','近'],
                'jing': ['京','经','精','静','境','敬'],
                'jiu': ['九','久','酒','旧','救','就'],
                'ju': ['局','举','巨','拒','具','据','距'],
                'juan': ['捐','卷'],
                'jue': ['决','绝','觉'],
                'jun': ['军','君','均','俊'],
                'kai': ['开','凯'],
                'kan': ['看','刊','砍'],
                'kang': ['康','抗'],
                'kao': ['考','靠'],
                'ke': ['可','科','客','课'],
                'ken': ['肯'],
                'keng': ['坑'],
                'kong': ['空','孔','恐'],
                'kou': ['口','扣'],
                'ku': ['苦','库','裤'],
                'kua': ['夸','垮','跨'],
                'kuai': ['快','块'],
                'kuan': ['宽','款'],
                'kuang': ['狂','况','矿','框'],
                'kui': ['亏','葵'],
                'kun': ['困'],
                'kuo': ['扩','括'],
                'la': ['拉','啦','落','辣'],
                'lai': ['来','赖'],
                'lan': ['兰','蓝','览','烂'],
                'lang': ['郎','狼','朗','浪'],
                'lao': ['老','劳','牢'],
                'le': ['乐','勒'],
                'lei': ['雷','累','泪','类'],
                'leng': ['冷'],
                'li': ['力','历','立','丽','利','里','理'],
                'lia': ['俩'],
                'lian': ['连','联','练','恋','链'],
                'liang': ['两','亮','量','凉','粮'],
                'liao': ['辽','疗','料'],
                'lie': ['列','劣','烈','猎'],
                'lin': ['林','临','淋'],
                'ling': ['令','灵','岭','领','另'],
                'liu': ['六','流','留','刘','柳'],
                'long': ['龙','笼','隆'],
                'lou': ['楼','漏','露'],
                'lu': ['路','陆','录'],
                'luan': ['乱','卵'],
                'lue': ['掠','略'],
                'lun': ['论','轮'],
                'luo': ['罗','落','络','骆'],
                'ma': ['马','妈','码','吗','麻'],
                'mai': ['买','卖','麦'],
                'man': ['满','慢','漫','忙'],
                'mang': ['忙','芒','盲','茫'],
                'mao': ['毛','矛','茅','茂','冒','貌'],
                'mei': ['没','每','美','妹'],
                'men': ['门','们','闷'],
                'meng': ['梦','蒙','猛'],
                'mi': ['米','密','蜜'],
                'mian': ['面','棉','免'],
                'miao': ['苗','描','秒','妙'],
                'mie': ['灭','蔑'],
                'min': ['民','敏'],
                'ming': ['名','明','命'],
                'miu': ['谬'],
                'mo': ['么','末','抹','沫','漠','莫','墨','默'],
                'mou': ['谋','某'],
                'mu': ['木','目','母','亩','幕','慕'],
                'na': ['那','拿','哪','纳'],
                'nai': ['奶','奈'],
                'nan': ['男','南','难'],
                'nao': ['脑','恼','闹'],
                'ne': ['呢'],
                'nei': ['内'],
                'nen': ['嫩'],
                'neng': ['能'],
                'ni': ['你','尼','泥','逆'],
                'nian': ['年','念'],
                'niang': ['娘'],
                'niao': ['鸟','尿'],
                'nie': ['捏','聂'],
                'nin': ['您'],
                'ning': ['宁','凝'],
                'niu': ['牛','扭','纽'],
                'nong': ['农','浓','弄'],
                'nu': ['努','怒'],
                'nuan': ['暖'],
                'nue': ['虐'],
                'nuo': ['挪','懦'],
                'o': ['哦'],
                'ou': ['欧','偶'],
                'pa': ['怕','爬','帕'],
                'pai': ['拍','排','派'],
                'pan': ['盘','判','叛','盼'],
                'pang': ['旁','胖'],
                'pao': ['跑','炮','泡'],
                'pei': ['配','陪','培','赔'],
                'pen': ['喷','盆'],
                'peng': ['朋','鹏','碰'],
                'pi': ['皮','疲','匹'],
                'pian': ['片','偏','篇','骗'],
                'piao': ['漂','飘','票'],
                'pie': ['撇'],
                'pin': ['拼','品','聘'],
                'ping': ['平','评','苹','瓶'],
                'po': ['坡','泼','婆','迫','破'],
                'pou': ['剖'],
                'pu': ['扑','铺','葡','朴','普'],
                'qi': ['七','奇','齐','起','气','汽'],
                'qia': ['恰'],
                'qian': ['千','前','钱','签','浅','欠'],
                'qiang': ['强','墙','抢'],
                'qiao': ['桥','巧','悄'],
                'qie': ['且','切','窃'],
                'qin': ['亲','琴','勤'],
                'qing': ['青','轻','清','情','晴','请'],
                'qiong': ['穷'],
                'qiu': ['秋','求','球'],
                'qu': ['区','取','去','趣'],
                'quan': ['全','权','泉','拳'],
                'que': ['却','缺','确'],
                'qun': ['群'],
                'ran': ['然','燃','染'],
                'rang': ['让'],
                'rao': ['饶','扰','绕'],
                're': ['热'],
                'ren': ['人','认','任','忍','仁'],
                'reng': ['仍'],
                'ri': ['日'],
                'rong': ['容','融','荣'],
                'rou': ['肉','柔','揉'],
                'ru': ['如','入','儒'],
                'ruan': ['软'],
                'rui': ['锐','瑞'],
                'run': ['润'],
                'ruo': ['若','弱'],
                'sa': ['洒','萨'],
                'sai': ['塞','赛'],
                'san': ['三','散','伞'],
                'sang': ['丧','桑'],
                'sao': ['扫','嫂'],
                'se': ['色','涩'],
                'sen': ['森'],
                'sha': ['杀','沙','纱','傻'],
                'shai': ['晒'],
                'shan': ['山','闪','扇','善','衫'],
                'shang': ['上','商','伤'],
                'shao': ['少','绍','烧'],
                'she': ['社','设','射','舍'],
                'shei': ['谁'],
                'shen': ['身','深','神','什','甚','审','肾'],
                'sheng': ['生','声','升','省','圣','剩'],
                'shi': ['十','什','石','时','识','实','拾','食','史','使','始','士','氏','世','市','示','式','事','势','视','试','是','适','室','释'],
                'shou': ['手','守','首','受','售','瘦'],
                'shu': ['书','叔','殊','梳','输','熟','暑','属','术','束','述','树','数'],
                'shua': ['刷'],
                'shuai': ['衰','摔','甩','帅'],
                'shuan': ['拴'],
                'shuang': ['双','霜','爽'],
                'shui': ['谁','水','税'],
                'shun': ['顺','瞬'],
                'shuo': ['说','硕'],
                'si': ['四','死','丝','司','私','思'],
                'song': ['松','送','宋'],
                'sou': ['搜','艘'],
                'su': ['苏','诉','素','速','塑'],
                'suan': ['酸','算'],
                'sui': ['虽','随','岁','碎'],
                'sun': ['孙','损','笋'],
                'suo': ['所','索','锁','缩'],
                'ta': ['他','她','它','塔'],
                'tai': ['太','台','态','泰'],
                'tan': ['谈','探','叹','炭','碳'],
                'tang': ['堂','唐','糖','躺','汤'],
                'tao': ['讨','逃','桃','陶'],
                'te': ['特'],
                'teng': ['疼','腾','藤'],
                'ti': ['体','提','题','替'],
                'tian': ['天','田','填'],
                'tiao': ['条','跳','调'],
                'tie': ['铁','贴'],
                'ting': ['听','停','庭','厅'],
                'tong': ['同','通','统','痛','童'],
                'tou': ['头','投','透'],
                'tu': ['土','图','徒','途','涂'],
                'tuan': ['团'],
                'tui': ['推','腿','退'],
                'tun': ['吞','屯','臀'],
                'tuo': ['托','拖','脱'],
                'wa': ['瓦','娃'],
                'wai': ['外'],
                'wan': ['万','完','玩','晚','碗'],
                'wang': ['王','网','往','忘','望'],
                'wei': ['为','位','卫','危','威','微','围','伟','味','畏','胃','喂','慰'],
                'wen': ['文','纹','闻','稳','问'],
                'weng': ['翁'],
                'wo': ['我','握','沃'],
                'wu': ['无','五','午','武','务','物','误','屋'],
                'xi': ['西','吸','希','息','席','习','喜','系','细'],
                'xia': ['下','夏','吓'],
                'xian': ['先','现','线','县','显','险','鲜'],
                'xiang': ['向','相','香','乡','象','像','响'],
                'xiao': ['小','笑','校','效','消'],
                'xie': ['写','谢','鞋','邪','协','胁'],
                'xin': ['心','新','信','辛'],
                'xing': ['行','星','型','形','性','姓','兴'],
                'xiong': ['兄','雄','胸','熊'],
                'xiu': ['休','修','秀','袖','锈'],
                'xu': ['须','需','许','序','续','徐'],
                'xuan': ['选','宣','悬','旋'],
                'xue': ['学','雪','血'],
                'xun': ['寻','训','讯','迅'],
                'ya': ['压','牙','亚','雅','呀','鸭'],
                'yan': ['言','严','岩','炎','沿','研','盐','颜','眼','演','验','燕'],
                'yang': ['阳','杨','扬','洋','仰','养'],
                'yao': ['要','药','摇','咬'],
                'ye': ['也','业','叶','夜','液'],
                'yi': ['一','以','已','义','亿','艺','忆','议','亦','异','役','译','易','疫','益','谊','意','翼'],
                'yin': ['因','阴','音','银','引','饮','隐','印'],
                'ying': ['应','英','迎','影','映','硬'],
                'yo': ['哟'],
                'yong': ['用','永','泳','勇','涌'],
                'you': ['又','由','油','游','友','有','右','幼'],
                'yu': ['于','与','予','玉','宇','羽','雨','语','育','郁','狱','浴','预','域','欲','遇','愈'],
                'yuan': ['元','园','员','原','圆','远','院','愿'],
                'yue': ['月','越','约','乐','岳','悦','阅'],
                'yun': ['云','运','允'],
                'za': ['杂','砸'],
                'zai': ['在','再','载','灾','栽'],
                'zan': ['赞','暂'],
                'zang': ['脏','葬'],
                'zao': ['早','造','遭','糟','澡','灶','燥','躁'],
                'ze': ['则','责','择','泽'],
                'zei': ['贼'],
                'zen': ['怎'],
                'zeng': ['增','赠','憎'],
                'zha': ['扎','炸','诈','榨','闸'],
                'zhai': ['摘','窄','债','宅'],
                'zhan': ['占','战','站','展','颤'],
                'zhang': ['张','章','掌','丈','帐','账','胀','障'],
                'zhao': ['找','召','照','罩','赵','兆'],
                'zhe': ['这','着','者','哲','浙'],
                'zhei': ['这'],
                'zhen': ['真','针','珍','诊','阵','振','镇','震'],
                'zheng': ['正','整','证','政','争','征','症'],
                'zhi': ['之','支','只','汁','芝','枝','知','织','执','直','值','职','植','止','址','纸','指','至','志','制','治','质','致','智','置','秩','稚'],
                'zhong': ['中','种','重','众','终','钟','仲','肿'],
                'zhou': ['州','舟','周','洲','粥','宙','昼','皱','骤'],
                'zhu': ['主','住','注','助','著','筑','铸','祝','珠','诸','猪','竹','烛','逐','柱','株','朱'],
                'zhua': ['抓'],
                'zhuai': ['拽'],
                'zhuan': ['专','转','赚','砖'],
                'zhuang': ['庄','装','壮','状','撞'],
                'zhui': ['追','准','锥'],
                'zhun': ['准'],
                'zhuo': ['捉','桌','卓','啄','浊'],
                'zi': ['子','字','自','资','姿','滋','紫','仔','籽'],
                'zong': ['总','宗','踪','纵','粽'],
                'zou': ['走','奏','邹'],
                'zu': ['足','组','族','祖','租','阻'],
                'zuan': ['钻','赚'],
                'zui': ['最','罪','嘴','醉'],
                'zun': ['尊','遵'],
                'zuo': ['作','做','坐','座','左','佐','昨']
                }};
                
                var candidates = dict[py.toLowerCase()] || [];
                
                if (candidates.length === 0) {{
                    for (var key in dict) {{
                        if (key.startsWith(py.toLowerCase()) && key !== py.toLowerCase()) {{
                            candidates = candidates.concat(dict[key].slice(0, 2));
                        }}
                    }}
                }}
                
                // 返回分页格式（备用词典不分页，但保持格式一致）
                showCandidates({{
                    candidates: candidates.slice(0, 5),
                    total: candidates.length,
                    has_more: false,
                    page: 0
                }});
            }}
        }}
        
        function showCandidates(result) {{
            var container = document.getElementById('candidatesContainer');
            container.innerHTML = '';
            
            // 处理返回值（可能是数组或对象）
            var candidates = [];
            var hasMore = false;
            var currentPage = 0;
            
            if (Array.isArray(result)) {{
                // 兼容旧格式（数组）
                candidates = result;
                console.log('[IME] Array format, length:', candidates.length);
            }} else if (result && result.candidates) {{
                // 新格式（分页对象）
                candidates = result.candidates;
                hasMore = result.has_more;
                currentPage = result.page || 0;
                console.log('[IME] Object: page=' + currentPage + ', count=' + candidates.length + ', hasMore=' + hasMore);
                console.log('[IME] Raw result:', JSON.stringify(result));
            }}
            
            if (!candidates || candidates.length === 0) return;
            
            // 创建外层容器，使用space-between布局
            var wrapperDiv = document.createElement('div');
            wrapperDiv.style.display = 'flex';
            wrapperDiv.style.justifyContent = 'space-between';
            wrapperDiv.style.alignItems = 'center';
            wrapperDiv.style.width = '100%';
            
            // 左侧容器：候选词
            var candidatesDiv = document.createElement('div');
            candidatesDiv.style.display = 'flex';
            candidatesDiv.style.flexWrap = 'wrap';
            candidatesDiv.style.gap = '4px';
            candidatesDiv.style.alignItems = 'center';
            candidatesDiv.style.flex = '1';
            
            // 添加候选词按钮（最多5个）
            candidates.slice(0, 5).forEach(function(ch) {{
                var btn = document.createElement('button');
                btn.className = 'candidate-item';
                btn.textContent = ch;
                btn.onclick = function() {{ selectCandidate(ch); }};
                candidatesDiv.appendChild(btn);
            }});
            
            // 右侧容器：翻页按钮（固定在最右边）
            var buttonsDiv = document.createElement('div');
            buttonsDiv.style.display = 'flex';
            buttonsDiv.style.gap = '4px';
            buttonsDiv.style.alignItems = 'center';
            buttonsDiv.style.marginLeft = '8px';
            
            // 如果不是第一页，显示 << 按钮
            if (currentPage > 0) {{
                var prevBtn = document.createElement('button');
                prevBtn.className = 'candidate-item more-btn';
                prevBtn.textContent = '<<';
                prevBtn.onclick = function() {{ 
                    fetchCandidates(currentCandidatePage - 1);
                }};
                buttonsDiv.appendChild(prevBtn);
            }}
            
            // 如果有更多候选词，显示 >> 按钮
            if (hasMore) {{
                var moreBtn = document.createElement('button');
                moreBtn.className = 'candidate-item more-btn';
                moreBtn.textContent = '>>';
                moreBtn.onclick = function() {{ 
                    fetchCandidates(currentCandidatePage + 1);
                }};
                buttonsDiv.appendChild(moreBtn);
            }}
            
            wrapperDiv.appendChild(candidatesDiv);
            wrapperDiv.appendChild(buttonsDiv);
            container.appendChild(wrapperDiv);
        }}
        
        function selectCandidate(ch) {{
            var input = document.getElementById('searchInput');
            input.value += ch;
            clearPinyinState();
            currentCandidatePage = 0;  // 重置页码
            
            if (input.value.length >= 2) {{
                fetchInputTips(input.value);
            }}
        }}
        
        function clearPinyinState() {{
            pinyinBuffer = '';
            currentCandidatePage = 0;  // 重置页码
            document.getElementById('pinyinText').textContent = '';
            document.getElementById('candidatesContainer').innerHTML = '';
        }}
        
        function handleBackspace() {{
            if (pinyinBuffer.length > 0) {{
                pinyinBuffer = pinyinBuffer.slice(0, -1);
                updatePinyinDisplay();
                if (pinyinBuffer.length > 0) fetchCandidates();
                else clearPinyinState();
            }} else {{
                var input = document.getElementById('searchInput');
                input.value = input.value.slice(0, -1);
            }}
        }}
        
        function toggleShift() {{
            isShiftOn = !isShiftOn;
            document.querySelectorAll('.key').forEach(function(key) {{
                var char = key.textContent;
                if (char.length === 1 && char >= 'A' && char <= 'Z') {{
                    key.textContent = isShiftOn ? char.toUpperCase() : char.toLowerCase();
                }}
            }});
        }}
        
        function confirmInput() {{
            clearPinyinState();
            var input = document.getElementById('searchInput');
            if (input.value.length >= 2) fetchInputTips(input.value);
            hideKeyboard();
        }}
        
        function toggleKeyboard() {{
            var kb = document.getElementById('keyboard');
            kb.classList.toggle('active');
        }}
        
        function hideKeyboard() {{
            document.getElementById('keyboard').classList.remove('active');
            document.getElementById('suggestionsList').style.display = 'none';
        }}
        
        function showSuggestions(tips) {{
            var list = document.getElementById('suggestionsList');
            list.innerHTML = '';
            
            if (!tips || tips.length === 0) {{
                list.style.display = 'none';
                return;
            }}
            
            tips.slice(0, 6).forEach(function(tip) {{
                var item = document.createElement('div');
                item.className = 'suggestion-item';
                
                // 构建地址显示
                var addr = '';
                if (tip.district) addr += tip.district;
                if (tip.address && tip.address !== tip.name) {{
                    addr += addr ? ' - ' + tip.address : tip.address;
                }}
                
                item.innerHTML = `
                    <div style="display: flex; align-items: center; width: 100%;">
                        <span style="margin-right: 8px;">📍</span>
                        <div style="flex: 1; overflow: hidden;">
                            <div style="font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${{tip.name}}</div>
                            <div style="font-size: 11px; color: #888; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${{addr || '点击选择此位置'}}</div>
                        </div>
                    </div>
                `;
                item.onclick = function() {{ selectSuggestion(tip); }};
                list.appendChild(item);
            }});
            
            list.style.display = 'block';
        }}
        
        function selectSuggestion(tip) {{
            document.getElementById('searchInput').value = tip.name;
            document.getElementById('suggestionsList').style.display = 'none';
            
            if (tip.location) {{
                var parts = tip.location.split(',');
                destPos = [parseFloat(parts[0]), parseFloat(parts[1])];
                
                // 移除旧的目的地标记
                if (destMarker) map.remove(destMarker);
                
                // 创建新的目的地标记
                destMarker = new AMap.Marker({{
                    position: destPos,
                    map: map,
                    title: tip.name,
                    animation: 'AMAP_ANIMATION_DROP',
                    label: {{
                        content: tip.name,
                        offset: new AMap.Pixel(0, -35),
                        direction: 'top'
                    }},
                    icon: new AMap.Icon({{
                        size: new AMap.Size(32, 32),
                        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
                        imageSize: new AMap.Size(32, 32)
                    }})
                }});
                
                // 调整地图视角以包含当前位置和目的地
                if (currentPos) {{
                    map.setFitView([currentMarker, destMarker], {{
                        padding: [60, 60, 60, 60]
                    }});
                }} else {{
                    map.setCenter(destPos);
                    map.setZoom(16);
                }}
                
                // 更新位置信息显示
                var addr = tip.district || '';
                if (tip.address) addr += (addr ? ' ' : '') + tip.address;
                document.getElementById('locationInfo').innerHTML = 
                    '🎯 目的地: ' + tip.name + '<br>' +
                    (addr ? '📍 ' + addr + '<br>' : '') +
                    destPos[0].toFixed(5) + ',' + destPos[1].toFixed(5);
                
                console.log('选中目的地:', tip.name, destPos);
            }}
        }}
        
        function startNavigation() {{
            if (!currentPos) {{ alert('等待GPS...'); return; }}
            
            if (!destPos) {{
                var addr = document.getElementById('searchInput').value;
                if (!addr) {{ alert('请输入目的地'); return; }}
                // 使用后端 API 搜索地点
                if (amapAPI) {{
                    amapAPI.place_search(addr, '全国').then(function(result) {{
                        try {{
                            var data = JSON.parse(result);
                            if (data.status === '1' && data.pois && data.pois.length > 0) {{
                                var poi = data.pois[0];
                                var location = poi.location.split(',');
                                destPos = [parseFloat(location[0]), parseFloat(location[1])];
                                // 添加目的地标记
                                if (destMarker) map.remove(destMarker);
                                destMarker = new AMap.Marker({{
                                    position: destPos,
                                    map: map,
                                    title: poi.name,
                                    icon: new AMap.Icon({{
                                        size: new AMap.Size(32, 32),
                                        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
                                        imageSize: new AMap.Size(32, 32)
                                    }})
                                }});
                                doNavigate();
                            }} else {{
                                alert('未找到该地点');
                            }}
                        }} catch(e) {{
                            console.error('搜索失败:', e);
                            alert('搜索失败');
                        }}
                    }}).catch(function(err) {{
                        console.error('搜索请求失败:', err);
                        alert('搜索请求失败');
                    }});
                }} else {{
                    alert('API未就绪');
                }}
            }} else doNavigate();
        }}
        
        function doNavigate() {{
            if (!currentPos || !destPos) return;
            isNavigating = true;
            driving.search(new AMap.LngLat(currentPos[0], currentPos[1]), new AMap.LngLat(destPos[0], destPos[1]));
            document.getElementById('navPanel').style.display = 'block';
        }}
        
        function onRouteComplete(result) {{
            routeInfo = result.routes[0];
            if (routeInfo && routeInfo.steps) {{
                var step = routeInfo.steps[0];
                document.getElementById('navInstruction').textContent = step.instruction;
                document.getElementById('navDetail').textContent = '剩余' + formatDist(routeInfo.distance) + '|预计' + formatTime(routeInfo.time);
            }}
        }}
        
        function stopNavigation() {{
            isNavigating = false;
            routeInfo = null;
            document.getElementById('navPanel').style.display = 'none';
            driving.clear();
        }}
        
        function clearAll() {{
            stopNavigation();
            if (destMarker) {{ map.remove(destMarker); destMarker = null; }}
            destPos = null;
            document.getElementById('searchInput').value = '';
            clearPinyinState();
        }}
        
        function formatDist(m) {{
            return m < 1000 ? Math.round(m) + '米' : (m/1000).toFixed(1) + '公里';
        }}
        
        function formatTime(s) {{
            var m = Math.ceil(s/60);
            return m < 60 ? m + '分钟' : Math.floor(m/60) + '小时' + (m%60) + '分';
        }}
        
        function updatePosition(lng, lat, province) {{
            currentPos = [lng, lat];
            
            if (currentMarker) {{
                currentMarker.setPosition(currentPos);
            }} else {{
                currentMarker = new AMap.Marker({{
                    position: currentPos,
                    map: map,
                    icon: new AMap.Icon({{
                        size: new AMap.Size(20, 20),
                        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png',
                        imageSize: new AMap.Size(20, 20)
                    }})
                }});
                // 首次定位：设置中心并调整为骑行导航级别的缩放
                map.setCenter(currentPos);
                map.setZoom(17);  // 骑行导航推荐缩放级别：17级
            }}
            
            document.getElementById('locationInfo').innerHTML = '📍' + (province || '未知') + '<br>' + lng.toFixed(5) + ',' + lat.toFixed(5);
            
            trackPoints.push(currentPos);
            if (trackPoints.length > 400) trackPoints.shift();
            
            if (trackPoints.length > 1) {{
                if (trackLine) map.remove(trackLine);
                trackLine = new AMap.Polyline({{
                    path: trackPoints,
                    strokeColor: '#4DB8FF',
                    strokeWeight: 3,
                    strokeOpacity: 0.8,
                    map: map
                }});
            }}
        }}
        
        window.updatePosition = updatePosition;
    </script>
</body>
</html>
"""

    def update_location(self, lat, lon, province="未知"):
        """更新当前位置"""
        self.current_lat = lat
        self.current_lon = lon
        js_code = f"updatePosition({lon}, {lat}, '{province}');"
        self.web_view.page().runJavaScript(js_code)
    
    def set_zoom(self, zoom_level):
        """设置地图缩放级别
        
        Args:
            zoom_level: 缩放级别，骑行导航推荐 16-17
                       15 - 看到街区范围
                       16-17 - 骑行导航最佳（能看清道路细节）
                       18 - 看到建筑细节
        """
        js_code = f"map.setZoom({zoom_level});"
        self.web_view.page().runJavaScript(js_code)
        print(f"[MapWidget] 地图缩放级别设置为: {zoom_level}")

    def check_navigation_status(self):
        pass

    def start_navigation(self, dest_lat, dest_lon):
        js_code = f"destPos = [{dest_lon}, {dest_lat}]; startNavigation();"
        self.web_view.page().runJavaScript(js_code)

    def stop_navigation(self):
        self.web_view.page().runJavaScript("stopNavigation();")

    def clear_track(self):
        self.web_view.page().runJavaScript("clearAll();")
