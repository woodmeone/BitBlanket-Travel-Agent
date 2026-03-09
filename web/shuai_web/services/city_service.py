"""City data service for route handlers."""

from __future__ import annotations

from collections.abc import Iterable


def _city(
    city_id: str,
    name: str,
    region: str,
    tags: list[str],
    budget: int,
    seasons: list[str],
    description: str,
    attractions: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "id": city_id,
        "name": name,
        "region": region,
        "tags": tags,
        "avg_budget_per_day": budget,
        "best_seasons": seasons,
        "description": description,
        "attractions": attractions,
    }


class CityService:
    """Encapsulates city list/filter/detail logic."""

    def __init__(self) -> None:
        curated = self._build_curated_cities()
        self._cities: list[dict[str, object]] = curated + self._build_generated_cities(curated)
        self._city_by_id = {str(item["id"]): item for item in self._cities}
        self._city_by_name = {str(item["name"]): item for item in self._cities}

    def list_cities(self, region: str | None = None, tags: str | None = None) -> list[dict[str, object]]:
        result = list(self._cities)

        if region:
            region_value = region.strip()
            result = [item for item in result if item.get("region") == region_value]

        if tags:
            tag_set = {item.strip() for item in tags.split(",") if item.strip()}
            if tag_set:
                result = [
                    item
                    for item in result
                    if any(tag in tag_set for tag in (item.get("tags") or []))
                ]

        return [
            {
                "id": item["id"],
                "name": item["name"],
                "region": item["region"],
                "tags": item["tags"],
            }
            for item in result
        ]

    def find_city(self, city_id: str) -> dict[str, object] | None:
        return self._city_by_id.get(city_id)

    def build_city_detail(self, city: dict[str, object]) -> dict[str, object]:
        city_id = str(city["id"])
        detail = self._city_by_id.get(city_id)
        return dict(detail) if detail else dict(city)

    def build_attractions(self, city_name: str) -> list[dict[str, object]]:
        city = self._city_by_name.get(city_name)
        if city:
            return list(city.get("attractions") or [])
        return self._default_attractions(city_name, ["城市漫步", "美食"])

    def list_regions(self) -> list[str]:
        return sorted({str(item["region"]) for item in self._cities})

    def list_tags(self) -> list[str]:
        tags: set[str] = set()
        for city in self._cities:
            tags.update(city.get("tags") or [])
        return sorted(tags)

    def _build_curated_cities(self) -> list[dict[str, object]]:
        return [
            _city(
                "beijing",
                "北京",
                "华北",
                ["历史文化", "博物馆", "亲子", "城市漫步"],
                880,
                ["春季", "秋季"],
                "北京适合第一次到访中国的大城市旅行者，故宫、中轴线、博物馆群和胡同漫步都很成熟，兼顾经典打卡与深度体验。",
                [
                    {"name": "故宫博物院", "type": "历史景点", "duration": "3-4小时", "ticket": 60},
                    {"name": "国家博物馆", "type": "博物馆", "duration": "2-3小时", "ticket": 0},
                    {"name": "什刹海胡同", "type": "城市漫步", "duration": "2小时", "ticket": 0},
                ],
            ),
            _city(
                "shanghai",
                "上海",
                "华东",
                ["现代都市", "购物", "夜景", "美食", "亲子"],
                980,
                ["春季", "秋季"],
                "上海适合想要高效率体验都市度假的人群，外滩、梧桐区和主题乐园之间切换顺滑，餐饮与住宿选择也很丰富。",
                [
                    {"name": "外滩", "type": "城市地标", "duration": "1-2小时", "ticket": 0},
                    {"name": "上海博物馆东馆", "type": "博物馆", "duration": "2-3小时", "ticket": 0},
                    {"name": "迪士尼度假区", "type": "乐园", "duration": "6-8小时", "ticket": 399},
                ],
            ),
            _city(
                "hangzhou",
                "杭州",
                "华东",
                ["自然风光", "休闲", "城市漫步", "美食", "少走路"],
                720,
                ["春季", "秋季"],
                "杭州的节奏舒服，西湖、茶山和南宋文化线很适合做轻松型旅行，适合情侣、亲子和周末短住。",
                [
                    {"name": "西湖", "type": "自然景观", "duration": "3小时", "ticket": 0},
                    {"name": "灵隐寺", "type": "人文景点", "duration": "2小时", "ticket": 75},
                    {"name": "良渚博物院", "type": "博物馆", "duration": "2小时", "ticket": 0},
                ],
            ),
            _city(
                "chengdu",
                "成都",
                "西南",
                ["美食", "休闲", "熊猫", "亲子", "夜生活"],
                680,
                ["春季", "秋季"],
                "成都适合把吃喝、逛街和慢节奏放在一起安排，城市容错率高，下雨天也不太影响整体体验。",
                [
                    {"name": "成都大熊猫繁育研究基地", "type": "亲子景点", "duration": "3小时", "ticket": 55},
                    {"name": "宽窄巷子", "type": "城市漫步", "duration": "2小时", "ticket": 0},
                    {"name": "三星堆博物馆", "type": "博物馆", "duration": "4小时", "ticket": 72},
                ],
            ),
            _city(
                "chongqing",
                "重庆",
                "西南",
                ["山城", "夜景", "美食", "城市漫步", "年轻人"],
                660,
                ["春季", "秋季"],
                "重庆适合喜欢强烈城市氛围和夜景的人，轨道、索道、江景和火锅的记忆点都很强。",
                [
                    {"name": "洪崖洞", "type": "夜景地标", "duration": "2小时", "ticket": 0},
                    {"name": "李子坝观景平台", "type": "城市打卡", "duration": "1小时", "ticket": 0},
                    {"name": "长江索道", "type": "交通体验", "duration": "1小时", "ticket": 30},
                ],
            ),
            _city(
                "xian",
                "西安",
                "西北",
                ["历史文化", "古都", "美食", "博物馆", "亲子"],
                640,
                ["春季", "秋季"],
                "西安适合想集中感受历史遗产的人，兵马俑、城墙和博物馆线清晰，亲子认知型旅行也很好安排。",
                [
                    {"name": "秦始皇帝陵博物院", "type": "历史景点", "duration": "4小时", "ticket": 120},
                    {"name": "西安城墙", "type": "古建筑", "duration": "2小时", "ticket": 54},
                    {"name": "陕西历史博物馆", "type": "博物馆", "duration": "2-3小时", "ticket": 0},
                ],
            ),
            _city(
                "guangzhou",
                "广州",
                "华南",
                ["美食", "亲子", "城市漫步", "购物", "雨天友好"],
                760,
                ["秋季", "冬季"],
                "广州适合把美食和轻观光结合起来，交通成熟、雨天替代方案多，也适合家庭出行。",
                [
                    {"name": "陈家祠", "type": "人文景点", "duration": "1-2小时", "ticket": 10},
                    {"name": "广州塔", "type": "城市地标", "duration": "2小时", "ticket": 150},
                    {"name": "永庆坊", "type": "城市漫步", "duration": "2小时", "ticket": 0},
                ],
            ),
            _city(
                "shenzhen",
                "深圳",
                "华南",
                ["现代都市", "海滨", "亲子", "乐园", "周末"],
                860,
                ["秋季", "冬季"],
                "深圳适合轻度度假和高效率周末游，海边、公园、乐园和城市商圈切换很方便。",
                [
                    {"name": "深圳湾公园", "type": "海滨散步", "duration": "2小时", "ticket": 0},
                    {"name": "世界之窗", "type": "乐园", "duration": "4-6小时", "ticket": 220},
                    {"name": "华侨城创意园", "type": "文艺街区", "duration": "2小时", "ticket": 0},
                ],
            ),
            _city(
                "xiamen",
                "厦门",
                "华南",
                ["海滨", "文艺", "休闲", "情侣", "少走路"],
                700,
                ["春季", "秋季", "冬季"],
                "厦门适合做轻松海滨假期，鼓浪屿、环岛路和沙坡尾都偏舒服，适合拍照、发呆和慢慢逛。",
                [
                    {"name": "鼓浪屿", "type": "海岛景点", "duration": "4小时", "ticket": 35},
                    {"name": "环岛路", "type": "海滨骑行", "duration": "2小时", "ticket": 0},
                    {"name": "沙坡尾", "type": "文艺街区", "duration": "2小时", "ticket": 0},
                ],
            ),
            _city(
                "sanya",
                "三亚",
                "华南",
                ["海滨", "度假", "亲子", "情侣", "高端酒店"],
                1280,
                ["冬季", "春季"],
                "三亚更适合把酒店度假和海边项目结合起来，想要轻松、少折腾、高松弛感会很合适。",
                [
                    {"name": "亚龙湾", "type": "海滨", "duration": "3小时", "ticket": 0},
                    {"name": "蜈支洲岛", "type": "海岛项目", "duration": "5小时", "ticket": 144},
                    {"name": "太阳湾公路", "type": "风景公路", "duration": "1小时", "ticket": 0},
                ],
            ),
            _city(
                "kunming",
                "昆明",
                "西南",
                ["气候舒适", "自然风光", "周边游", "亲子", "慢节奏"],
                620,
                ["春季", "夏季", "秋季"],
                "昆明适合作为云南旅行的轻松起点，城市本身节奏舒适，向周边延展也很自然。",
                [
                    {"name": "滇池海埂大坝", "type": "自然景观", "duration": "2小时", "ticket": 0},
                    {"name": "云南省博物馆", "type": "博物馆", "duration": "2小时", "ticket": 0},
                    {"name": "石林风景区", "type": "自然景区", "duration": "4小时", "ticket": 130},
                ],
            ),
            _city(
                "harbin",
                "哈尔滨",
                "东北",
                ["冰雪", "俄式风情", "亲子", "冬季限定", "摄影"],
                760,
                ["冬季"],
                "哈尔滨在冬天的辨识度非常高，冰雪大世界、中央大街和松花江氛围很强，适合冬游体验。",
                [
                    {"name": "冰雪大世界", "type": "冬季乐园", "duration": "4小时", "ticket": 328},
                    {"name": "中央大街", "type": "城市漫步", "duration": "2小时", "ticket": 0},
                    {"name": "索菲亚教堂广场", "type": "地标建筑", "duration": "1小时", "ticket": 0},
                ],
            ),
        ]

    def _build_generated_cities(self, curated: Iterable[dict[str, object]]) -> list[dict[str, object]]:
        curated_names = {str(item["name"]) for item in curated}
        groups: list[dict[str, object]] = [
            {
                "region": "华北",
                "budget": 560,
                "tags": ["历史文化", "周末", "城市漫步"],
                "cities": ["天津", "石家庄", "保定", "承德", "秦皇岛", "大同", "太原", "呼和浩特", "张家口", "廊坊"],
            },
            {
                "region": "华东",
                "budget": 650,
                "tags": ["城市漫步", "美食", "周末", "雨天友好"],
                "cities": ["南京", "苏州", "无锡", "扬州", "绍兴", "宁波", "温州", "嘉兴", "湖州", "台州", "合肥", "黄山", "福州", "泉州", "漳州", "景德镇", "南昌", "青岛", "济南", "烟台", "威海"],
            },
            {
                "region": "华南",
                "budget": 720,
                "tags": ["海滨", "美食", "度假", "亲子"],
                "cities": ["珠海", "佛山", "东莞", "中山", "惠州", "汕头", "湛江", "北海", "南宁", "桂林", "柳州", "海口", "文昌", "陵水", "万宁", "汕尾", "潮州"],
            },
            {
                "region": "华中",
                "budget": 560,
                "tags": ["美食", "历史文化", "城市漫步", "周末"],
                "cities": ["武汉", "长沙", "张家界", "岳阳", "襄阳", "宜昌", "洛阳", "开封", "郑州", "南阳", "恩施", "神农架", "株洲"],
            },
            {
                "region": "西南",
                "budget": 620,
                "tags": ["自然风光", "慢节奏", "美食", "摄影"],
                "cities": ["贵阳", "遵义", "安顺", "凯里", "都匀", "六盘水", "大理", "丽江", "香格里拉", "西双版纳", "腾冲", "芒市", "普洱", "乐山", "自贡", "宜宾", "泸州"],
            },
            {
                "region": "西北",
                "budget": 680,
                "tags": ["历史文化", "自然风光", "摄影", "亲子"],
                "cities": ["兰州", "敦煌", "嘉峪关", "张掖", "天水", "西宁", "银川", "中卫", "乌鲁木齐", "喀什", "伊宁", "库尔勒", "吐鲁番", "阿勒泰"],
            },
            {
                "region": "东北",
                "budget": 620,
                "tags": ["自然风光", "冰雪", "森林", "避暑"],
                "cities": ["长春", "吉林", "延吉", "长白山", "沈阳", "大连", "本溪", "丹东", "齐齐哈尔", "牡丹江", "佳木斯", "漠河"],
            },
            {
                "region": "港澳台",
                "budget": 980,
                "tags": ["都市度假", "购物", "美食", "亲子", "海滨"],
                "cities": ["香港", "澳门", "台北", "高雄", "台中", "花莲", "垦丁", "台南"],
            },
            {
                "region": "海外",
                "budget": 1880,
                "tags": ["出境游", "海岛", "城市地标", "度假", "购物"],
                "cities": ["东京", "大阪", "京都", "札幌", "福冈", "首尔", "釜山", "新加坡", "曼谷", "清迈", "普吉", "吉隆坡", "槟城", "河内", "岘港", "芽庄", "巴厘岛", "雅加达", "迪拜", "伊斯坦布尔", "巴黎", "伦敦", "罗马", "巴塞罗那", "阿姆斯特丹", "苏黎世", "纽约", "洛杉矶", "旧金山", "温哥华", "悉尼", "墨尔本"],
            },
        ]

        generated: list[dict[str, object]] = []
        index = 1
        for group in groups:
            for name in group["cities"]:
                if name in curated_names:
                    continue
                tags = list(group["tags"])
                city_id = f"city-{index:03d}"
                generated.append(
                    _city(
                        city_id,
                        name,
                        str(group["region"]),
                        tags,
                        int(group["budget"]),
                        self._default_best_seasons(str(group["region"]), tags),
                        self._default_description(name, str(group["region"]), tags),
                        self._default_attractions(name, tags),
                    )
                )
                index += 1
        return generated

    @staticmethod
    def _default_best_seasons(region: str, tags: list[str]) -> list[str]:
        if "冰雪" in tags:
            return ["冬季"]
        if "海滨" in tags or "海岛" in tags:
            return ["春季", "秋季", "冬季"]
        if region in {"西北", "东北"}:
            return ["夏季", "秋季"]
        return ["春季", "秋季"]

    @staticmethod
    def _default_description(name: str, region: str, tags: list[str]) -> str:
        highlights = "、".join(tags[:3]) if tags else "旅行体验"
        return f"{name}位于{region}，适合以{highlights}为核心来安排行程，做 2-4 天的轻量旅行或中转延展都比较合适。"

    @staticmethod
    def _default_attractions(name: str, tags: list[str]) -> list[dict[str, object]]:
        if "海滨" in tags or "海岛" in tags:
            return [
                {"name": f"{name}滨海步道", "type": "海滨散步", "duration": "1-2小时", "ticket": 0},
                {"name": f"{name}城市观景点", "type": "城市地标", "duration": "1小时", "ticket": 0},
                {"name": f"{name}海鲜市场", "type": "美食体验", "duration": "1-2小时", "ticket": 0},
            ]
        if "历史文化" in tags:
            return [
                {"name": f"{name}博物馆", "type": "博物馆", "duration": "2小时", "ticket": 0},
                {"name": f"{name}古城步行区", "type": "历史街区", "duration": "2小时", "ticket": 0},
                {"name": f"{name}城市地标", "type": "经典打卡", "duration": "1小时", "ticket": 30},
            ]
        if "自然风光" in tags:
            return [
                {"name": f"{name}景观公园", "type": "自然景观", "duration": "2小时", "ticket": 0},
                {"name": f"{name}郊野风景区", "type": "自然景区", "duration": "3小时", "ticket": 80},
                {"name": f"{name}城市观景平台", "type": "摄影点", "duration": "1小时", "ticket": 20},
            ]
        return [
            {"name": f"{name}核心街区", "type": "城市漫步", "duration": "2小时", "ticket": 0},
            {"name": f"{name}本地美食集合区", "type": "美食体验", "duration": "2小时", "ticket": 0},
            {"name": f"{name}城市博物馆", "type": "博物馆", "duration": "2小时", "ticket": 0},
        ]
