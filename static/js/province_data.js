/**
 * 中国省份数据 - 动态加载城市
 * 只保留省份列表，城市和区县通过API动态获取
 */

const PROVINCE_LIST = [
    { key: 'beijing', name: '北京' },
    { key: 'tianjin', name: '天津' },
    { key: 'hebei', name: '河北' },
    { key: 'shanxi', name: '山西' },
    { key: 'neimenggu', name: '内蒙古' },
    { key: 'liaoning', name: '辽宁' },
    { key: 'jilin', name: '吉林' },
    { key: 'heilongjiang', name: '黑龙江' },
    { key: 'shanghai', name: '上海' },
    { key: 'jiangsu', name: '江苏' },
    { key: 'zhejiang', name: '浙江' },
    { key: 'anhui', name: '安徽' },
    { key: 'fujian', name: '福建' },
    { key: 'jiangxi', name: '江西' },
    { key: 'shandong', name: '山东' },
    { key: 'henan', name: '河南' },
    { key: 'hubei', name: '湖北' },
    { key: 'hunan', name: '湖南' },
    { key: 'guangdong', name: '广东' },
    { key: 'guangxi', name: '广西' },
    { key: 'hainan', name: '海南' },
    { key: 'chongqing', name: '重庆' },
    { key: 'sichuan', name: '四川' },
    { key: 'guizhou', name: '贵州' },
    { key: 'yunnan', name: '云南' },
    { key: 'xizang', name: '西藏' },
    { key: 'shaanxi', name: '陕西' },
    { key: 'gansu', name: '甘肃' },
    { key: 'qinghai', name: '青海' },
    { key: 'ningxia', name: '宁夏' },
    { key: 'xinjiang', name: '新疆' },
    { key: 'taiwan', name: '台湾' },
    { key: 'xianggang', name: '香港' },
    { key: 'aomen', name: '澳门' }
];

// 城市中文名到拼音键的映射（常用城市）
const CITY_TO_PINYIN = {
    '北京': 'beijing', '上海': 'shanghai', '天津': 'tianjin', '重庆': 'chongqing',
    '广州': 'guangzhou', '深圳': 'shenzhen', '珠海': 'zhuhai', '东莞': 'dongguan', '佛山': 'foshan',
    '南京': 'nanjing', '苏州': 'suzhou', '无锡': 'wuxi', '常州': 'changzhou', '徐州': 'xuzhou', '南通': 'nantong', '扬州': 'yangzhou', '盐城': 'yancheng', '连云港': 'lianyungang', '淮安': 'huaian', '泰州': 'taizhou', '镇江': 'zhenjiang', '宿迁': 'suqian',
    '杭州': 'hangzhou', '宁波': 'ningbo', '温州': 'wenzhou', '嘉兴': 'jiaxing', '湖州': 'huzhou', '绍兴': 'shaoxing', '金华': 'jinhua', '衢州': 'quzhou', '舟山': 'zhoushan', '台州': 'taizhou', '丽水': 'lishui',
    '合肥': 'hefei', '芜湖': 'wuhu', '蚌埠': 'bangbu', '淮南': 'huainan', '马鞍山': 'maanshan', '淮北': 'huaibei', '铜陵': 'tongling', '安庆': 'anqing', '黄山': 'huangshan', '滁州': 'chuzhou', '阜阳': 'fuyang', '宿州': 'suzhou', '六安': 'liuan', '亳州': 'bozhou', '池州': 'chizhou', '宣城': 'xuancheng',
    '福州': 'fuzhou', '厦门': 'xiamen', '泉州': 'quanzhou', '漳州': 'zhangzhou', '莆田': 'putian', '三明': 'sanming', '南平': 'nanping', '龙岩': 'longyan', '宁德': 'ningde',
    '南昌': 'nanchang', '景德镇': 'jingdezhen', '九江': 'jiujiang', '赣州': 'ganzhou', '吉安': 'jian', '宜春': 'yichun', '抚州': 'fuzhou', '上饶': 'shangrao', '萍乡': 'pingxiang', '新余': 'xinyu', '鹰潭': 'yingtan',
    '济南': 'jinan', '青岛': 'qingdao', '烟台': 'yantai', '潍坊': 'weifang', '威海': 'weihai', '淄博': 'zibo', '枣庄': 'zaozhuang', '东营': 'dongying', '济宁': 'jining', '泰安': 'taian', '日照': 'rizhao', '莱芜': 'laiwu', '临沂': 'linyi', '德州': 'dezhou', '聊城': 'liaocheng', '滨州': 'binzhou', '菏泽': 'heze',
    '郑州': 'zhengzhou', '洛阳': 'luoyang', '开封': 'kaifeng', '平顶山': 'pingdingshan', '安阳': 'anyang', '鹤壁': 'hebi', '新乡': 'xinxiang', '焦作': 'jiaozuo', '濮阳': 'puyang', '许昌': 'xuchang', '漯河': 'luohe', '三门峡': 'sanmenxia', '南阳': 'nanyang', '商丘': 'shangqiu', '信阳': 'xinyang', '周口': 'zhoukou', '驻马店': 'zhumadian', '济源': 'jiyuan',
    '武汉': 'wuhan', '黄石': 'huangshi', '十堰': 'shiyan', '宜昌': 'yichang', '襄阳': 'xiangyang', '鄂州': 'ezhou', '荆门': 'jingmen', '孝感': 'xiaogan', '荆州': 'jingzhou', '黄冈': 'huanggang', '咸宁': 'xianning', '随州': 'suizhou', '恩施': 'enshi', '仙桃': 'xiantao', '潜江': 'qianjiang', '天门': 'tianmen', '神农架': 'shennongjia',
    '长沙': 'changsha', '株洲': 'zhuzhou', '湘潭': 'xiangtan', '衡阳': 'hengyang', '邵阳': 'shaoyang', '岳阳': 'yueyang', '常德': 'changde', '张家界': 'zhangjiajie', '益阳': 'yiyang', '郴州': 'chenzhou', '永州': 'yongzhou', '怀化': 'huaihua', '娄底': 'loudi', '湘西': 'xiangxi',
    '广州': 'guangzhou', '深圳': 'shenzhen', '珠海': 'zhuhai', '东莞': 'dongguan', '佛山': 'foshan', '中山': 'zhongshan', '惠州': 'huizhou', '江门': 'jiangmen', '湛江': 'zhanjiang', '茂名': 'maoming', '肇庆': 'zhaoqing', '梅州': 'meizhou', '汕尾': 'shanwei', '河源': 'heyuan', '阳江': 'yangjiang', '清远': 'qingyuan', '韶关': 'shaoguan', '揭阳': 'jieyang', '潮州': 'chaozhou', '汕头': 'shantou', '云浮': 'yunfu',
    '南宁': 'nanning', '柳州': 'liuzhou', '桂林': 'guilin', '梧州': 'wuzhou', '北海': 'beihai', '防城港': 'fangchenggang', '钦州': 'qinzhou', '贵港': 'guigang', '玉林': 'yulin', '百色': 'baise', '贺州': 'hezhou', '河池': 'hechi', '来宾': 'laibin', '崇左': 'chongzuo',
    '海口': 'haikou', '三亚': 'sanya', '三沙': 'sansha', '儋州': 'danzhou',
    '成都': 'chengdu', '绵阳': 'mianyang', '自贡': 'zigong', '攀枝花': 'panzhihua', '泸州': 'luzhou', '德阳': 'deyang', '广元': 'guangyuan', '遂宁': 'suining', '内江': 'neijiang', '乐山': 'leshan', '南充': 'nanchong', '眉山': 'meishan', '宜宾': 'yibin', '广安': 'guangan', '达州': 'dazhou', '雅安': 'yaan', '巴中': 'bazhong', '资阳': 'ziyang', '阿坝': 'aba', '甘孜': 'ganzi', '凉山': 'liangshan',
    '贵阳': 'guiyang', '遵义': 'zunyi', '六盘水': 'liupanshui', '安顺': 'anshun', '毕节': 'bijie', '铜仁': 'tongren', '黔西南': 'qianxinna', '黔东南': 'qiandongnan', '黔南': 'qiannan',
    '昆明': 'kunming', '曲靖': 'qujing', '玉溪': 'yuxi', '保山': 'baoshan', '昭通': 'zhaotong', '丽江': 'lijiang', '普洱': 'puer', '临沧': 'lincang', '楚雄': 'chuxiong', '红河': 'honghe', '文山': 'wenshan', '西双版纳': 'xishuangbanna', '大理': 'dali', '德宏': 'dehong', '怒江': 'nujiang', '迪庆': 'diqing',
    '拉萨': 'lhasa', '日喀则': 'rikaze', '昌都': 'changdu', '林芝': 'linzhi', '山南': 'shannan', '那曲': 'naqu', '阿里': 'ali',
    '西安': 'xian', '宝鸡': 'baoji', '咸阳': 'xianyang', '铜川': 'tongchuan', '渭南': 'weinan', '延安': 'yanan', '汉中': 'hanzhong', '榆林': 'yulin', '安康': 'ankang', '商洛': 'shangluo',
    '兰州': 'lanzhou', '嘉峪关': 'jiayuguan', '金昌': 'jinchang', '白银': 'baiyin', '天水': 'tianshui', '武威': 'wuwei', '张掖': 'zhangye', '平凉': 'pingliang', '酒泉': 'jiuquan', '庆阳': 'qingyang', '定西': 'dingxi', '陇南': 'longnan', '临夏': 'linxia', '甘南': 'gannan',
    '西宁': 'xining', '海东': 'haidong', '海北': 'haibei', '黄南': 'huangnan', '海南州': 'hainanzhou', '果洛': 'guoluo', '玉树': 'yushu', '海西': 'haixi',
    '银川': 'yinchuan', '石嘴山': 'shizuishan', '吴忠': 'wuzhong', '固原': 'guyuan', '中卫': 'zhongwei',
    '乌鲁木齐': 'urumqi', '克拉玛依': 'kelamayi', '吐鲁番': 'tulufan', '哈密': 'hami', '昌吉': 'changji', '博尔塔拉': 'boertala', '巴音郭楞': 'bayinguoleng', '阿克苏': 'akesu', '克孜勒苏': 'kezilesu', '喀什': 'kashi', '和田': 'hetian', '伊犁': 'yili', '塔城': 'tacheng', '阿勒泰': 'aletai',
    '呼和浩特': 'hohhot', '包头': 'baotou', '乌海': 'wuhai', '赤峰': 'chifeng', '通辽': 'tongliao', '鄂尔多斯': 'eerduosi', '呼伦贝尔': 'hulunbeier', '巴彦淖尔': 'bayannaoer', '乌兰察布': 'wulanchabu', '兴安': 'xingan', '锡林郭勒': 'xilinguole', '阿拉善': 'alashan',
    '沈阳': 'shenyang', '大连': 'dalian', '鞍山': 'anshan', '抚顺': 'fushun', '本溪': 'benxi', '丹东': 'dandong', '锦州': 'jinzhou', '营口': 'yingkou', '阜新': 'fuxin', '辽阳': 'liaoyang', '盘锦': 'panjin', '铁岭': 'tieling', '朝阳': 'chaoyang', '葫芦岛': 'huludao',
    '长春': 'changchun', '吉林': 'jilin', '四平': 'siping', '辽源': 'liaoyuan', '通化': 'tonghua', '白山': 'baishan', '松原': 'songyuan', '白城': 'baicheng', '延边': 'yanbian',
    '哈尔滨': 'harbin', '齐齐哈尔': 'qiqihar', '鸡西': 'jixi', '鹤岗': 'hegang', '双鸭山': 'shuangyashan', '大庆': 'daqing', '伊春': 'yichun', '佳木斯': 'jiamusi', '七台河': 'qitaihe', '牡丹江': 'mudanjiang', '黑河': 'heihe', '绥化': 'suihua', '大兴安岭': 'daxinganling',
    '台北': 'taipei', '高雄': 'kaohsiung', '基隆': 'keelung', '新北': 'xinbei', '桃园': 'taoyuan', '台中': 'taichung', '台南': 'tainan', '新竹': 'hsinchu',
    '香港': 'hongkong', '澳门': 'macau'
};

// 城市拼音到中文的映射
const PINYIN_TO_CITY = {};
for (const city in CITY_TO_PINYIN) {
    PINYIN_TO_CITY[CITY_TO_PINYIN[city]] = city;
}

// 导出到window对象
window.PROVINCE_LIST = PROVINCE_LIST;
window.CITY_TO_PINYIN = CITY_TO_PINYIN;
window.PINYIN_TO_CITY = PINYIN_TO_CITY;
