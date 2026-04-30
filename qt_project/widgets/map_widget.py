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

try:
    from services.nav_engine import NavEngine
    _HAS_NAV_ENGINE = True
except ImportError:
    try:
        from qt_project.services.nav_engine import NavEngine
        _HAS_NAV_ENGINE = True
    except ImportError:
        _HAS_NAV_ENGINE = False
        print("[警告] 离线导航引擎加载失败")

# 导入智能拼音输入法
try:
    from ui.smart_pinyin_ime import get_ime
    _HAS_SMART_IME = True
except ImportError:
    try:
        from qt_project.ui.smart_pinyin_ime import get_ime
        _HAS_SMART_IME = True
    except ImportError:
        try:
            from .smart_pinyin_ime import get_ime
            _HAS_SMART_IME = True
        except ImportError:
            try:
                from smart_pinyin_ime import get_ime
                _HAS_SMART_IME = True
            except ImportError:
                _HAS_SMART_IME = False
                print("[警告] 智能拼音输入法加载失败，使用基础词典")


class NavigationHandler(QObject):
    """导航指令处理器 - 接收 JS 端的导航回调"""

    # 导航信号
    nav_started = pyqtSignal()  # 导航开始
    nav_stopped = pyqtSignal()  # 导航结束
    nav_instruction = pyqtSignal(str, str)  # 导航指令 (instruction, detail)
    nav_overview = pyqtSignal(str)  # 导航总览播报文本
    nav_position_updated = pyqtSignal(float, float)  # 位置更新 (lat, lon)
    nav_error = pyqtSignal(str)  # 导航错误

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_step = 0
        self._total_steps = 0
        self._last_instruction = ""

    @pyqtSlot()
    def on_nav_started(self):
        """导航开始回调"""
        print("[NavigationHandler] 导航开始")
        self.nav_started.emit()

    @pyqtSlot()
    def on_nav_stopped(self):
        """导航结束回调"""
        print("[NavigationHandler] 导航结束")
        self.nav_stopped.emit()

    @pyqtSlot(str, str, int, int)
    def on_nav_instruction(self, instruction: str, detail: str, current_step: int, total_steps: int):
        """导航指令回调

        Args:
            instruction: 导航指令文本（如"前方500米右转"）
            detail: 详细信息（如"剩余2.5公里|预计15分钟"）
            current_step: 当前步骤索引
            total_steps: 总步骤数
        """
        self._current_step = current_step
        self._total_steps = total_steps

        # 避免重复播报相同指令（偏航类消息除外，每次都需要通知）
        if instruction != self._last_instruction or "偏离路线" in instruction:
            self._last_instruction = instruction
            print(f"[NavigationHandler] 导航指令 [{current_step+1}/{total_steps}]: {instruction}")
            self.nav_instruction.emit(instruction, detail)

    @pyqtSlot(str)
    def on_nav_overview(self, text: str):
        """导航总览回调（在线地图导航开始时播报）"""
        print(f"[NavigationHandler] 导航总览: {text}")
        self.nav_overview.emit(text)

    @pyqtSlot(float, float)
    def on_position_updated(self, lat: float, lon: float):
        """位置更新回调"""
        self.nav_position_updated.emit(lat, lon)

    @pyqtSlot(str)
    def on_nav_error(self, error_msg: str):
        """导航错误回调"""
        print(f"[NavigationHandler] 导航错误: {error_msg}")
        self.nav_error.emit(error_msg)

    def reset(self):
        """重置导航状态"""
        self._current_step = 0
        self._total_steps = 0
        self._last_instruction = ""


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
    
    @pyqtSlot(str, str, str, result=str)
    def input_tips(self, keywords, city="全国", location=""):
        """输入提示：根据关键词获取地点候选
        
        Args:
            keywords: 输入的关键词
            city: 城市（默认全国）
            location: 当前位置坐标 "longitude,latitude"，用于优先返回附近结果
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
            
            # 如果有位置信息，添加location参数优先返回附近结果
            if location:
                params['location'] = location
            
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            
            print(f"[AMapAPI] 输入提示请求: {keywords}, 位置: {location or '未指定'}")
            
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
    
    @pyqtSlot(str, str, result=str)
    def route_planning(self, origin, destination):
        """路线规划（骑行）- 使用 v5 API
        
        Args:
            origin: 起点坐标 "longitude,latitude"
            destination: 终点坐标 "longitude,latitude"
        Returns:
            JSON 字符串，包含路线信息
        """
        try:
            # 使用 v5 版本骑行路线规划 API
            url = "https://restapi.amap.com/v5/direction/bicycling"
            params = {
                'key': self.amap_key,
                'origin': origin,
                'destination': destination,
                'show_fields': 'polyline,cost,navi',  # 获取路线坐标、耗时、导航指令
                'output': 'json'
            }
            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            
            print(f"[AMapAPI] 骑行路线规划(v5): {origin} -> {destination}")
            
            with urllib.request.urlopen(full_url, timeout=10) as response:
                data = response.read().decode('utf-8')
                result = json.loads(data)
                
                if result.get('status') == '1' and result.get('route', {}).get('paths'):
                    path = result['route']['paths'][0]
                    distance = path.get('distance', 'N/A')
                    # duration 在 cost 对象内
                    duration = path.get('cost', {}).get('duration', 'N/A')
                    print(f"[AMapAPI] 路线规划成功: {distance}米, {duration}秒")
                else:
                    print(f"[AMapAPI] 路线规划失败: {result.get('info', '未知错误')}")
                
                return data
        except Exception as e:
            print(f"[AMapAPI] 路线规划失败: {e}")
            return json.dumps({'status': '0', 'info': str(e)})
    
    @pyqtSlot()
    def report_route_planning_failed(self):
        """报告在线路线规划失败，触发自动降级"""
        parent = self.parent()
        if parent and hasattr(parent, '_mode') and parent._mode == 'online':
            print("[Map] 在线路线规划失败，建议自动降级到离线")
            if hasattr(parent, 'route_planning_failed'):
                parent.route_planning_failed.emit(True)

    @pyqtSlot(bool)
    def report_map_status(self, success):
        """报告地图加载状态

        Args:
            success: 地图是否加载成功
        """
        parent = self.parent()
        if parent and hasattr(parent, '_map_html_loaded'):
            parent._map_html_loaded = success
        # 如果是模式切换导致的加载，跳过播报
        if parent and hasattr(parent, '_skip_next_map_loaded') and parent._skip_next_map_loaded:
            parent._skip_next_map_loaded = False
            print(f"[Map] 地图加载{'成功' if success else '失败'} (模式切换，跳过播报)")
            # 在线模式下加载失败，仍然触发降级
            if not success and parent and hasattr(parent, '_mode') and parent._mode == 'online':
                print("[Map] 在线地图加载失败，建议自动降级到离线")
                if hasattr(parent, 'route_planning_failed'):
                    parent.route_planning_failed.emit(True)
            return
        if success:
            print(f"[Map] ✅ 地图加载成功!")
            if parent and hasattr(parent, 'map_loaded'):
                parent.map_loaded.emit(True)
        else:
            print(f"[Map] ❌ 地图加载失败!")
            if parent and hasattr(parent, 'map_loaded'):
                parent.map_loaded.emit(False)
            # 在线模式下加载失败，触发自动降级信号
            if parent and hasattr(parent, '_mode') and parent._mode == 'online':
                print("[Map] 在线地图加载失败，建议自动降级到离线")
                if hasattr(parent, 'route_planning_failed'):
                    parent.route_planning_failed.emit(True)

    @pyqtSlot(float, float)
    def set_offline_destination(self, lat: float, lon: float):
        """离线模式：设置目的地标记（不立即导航）

        Args:
            lat: 目的地纬度
            lon: 目的地经度
        """
        parent = self.parent()
        if parent and hasattr(parent, '_set_offline_dest_js'):
            parent._set_offline_dest_js(lat, lon)
        print(f"[AMapAPI] 离线目的地已设置: {lat}, {lon}")

    @pyqtSlot(float, float)
    def plan_offline_route(self, lat: float, lon: float):
        """离线模式：规划路线（不启动导航）

        Args:
            lat: 目的地纬度
            lon: 目的地经度
        """
        parent = self.parent()
        if parent and hasattr(parent, 'plan_offline_route'):
            parent.plan_offline_route(lat, lon)
        print(f"[AMapAPI] 离线路线规划: {lat}, {lon}")

    @pyqtSlot(float, float)
    def start_offline_navigation(self, lat: float, lon: float):
        """离线模式：开始导航到指定坐标

        Args:
            lat: 目的地纬度
            lon: 目的地经度
        """
        parent = self.parent()
        if parent and hasattr(parent, 'start_navigation'):
            parent.start_navigation(lat, lon)
        print(f"[AMapAPI] 离线导航开始: {lat}, {lon}")

    @pyqtSlot(float, float)
    def notify_nav_started(self, lat: float, lon: float):
        """在线/离线模式：通知 Python 端导航已开始（JS 端已自行启动导航 UI）

        Args:
            lat: 目的地纬度
            lon: 目的地经度
        """
        parent = self.parent()
        if parent:
            if hasattr(parent, '_dest_lat'):
                parent._dest_lat = lat
            if hasattr(parent, '_dest_lon'):
                parent._dest_lon = lon
            if hasattr(parent, 'is_navigating'):
                parent.is_navigating = True
            if hasattr(parent, 'navigation_handler'):
                parent.navigation_handler.nav_started.emit()
                print(f"[AMapAPI] 导航开始信号已发射: {lat}, {lon}")
            else:
                print(f"[AMapAPI] 警告: parent 没有 navigation_handler")
        else:
            print(f"[AMapAPI] 警告: notify_nav_started 没有 parent")


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
    """地图组件 - 支持在线(高德)和离线(Leaflet)双模式"""

    nav_status_changed = pyqtSignal(str)
    nav_instruction = pyqtSignal(str)
    map_loaded = pyqtSignal(bool)  # 地图加载完成信号
    mode_changed = pyqtSignal(str)  # 模式切换信号 ('online'/'offline')
    route_planning_failed = pyqtSignal(bool)  # 路线规划失败，bool 表示是否建议自动降级

    def __init__(self,
                 amap_key="8b657a470f4b69e82bf81f72b3a2b3c0",  # Web服务 API Key
                 jsapi_key="c507e554a5bb6e08b7097fa61164f0e4",   # JS API Key
                 security_key="8ee0cb41f7666cfd320749d269ab6121",  # 安全密钥
                 tile_server_url="http://localhost:8766/{z}/{x}/{y}.png",
                 mode="online",
                 parent=None):
        super().__init__(parent)
        self.amap_key = amap_key      # WebService API Key（用于地点搜索等）
        self.jsapi_key = jsapi_key    # JS API Key（用于地图加载）
        self.security_key = security_key  # JS API 安全密钥
        self.tile_server_url = tile_server_url
        self._mode = mode  # 'online' 或 'offline'
        self.current_lat = None
        self.current_lon = None
        self._dest_lat = None
        self._dest_lon = None
        self.is_navigating = False  # 是否正在导航
        self._pending_auto_navigate = False  # App设置目的地后自动开始导航
        self._map_html_loaded = False  # HTML 页面是否已成功加载
        self._skip_next_map_loaded = False  # 切换模式时跳过地图加载播报

        self.pinyin_handler = PinyinHandler(self)
        self.navigation_handler = NavigationHandler(self)

        # 离线导航引擎
        self.nav_engine = NavEngine(parent=self) if _HAS_NAV_ENGINE else None
        self._offline_nav_active = False
        self._last_nav_instruction = ""
        self._last_rel_dir = ""
        self._is_rerouting = False  # 防止偏航重复重新规划
        if self.nav_engine:
            self.nav_engine.route_planned.connect(self._on_route_planned)
            self.nav_engine.route_failed.connect(self._on_route_failed)
            self.nav_engine.nav_updated.connect(self._on_nav_updated)

        self.init_ui()

    @property
    def mode(self):
        return self._mode

    def is_map_loaded(self) -> bool:
        """HTML 页面是否已成功加载"""
        return self._map_html_loaded

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
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        # 配置页面禁用缓存（开发调试用）
        self.web_view.page().profile().setHttpCacheType(QWebEngineProfile.NoCache)

        self.channel = QWebChannel()
        self.channel.registerObject('pinyinHandler', self.pinyin_handler)

        # 注册高德地图 API 处理后端
        self.amap_api_handler = AMapAPIHandler(self.amap_key, self)
        self.channel.registerObject('amapAPI', self.amap_api_handler)

        # 注册导航处理器
        self.channel.registerObject('navHandler', self.navigation_handler)

        self.web_view.page().setWebChannel(self.channel)

        main_layout.addWidget(self.web_view)
        self.load_map()

        self.nav_timer = QTimer(self)
        self.nav_timer.timeout.connect(self.check_navigation_status)
        self.nav_timer.start(1000)

    def set_mode(self, mode: str):
        """切换地图模式

        Args:
            mode: 'online' 或 'offline'
        """
        if mode not in ('online', 'offline'):
            print(f"[MapWidget] 无效模式: {mode}")
            return

        if self._mode == mode:
            return

        self._mode = mode
        print(f"[MapWidget] 切换地图模式: {mode}")
        # 切换模式时清理离线导航状态
        self._offline_nav_active = False
        self._last_nav_instruction = ""
        self._last_rel_dir = ""
        if self.nav_engine:
            self.nav_engine.clear()
        self._skip_next_map_loaded = True  # 标记：模式切换导致的加载，跳过播报
        self.load_map()
        self.mode_changed.emit(mode)

    def load_map(self):
        """加载地图（根据当前模式选择在线或离线）"""
        from PyQt5.QtCore import QUrl
        if self._mode == 'offline':
            html_content = self.generate_offline_html()
            title = "离线地图"
        else:
            html_content = self.generate_amap_html()
            title = "高德骑行地图"

        # 使用本地目录作为 base URL，使 leaflet/ 等相对路径可用
        # map_widget.py 位于 widgets/ 子目录，其上级目录即为 qt_project/
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_url = QUrl.fromLocalFile(base_path + os.sep)

        # 调试：保存离线 HTML 到文件便于排查
        if self._mode == 'offline':
            debug_path = os.path.join(base_path, 'offline_map_debug.html')
            try:
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                print(f"[MapWidget] 离线地图调试文件已保存: {debug_path}")
            except Exception as e:
                print(f"[MapWidget] 保存调试文件失败: {e}")

        print(f"[MapWidget] 正在加载 {title}, base_url={base_url.toString()}, html_len={len(html_content)}")
        self.web_view.setHtml(html_content, base_url)
        print(f"[MapWidget] 已加载 {title}")

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
            z-index: 2000;
        }}

        .input-row {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}

        .search-input {{
            width: 420px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            color: #000;
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
        /* 四个功能按钮 */
        .btn-route {{ background: linear-gradient(135deg, #3498db, #2980b9); }}
        .btn-route:hover::after {{ content: '规划路线'; position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.8); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; z-index: 10000; }}
        
        .btn-nav {{ background: linear-gradient(135deg, #2ecc71, #27ae60); }}
        .btn-nav:hover::after {{ content: '导航模式'; position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.8); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; z-index: 10000; }}
        
        .btn-locate {{ background: linear-gradient(135deg, #9b59b6, #8e44ad); font-size: 18px; padding: 12px; }}
        .btn-locate:hover::after {{ content: '当前位置'; position: absolute; bottom: -25px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.8); color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; z-index: 10000; }}
        
        .btn-stop {{ background: linear-gradient(135deg, #e74c3c, #c0392b); padding: 12px; display: none; }}
        .btn-clear {{ background: linear-gradient(135deg, #666, #555); padding: 12px; }}

        /* 展开/收起按钮 */
        .btn-toggle {{
            background: linear-gradient(135deg, #f39c12, #e67e22);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            height: 48px;
            transition: all 0.1s;
            min-width: 48px;
        }}
        .btn-toggle:active {{ transform: scale(0.95); }}

        /* 按钮面板 —— 默认收起在 》》 按钮后方 */
        .btn-slide-group {{
            display: flex;
            gap: 8px;
            max-width: 0;
            opacity: 0;
            overflow: hidden;
            transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            align-items: center;
            pointer-events: none;
            white-space: nowrap;
        }}
        .btn-slide-group.show {{
            max-width: 600px;
            opacity: 1;
            pointer-events: auto;
        }}

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
        
        /* ========== 右侧半透明键盘 ========== */
        .keyboard-wrapper {{
            position: fixed;
            bottom: 10px;
            right: 10px;
            width: 480px;
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
            padding: 12px 14px;
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
            border-radius: 8px;
            padding: 7px 14px;
            font-size: 18px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.1s;
            min-width: 42px;
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
            padding: 12px 10px 14px 10px;
        }}

        .kb-row {{
            display: flex;
            gap: 6px;
            margin-bottom: 7px;
            justify-content: center;
        }}

        /* 按键样式 - 半透明 */
        .key {{
            background: rgba(120, 120, 120, 0.6);
            color: white;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 0;
            font-size: 18px;
            font-weight: 500;
            cursor: pointer;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.08s;
            flex: 1;
            max-width: 48px;
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
            max-width: 62px;
            background: rgba(100, 100, 100, 0.65);
            font-size: 16px;
        }}
        .key-back {{
            flex: 1.3;
            max-width: 62px;
            background: rgba(110, 110, 110, 0.65);
            font-size: 16px;
        }}
        .key-space {{
            flex: 4;
            max-width: 220px;
            font-size: 16px;
            background: rgba(120, 120, 120, 0.6);
        }}
        .key-enter {{
            flex: 1.4;
            max-width: 78px;
            background: rgba(46, 204, 113, 0.7);
            font-size: 16px;
            color: white;
            font-weight: 600;
        }}
        .key-enter:hover {{ 
            background: rgba(46, 204, 113, 0.85);
        }}
        .key-enter:active {{ 
            background: rgba(39, 174, 96, 0.9);
        }}
        
        .key-lang {{ 
            flex: 1;
            max-width: 50px;
            font-size: 13px;
            background: rgba(52, 152, 219, 0.7);
        }}
        
        .key-lang:hover {{ 
            background: rgba(52, 152, 219, 0.85);
        }}
        
        .key-lang:active {{ 
            background: rgba(41, 128, 185, 0.9);
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
        
        /* Toast 提示框 */
        .toast {{
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.85);
            color: #fff;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        
        .toast.show {{ opacity: 1; }}
        .toast.error {{ background: rgba(231, 76, 60, 0.9); }}
        .toast.success {{ background: rgba(46, 204, 113, 0.9); }}
        .toast.warning {{ background: rgba(241, 196, 15, 0.9); }}
        .suggestion-addr {{ color: #888; font-size: 11px; margin-left: auto; }}
    </style>
</head>
<body>
    <div id="container"></div>
    
    <!-- 搜索面板 -->
    <div class="search-panel">
        <div style="position: relative;">
            <div class="input-row">
                <input type="text" id="searchInput" class="search-input" placeholder="点击输入目的地..." readonly onclick="showKeyboard()">
                <button class="btn btn-toggle" onclick="toggleBtnPanel()" title="展开/收起">》》</button>
                <div id="btnPanel" class="btn-slide-group">
                    <button class="btn btn-route" onclick="planRoute()" title="规划路线">🗺️ 路线</button>
                    <button class="btn btn-nav" onclick="enterNavMode()" title="导航模式">🧭 导航</button>
                    <button class="btn-zoom" onclick="zoomIn()" title="放大">+</button>
                    <button class="btn-zoom" onclick="zoomOut()" title="缩小">−</button>
                    <button class="btn btn-locate" onclick="showCurrentLocation()" title="当前位置">📍</button>
                    <button class="btn btn-clear" onclick="clearAll()" title="清除">🗑️</button>
                </div>
            </div>
            <div id="suggestionsList" class="suggestions-list"></div>
        </div>
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
            <!-- 第1行：QWERTY -->
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
                <button class="key key-lang" onclick="toggleLang()">中/英</button>
                <button class="key key-space" onclick="inputChar(' ')">空格</button>
                <button class="key key-enter" onclick="confirmInput()">确定</button>
            </div>
        </div>
    </div>

    <script>
        window._AMapSecurityConfig = {{
            securityJsCode: '{self.security_key}'
        }};
    </script>
    <script src="https://webapi.amap.com/maps?v=2.0&key={self.jsapi_key}&plugin=AMap.Driving,AMap.Scale"></script>
    
    <script>
        // 全局变量
        var map, currentPos, destPos, currentMarker, destMarker, trackLine, yawMarker;
        var isNavigating = false, routeInfo = null, trackPoints = [];
        var pinyinBuffer = "";
        var isShiftOn = false;
        var amapAPI = null;
        var pinyinHandler = null;
        var isMapInitialized = false;
        var pendingYaw = null;
        
        // DOM 加载完成后初始化
        document.addEventListener("DOMContentLoaded", function() {{
            console.log('DOM 加载完成');
            
            // 等待 AMap 加载（轮询检查）
            var checkCount = 0;
            var checkAMap = setInterval(function() {{
                checkCount++;
                
                if (typeof AMap !== 'undefined') {{
                    clearInterval(checkAMap);
                    console.log('✅ AMap 加载成功（检查' + checkCount + '次）');
                    initAll();
                }} else if (checkCount > 50) {{  // 5秒后放弃
                    clearInterval(checkAMap);
                    console.error('ERROR: AMap 加载超时！请检查 JS API Key 和安全密钥配置');
                    document.getElementById('container').innerHTML = 
                        '<div style="color: red; padding: 20px; text-align: center;">' +
                        '<h3>地图加载失败</h3>' +
                        '<p>请检查：</p>' +
                        '<ul style="text-align: left; display: inline-block;">' +
                        '<li>JS API Key 是否正确</li>' +
                        '<li>安全密钥是否正确</li>' +
                        '<li>Key 是否启用了 JS API 服务</li>' +
                        '</ul></div>';
                }}
            }}, 100);  // 每100ms检查一次
        }});
        
        function initAll() {{
            // 先初始化地图
            initMap();
            
            // 连接 QWebChannel
            if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    amapAPI = channel.objects.amapAPI;
                    pinyinHandler = channel.objects.pinyinHandler;
                    navHandler = channel.objects.navHandler;
                    console.log('QWebChannel 连接成功, amapAPI:', amapAPI ? '可用' : '不可用');
                    
                    // 绑定需要 API 的地图事件
                    bindMapEvents();
                }});
            }} else {{
                console.error('QWebChannel 未就绪');
            }}

            // 点击键盘外部区域隐藏键盘（第一次点击生效）
            document.addEventListener('click', function(e) {{
                var kb = document.getElementById('keyboard');
                var input = document.getElementById('searchInput');
                var suggestions = document.getElementById('suggestionsList');
                if (!kb || !kb.classList.contains('active')) return;
                if (kb.contains(e.target) || input.contains(e.target)) return;
                if (suggestions && suggestions.contains(e.target)) return;
                hideKeyboard();
            }});
        }}
        
        // 初始化地图（不依赖 API）
        function initMap() {{
            if (isMapInitialized) return;
            
            try {{
                console.log('开始初始化地图...');
                
                map = new AMap.Map('container', {{
                    zoom: 16,
                    center: [112.944, 27.828],
                    viewMode: '2D',
                    mapStyle: 'amap://styles/dark'
                }});
                
                console.log('地图对象创建成功');
                
                map.addControl(new AMap.Scale({{position: 'LB'}}));
                
                console.log('比例尺控件添加成功');
                
                // 初始化全局变量
                currentPos = null;
                window.routeLine = null;
                
                isMapInitialized = true;
                console.log('地图初始化完成');
                
                // 通知 Python 地图已加载成功
                if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                    setTimeout(function() {{
                        if (amapAPI) {{
                            amapAPI.report_map_status(true);
                        }}
                    }}, 500);
                }}
            }} catch (e) {{
                console.error('地图初始化失败:', e);
                document.getElementById('container').innerHTML = 
                    '<div style="color: red; padding: 20px;">地图初始化失败: ' + e.message + '</div>';
                
                if (amapAPI) {{
                    amapAPI.report_map_status(false);
                }}
            }}
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

                // QWebChannel 返回 Promise
                amapAPI.geocode_regeo(location).then(function(result) {{
                    try {{
                        var data = JSON.parse(result);
                        console.log('逆地理编码结果:', data);

                        if (data.status === '1' && data.regeocode) {{
                            var address = data.regeocode.formatted_address;
                            var comp = data.regeocode.addressComponent;
                            // 确保获取字符串值（防止某些字段是对象）
                            var district = (comp.district && typeof comp.district === 'string') ? comp.district : '';
                            var street = (comp.street && typeof comp.street === 'string') ? comp.street : '';
                            var number = (comp.streetNumber && typeof comp.streetNumber === 'string') ? comp.streetNumber : '';
                            var shortAddress = district + street + number;
                            if (!shortAddress) shortAddress = address;

                            addTempMarker(e.lnglat, shortAddress);
                            document.getElementById('searchInput').value = shortAddress;
                        }}
                    }} catch(e) {{
                        console.error('解析失败:', e);
                    }}
                }}).catch(function(err) {{
                    console.error('请求失败:', err);
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
            // 如果有当前位置，传入以优先显示附近结果
            var locationStr = currentPos ? currentPos[0] + ',' + currentPos[1] : '';
            amapAPI.input_tips(keywords, '全国', locationStr).then(function(result) {{
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
        // 导航步骤追踪
        var currentNavStep = 0;
        var navSteps = [];
        var navMonitorTimer = null;
        window._isRerouting = false;
        window._lastRerouteTime = 0;
        
        // 开始导航监控（模拟实时导航）
        function startNavMonitoring() {{
            if (navMonitorTimer) {{
                clearInterval(navMonitorTimer);
            }}

            currentNavStep = 0;

            // 播报总览信息（全程距离 + 预计时间 + 方向）
            if (routeInfo && navSteps.length > 0) {{
                var totalDist = routeInfo.distance;
                var totalTime = routeInfo.time;
                var firstStep = navSteps[0];
                var firstInstr = firstStep.instruction ? firstStep.instruction.replace(/<[^>]+>/g, '') : '';

                var overviewParts = ['开始骑行'];
                if (totalDist > 0) overviewParts.push('全程' + formatDist(totalDist));
                if (totalTime > 0) overviewParts.push('预计' + formatTime(totalTime));
                // 相对方向（Python 端传入）
                if (window._navRelDir) overviewParts.push('骑行路线在你的' + window._navRelDir);
                if (firstInstr) overviewParts.push(firstInstr);

                var overviewText = overviewParts.join('，');
                console.log('[Navigation] 总览播报:', overviewText);
                if (typeof navHandler !== 'undefined' && navHandler) {{
                    navHandler.on_nav_overview(overviewText);
                }}
            }}

            console.log('[Navigation] 开始导航监控，共', navSteps.length, '步');
        }}
        
        // 停止导航监控
        function stopNavMonitoring() {{
            if (navMonitorTimer) {{
                clearInterval(navMonitorTimer);
                navMonitorTimer = null;
            }}
            
            // 通知 Python 端导航结束
            if (typeof navHandler !== 'undefined' && navHandler) {{
                navHandler.on_nav_stopped();
            }}
            
            currentNavStep = 0;
            navSteps = [];
            console.log('[Navigation] 停止导航监控');
        }}
        
        // 播报导航步骤
        function announceNavStep(stepIndex) {{
            if (stepIndex >= navSteps.length) return;

            var step = navSteps[stepIndex];
            var instruction = step.instruction;

            // 清理 HTML 标签
            instruction = instruction.replace(/<[^>]+>/g, '');

            var detail = '剩余' + formatDist(routeInfo.distance) + '|预计' + formatTime(routeInfo.time);

            // 构造带距离的友好播报文本
            var stepDist = step.distance || 0;
            var speakText = instruction;
            if (stepDist > 0 && stepIndex < navSteps.length - 1) {{
                speakText = '前方' + formatDist(stepDist) + '，' + instruction;
            }}

            console.log('[Navigation] 播报步骤', stepIndex + 1, ':', speakText);

            // 通知 Python 端（发送带距离的友好文本）
            if (typeof navHandler !== 'undefined' && navHandler) {{
                navHandler.on_nav_instruction(speakText, detail, stepIndex, navSteps.length);
            }}
        }}
        
        // 检查是否需要播报下一条指令（基于距离）
        function checkNavStep() {{
            if (!isNavigating || !currentPos || navSteps.length === 0) return;
            
            if (currentNavStep >= navSteps.length - 1) return;  // 最后一步
            
            var nextStep = navSteps[currentNavStep + 1];
            var nextPoint = nextStep.start_location;  // 下一段的起点
            
            // 计算到下一个转向点的距离
            var distance = AMap.GeometryUtil.distance(
                new AMap.LngLat(currentPos[0], currentPos[1]),
                new AMap.LngLat(nextPoint.lng, nextPoint.lat)
            );
            
            // 距离小于200米时播报下一条
            if (distance < 200) {{
                currentNavStep++;
                announceNavStep(currentNavStep);
            }}
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
        
        // 拼音输入处理（支持中英切换）
        function inputChar(char) {{
            var input = document.getElementById('searchInput');
            
            if (isShiftOn && char >= 'a' && char <= 'z') {{
                char = char.toUpperCase();
            }}
            
            // 英文模式直接输入，中文模式走拼音
            if (char >= 'a' && char <= 'z' && isChineseMode) {{
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
                btn.onclick = function(e) {{ e.stopPropagation(); selectCandidate(ch); }};
                candidatesDiv.appendChild(btn);
            }});
            
            // 右侧容器：翻页按钮（固定在最右边）
            var buttonsDiv = document.createElement('div');
            buttonsDiv.style.display = 'flex';
            buttonsDiv.style.gap = '4px';
            buttonsDiv.style.alignItems = 'center';
            buttonsDiv.style.marginLeft = '8px';
            
            // 始终显示 << 按钮，第一页时禁用
            var prevBtn = document.createElement('button');
            prevBtn.className = 'candidate-item more-btn';
            prevBtn.textContent = '<<';
            if (currentPage > 0) {{
                prevBtn.onclick = function(e) {{ e.stopPropagation();
                    fetchCandidates(currentCandidatePage - 1);
                }};
            }} else {{
                prevBtn.style.opacity = '0.3';
                prevBtn.style.cursor = 'not-allowed';
            }}
            buttonsDiv.appendChild(prevBtn);
            
            // 始终显示 >> 按钮，没有更多时禁用
            var moreBtn = document.createElement('button');
            moreBtn.className = 'candidate-item more-btn';
            moreBtn.textContent = '>>';
            if (hasMore) {{
                moreBtn.onclick = function(e) {{ e.stopPropagation();
                    fetchCandidates(currentCandidatePage + 1);
                }};
            }} else {{
                moreBtn.style.opacity = '0.3';
                moreBtn.style.cursor = 'not-allowed';
            }}
            buttonsDiv.appendChild(moreBtn);
            
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
            // 确保键盘保持显示，方便继续输入
            showKeyboard();
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
        
        var isChineseMode = true;  // 默认中文模式
        
        function toggleLang() {{
            isChineseMode = !isChineseMode;
            var btn = document.querySelector('.key-lang');
            btn.textContent = isChineseMode ? '中/英' : '英/中';
            btn.style.background = isChineseMode ? 'rgba(52, 152, 219, 0.7)' : 'rgba(155, 89, 182, 0.7)';
            console.log('切换输入模式:', isChineseMode ? '中文' : '英文');
        }}
        
        function confirmInput() {{
            clearPinyinState();
            var input = document.getElementById('searchInput');
            if (input.value.length >= 2) fetchInputTips(input.value);
            hideKeyboard();
        }}
        
        function showKeyboard() {{
            var kb = document.getElementById('keyboard');
            kb.classList.add('active');
        }}

        function hideKeyboard() {{
            document.getElementById('keyboard').classList.remove('active');
            document.getElementById('suggestionsList').style.display = 'none';
        }}

        function toggleBtnPanel() {{
            var panel = document.getElementById('btnPanel');
            panel.classList.toggle('show');
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
                
                var addr = tip.district || '';
                if (tip.address) addr += (addr ? ' ' : '') + tip.address;
                
                console.log('选中目的地:', tip.name, destPos);
            }}
        }}
        
        function startNavigation() {{
            if (!currentPos) {{ showToast('⏳ 等待GPS定位...', 'warning'); return; }}
            
            if (!destPos) {{
                var addr = document.getElementById('searchInput').value;
                if (!addr) {{ showToast('📍 请输入目的地', 'warning'); return; }}
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
                                showToast('❌ 未找到该地点', 'error');
                            }}
                        }} catch(e) {{
                            console.error('搜索失败:', e);
                            showToast('❌ 搜索失败', 'error');
                        }}
                    }}).catch(function(err) {{
                        console.error('搜索请求失败:', err);
                        showToast('❌ 搜索请求失败', 'error');
                    }});
                }} else {{
                    showToast('⚠️ API未就绪，请稍后再试', 'warning');
                }}
            }} else doNavigate();
        }}
        
        // 将 WebService API (v5) 路线结果转换为 AMap 格式
        function convertRouteData(wsData) {{
            console.log('convertRouteData 输入:', JSON.stringify(wsData).substring(0, 800));
            
            var path = wsData.route.paths[0];
            var steps = [];
            
            // v5 API: duration 可能在 path.duration 或 path.cost.duration
            var totalDuration = 0;
            if (path.duration) {{
                totalDuration = parseInt(path.duration);
            }} else if (path.cost && path.cost.duration) {{
                totalDuration = parseInt(path.cost.duration);
            }}
            
            // 转换 steps
            if (path.steps && path.steps.length > 0) {{
                for (var i = 0; i < path.steps.length; i++) {{
                    var step = path.steps[i];
                    
                    // 解析 step 的 polyline 获取起点终点
                    var startLoc = {{lng: 0, lat: 0}};
                    var endLoc = {{lng: 0, lat: 0}};
                    
                    if (step.polyline) {{
                        var points = step.polyline.split(';');
                        if (points.length > 0) {{
                            var first = points[0].split(',');
                            var last = points[points.length - 1].split(',');
                            if (first.length === 2) {{
                                startLoc = {{lng: parseFloat(first[0]), lat: parseFloat(first[1])}};
                            }}
                            if (last.length === 2) {{
                                endLoc = {{lng: parseFloat(last[0]), lat: parseFloat(last[1])}};
                            }}
                        }}
                    }}
                    
                    steps.push({{
                        instruction: step.instruction || '继续骑行',
                        distance: parseInt(step.step_distance) || 0,
                        duration: 0,
                        start_location: startLoc,
                        end_location: endLoc,
                        polyline: step.polyline || ''
                    }});
                }}
            }}
            
            // 绘制路线到地图（使用所有 steps 的 polyline）
            var allPoints = [];
            for (var j = 0; j < steps.length; j++) {{
                if (steps[j].polyline) {{
                    var pts = steps[j].polyline.split(';');
                    for (var k = 0; k < pts.length; k++) {{
                        var coord = pts[k].split(',');
                        if (coord.length === 2) {{
                            allPoints.push([parseFloat(coord[0]), parseFloat(coord[1])]);
                        }}
                    }}
                }}
            }}
            
            // 保存路线点用于导航时的路径匹配
            window.routePoints = allPoints;
            console.log('路线已保存，共', allPoints.length, '个点');
            
            if (allPoints.length > 0) {{
                drawRouteLine(allPoints);
            }}
            
            return {{
                routes: [{{
                    distance: parseInt(path.distance) || 0,
                    time: totalDuration,
                    steps: steps
                }}]
            }};
        }}
        
        // 绘制路线线条
        function drawRouteLine(points) {{
            console.log('[DEBUG] drawRouteLine called, points:', points ? points.length : 0);
            
            if (!points || points.length === 0) {{
                console.log('[DEBUG] No points to draw');
                return;
            }}
            
            // 清除旧路线和红色导航直线
            if (window.routeLine) {{
                console.log('[DEBUG] Removing old route line');
                map.remove(window.routeLine);
            }}
            if (window.navStraightLine) {{
                console.log('[DEBUG] Removing old nav straight line');
                map.remove(window.navStraightLine);
                window.navStraightLine = null;
            }}
            
            // 创建带方向箭头的路线
            console.log('[DEBUG] Creating Polyline with showDir=true');
            try {{
                window.routeLine = new AMap.Polyline({{
                    path: points,
                    strokeColor: '#4CAF50',
                    strokeWeight: 10,
                    strokeOpacity: 0.9,
                    lineJoin: 'round',
                    showDir: true,  // 启用内置方向箭头
                    zIndex: 100
                }});
                
                window.routeLine.setMap(map);
                console.log('[DEBUG] Polyline added to map');
                
                // 手动添加方向箭头标记（备选方案）
                addRouteArrowsManual(points);
                
            }} catch (e) {{
                console.error('[DEBUG] Error creating polyline:', e);
            }}
            
            // 调整视野
            var fitObjects = [window.routeLine];
            if (currentMarker) fitObjects.push(currentMarker);
            if (destMarker) fitObjects.push(destMarker);
            if (window.startMarker) fitObjects.push(window.startMarker);
            if (window.endMarker) fitObjects.push(window.endMarker);
            
            // 更新起点和终点标记位置，确保精确对准路线起点和终点
            if (points.length > 0) {{
                var routeStart = points[0];
                var routeEnd = points[points.length - 1];
                
                // 更新起点标记到路线实际起点
                if (window.startMarker) {{
                    window.startMarker.setPosition(new AMap.LngLat(routeStart[0], routeStart[1]));
                }}
                // 更新终点标记到路线实际终点
                if (window.endMarker) {{
                    window.endMarker.setPosition(new AMap.LngLat(routeEnd[0], routeEnd[1]));
                }}
                
                console.log('[DEBUG] 标记位置已更新到路线起点/终点');
            }}
            
            // 重新画红色导航直线（连接当前位置和终点）
            if (isNavigating && currentPos && destPos) {{
                window.navStraightLine = new AMap.Polyline({{
                    path: [currentPos, destPos],
                    strokeColor: '#f44336',
                    strokeWeight: 4,
                    strokeOpacity: 0.6,
                    lineJoin: 'round',
                    zIndex: 99
                }});
                window.navStraightLine.setMap(map);
                console.log('[DEBUG] 红色导航直线已重新绘制');
            }}
            
            // 只在非导航状态下调整视野（导航中保持当前位置在屏幕中央）
            if (!isNavigating) {{
                map.setFitView(fitObjects, {{
                    padding: [80, 80, 80, 420]  // 为右侧键盘留空间
                }});
            }}
            
            console.log('✅ 路线绘制完成，共' + points.length + '个点');
        }}
        
        // 手动添加路线方向箭头标记
        function addRouteArrowsManual(points) {{
            // 清除旧箭头
            if (window.routeArrowMarkers) {{
                window.routeArrowMarkers.forEach(function(m) {{ map.remove(m); }});
            }}
            window.routeArrowMarkers = [];
            
            if (!points || points.length < 2) return;

            // 每隔一定点数添加一个箭头，确保分布均匀
            var step = Math.max(2, Math.floor(points.length / 10));

            for (var i = step; i < points.length; i += step) {{
                var p1 = points[i - 1];
                var p2 = points[i];

                var dx = p2[0] - p1[0];
                var dy = p2[1] - p1[1];

                // 跳过重复点，避免角度无效
                if (dx === 0 && dy === 0) continue;

                // 计算 bearing（从北方向顺时针，0~360）
                var bearing = Math.atan2(dx, dy) * 180 / Math.PI;
                if (bearing < 0) bearing += 360;

                // >> 默认指向东，需要逆时针转 90° 才能指向北
                // CSS transform rotate 正角度为顺时针
                var rotate = bearing - 90;

                // 使用内联 CSS transform 直接控制旋转，不依赖 Marker.angle
                var arrowContent = '<div style="font-size:14px;font-weight:bold;color:white;text-shadow:0 1px 2px rgba(0,0,0,0.5);font-family:Arial,sans-serif;transform:rotate(' + rotate + 'deg);display:inline-block;">&gt;&gt;</div>';

                // 创建箭头标记（angle 设为 0，旋转完全由 CSS 控制）
                var marker = new AMap.Marker({{
                    position: new AMap.LngLat(p2[0], p2[1]),
                    content: arrowContent,
                    offset: new AMap.Pixel(-8, -8),
                    angle: 0,
                    zIndex: 60
                }});

                marker.setMap(map);
                window.routeArrowMarkers.push(marker);
            }}
            
            console.log('[DEBUG] 手动添加箭头:', window.routeArrowMarkers.length, '个');
        }}
        
        function doNavigate() {{
            console.log('开始导航:', 'currentPos=', currentPos, 'destPos=', destPos);

            if (!currentPos) {{
                showToast('⚠️ 等待GPS定位...', 'warning', 3000);
                return Promise.reject('无GPS');
            }}
            if (!destPos) {{
                showToast('⚠️ 请先选择目的地', 'warning', 3000);
                return Promise.reject('无目的地');
            }}
            if (!amapAPI) {{
                showToast('⚠️ API未就绪', 'error');
                return Promise.reject('API未就绪');
            }}

            isNavigating = true;
            showToast('🗺️ 正在规划路线...', 'info', 2000);

            // 使用 WebService API 进行路线规划
            var origin = currentPos[0] + ',' + currentPos[1];
            var destination = destPos[0] + ',' + destPos[1];

            console.log('路线规划(WS):', origin, '->', destination);

            return amapAPI.route_planning(origin, destination).then(function(result) {{
                try {{
                    var data = JSON.parse(result);
                    console.log('路线规划结果:', data);

                    if (data.status === '1' && data.route && data.route.paths && data.route.paths.length > 0) {{
                        // 转换 WebService 结果为 AMap 格式
                        var routeData = convertRouteData(data);
                        onRouteComplete(routeData);
                        return Promise.resolve();
                    }} else {{
                        var info = data.info || '无法规划路线';
                        console.error('路线规划失败:', info);
                        showToast('路线规划失败: ' + info, 'error');
                        isNavigating = false;
                        return Promise.reject(info);
                    }}
                }} catch(e) {{
                    console.error('路线结果解析失败:', e);
                    showToast('路线解析失败', 'error');
                    isNavigating = false;
                    return Promise.reject(e);
                }}
            }}).catch(function(err) {{
                console.error('路线规划请求失败:', err);
                showToast('路线规划请求失败', 'error');
                isNavigating = false;
                // 通知 Python 端在线路线规划失败，建议自动降级
                if (typeof amapAPI !== 'undefined' && amapAPI && amapAPI.report_route_planning_failed) {{
                    amapAPI.report_route_planning_failed();
                }}
                return Promise.reject(err);
            }});
        }}
        
        function onRouteComplete(result) {{
            console.log('onRouteComplete:', result);
            
            if (!result || !result.routes || result.routes.length === 0) {{
                console.error('路线结果为空');
                showToast('⚠️ 无法获取路线信息', 'error');
                isNavigating = false;
                return;
            }}
            
            routeInfo = result.routes[0];
            console.log('路线信息:', routeInfo);
            
            if (routeInfo && routeInfo.steps && routeInfo.steps.length > 0) {{
                navSteps = routeInfo.steps;
                currentNavStep = 0;  // 重新规划后重置步骤索引

                // 仅保存数据（不显示面板，不启动监控）
                var step = routeInfo.steps[0];
                var instruction = step.instruction ? step.instruction.replace(/<[^>]+>/g, '') : '开始导航';

                console.log('✅ 路线规划完成:', instruction);
                console.log('✅ 路线详情:', routeInfo.distance, '米,', routeInfo.time, '秒');
                console.log('✅ 共', navSteps.length, '个步骤');

                showToast('✅ 路线规划成功', 'success', 2000);
            }} else {{
                console.error('路线步骤为空');
                showToast('⚠️ 路线步骤为空', 'error');
                isNavigating = false;
            }}
        }}
        
        function stopNavigation(silent) {{
            isNavigating = false;
            routeInfo = null;
            navSteps = [];
            currentNavStep = 0;

            // 停止导航监控（silent=true时不发射信号，不播报）
            if (!silent) {{
                stopNavMonitoring();
            }} else {{
                if (navMonitorTimer) {{
                    clearInterval(navMonitorTimer);
                    navMonitorTimer = null;
                }}
                currentNavStep = 0;
                navSteps = [];
            }}

            // 恢复导航按钮为"开始导航"
            var navBtn = document.querySelector('.btn-nav');
            if (navBtn) {{
                navBtn.innerHTML = '🧭 导航';
                navBtn.onclick = enterNavMode;
                navBtn.title = '导航模式';
            }}

            // 重置地图旋转（仅高德地图支持）
            if (typeof map.setRotation === 'function') {{
                map.setRotation(0);
            }}

            // 重置导航状态
            window.navRouteIndex = 0;

            // 移除蓝色导航箭头、导航直线，恢复普通位置标记
            if (window.navArrowMarker) {{
                map.remove(window.navArrowMarker);
                window.navArrowMarker = null;
            }}
            if (window.navStraightLine) {{
                map.remove(window.navStraightLine);
                window.navStraightLine = null;
            }}

            // 恢复普通位置标记（Leaflet 离线模式使用 L.marker，高德使用 AMap.Marker）
            if (currentPos && !currentMarker) {{
                if (typeof AMap !== 'undefined') {{
                    currentMarker = new AMap.Marker({{
                        position: currentPos,
                        map: map,
                        title: '当前位置',
                        offset: new AMap.Pixel(-8, -8),
                        content: '<div style="width:16px;height:16px;background:#4DB8FF;border:2px solid #FFFFFF;border-radius:50%;box-shadow:0 0 4px rgba(0,0,0,0.6);"></div>'
                    }});
                }} else if (typeof L !== 'undefined') {{
                    currentMarker = L.marker([currentPos[1], currentPos[0]], {{
                        icon: L.divIcon({{
                            className: '',
                            html: '<div style="width:16px;height:16px;background:#4DB8FF;border:2px solid #FFFFFF;border-radius:50%;box-shadow:0 0 4px rgba(0,0,0,0.6);"></div>',
                            iconSize: [16, 16],
                            iconAnchor: [8, 8]
                        }})
                    }}).addTo(map);
                }}
            }}
            // 恢复航向标记（如果有缓存的航向）
            if (currentPos && pendingYaw !== null && !yawMarker) {{
                updateYaw(pendingYaw);
            }}
            // 清除导航直线
            if (window.navStraightLine) {{ map.remove(window.navStraightLine); window.navStraightLine = null; }}
        }}

        function clearVisualsOnly() {{
            // 只清除地图视觉元素，不停止导航
            // 清除路线
            if (window.routeLine) {{ map.remove(window.routeLine); window.routeLine = null; }}
            if (window.navStraightLine) {{ map.remove(window.navStraightLine); window.navStraightLine = null; }}

            // 清除路线箭头标记
            if (window.routeArrowMarkers) {{
                window.routeArrowMarkers.forEach(function(m) {{ map.remove(m); }});
                window.routeArrowMarkers = [];
            }}

            // 清除所有标记
            if (window.startMarker) {{ map.remove(window.startMarker); window.startMarker = null; }}
            if (window.endMarker) {{ map.remove(window.endMarker); window.endMarker = null; }}
            if (window.navArrowMarker) {{ map.remove(window.navArrowMarker); window.navArrowMarker = null; }}
            if (yawMarker) {{ map.remove(yawMarker); yawMarker = null; }}

            // 清除历史轨迹
            if (window.historyLine) {{ map.remove(window.historyLine); window.historyLine = null; }}
            if (window.historyStartMarker) {{ map.remove(window.historyStartMarker); window.historyStartMarker = null; }}
            if (window.historyEndMarker) {{ map.remove(window.historyEndMarker); window.historyEndMarker = null; }}

            // 清除数据
            destPos = null;
            window.routeStartPos = null;
            window.routePoints = null;
            window.navRouteIndex = 0;

            document.getElementById('searchInput').value = '';
            clearPinyinState();
        }}

        function clearAll() {{
            stopNavigation(true);  // silent=true: 不播报导航结束
            clearVisualsOnly();
        }}
        
        function formatDist(m) {{
            return m < 1000 ? Math.round(m) + '米' : (m/1000).toFixed(1) + '公里';
        }}
        
        function formatTime(s) {{
            var m = Math.ceil(s/60);
            return m < 60 ? m + '分钟' : Math.floor(m/60) + '小时' + (m%60) + '分';
        }}
        
        // 显示当前位置（地图中央）
        function showCurrentLocation() {{
            if (!currentPos) {{
                showToast('⚠️ 暂无位置信息', 'warning');
                return;
            }}
            map.setCenter(currentPos);
            map.setZoom(17);
            showToast('📍 已定位到当前位置', 'success');
        }}
        
        // 规划路线（全局视图）
        function planRoute() {{
            if (!destPos) {{
                showToast('⚠️ 请先选择目的地', 'warning');
                return;
            }}
            
            // 确定起点
            var startPos = currentPos || map.getCenter();
            
            // 清除旧标记
            if (window.startMarker) {{ map.remove(window.startMarker); }}
            if (window.endMarker) {{ map.remove(window.endMarker); }}
            if (window.navArrowMarker) {{ map.remove(window.navArrowMarker); }}
            
            // 添加起点圆形标记（绿色圆圈+白边框）
            window.startMarker = new AMap.Marker({{
                position: startPos,
                map: map,
                title: '起点',
                zIndex: 100,
                offset: new AMap.Pixel(-12, -12),
                content: '<div style="width: 24px; height: 24px; background: #4CAF50; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.5);"></div>'
            }});
            
            // 添加终点圆形标记（红色圆圈+白边框）- 与起点样式一致，只是颜色不同
            window.endMarker = new AMap.Marker({{
                position: destPos,
                map: map,
                title: '终点',
                zIndex: 100,
                offset: new AMap.Pixel(-12, -12),
                content: '<div style="width: 24px; height: 24px; background: #f44336; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.5);"></div>'
            }});
            
            // 保存起点
            if (!currentPos) {{
                currentPos = [startPos.lng || startPos[0], startPos.lat || startPos[1]];
            }}
            window.routeStartPos = startPos;
            
            // 执行路线规划
            doNavigate();
            
            // 调整视野
            setTimeout(function() {{
                var fitObjects = [window.startMarker, window.endMarker];
                if (window.routeLine) fitObjects.push(window.routeLine);
                map.setFitView(fitObjects, {{
                    padding: [100, 100, 100, 450]
                }});
            }}, 500);
            
            showToast('🗺️ 已显示全局路线', 'success');
        }}
        
        // 创建蓝色导航箭头标记（类似高德地图）
        function createNavArrowMarker() {{
            // 蓝色箭头SVG，指向北方（0度）
            var arrowSvg = '<svg width="48" height="48" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">' +
                '<defs>' +
                '<filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">' +
                '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="rgba(0,0,0,0.3)"/>' +
                '</filter>' +
                '</defs>' +
                '<circle cx="24" cy="24" r="22" fill="white" stroke="#2196F3" stroke-width="3" filter="url(#shadow)"/>' +
                '<path d="M24 6 L16 28 L24 24 L32 28 Z" fill="#2196F3" stroke="white" stroke-width="1.5"/>' +
                '</svg>';
            
            return new AMap.Marker({{
                position: currentPos || map.getCenter(),
                map: map,
                title: '当前位置',
                zIndex: 200,
                offset: new AMap.Pixel(-24, -24),
                content: '<div style="width:48px;height:48px;" id="navArrowContainer">' + arrowSvg + '</div>',
                angle: 0  // 初始角度，会根据移动方向更新
            }});
        }}
        
        // 更新导航箭头角度（根据移动方向）
        function updateNavArrowAngle(newPos) {{
            if (!window.navArrowMarker || !window.lastNavPos) return;
            
            // 计算移动方向的角度
            var dx = newPos[0] - window.lastNavPos[0];
            var dy = newPos[1] - window.lastNavPos[1];
            
            // 如果移动距离太小，不更新角度
            if (Math.abs(dx) < 0.00001 && Math.abs(dy) < 0.00001) return;
            
            // 计算角度（转换为度，0度指向北/上）
            var angle = Math.atan2(dx, dy) * 180 / Math.PI;
            
            // 高德地图的Marker angle：0指向北，顺时针增加
            window.navArrowMarker.setAngle(angle);
        }}
        
        // 进入导航模式（骑行级比例尺）
        function enterNavMode() {{
            if (!destPos) {{
                showToast('⚠️ 请先选择目的地', 'warning');
                return;
            }}

            // 启动导航的公共逻辑（地图视图、标记等）
            var startNavUI = function() {{
                // 设置骑行导航级别的比例尺
                var centerPos = currentPos || window.routeStartPos || map.getCenter();
                map.setCenter(centerPos);
                map.setZoom(18);

                // 移除起点绿色圈（导航模式下起点就是当前位置）
                if (window.startMarker) {{ map.remove(window.startMarker); window.startMarker = null; }}

                // 确保终点红色圈存在
                if (!window.endMarker) {{
                    window.endMarker = new AMap.Marker({{
                        position: destPos,
                        map: map,
                        title: '终点',
                        zIndex: 100,
                        offset: new AMap.Pixel(-12, -12),
                        content: '<div style="width: 24px; height: 24px; background: #f44336; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.5);"></div>'
                    }});
                }}

                // 保留普通位置标记和航偏角箭头，只清理旧的蓝色导航箭头
                if (window.navArrowMarker) {{ map.remove(window.navArrowMarker); window.navArrowMarker = null; }}

                // 确保当前位置标记存在
                if (currentPos && !currentMarker) {{
                    currentMarker = new AMap.Marker({{
                        position: currentPos,
                        map: map,
                        title: '当前位置',
                        offset: new AMap.Pixel(-8, -8),
                        content: '<div style="width:16px;height:16px;background:#4DB8FF;border:2px solid #FFFFFF;border-radius:50%;box-shadow:0 0 4px rgba(0,0,0,0.6);"></div>'
                    }});
                }}
                if (currentPos && pendingYaw !== null && !yawMarker) {{ updateYaw(pendingYaw); }}

                // 导航模式下用红色直线连接起点和终点（保留已有的规划路线）
                if (window.navStraightLine) {{ map.remove(window.navStraightLine); }}
                var startForNav = currentPos || window.routeStartPos || map.getCenter();
                window.navStraightLine = new AMap.Polyline({{
                    path: [startForNav, destPos],
                    strokeColor: '#f44336',
                    strokeWeight: 4,
                    strokeOpacity: 0.9,
                    lineJoin: 'round',
                    zIndex: 99
                }});
                window.navStraightLine.setMap(map);

                showToast('🧭 已进入导航模式', 'success');
            }};

            if (!isNavigating) {{
                // 尚未规划路线，先规划再启动导航
                doNavigate().then(function() {{
                    startNavUI();
                    startNavMonitoring();
                    // 通知 Python 端导航已开始
                    if (typeof amapAPI !== 'undefined' && amapAPI && destPos) {{
                        amapAPI.notify_nav_started(destPos[1], destPos[0]);
                    }}
                    // 修改按钮为"结束导航"
                    var navBtn = document.querySelector('.btn-nav');
                    if (navBtn) {{
                        navBtn.innerHTML = '⏹ 结束导航';
                        navBtn.onclick = function() {{ stopNavigation(); }};
                        navBtn.title = '结束导航';
                    }}
                }}).catch(function(err) {{
                    showToast('路线规划失败，无法进入导航模式', 'error');
                }});
            }} else {{
                // 路线已规划好，直接进入导航
                startNavUI();
                startNavMonitoring();
                // 通知 Python 端导航已开始
                if (typeof amapAPI !== 'undefined' && amapAPI && destPos) {{
                    amapAPI.notify_nav_started(destPos[1], destPos[0]);
                }}
                // 修改按钮为"结束导航"
                var navBtn = document.querySelector('.btn-nav');
                if (navBtn) {{
                    navBtn.innerHTML = '⏹ 结束导航';
                    navBtn.onclick = function() {{ stopNavigation(); }};
                    navBtn.title = '结束导航';
                }}
            }}
        }}
        
        // 将GPS位置投影到路线上（路径匹配）
        // 导航状态变量
        
        function updatePosition(lng, lat, province) {{
            var newPos = [lng, lat];
            currentPos = newPos;

            // 如果之前有缓存的 yaw，现在位置已就绪，立即应用
            if (pendingYaw !== null) {{
                updateYaw(pendingYaw);
            }}

            // 如果在导航中，地图跟随当前位置
            if (isNavigating) {{
                map.setCenter(currentPos);

                // 导航模式下保持 currentMarker + yawMarker 更新
                if (currentMarker) {{
                    currentMarker.setPosition(currentPos);
                }}
                if (yawMarker) {{
                    yawMarker.setPosition(currentPos);
                }}

                // 偏航检测与自动重新规划
                if (window.routePoints && window.routePoints.length > 2 && !window._isRerouting) {{
                    var distToRoute = Infinity;
                    if (AMap.GeometryUtil && AMap.GeometryUtil.distanceToLine) {{
                        distToRoute = AMap.GeometryUtil.distanceToLine(currentPos, window.routePoints);
                    }} else {{
                        // 自定义点到线段距离计算（米）
                        function pointToSegmentDistance(p, a, b) {{
                            var ax = a[0], ay = a[1];
                            var bx = b[0], by = b[1];
                            var px = p[0], py = p[1];
                            var dx = bx - ax, dy = by - ay;
                            if (dx === 0 && dy === 0) {{
                                return Math.sqrt((px-ax)*(px-ax) + (py-ay)*(py-ay));
                            }}
                            var t = ((px-ax)*dx + (py-ay)*dy) / (dx*dx + dy*dy);
                            t = Math.max(0, Math.min(1, t));
                            var nx = ax + t*dx, ny = ay + t*dy;
                            var dLng = px - nx, dLat = py - ny;
                            var latFactor = 111000;
                            var lngFactor = 111000 * Math.cos(py * Math.PI / 180);
                            return Math.sqrt((dLng*lngFactor)*(dLng*lngFactor) + (dLat*latFactor)*(dLat*latFactor));
                        }}
                        for (var i = 0; i < window.routePoints.length - 1; i++) {{
                            var d = pointToSegmentDistance(currentPos, window.routePoints[i], window.routePoints[i+1]);
                            if (d < distToRoute) distToRoute = d;
                        }}
                    }}
                    if (distToRoute > 100) {{
                        console.log('[Reroute] 偏航 detected, dist=' + distToRoute.toFixed(1) + 'm');
                        var now = Date.now();
                        if (!window._lastRerouteTime || now - window._lastRerouteTime > 15000) {{
                            window._lastRerouteTime = now;
                            window._isRerouting = true;
                            showToast('⚠️ 已偏离路线，正在重新规划...', 'warning', 3000);
                            if (typeof navHandler !== 'undefined' && navHandler) {{
                                navHandler.on_nav_instruction('您已偏离路线，正在重新规划', '已偏离路线', -1, -1);
                            }}
                            var wasNavigating = isNavigating;
                            doNavigate().then(function() {{
                                window._isRerouting = false;
                                showToast('✅ 路线已重新规划', 'success', 2000);
                                if (typeof navHandler !== 'undefined' && navHandler) {{
                                    navHandler.on_nav_instruction('路线已重新规划', '', -1, -1);
                                }}
                            }}).catch(function(err) {{
                                isNavigating = wasNavigating;
                                window._isRerouting = false;
                                showToast('重新规划失败，请检查网络', 'error');
                            }});
                        }}
                    }}
                }}

                // 检查是否需要播报下一条指令
                checkNavStep();
            }}
            
            // 通知 Python 端位置更新
            if (typeof navHandler !== 'undefined' && navHandler) {{
                navHandler.on_position_updated(lat, lng);
            }}
            
            // 非导航模式下更新当前位置标记
            if (!isNavigating) {{
                if (currentMarker) {{
                    currentMarker.setPosition(currentPos);
                }} else {{
                    currentMarker = new AMap.Marker({{
                        position: currentPos,
                        map: map,
                        title: '当前位置',
                        offset: new AMap.Pixel(-8, -8),
                        content: '<div style="width:16px;height:16px;background:#4DB8FF;border:2px solid #FFFFFF;border-radius:50%;box-shadow:0 0 4px rgba(0,0,0,0.6);"></div>'
                    }});
                }}
                if (yawMarker) {{
                    yawMarker.setPosition(currentPos);
                }}
                map.setCenter(currentPos);
                map.setZoom(16);
                
                // 绘制轨迹
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
            
        }}
        
        window.updatePosition = updatePosition;

        // 更新航偏角方向标记（非导航模式下显示）
        // 与 currentMarker 共存：定位点 + 旋转航向箭头
        function updateYaw(angle) {{
            if (!currentPos) {{
                pendingYaw = angle;
                return;
            }}
            pendingYaw = null;
            var arrowHtml = '<div id="yaw-arrow" style="width:48px;height:48px;transform-origin:center center;">' +
                '<svg width="48" height="48" viewBox="0 0 48 48" style="overflow:visible;">' +
                '<polygon points="24,6 38,34 24,26 10,34" fill="rgba(77,184,255,0.85)" stroke="#FFFFFF" stroke-width="2"/>' +
                '<circle cx="24" cy="24" r="3" fill="#FFFFFF" stroke="#4DB8FF" stroke-width="1.5"/>' +
                '</svg></div>';
            if (!yawMarker) {{
                yawMarker = new AMap.Marker({{
                    position: currentPos,
                    map: map,
                    content: arrowHtml,
                    offset: new AMap.Pixel(-24, -24),
                    zIndex: 111
                }});
            }} else {{
                yawMarker.setPosition(currentPos);
            }}
            var el = document.getElementById('yaw-arrow');
            if (el) {{
                el.style.transform = 'rotate(' + angle + 'deg)';
            }}
        }}
        window.updateYaw = updateYaw;

        // Toast 提示函数
        function showToast(message, type = 'info', duration = 2500) {{
            var toast = document.getElementById('toast');
            if (!toast) {{
                toast = document.createElement('div');
                toast.id = 'toast';
                toast.className = 'toast';
                document.body.appendChild(toast);
            }}
            toast.textContent = message;
            toast.className = 'toast ' + type;
            toast.classList.add('show');
            
            setTimeout(function() {{
                toast.classList.remove('show');
            }}, duration);
        }}
    </script>
    
    <!-- Toast 提示框 -->
    <div id="toast" class="toast"></div>
</body>
</html>
"""

    def generate_offline_html(self):
        """生成离线地图 HTML (Leaflet + 本地瓦片)"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>离线骑行地图</title>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <link rel="stylesheet" href="leaflet/leaflet.css" />
    <script src="leaflet/leaflet.js"></script>
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
            z-index: 2000;
        }}
        .input-row {{
            display: flex;
            gap: 8px;
            align-items: center;
        }}
        .search-input {{
            width: 420px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            color: #000;
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
        .btn-route {{ background: linear-gradient(135deg, #3498db, #2980b9); }}
        .btn-nav {{ background: linear-gradient(135deg, #2ecc71, #27ae60); }}
        .btn-locate {{ background: linear-gradient(135deg, #9b59b6, #8e44ad); font-size: 18px; padding: 12px; }}
        .btn-stop {{ background: linear-gradient(135deg, #e74c3c, #c0392b); padding: 12px; display: none; }}
        .btn-clear {{ background: linear-gradient(135deg, #666, #555); padding: 12px; }}

        /* 展开/收起按钮 */
        .btn-toggle {{
            background: linear-gradient(135deg, #f39c12, #e67e22);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px 10px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            height: 48px;
            transition: all 0.1s;
            min-width: 48px;
        }}
        .btn-toggle:active {{ transform: scale(0.95); }}

        /* 按钮面板 —— 默认收起在 》》 按钮后方 */
        .btn-slide-group {{
            display: flex;
            gap: 8px;
            max-width: 0;
            opacity: 0;
            overflow: hidden;
            transition: all 0.35s cubic-bezier(0.25, 0.46, 0.45, 0.94);
            align-items: center;
            pointer-events: none;
            white-space: nowrap;
        }}
        .btn-slide-group.show {{
            max-width: 600px;
            opacity: 1;
            pointer-events: auto;
        }}

        /* 地图缩放按钮 */
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

        /* ========== 右侧半透明键盘 ========== */
        .keyboard-wrapper {{
            position: fixed;
            bottom: 10px;
            right: 10px;
            width: 480px;
            z-index: 3000;
            display: none;
        }}
        .keyboard-wrapper.active {{ display: block; }}
        .candidates-area {{
            background: rgba(80, 80, 80, 0.5);
            backdrop-filter: blur(4px);
            border-radius: 12px 12px 0 0;
            border: 1px solid rgba(255,255,255,0.1);
            border-bottom: none;
            padding: 12px 14px;
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
            border-radius: 8px;
            padding: 7px 14px;
            font-size: 18px;
            cursor: pointer;
            white-space: nowrap;
            transition: all 0.1s;
            min-width: 42px;
            text-align: center;
        }}
        .candidate-item:hover {{
            background: rgba(77, 184, 255, 0.8);
            border-color: #4DB8FF;
        }}
        .candidate-item:active {{ transform: scale(0.95); }}
        .more-btn {{
            background: #4DB8FF !important;
            color: #fff !important;
            font-weight: bold;
            min-width: 40px;
        }}
        .keyboard-main {{
            background: rgba(70, 70, 70, 0.5);
            backdrop-filter: blur(4px);
            border-radius: 0 0 12px 12px;
            border: 1px solid rgba(255,255,255,0.1);
            border-top: 1px solid rgba(255,255,255,0.05);
            padding: 12px 10px 14px 10px;
        }}
        .kb-row {{
            display: flex;
            gap: 6px;
            margin-bottom: 7px;
            justify-content: center;
        }}
        .key {{
            background: rgba(120, 120, 120, 0.6);
            color: white;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            padding: 0;
            font-size: 18px;
            font-weight: 500;
            cursor: pointer;
            height: 50px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.08s;
            flex: 1;
            max-width: 48px;
        }}
        .key:hover {{ background: rgba(140, 140, 140, 0.7); }}
        .key:active {{ background: rgba(100, 100, 100, 0.8); transform: scale(0.96); }}
        .key-shift {{ flex: 1.3; max-width: 62px; background: rgba(100, 100, 100, 0.65); font-size: 16px; }}
        .key-back {{ flex: 1.3; max-width: 62px; background: rgba(110, 110, 110, 0.65); font-size: 16px; }}
        .key-space {{ flex: 4; max-width: 220px; font-size: 16px; background: rgba(120, 120, 120, 0.6); }}
        .key-enter {{ flex: 1.4; max-width: 78px; background: rgba(46, 204, 113, 0.7); font-size: 16px; color: white; font-weight: 600; }}
        .key-lang {{ flex: 1; max-width: 50px; font-size: 13px; background: rgba(52, 152, 219, 0.7); }}
        .row-qwerty {{ padding-left: 15px; padding-right: 15px; }}
        .row-asdf {{ padding-left: 25px; padding-right: 25px; }}
        .row-zxcv {{ padding-left: 10px; padding-right: 10px; }}
        .row-space {{ padding-left: 20px; padding-right: 20px; }}

        /* 离线提示 */
        .offline-badge {{
            position: absolute;
            top: 75px;
            right: 8px;
            background: rgba(231, 76, 60, 0.9);
            color: white;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            z-index: 1000;
        }}

        /* Toast 提示框 */
        .toast {{
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.85);
            color: #fff;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 9999;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        .toast.show {{ opacity: 1; }}
        .toast.error {{ background: rgba(231, 76, 60, 0.9); }}
        .toast.success {{ background: rgba(46, 204, 113, 0.9); }}
        .toast.warning {{ background: rgba(241, 196, 15, 0.9); }}

        /* Leaflet 暗黑滤镜 */
        .leaflet-tile-pane {{ filter: brightness(0.7) contrast(1.1) saturate(0.8); }}
        .leaflet-container {{ background: #1a1a1a; }}
    </style>
</head>
<body>
    <div id="container"></div>

    <!-- 离线标识 -->
    <div class="offline-badge" id="offlineBadge">离线模式</div>

    <!-- 搜索面板 -->
    <div class="search-panel">
        <div style="position: relative;">
            <div class="input-row">
                <input type="text" id="searchInput" class="search-input" placeholder="点击地图选点或输入坐标 如 27.83,112.93" onclick="showKeyboard()">
                <button class="btn btn-toggle" onclick="toggleBtnPanel()" title="展开/收起">》》</button>
                <div id="btnPanel" class="btn-slide-group">
                    <button class="btn btn-route" onclick="planOfflineRoute()" title="规划路线">🗺️ 路线</button>
                    <button class="btn btn-nav" onclick="enterNavMode()" title="导航模式">🧭 导航</button>
                    <button class="btn-zoom" onclick="zoomIn()" title="放大">+</button>
                    <button class="btn-zoom" onclick="zoomOut()" title="缩小">−</button>
                    <button class="btn btn-locate" onclick="showCurrentLocation()" title="当前位置">📍</button>
                    <button class="btn btn-clear" onclick="clearAll()" title="清除">🗑️</button>
                </div>
            </div>
        </div>
    </div>

    <!-- 键盘 -->
    <div class="keyboard-wrapper" id="keyboard">
        <div class="candidates-area">
            <div class="pinyin-row">
                <span class="pinyin-label">拼音</span>
                <span id="pinyinText" class="pinyin-text"></span>
            </div>
            <div id="candidatesContainer" class="candidates-row"></div>
        </div>
        <div class="keyboard-main">
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
            <div class="kb-row row-space">
                <button class="key key-lang" onclick="toggleLang()">中/英</button>
                <button class="key key-space" onclick="inputChar(' ')">空格</button>
                <button class="key key-enter" onclick="confirmInput()">确定</button>
            </div>
        </div>
    </div>

    <script>
        // 全局变量
        var map, currentPos, destPos, currentMarker, destMarker, trackLine, yawMarker;
        var isNavigating = false, routeInfo = null, trackPoints = [];
        var pinyinBuffer = "";
        var isShiftOn = false;
        var isChineseMode = true;
        var amapAPI = null;
        var pinyinHandler = null;
        var navHandler = null;
        var isMapInitialized = false;
        var pendingYaw = null;
        var routeLine = null;
        var offlineRouteShape = [];
        var offlineManeuvers = [];

        // DOM 加载完成后初始化
        document.addEventListener("DOMContentLoaded", function() {{
            console.log('DOM 加载完成');
            initAll();
        }});

        function initAll() {{
            initMap();

            // 连接 QWebChannel
            if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                new QWebChannel(qt.webChannelTransport, function(channel) {{
                    amapAPI = channel.objects.amapAPI;
                    pinyinHandler = channel.objects.pinyinHandler;
                    navHandler = channel.objects.navHandler;
                    console.log('QWebChannel 连接成功');
                }});
            }} else {{
                console.error('QWebChannel 未就绪');
            }}

            document.addEventListener('click', function(e) {{
                var kb = document.getElementById('keyboard');
                var input = document.getElementById('searchInput');
                if (!kb || !kb.classList.contains('active')) return;
                if (kb.contains(e.target) || input.contains(e.target)) return;
                hideKeyboard();
            }});
        }}

        function initMap() {{
            if (isMapInitialized) return;

            try {{
                console.log('开始初始化离线地图...');

                map = L.map('container', {{
                    zoomControl: false,
                    attributionControl: false
                }}).setView([27.828, 112.944], 16);

                L.tileLayer('{self.tile_server_url}', {{
                    minZoom: 13,
                    maxZoom: 16,
                    tileSize: 256
                }}).addTo(map);

                // 比例尺
                L.control.scale({{position: 'bottomleft', metric: true, imperial: false}}).addTo(map);

                currentPos = null;
                isMapInitialized = true;
                console.log('离线地图初始化完成');

                // 地图点击选点作为目的地
                map.on('click', function(e) {{
                    var lat = e.latlng.lat;
                    var lng = e.latlng.lng;
                    destPos = [lng, lat];
                    if (destMarker) map.removeLayer(destMarker);
                    destMarker = L.marker([lat, lng], {{
                        icon: L.divIcon({{
                            className: '',
                            html: '<div style="width:32px;height:32px;background:#e74c3c;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:14px;">终</div>',
                            iconSize: [32, 32],
                            iconAnchor: [16, 16]
                        }})
                    }}).addTo(map);
                    document.getElementById('searchInput').value = lat.toFixed(5) + ',' + lng.toFixed(5);
                    showToast('已设置目的地: ' + lat.toFixed(5) + ',' + lng.toFixed(5), 'success');
                }});

                // 通知 Python
                if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
                    setTimeout(function() {{
                        if (amapAPI) {{
                            amapAPI.report_map_status(true);
                        }}
                    }}, 500);
                }}
            }} catch (e) {{
                console.error('地图初始化失败:', e);
                document.getElementById('container').innerHTML =
                    '<div style="color: red; padding: 20px; text-align: center;">' +
                    '<h3>离线地图加载失败</h3><p>' + e.message + '</p></div>';
                if (amapAPI) {{
                    amapAPI.report_map_status(false);
                }}
            }}
        }}

        // ========== 位置更新 ==========
        window.updatePosition = function(lon, lat, province) {{
            if (!map) return;
            console.log('更新位置:', lon, lat, province);
            currentPos = [lat, lon];

            // 移动地图中心
            map.panTo([lat, lon]);

            // 添加/更新定位标记
            var arrowHtml = '<div id="yaw-arrow" style="width:48px;height:48px;transform-origin:center center;">' +
                '<svg width="48" height="48" viewBox="0 0 48 48">' +
                '<circle cx="24" cy="24" r="8" fill="#4DB8FF" stroke="white" stroke-width="2"/>' +
                '<path d="M24 4 L34 24 L24 20 L14 24 Z" fill="#4DB8FF" stroke="white" stroke-width="2"/>' +
                '</svg></div>';

            if (!currentMarker) {{
                currentMarker = L.marker([lat, lon], {{
                    icon: L.divIcon({{
                        html: arrowHtml,
                        className: '',
                        iconSize: [48, 48],
                        iconAnchor: [24, 24]
                    }})
                }}).addTo(map);
            }} else {{
                currentMarker.setLatLng([lat, lon]);
            }}


            if (pendingYaw !== null) {{
                updateYaw(pendingYaw);
                pendingYaw = null;
            }}
        }};

        // ========== 航偏角更新 ==========
        window.updateYaw = function(angle) {{
            if (!currentMarker) {{
                pendingYaw = angle;
                return;
            }}
            var el = document.getElementById('yaw-arrow');
            if (el) {{
                el.style.transform = 'rotate(' + angle + 'deg)';
            }}
        }};

        // ========== 缩放控制 ==========
        window.zoomIn = function() {{
            if (map) map.zoomIn();
        }};
        window.zoomOut = function() {{
            if (map) map.zoomOut();
        }};

        // ========== 当前位置 ==========
        window.showCurrentLocation = function() {{
            if (currentPos) {{
                map.setView(currentPos, 16);
                showToast('已定位到当前位置', 'success');
            }} else {{
                showToast('当前位置未知', 'warning');
            }}
        }};

        // ========== 导航模式（离线简化版：直线导航） ==========
        window.enterNavMode = function() {{
            if (!currentPos || !destPos) {{
                showToast('请先设置目的地', 'warning');
                return;
            }}
            isNavigating = true;
            var stopBtn = document.querySelector('.btn-stop');
            if (stopBtn) stopBtn.style.display = 'inline-block';
            // 修改按钮为"结束导航"
            var navBtn = document.querySelector('.btn-nav');
            if (navBtn) {{
                navBtn.innerHTML = '⏹ 结束导航';
                navBtn.onclick = window.stopNavigation;
                navBtn.title = '结束导航';
            }}
            showToast('开始导航（离线模式）', 'success');
            // 通知 Python 开始导航（Python 会负责绘制路线、zoom、语音播报）
            if (amapAPI) amapAPI.start_offline_navigation(destPos[1], destPos[0]);
        }};

        window.stopNavigation = function(silent) {{
            isNavigating = false;
            var stopBtn = document.querySelector('.btn-stop');
            if (stopBtn) stopBtn.style.display = 'none';
            if (routeLine) {{
                map.removeLayer(routeLine);
                routeLine = null;
            }}
            offlineRouteShape = [];
            offlineManeuvers = [];
            // 恢复导航按钮为"开始导航"
            var navBtn = document.querySelector('.btn-nav');
            if (navBtn) {{
                navBtn.innerHTML = '🧭 导航';
                navBtn.onclick = window.enterNavMode;
                navBtn.title = '导航模式';
            }}
            if (!silent && navHandler) navHandler.on_nav_stopped();
        }};

        window.drawRouteLine = function() {{
            if (!currentPos || !destPos || !map) return;
            if (routeLine) {{
                map.removeLayer(routeLine);
            }}
            routeLine = L.polyline([
                [currentPos[0], currentPos[1]],
                [destPos[1], destPos[0]]
            ], {{
                color: '#4DB8FF',
                weight: 5,
                opacity: 0.8,
                dashArray: '10, 10'
            }}).addTo(map);
        }};

        // 绘制 Valhalla 离线路线
        window.drawOfflineRoute = function(shape, maneuvers, shouldFitBounds) {{
            if (!map || !shape || shape.length < 2) return;
            offlineRouteShape = shape;
            offlineManeuvers = maneuvers || [];
            if (routeLine) {{
                map.removeLayer(routeLine);
            }}
            // 绘制路线
            routeLine = L.polyline(shape, {{
                color: '#2ecc71',
                weight: 6,
                opacity: 0.9
            }}).addTo(map);
            // 适应视野（导航中不自动调整，避免覆盖当前位置居中）
            if (shouldFitBounds !== false) {{
                var bounds = L.latLngBounds(shape);
                map.fitBounds(bounds, {{padding: [40, 40]}});
            }}
            console.log('离线路线绘制完成，共' + shape.length + '个点，' + offlineManeuvers.length + '个导航指令');
        }};

        // ========== 清除 ==========
        window.clearVisualsOnly = function() {{
            if (routeLine) {{
                map.removeLayer(routeLine);
                routeLine = null;
            }}
            if (destMarker) {{
                map.removeLayer(destMarker);
                destMarker = null;
            }}
            if (window.historyLine) {{
                map.removeLayer(window.historyLine);
                window.historyLine = null;
            }}
            if (window.historyStartMarker) {{
                map.removeLayer(window.historyStartMarker);
                window.historyStartMarker = null;
            }}
            if (window.historyEndMarker) {{
                map.removeLayer(window.historyEndMarker);
                window.historyEndMarker = null;
            }}
            offlineRouteShape = [];
            offlineManeuvers = [];
            destPos = null;
        }};

        window.clearAll = function() {{
            stopNavigation(true);  // silent=true: 不播报导航结束
            window.clearVisualsOnly();
        }};

        // ========== 工具函数 ==========
        function formatDist(m) {{
            if (m >= 1000) return (m / 1000).toFixed(1) + '公里';
            return Math.round(m) + '米';
        }}
        function formatTime(s) {{
            if (s >= 3600) return Math.floor(s / 3600) + '小时' + Math.floor((s % 3600) / 60) + '分';
            return Math.floor(s / 60) + '分钟';
        }}

        // ========== 键盘输入 ==========
        function inputChar(char) {{
            if (isShiftOn && char >= 'a' && char <= 'z') {{
                char = char.toUpperCase();
            }}
            if (char >= 'a' && char <= 'z' && isChineseMode) {{
                pinyinBuffer += char;
                updatePinyinDisplay();
                fetchCandidates();
            }} else {{
                var input = document.getElementById('searchInput');
                input.value += char;
                clearPinyinState();
            }}
        }}
        function updatePinyinDisplay() {{
            var text = document.getElementById('pinyinText');
            text.textContent = pinyinBuffer;
        }}
        function clearPinyinState() {{
            pinyinBuffer = "";
            updatePinyinDisplay();
            document.getElementById('candidatesContainer').innerHTML = '';
        }}
        function fetchCandidates(page) {{
            if (page === undefined) page = 0;
            if (pinyinHandler) {{
                pinyinHandler.get_candidates(pinyinBuffer, page).then(function(result) {{
                    showCandidates(result);
                }}).catch(function(err) {{
                    console.error('获取候选词失败:', err);
                }});
            }}
        }}
        function showCandidates(result) {{
            var container = document.getElementById('candidatesContainer');
            container.innerHTML = '';
            if (!result || !result.candidates) return;
            result.candidates.forEach(function(c, i) {{
                var span = document.createElement('span');
                span.className = 'candidate-item';
                span.textContent = c;
                span.onclick = function(e) {{ e.stopPropagation(); selectCandidate(c); }};
                container.appendChild(span);
            }});
            if (result.has_more) {{
                var more = document.createElement('span');
                more.className = 'candidate-item more-btn';
                more.textContent = '>';
                more.onclick = function(e) {{ e.stopPropagation(); fetchCandidates(result.page + 1); }};
                container.appendChild(more);
            }}
        }}
        function selectCandidate(char) {{
            var input = document.getElementById('searchInput');
            input.value += char;
            clearPinyinState();
            showKeyboard();
        }}
        function handleBackspace() {{
            var input = document.getElementById('searchInput');
            if (pinyinBuffer.length > 0) {{
                pinyinBuffer = pinyinBuffer.slice(0, -1);
                updatePinyinDisplay();
                fetchCandidates();
            }} else {{
                input.value = input.value.slice(0, -1);
            }}
        }}
        function toggleShift() {{ isShiftOn = !isShiftOn; }}
        function toggleLang() {{ isChineseMode = !isChineseMode; clearPinyinState(); }}
        function confirmInput() {{
            hideKeyboard();
            var val = document.getElementById('searchInput').value.trim();
            if (!val) return;
            var parts = val.split(/[,， ]+/);
            if (parts.length >= 2) {{
                var lat = parseFloat(parts[0]);
                var lon = parseFloat(parts[1]);
                if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {{
                    destPos = [lon, lat];
                    if (destMarker) map.removeLayer(destMarker);
                    destMarker = L.marker([lat, lon], {{
                        icon: L.divIcon({{
                            className: '',
                            html: '<div style="width:32px;height:32px;background:#e74c3c;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:14px;">终</div>',
                            iconSize: [32, 32],
                            iconAnchor: [16, 16]
                        }})
                    }}).addTo(map);
                    showToast('目的地已设置: ' + lat.toFixed(5) + ',' + lon.toFixed(5), 'success');
                    return;
                }}
            }}
            showToast('坐标格式错误，请使用 纬度,经度 如 27.83,112.93', 'warning');
        }}

        function planOfflineRoute() {{
            var val = document.getElementById('searchInput').value.trim();
            if (!val) {{
                showToast('请先输入目的地坐标或点击地图选点', 'warning');
                return;
            }}
            var parts = val.split(/[,， ]+/);
            if (parts.length >= 2) {{
                var lat = parseFloat(parts[0]);
                var lon = parseFloat(parts[1]);
                if (!isNaN(lat) && !isNaN(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {{
                    if (amapAPI) {{
                        showToast('正在规划离线路线...', 'info');
                        amapAPI.plan_offline_route(lat, lon);
                    }} else {{
                        showToast('QWebChannel 未就绪', 'error');
                    }}
                    return;
                }}
            }}
            showToast('坐标格式错误，请使用 纬度,经度 如 27.83,112.93', 'warning');
        }}

        function showKeyboard() {{
            document.getElementById('keyboard').classList.add('active');
        }}
        function hideKeyboard() {{
            document.getElementById('keyboard').classList.remove('active');
            clearPinyinState();
        }}

        function toggleBtnPanel() {{
            var panel = document.getElementById('btnPanel');
            panel.classList.toggle('show');
        }}

        // ========== Toast ==========
        function showToast(message, type, duration) {{
            if (duration === undefined) duration = 2500;
            var toast = document.getElementById('toast');
            if (!toast) {{
                toast = document.createElement('div');
                toast.id = 'toast';
                toast.className = 'toast';
                document.body.appendChild(toast);
            }}
            toast.textContent = message;
            toast.className = 'toast ' + type;
            toast.classList.add('show');
            setTimeout(function() {{ toast.classList.remove('show'); }}, duration);
        }}
    </script>
    <div id="toast" class="toast"></div>
</body>
</html>
"""

    def update_location(self, lat, lon, province="未知"):
        """更新当前位置"""
        self.current_lat = lat
        self.current_lon = lon
        js_code = f"updatePosition({lon}, {lat}, '{province}');"
        self.web_view.page().runJavaScript(js_code)

        # 离线导航跟踪
        nav_active = self._offline_nav_active and self.nav_engine and self.nav_engine.is_active()
        print(f"[update_location] lat={lat}, lon={lon}, offline_nav_active={self._offline_nav_active}, nav_engine_active={nav_active}")
        if nav_active:
            print(f"[update_location] 调用 nav_engine.update_position({lat}, {lon})")
            self.nav_engine.update_position(lat, lon)

    def update_yaw(self, angle):
        """更新航偏角箭头（0°指北，顺时针增加）"""
        js_code = f"updateYaw({angle});"
        self.web_view.page().runJavaScript(js_code)
        # 传给离线导航引擎
        if self.nav_engine:
            self.nav_engine.update_yaw(angle)

    def set_zoom(self, zoom_level):
        """设置地图缩放级别

        Args:
            zoom_level: 缩放级别，骑行导航推荐 16-17
                       15 - 看到街区范围
                       16-17 - 骑行导航最佳（能看清道路细节）
                       18 - 看到建筑细节
        """
        if self._mode == 'offline':
            js_code = f"if(map) map.setZoom({zoom_level});"
        else:
            js_code = f"map.setZoom({zoom_level});"
        self.web_view.page().runJavaScript(js_code)
        print(f"[MapWidget] 地图缩放级别设置为: {zoom_level}")

    def check_navigation_status(self):
        """检查导航状态（由定时器调用）"""
        pass

    def plan_offline_route(self, dest_lat, dest_lon):
        """离线模式：仅规划路线（不启动导航）

        Args:
            dest_lat: 目的地纬度
            dest_lon: 目的地经度
        """
        if not self.current_lat or not self.current_lon:
            print("[MapWidget] 无法规划：当前位置未知")
            return False

        if not self.nav_engine:
            print("[MapWidget] 离线路线规划不可用：导航引擎未初始化")
            return False

        # 备份 yaw，避免 clear 后丢失
        yaw_backup = self.nav_engine._current_yaw
        self.nav_engine.clear()
        self.nav_engine._current_yaw = yaw_backup
        self._offline_nav_active = False
        self._last_nav_instruction = ""

        js_code = f"""
            destPos = [{dest_lon}, {dest_lat}];
            if (destMarker) map.removeLayer(destMarker);
            destMarker = L.marker([{dest_lat}, {dest_lon}], {{
                icon: L.divIcon({{
                    className: '',
                    html: '<div style=\"width:32px;height:32px;background:#e74c3c;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:14px;\">终</div>',
                    iconSize: [32, 32],
                    iconAnchor: [16, 16]
                }})
            }}).addTo(map);
            showToast('正在规划离线路线...', 'info');
        """
        self.web_view.page().runJavaScript(js_code)

        self.nav_engine.plan_route(
            self.current_lon, self.current_lat,
            dest_lon, dest_lat,
            costing="bicycle"
        )
        return True

    def start_navigation(self, dest_lat, dest_lon):
        """开始导航到指定位置

        Args:
            dest_lat: 目的地纬度
            dest_lon: 目的地经度
        """
        if not self.current_lat or not self.current_lon:
            print("[MapWidget] 无法导航：当前位置未知")
            return False

        if self._mode == 'offline':
            # 离线模式：需要先规划好路线才能导航
            if not self.nav_engine or not self.nav_engine.is_active():
                js = "showToast('请先点击路线按钮规划路线', 'warning');"
                self.web_view.page().runJavaScript(js)
                return False

            self._offline_nav_active = True
            self._last_nav_instruction = ""
            self._last_rel_dir = ""
            self.is_navigating = True
            self._dest_lat = dest_lat
            self._dest_lon = dest_lon

            # Python 直接发送 JS 绘制正确路线 + 显示面板 + zoom=16
            # 不依赖 JS 全局变量 offlineRouteShape
            shape_js = json.dumps(self.nav_engine._shape)
            js = f"""
                offlineRouteShape = {shape_js};
                if (routeLine) map.removeLayer(routeLine);
                routeLine = L.polyline(offlineRouteShape, {{
                    color: '#2ecc71',
                    weight: 6,
                    opacity: 0.9
                }}).addTo(map);
                // 红色直线连接当前位置和目的地
                if (window.navStraightLine) map.removeLayer(window.navStraightLine);
                window.navStraightLine = L.polyline([[{self.current_lat}, {self.current_lon}], [{dest_lat}, {dest_lon}]], {{
                    color: '#f44336',
                    weight: 4,
                    opacity: 0.6
                }}).addTo(map);
                var stopBtn = document.querySelector('.btn-stop');
                if (stopBtn) stopBtn.style.display = 'inline-block';
                if(map) {{
                    map.setView([{self.current_lat}, {self.current_lon}], 16);
                }}
            """
            self.web_view.page().runJavaScript(js)

            # 语音播报第一条指令 + 总览
            maneuvers = self.nav_engine._maneuvers
            total_dist = self.nav_engine._route.get('total_distance_km', 0) if self.nav_engine._route else 0
            total_time = self.nav_engine._route.get('total_time_sec', 0) if self.nav_engine._route else 0

            speak_parts = ["开始骑行"]
            if total_dist > 0:
                speak_parts.append(f"全程{total_dist:.1f}公里")
            if total_time > 0:
                minutes = int(total_time / 60)
                speak_parts.append(f"预计{minutes}分钟")

            # 加入相对方向（如果有 yaw 数据）
            rel_dir = ""
            yaw = self.nav_engine._current_yaw if self.nav_engine else None
            print(f"[NavStart] yaw={yaw}, start={self.nav_engine._route['start']}, end={self.nav_engine._route['end']}")
            if (self.nav_engine and yaw is not None):
                from services.nav_engine import _bearing, _relative_direction
                # 从当前位置看向终点的方位，作为"路线在你哪个方向"
                end_lat, end_lon = self.nav_engine._route['end']
                route_bearing = _bearing(self.current_lat, self.current_lon, end_lat, end_lon)
                rel_dir = _relative_direction(yaw, route_bearing)
                print(f"[NavStart] route_bearing(current->end)={route_bearing:.1f}, rel_dir={rel_dir}")
                if rel_dir:
                    speak_parts.append(f"骑行路线在你的{rel_dir}")
                    self._last_rel_dir = rel_dir  # 同步，避免 _on_nav_updated 再播报一次
            else:
                print("[NavStart] 无 yaw 数据，跳过方向播报")

            self.nav_instruction.emit("，".join(speak_parts))
            self.navigation_handler.nav_started.emit()
            return True
        else:
            # 在线模式：计算相对方向（如果有 yaw）并通过 JS 传递
            rel_dir = ""
            if self.current_lat and self.current_lon:
                yaw = getattr(self.nav_engine, '_current_yaw', None) if self.nav_engine else None
                if yaw is not None:
                    from services.nav_engine import _bearing, _relative_direction
                    route_bearing = _bearing(self.current_lat, self.current_lon, dest_lat, dest_lon)
                    rel_dir = _relative_direction(yaw, route_bearing)
                    print(f"[NavStart-Online] yaw={yaw}, route_bearing={route_bearing:.1f}, rel_dir={rel_dir}")

            js_code = f"""
                // 兜底：如果 JS 端 currentPos 尚未就绪，用 Python 端最新坐标补位
                if (!currentPos) {{
                    currentPos = [{self.current_lon or 0}, {self.current_lat or 0}];
                    console.log('[JS] currentPos 兜底补位:', currentPos);
                }}
                destPos = [{dest_lon}, {dest_lat}];
                window._navRelDir = "{rel_dir}";
                // 添加目的地标记
                if (destMarker) map.remove(destMarker);
                destMarker = new AMap.Marker({{
                    position: destPos,
                    map: map,
                    title: '目的地',
                    icon: new AMap.Icon({{
                        size: new AMap.Size(32, 32),
                        image: 'https://webapi.amap.com/theme/v1.3/markers/n/mark_b.png',
                        imageSize: new AMap.Size(32, 32)
                    }})
                }});
                console.log('[JS] 在线导航开始, currentPos=', currentPos, 'destPos=', destPos);
                doNavigate().catch(function(err) {{
                    console.error('[JS] doNavigate 失败:', err);
                    showToast('导航启动失败: ' + err, 'error', 3000);
                }});
            """
            self.web_view.page().runJavaScript(js_code)
            self.is_navigating = True
            self._dest_lat = dest_lat
            self._dest_lon = dest_lon
            self.navigation_handler.nav_started.emit()
            print(f"[MapWidget] 在线导航已启动: ({dest_lat}, {dest_lon})")
            return True

    def get_navigation_destination(self):
        """返回当前导航目的地坐标 (lat, lon)，未设置时返回 (None, None)"""
        return self._dest_lat, self._dest_lon

    def navigate_to(self, dest_lat: float, dest_lon: float):
        """App 设置目的地并自动开始导航（根据当前在线/离线模式自动适配）

        Args:
            dest_lat: 目的地纬度
            dest_lon: 目的地经度
        """
        self._dest_lat = dest_lat
        self._dest_lon = dest_lon

        # 无论当前位置是否已知，都先在地图上标记目的地
        js_set_dest = f"""
            destPos = [{dest_lon}, {dest_lat}];
            if (typeof map !== 'undefined') {{
                if (typeof destMarker !== 'undefined' && destMarker) {{
                    if (window._mode === 'offline') map.removeLayer(destMarker);
                    else map.remove(destMarker);
                }}
                if (window._mode === 'offline') {{
                    destMarker = L.marker([{dest_lat}, {dest_lon}], {{
                        icon: L.divIcon({{
                            className: '',
                            html: '<div style="width:32px;height:32px;background:#e74c3c;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:14px;">终</div>',
                            iconSize: [32, 32],
                            iconAnchor: [16, 16]
                        }})
                    }}).addTo(map);
                    map.setView([{dest_lat}, {dest_lon}], 14);
                }}
            }}
        """
        self.web_view.page().runJavaScript(js_set_dest)

        if not self.current_lat or not self.current_lon:
            print("[MapWidget] 无法导航：当前位置未知，已仅标记目的地")
            self.nav_instruction.emit("无法导航：当前位置未知，请等待GPS定位")
            return False

        if self._mode == 'offline':
            # 离线模式：先规划路线，规划完成后 _on_route_planned 会自动开始导航
            self._pending_auto_navigate = True
            print(f"[MapWidget] App导航请求(离线): 规划路线 ({self.current_lat}, {self.current_lon}) -> ({dest_lat}, {dest_lon})")
            self.plan_offline_route(dest_lat, dest_lon)
            return None  # 异步，结果通过信号回调
        else:
            # 在线模式：直接开始导航
            print(f"[MapWidget] App导航请求(在线): 直接导航 -> ({dest_lat}, {dest_lon})")
            return self.start_navigation(dest_lat, dest_lon)

    def _on_route_planned(self, route):
        """Valhalla 路线规划完成回调（绘制路线；若由 App 触发则自动进入导航）"""
        self._is_rerouting = False
        self._last_nav_instruction = ""  # 重置语音播报去重，避免重新规划后不播报
        self._last_rel_dir = ""          # 重置方向去重
        print(f"[MapWidget] _on_route_planned 被调用, offline_nav_active={self._offline_nav_active}, 总长={route['total_distance_km']:.2f}km, shape点数={len(route.get('shape', []))}")

        # App 设置目的地后自动开始导航
        if self._pending_auto_navigate and self._dest_lat and self._dest_lon:
            self._pending_auto_navigate = False
            print(f"[MapWidget] 自动开始离线导航: ({self._dest_lat}, {self._dest_lon})")
            self.start_navigation(self._dest_lat, self._dest_lon)
        shape = route['shape']
        maneuvers = route['maneuvers']
        # 传给 JS 绘制
        shape_js = json.dumps(shape)
        maneuvers_js = json.dumps([
            {"type": m.get("type", 0),
             "instruction": m.get("instruction", ""),
             "length": m.get("length", 0),
             "time": m.get("time", 0)}
            for m in maneuvers
        ])
        js = f"""
            drawOfflineRoute({shape_js}, {maneuvers_js}, false);
            // 红色直线连接当前位置和目的地
            if (window.navStraightLine) map.removeLayer(window.navStraightLine);
            if (destPos) {{
                window.navStraightLine = L.polyline([[{self.current_lat or 0}, {self.current_lon or 0}], [destPos[1], destPos[0]]], {{
                    color: '#f44336',
                    weight: 4,
                    opacity: 0.6
                }}).addTo(map);
            }}
            if(map) {{
                map.setView([{self.current_lat if self.current_lat is not None else 'destPos[1]'}, {self.current_lon if self.current_lon is not None else 'destPos[0]'}], 16);
            }}
            {'showToast("已重新规划路线", "success");' if self._offline_nav_active else "showToast('路线规划完成，点击导航开始骑行', 'success');"}
        """
        self.web_view.page().runJavaScript(js)
        # 不进入导航模式，不播报 — 等待用户点击"导航"按钮

    def _on_route_failed(self, error_msg):
        """Valhalla 路线规划失败回调"""
        print(f"[MapWidget] 离线路线规划失败: {error_msg}")
        self._is_rerouting = False  # 重置标志，允许下次重新规划
        self._pending_auto_navigate = False  # 重置自动导航标志，避免下次意外触发
        # 注意：偏航重新规划失败不应停止导航，只提示失败即可
        js = f"showToast('路线规划失败: {error_msg}', 'error');"
        self.web_view.page().runJavaScript(js)
        self.nav_instruction.emit(f"路线规划失败: {error_msg}")

    def _on_nav_updated(self, state):
        """离线导航状态更新回调"""
        if not state or not self._offline_nav_active:
            return
        instruction = state.get("current_instruction", "")
        dist_next = state.get("distance_to_next_maneuver", 0)
        remaining_km = state.get("remaining_distance_km", 0)
        off_route = state.get("off_route", False)
        arrived = state.get("arrived", False)

        if arrived:
            js = "showToast('已到达目的地', 'success');"
            self.web_view.page().runJavaScript(js)
            self.nav_instruction.emit("已到达目的地")
            self._offline_nav_active = False
            return

        print(f"[_on_nav_updated] off_route={off_route}, deviation_count={state.get('deviation_count', 0)}, _is_rerouting={self._is_rerouting}, _dest=({self._dest_lat}, {self._dest_lon})")
        if off_route and state.get("deviation_count", 0) > 0:
            if not self._is_rerouting and self._dest_lat is not None and self._dest_lon is not None:
                self._is_rerouting = True
                print(f"[MapWidget] >>> 触发偏航重新规划: ({self.current_lat}, {self.current_lon}) -> ({self._dest_lat}, {self._dest_lon})")
                self.nav_instruction.emit("您已偏离路线，正在重新规划")
                if self.nav_engine:
                    print(f"[MapWidget] 调用 nav_engine.plan_route()")
                    self.nav_engine.plan_route(
                        self.current_lon, self.current_lat,
                        self._dest_lon, self._dest_lat,
                        costing="bicycle"
                    )
                    print(f"[MapWidget] nav_engine.plan_route() 返回")
                else:
                    print(f"[MapWidget] nav_engine 为 None，无法重新规划")
            else:
                print(f"[MapWidget] 偏航但跳过重规划: _is_rerouting={self._is_rerouting}, _dest_lat={self._dest_lat}, _dest_lon={self._dest_lon}")
                self.nav_instruction.emit("您已偏离路线")
            return

        # 语音播报：1. 相对方向变化（只要有 yaw 数据就播报，不受距离限制）
        rel_dir = state.get("relative_direction", "")
        print(f"[NavUpdate] step={state.get('current_step')}, rel_dir={rel_dir}, last_rel_dir={self._last_rel_dir}, dist_next={dist_next}")
        if rel_dir and rel_dir != self._last_rel_dir:
            self._last_rel_dir = rel_dir
            print(f"[NavUpdate] 播报方向: 骑行路线在你的{rel_dir}")
            self.nav_instruction.emit(f"骑行路线在你的{rel_dir}")

        # 语音播报：2. 转弯指令（只在接近时播报，且不再播报绝对方向如"出发后左转"）
        if instruction and instruction != self._last_nav_instruction:
            if dist_next < 200 or state.get("current_step", 0) == 0:
                self._last_nav_instruction = instruction
                # 只播报距离提示，不播报"出发后左转"这类绝对指令
                if 0 < dist_next < 200:
                    self.nav_instruction.emit(f"前方{dist_next:.0f}米转弯")

    def stop_navigation(self):
        """停止导航"""
        self.web_view.page().runJavaScript("stopNavigation();")
        self.is_navigating = False
        self._offline_nav_active = False
        self._last_nav_instruction = ""
        self._last_rel_dir = ""
        if self.nav_engine:
            self.nav_engine.clear()
        self.navigation_handler.reset()

    def _set_offline_dest_js(self, lat: float, lon: float):
        """JS 回调：在地图上设置目的地标记（不启动导航）"""
        js = f"""
            destPos = [{lon}, {lat}];
            if (destMarker) map.removeLayer(destMarker);
            destMarker = L.marker([{lat}, {lon}], {{
                icon: L.divIcon({{
                    className: '',
                    html: '<div style=\"width:32px;height:32px;background:#e74c3c;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:14px;\">终</div>',
                    iconSize: [32, 32],
                    iconAnchor: [16, 16]
                }})
            }}).addTo(map);
            document.getElementById('searchInput').value = '{lat:.5f},{lon:.5f}';
            showToast('目的地已设置: {lat:.5f},{lon:.5f}', 'success');
        """
        self.web_view.page().runJavaScript(js)

    def get_navigation_handler(self):
        """获取导航处理器"""
        return self.navigation_handler

    def clear_track(self):
        self.web_view.page().runJavaScript("clearAll();")

    def clear_visuals_only(self):
        """只清除地图视觉元素，不停止导航（用于页面切换）"""
        self.web_view.page().runJavaScript("clearVisualsOnly();")

    def load_history_track(self, track_points):
        """
        加载历史轨迹到地图
        track_points: [{"lat": float, "lon": float}, ...]
        """
        if not track_points:
            return
        path_js = str([[p["lat"], p["lon"]] for p in track_points])
        start = track_points[0]
        end = track_points[-1]

        if self._mode == 'offline':
            js = f"""
                clearAll();
                var historyPath = {path_js};
                if (historyPath.length > 0) {{
                    window.historyLine = L.polyline(historyPath, {{
                        color: '#2ecc71',
                        weight: 4,
                        opacity: 0.9
                    }}).addTo(map);

                    window.historyStartMarker = L.marker([{start['lat']}, {start['lon']}], {{
                        icon: L.divIcon({{
                            className: '',
                            html: '<div style=\"width:28px;height:28px;background:#2ecc71;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:12px;\">起</div>',
                            iconSize: [28, 28],
                            iconAnchor: [14, 14]
                        }})
                    }}).addTo(map);
                    window.historyEndMarker = L.marker([{end['lat']}, {end['lon']}], {{
                        icon: L.divIcon({{
                            className: '',
                            html: '<div style=\"width:28px;height:28px;background:#e74c3c;border-radius:50%;border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center;color:white;font-weight:bold;font-size:12px;\">终</div>',
                            iconSize: [28, 28],
                            iconAnchor: [14, 14]
                        }})
                    }}).addTo(map);

                    var bounds = L.latLngBounds(historyPath);
                    setTimeout(function() {{
                        var targetZoom = map.getBoundsZoom(bounds, {{padding: [30, 30]}});
                        if (targetZoom < 13) targetZoom = 13;
                        if (targetZoom > 16) targetZoom = 16;
                        map.fitBounds(bounds, {{padding: [30, 30], maxZoom: 16}});
                        if (map.getZoom() < 13) {{
                            map.setZoom(13);
                        }}
                    }}, 200);
                }}
            """
        else:
            path_js_amap = str([[p["lon"], p["lat"]] for p in track_points])
            js = f"""
                clearAll();
                var historyPath = {path_js_amap};
                if (historyPath.length > 0) {{
                    window.historyLine = new AMap.Polyline({{
                        path: historyPath,
                        strokeColor: '#2ecc71',
                        strokeWeight: 4,
                        strokeOpacity: 0.9,
                        map: map,
                        showDir: true
                    }});

                    window.historyStartMarker = new AMap.Marker({{
                        position: [{start['lon']}, {start['lat']}],
                        map: map,
                        icon: new AMap.Icon({{
                            size: new AMap.Size(24, 24),
                            image: 'https://webapi.amap.com/theme/v1.3/markers/n/start.png',
                            imageSize: new AMap.Size(24, 24)
                        }}),
                        title: '起点'
                    }});

                    window.historyEndMarker = new AMap.Marker({{
                        position: [{end['lon']}, {end['lat']}],
                        map: map,
                        icon: new AMap.Icon({{
                            size: new AMap.Size(24, 24),
                            image: 'https://webapi.amap.com/theme/v1.3/markers/n/end.png',
                            imageSize: new AMap.Size(24, 24)
                        }}),
                        title: '终点'
                    }});

                    // 延迟执行 setFitView，确保 overlay 已渲染
                    setTimeout(function() {{
                        map.setFitView([window.historyLine, window.historyStartMarker, window.historyEndMarker]);
                    }}, 200);
                }}
            """
        self.web_view.page().runJavaScript(js)
