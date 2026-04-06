"""
数据库模块 - 使用SQLite替代CSV进行数据存储
提供线程安全的数据库连接和操作函数
"""

import sqlite3
import csv
import os
import shutil
import threading
from datetime import datetime

# 数据库文件路径
DB_FILE = '/home/ubuntu/jlu8/alumni.db'

# 中国城市经纬度坐标表（部分常用城市）
CHINA_CITY_COORDS = {
    # 直辖市
    '北京': '39.9042,116.4074',
    '上海': '31.2304,121.4737',
    '天津': '39.3434,117.3616',
    '重庆': '29.5630,106.5516',

    # 省会城市
    '长春': '43.8171,125.3235',
    '长沙': '28.2282,112.9388',
    '成都': '30.5728,104.0668',
    '福州': '26.0745,119.2965',
    '广州': '23.1291,113.2644',
    '贵阳': '26.6470,106.6302',
    '哈尔滨': '45.8038,126.5350',
    '杭州': '30.2741,120.1551',
    '合肥': '31.8206,117.2272',
    '呼和浩特': '40.8414,111.7492',
    '济南': '36.6512,117.1201',
    '昆明': '25.0406,102.7129',
    '兰州': '36.0611,103.8343',
    '拉萨': '29.6500,91.1000',
    '南宁': '22.8170,108.3665',
    '南京': '32.0603,118.7969',
    '南昌': '28.6829,115.8579',
    '沈阳': '41.8057,123.4328',
    '石家庄': '38.0428,114.5149',
    '太原': '37.8706,112.5489',
    '乌鲁木齐': '43.8256,87.6168',
    '武汉': '30.5928,114.3055',
    '西安': '34.3416,108.9398',
    '咸阳': '34.3296,108.7093',
    '西宁': '36.6232,101.7780',
    '郑州': '34.7466,113.6253',

    # 计划单列市
    '大连': '38.9140,121.6147',
    '青岛': '36.0671,120.3826',
    '宁波': '29.8683,121.5440',
    '厦门': '24.4798,118.0894',
    '深圳': '22.5431,114.0579',
    '成都': '30.5728,104.0668',

    # 地级市（部分）
    '安庆': '30.5436,117.0634',
    '蚌埠': '32.9167,117.3888',
    '保定': '38.8738,115.4648',
    '宝鸡': '34.3619,107.2373',
    '包头': '40.6571,109.8403',
    '北海': '21.4735,109.1193',
    '沧州': '38.3037,116.8387',
    '常德': '29.0319,111.6985',
    '常州': '31.8106,119.9740',
    '潮州': '23.6567,116.6226',
    '承德': '40.9513,117.9631',
    '赤峰': '42.2585,118.8867',
    '楚雄': '25.0453,101.5280',
    '大理': '25.6065,100.2676',
    '大庆': '46.5907,125.1035',
    '大同': '40.0903,113.2960',
    '德阳': '31.1270,104.3979',
    '德州': '37.4356,116.3071',
    '东莞': '23.0489,113.7447',
    '东营': '37.4346,118.6749',
    '鄂尔多斯': '39.6086,109.7813',
    '峨眉山': '29.6021,103.4851',
    '佛山': '23.0218,113.1219',
    '抚顺': '41.8807,123.9573',
    '阜新': '42.0211,121.6489',
    '阜阳': '32.8908,115.8142',
    '赣州': '25.8453,114.9332',
    '格尔木': '36.4175,94.9043',
    '桂林': '25.2738,110.2900',
    '贵阳': '26.6470,106.6302',
    '桂林': '25.2738,110.2900',
    '海口': '20.0444,110.3498',
    '海拉尔': '49.2122,119.7657',
    '邯郸': '36.6258,114.5391',
    '杭州': '30.2741,120.1551',
    '菏泽': '35.2333,115.4412',
    '衡水': '37.7392,115.6708',
    '衡阳': '26.8930,112.5719',
    '红河': '23.3639,103.3755',
    '葫芦岛': '40.7106,120.8370',
    '湖州': '30.8922,120.0930',
    '淮南': '32.6259,116.9999',
    '淮安': '33.5517,119.0153',
    '淮北': '33.9557,116.7977',
    '黄石': '30.1996,115.0389',
    '惠州': '23.1115,114.4152',
    '鸡西': '45.2953,130.9694',
    '吉林': '43.8384,126.5497',
    '济南': '36.6512,117.1201',
    '济宁': '35.4143,116.5871',
    '佳木斯': '46.8131,130.3184',
    '嘉兴': '30.7522,120.7551',
    '九江': '29.7046,116.0018',
    '酒泉': '39.7436,98.4943',
    '开封': '34.7971,114.3414',
    '康定': '30.0489,101.9644',
    '克拉玛依': '45.5798,84.8892',
    '库尔勒': '41.7259,86.1746',
    '昆明': '25.0406,102.7129',
    '昆山': '31.3846,120.9755',
    '廊坊': '39.5380,116.6837',
    '乐山': '29.5521,103.7657',
    '丽江': '26.8557,100.2278',
    '丽水': '28.4672,119.9230',
    '连云港': '34.5967,119.2216',
    '辽阳': '41.2686,123.1735',
    '辽源': '42.8878,125.1439',
    '临汾': '36.0881,111.5190',
    '临沂': '35.1041,118.3566',
    '柳州': '24.3265,109.4286',
    '六安': '31.7349,116.5088',
    '六盘水': '26.5942,104.8334',
    '龙岩': '25.0757,117.0176',
    '娄底': '27.6982,111.9943',
    '泸州': '28.8717,105.4423',
    '洛阳': '34.6197,112.4540',
    '漯河': '33.5813,114.0166',
    '马鞍山': '31.6701,118.5073',
    '茂名': '21.6629,110.9254',
    '眉山': '30.0493,103.8486',
    '梅州': '24.2883,116.1176',
    '绵阳': '31.4676,104.6796',
    '牡丹江': '44.5512,129.6329',
    '内江': '29.5801,105.0583',
    '宁波': '29.8683,121.5440',
    '南充': '30.8025,106.1107',
    '南平': '26.6418,118.1777',
    '南通': '32.0146,120.8645',
    '南阳': '32.9987,112.5292',
    '乌兰浩特': '46.0769,122.0683',
    '乌海': '39.6550,106.7948',
    '无锡': '31.4912,120.3119',
    '吴江': '30.9748,120.6349',
    '芜湖': '31.3529,118.4339',
    '梧州': '23.4769,111.2791',
    '厦门': '24.4798,118.0894',
    '西安': '34.3416,108.9398',
    '咸阳': '34.3296,108.7093',
    '西宁': '36.6232,101.7780',
    '锡林浩特': '43.9333,116.0467',
    '襄阳': '32.0091,112.1226',
    '孝感': '30.9279,113.9268',
    '新疆': '43.8256,87.6168',
    '兴安盟': '46.0769,122.0683',
    '徐州': '34.2044,117.2859',
    '许昌': '34.0357,113.8526',
    '宣城': '30.9405,118.7586',
    '雅安': '29.9805,103.0010',
    '烟台': '37.4639,121.4481',
    '延安': '36.5853,109.4898',
    '延边': '42.8913,129.5093',
    '盐城': '33.3497,120.1633',
    '扬州': '32.3912,119.4210',
    '阳江': '21.8576,111.9826',
    '阳泉': '37.8574,113.5808',
    '伊春': '47.7276,128.8413',
    '伊宁': '43.9219,81.3177',
    '宜宾': '28.7518,104.6418',
    '宜昌': '30.6918,111.2867',
    '宜春': '27.8136,114.4163',
    '益阳': '28.5539,112.3553',
    '营口': '40.6658,122.2351',
    '永州': '26.4205,111.6134',
    '榆林': '38.2852,109.7348',
    '玉林': '22.6540,110.1811',
    '玉溪': '24.3518,102.5457',
    '岳阳': '29.3570,113.1286',
    '云浮': '22.9375,112.0445',
    '运城': '35.0268,111.0070',
    '枣庄': '34.8107,117.3237',
    '湛江': '21.2707,110.3594',
    '张家界': '29.1170,110.4792',
    '张家口': '40.7677,114.8863',
    '张掖': '38.9259,100.4493',
    '漳州': '24.5093,117.6471',
    '昭通': '27.3436,103.7172',
    '肇庆': '23.0469,112.4654',
    '镇江': '32.1874,119.4248',
    '中山': '22.5176,113.3926',
    '中卫': '37.5142,105.1966',
    '舟山': '29.9853,122.1072',
    '周口': '33.6254,114.7020',
    '珠海': '22.2710,113.5767',
    '驻马店': '32.9807,114.0244',
    '株洲': '27.8406,113.1340',
    '资阳': '30.1283,104.6278',
    '淄博': '36.8131,118.0548',
    '自贡': '29.3392,104.7794',
    '遵义': '27.7256,106.9272',

    # 省份简称（用于匹配籍贯）
    '黑龙江': '47.7516,127.5759',
    '哈尔滨': '45.8038,126.5350',
    '吉林': '43.8171,125.3235',
    '辽宁': '41.8057,123.4328',
    '河北': '38.0428,114.5149',
    '山西': '37.8706,112.5489',
    '陕西': '34.3416,108.9398',
    '甘肃': '36.0611,103.8343',
    '青海': '36.6232,101.7780',
    '四川': '30.5728,104.0668',
    '云南': '25.0406,102.7129',
    '贵州': '26.6470,106.6302',
    '广东': '23.1291,113.2644',
    '广西': '22.8170,108.3665',
    '海南': '20.0444,110.3498',
    '河南': '34.7466,113.6253',
    '山东': '36.6512,117.1201',
    '江苏': '32.0603,118.7969',
    '安徽': '31.8206,117.2272',
    '浙江': '30.2741,120.1551',
    '福建': '26.0745,119.2965',
    '江西': '28.6829,115.8579',
    '湖南': '28.2282,112.9388',
    '湖北': '30.5928,114.3055',
    '内蒙古': '40.8414,111.7492',
    '宁夏': '38.4872,106.2309',
    '新疆': '43.8256,87.6168',
    '西藏': '29.6500,91.1000',
    '台湾': '25.0330,121.5654',
}

# 区县级坐标（更精确的位置）
CHINA_DISTRICT_COORDS = {
    # 深圳
    '深圳市': {
        '福田区': '22.5291,114.0511',
        '罗湖区': '22.5431,114.1023',
        '南山区': '22.5255,113.9535',
        '宝安区': '22.5279,113.9299',
        '龙岗区': '22.6035,114.1471',
        '龙华区': '22.7015,114.0455',
        '坪山区': '22.6815,114.3515',
        '光明区': '22.7815,113.9515',
        '盐田区': '22.5615,114.2515',
        '大鹏新区': '22.5815,114.4815',
    },
    # 广州
    '广州市': {
        '天河区': '23.1291,113.3611',
        '越秀区': '23.1291,113.2611',
        '海珠区': '23.0891,113.2611',
        '荔湾区': '23.1291,113.1611',
        '白云区': '23.1691,113.2611',
        '黄埔区': '23.1091,113.4611',
        '番禺区': '22.9891,113.3611',
        '花都区': '23.3691,113.1611',
        '南沙区': '22.7891,113.4611',
        '从化区': '23.6891,113.5611',
        '增城区': '23.2891,113.8611',
    },
    # 北京
    '北京市': {
        '东城区': '39.9042,116.4074',
        '西城区': '39.9042,116.3674',
        '朝阳区': '39.9042,116.4574',
        '丰台区': '39.8542,116.2874',
        '石景山区': '39.9042,116.2274',
        '海淀区': '39.9042,116.3174',
        '门头沟区': '39.9042,116.1074',
        '房山区': '39.7542,116.1474',
        '通州区': '39.9042,116.6574',
        '顺义区': '40.0542,116.6574',
        '昌平区': '40.2042,116.2574',
        '大兴区': '39.7542,116.3574',
        '怀柔区': '40.3542,116.6574',
        '平谷区': '40.1542,117.1574',
        '密云区': '40.3542,116.8574',
        '延庆区': '40.4542,115.9574',
    },
    # 上海
    '上海市': {
        '黄浦区': '31.2304,121.4737',
        '徐汇区': '31.2004,121.4437',
        '长宁区': '31.2204,121.4137',
        '静安区': '31.2304,121.4537',
        '普陀区': '31.2504,121.4037',
        '虹口区': '31.2404,121.4937',
        '杨浦区': '31.2704,121.5237',
        '闵行区': '31.1204,121.3737',
        '宝山区': '31.4204,121.4937',
        '嘉定区': '31.3804,121.2737',
        '浦东新区': '31.2304,121.5437',
        '金山区': '30.7804,121.1537',
        '松江区': '31.0304,121.2437',
        '青浦区': '31.1504,121.1237',
        '奉贤区': '30.9204,121.4737',
        '崇明区': '31.6204,121.4737',
    },
    # 成都
    '成都市': {
        '锦江区': '30.5728,104.0668',
        '青羊区': '30.5728,104.0268',
        '金牛区': '30.5728,104.0068',
        '武侯区': '30.5728,104.0468',
        '成华区': '30.6128,104.0868',
        '龙泉驿区': '30.6728,104.2268',
        '青白江区': '30.5728,103.9468',
        '新都区': '30.8228,104.0468',
        '温江区': '30.5728,103.8668',
        '双流区': '30.4728,103.9668',
        '郫都区': '30.7528,103.8868',
        '都江堰市': '30.9728,103.6268',
        '彭州市': '30.9728,103.9268',
        '邛崃市': '30.4228,103.4668',
        '崇州市': '30.6728,103.6868',
        '简阳市': '30.3728,104.5468',
    },
    # 武汉
    '武汉市': {
        '江岸区': '30.5928,114.3055',
        '江汉区': '30.5928,114.2855',
        '硚口区': '30.5928,114.2655',
        '汉阳区': '30.5528,114.2655',
        '武昌区': '30.5728,114.3055',
        '青山区': '30.6328,114.3855',
        '洪山区': '30.5528,114.3455',
        '东西湖区': '30.6228,114.1455',
        '汉南区': '30.3028,114.0855',
        '蔡甸区': '30.5828,113.9655',
        '江夏区': '30.3528,114.3255',
        '黄陂区': '30.8528,114.3655',
        '新洲区': '30.8528,114.5455',
    },
    # 南京
    '南京市': {
        '玄武区': '32.0603,118.7969',
        '秦淮区': '32.0003,118.7969',
        '建邺区': '32.0603,118.7569',
        '鼓楼区': '32.0603,118.7369',
        '浦口区': '32.0603,118.6969',
        '栖霞区': '32.1203,118.8569',
        '雨花台区': '32.0003,118.7569',
        '江宁区': '31.9003,118.8569',
        '六合区': '32.3003,118.8369',
        '溧水区': '31.6503,119.0369',
        '高淳区': '31.3503,118.8769',
    },
    # 杭州
    '杭州市': {
        '上城区': '30.2741,120.1551',
        '下城区': '30.2741,120.1751',
        '江干区': '30.2741,120.1951',
        '拱墅区': '30.2941,120.1351',
        '西湖区': '30.2541,120.1351',
        '滨江区': '30.2141,120.2151',
        '萧山区': '30.1741,120.2551',
        '余杭区': '30.2941,120.0751',
        '富阳区': '30.0541,119.9551',
        '临安区': '30.2341,119.7251',
        '桐庐县': '29.8541,119.6551',
        '淳安县': '29.6541,119.0551',
    },
    # 西安
    '西安市': {
        '新城区': '34.3416,108.9398',
        '碑林区': '34.3416,108.9198',
        '莲湖区': '34.3116,108.9398',
        '灞桥区': '34.2816,108.9998',
        '未央区': '34.3116,108.8998',
        '雁塔区': '34.2116,108.9398',
        '阎良区': '34.6516,109.2398',
        '临潼区': '34.3816,109.2198',
        '长安区': '34.1616,108.9398',
        '高陵区': '34.5316,109.0398',
        '鄠邑区': '34.0616,108.6598',
        '蓝田县': '34.1616,109.3398',
        '周至县': '34.1616,108.2198',
    },
    # 重庆
    '重庆市': {
        '万州区': '30.8085,108.4085',
        '涪陵区': '29.7085,107.4085',
        '渝中区': '29.5630,106.5516',
        '大渡口区': '29.4830,106.4816',
        '江北区': '29.5630,106.5716',
        '沙坪坝区': '29.5630,106.4516',
        '九龙坡区': '29.5030,106.5116',
        '南岸区': '29.5230,106.5616',
        '北碚区': '29.8230,106.4416',
        '綦江区': '29.0230,106.6516',
        '大足区': '29.7030,105.7516',
        '渝北区': '29.5630,106.6316',
        '巴南区': '29.3830,106.5516',
        '黔江区': '29.5330,108.7516',
        '长寿区': '29.8530,107.0516',
        '江津区': '29.3530,106.2516',
        '合川区': '29.9030,106.2516',
        '永川区': '29.3530,105.9516',
        '南川区': '29.1530,107.0516',
        '璧山区': '29.5830,106.1516',
        '铜梁区': '29.8030,106.0516',
        '潼南区': '30.1530,105.8516',
        '荣昌区': '29.4530,105.5516',
        '开州区': '31.1530,108.3516',
        '梁平区': '30.6530,107.8516',
        '武隆区': '29.3530,107.7516',
    },
    # 苏州
    '苏州市': {
        '姑苏区': '31.8106,119.9740',
        '虎丘区': '31.8106,120.0540',
        '吴中区': '31.2606,120.0540',
        '相城区': '31.4106,120.0640',
        '吴江区': '31.1606,120.0540',
        '苏州工业园区': '31.3106,120.0740',
        '常熟市': '31.8106,120.7540',
        '张家港市': '31.9106,120.5540',
        '昆山市': '31.4106,120.9540',
        '太仓市': '31.5106,121.1540',
    },
    # 天津
    '天津市': {
        '和平区': '39.3434,117.3616',
        '河东区': '39.3934,117.4016',
        '河西区': '39.2934,117.4016',
        '南开区': '39.3434,117.3216',
        '河北区': '39.3434,117.2816',
        '红桥区': '39.3434,117.2416',
        '东丽区': '39.0434,117.4016',
        '西青区': '39.0434,117.1416',
        '津南区': '39.0434,117.3016',
        '北辰区': '39.2434,117.2016',
        '武清区': '39.3934,117.0616',
        '宝坻区': '39.6934,117.3416',
        '滨海新区': '39.0934,117.7016',
        '宁河区': '39.3934,117.8216',
        '静海区': '38.8934,116.9416',
        '蓟州区': '40.0934,117.4016',
    },
    # 长沙
    '长沙市': {
        '芙蓉区': '28.2282,112.9388',
        '天心区': '28.1282,112.9388',
        '岳麓区': '28.2282,112.8888',
        '开福区': '28.2282,112.9788',
        '雨花区': '28.1282,112.9788',
        '望城区': '28.3282,112.8188',
        '长沙县': '28.2282,113.0788',
        '浏阳市': '28.1282,113.6388',
        '宁乡市': '28.3282,112.5588',
    },
    # 郑州
    '郑州市': {
        '中原区': '34.7466,113.6253',
        '二七区': '34.7266,113.6453',
        '管城区': '34.7566,113.6653',
        '金水区': '34.7766,113.6253',
        '上街区': '34.8266,113.5253',
        '惠济区': '34.7966,113.5853',
        '中牟县': '34.7266,113.9753',
        '巩义市': '34.7766,112.9753',
        '荥阳市': '34.8266,113.2253',
        '新密市': '34.8266,113.4253',
        '新郑市': '34.4266,113.7253',
        '登封市': '34.4266,113.0253',
    },
    # 青岛
    '青岛市': {
        '市南区': '36.0671,120.3826',
        '市北区': '36.0671,120.3626',
        '黄岛区': '36.0671,120.1426',
        '崂山区': '36.1071,120.4626',
        '李沧区': '36.1071,120.4026',
        '城阳区': '36.1071,120.3026',
        '胶州市': '36.2071,120.0026',
        '即墨区': '36.3071,120.4526',
        '平度市': '36.5071,120.0026',
        '莱西市': '36.8071,120.5026',
    },
    # 济南
    '济南市': {
        '历下区': '36.6512,117.1201',
        '市中区': '36.6012,117.1201',
        '槐荫区': '36.6512,117.0801',
        '天桥区': '36.6512,117.0401',
        '历城区': '36.6512,117.1601',
        '长清区': '36.5512,116.8001',
        '平阴县': '36.3012,116.4501',
        '济阳县': '36.8012,117.2201',
        '商河县': '37.0012,117.1201',
        '章丘区': '36.7012,117.5501',
        '莱芜区': '36.2012,117.7001',
        '钢城区': '36.0512,117.8501',
    },
    # 大连
    '大连市': {
        '中山区': '38.9140,121.6147',
        '西岗区': '38.9140,121.5947',
        '沙河口区': '38.9140,121.5747',
        '甘井子区': '38.9640,121.5647',
        '旅顺口区': '38.8140,121.2547',
        '金州区': '39.0140,121.7147',
        '普兰店区': '39.3640,121.9647',
        '长海县': '39.2640,122.5847',
        '瓦房店市': '39.6640,121.9647',
        '庄河市': '39.7140,122.9647',
    },
    # 沈阳
    '沈阳市': {
        '和平区': '41.8057,123.4328',
        '沈河区': '41.8557,123.4328',
        '大东区': '41.8057,123.4828',
        '皇姑区': '41.8557,123.4128',
        '铁西区': '41.8057,123.3528',
        '苏家屯区': '41.7557,123.3328',
        '浑南区': '41.7557,123.4828',
        '沈北新区': '41.9057,123.5228',
        '于洪区': '41.8057,123.3028',
        '辽中区': '41.5057,122.7528',
        '康平县': '42.7057,123.3528',
        '法库县': '42.5057,123.4528',
        '新民市': '41.9557,122.8528',
    },
    # 长春
    '长春市': {
        '南关区': '43.8171,125.3235',
        '宽城区': '43.9171,125.3235',
        '朝阳区': '43.8171,125.2835',
        '二道区': '43.8171,125.4035',
        '绿园区': '43.8571,125.2535',
        '双阳区': '43.5171,125.6535',
        '九台区': '43.9171,125.8535',
        '农安县': '44.0171,125.1535',
        '榆树市': '44.8171,126.5535',
        '德惠市': '44.1171,125.6535',
    },
    # 哈尔滨
    '哈尔滨市': {
        '道里区': '45.8038,126.5350',
        '南岗区': '45.8038,126.5950',
        '道外区': '45.8038,126.4750',
        '平房区': '45.6038,126.5350',
        '松北区': '45.8538,126.5950',
        '香坊区': '45.7538,126.5950',
        '呼兰区': '45.9538,126.5350',
        '阿城区': '45.5038,126.5950',
        '双城区': '45.3538,126.2850',
        '依兰县': '46.3038,129.5550',
        '方正县': '45.8538,128.8050',
        '宾县': '45.7538,127.4850',
        '巴彦县': '46.0538,127.3850',
        '木兰县': '45.9538,128.0350',
        '通河县': '45.9538,128.7050',
        '延寿县': '45.4538,128.3350',
        '尚志市': '45.2038,127.9550',
        '五常市': '44.9538,126.9550',
    },
}


def get_coords_by_city(city_name, district=None):
    """根据城市名称获取经纬度坐标，可选区级细分"""
    if not city_name:
        return None

    # 首先检查是否有区级精确坐标
    if district and district not in ('', city_name):
        if city_name in CHINA_DISTRICT_COORDS:
            city_districts = CHINA_DISTRICT_COORDS[city_name]
            if district in city_districts:
                return city_districts[district]
            # 模糊匹配区名
            for d, coords in city_districts.items():
                if district in d or d in district:
                    return coords

    # 精确匹配城市坐标
    base_coords = None
    if city_name in CHINA_CITY_COORDS:
        base_coords = CHINA_CITY_COORDS[city_name]
    else:
        # 模糊匹配
        for city, coords in CHINA_CITY_COORDS.items():
            if city_name in city or city in city_name:
                base_coords = coords
                break

    if not base_coords:
        return None

    # 如果有区级信息且不是城市的直辖区，在城市坐标基础上添加小偏移
    if district and district not in ('', city_name):
        # 使用区名生成确定性偏移量（不同区在同一城市内略有不同位置）
        # 偏移范围约 ±0.04 度（约4公里）
        hash_val = 0
        for i, c in enumerate(district):
            hash_val = hash_val * 31 + ord(c)
        # 确保不同区获得不同的偏移
        offset_lat = ((hash_val % 200) - 100) / 2500.0
        offset_lon = (((hash_val // 200) % 200) - 100) / 2500.0
        lat, lon = map(float, base_coords.split(','))
        return f"{lat + offset_lat:.4f},{lon + offset_lon:.4f}"

    return base_coords

# CSV文件路径
DATA_DIR = '/home/ubuntu/jlu8'
TXL_FILE = os.path.join(DATA_DIR, 'txl.csv')
LYB_FILE = os.path.join(DATA_DIR, 'lyb.csv')
VIDEOS_FILE = os.path.join(DATA_DIR, 'videos.csv')
PHOTOS_FILE = os.path.join(DATA_DIR, 'photos.csv')
DELETED_FILE = os.path.join(DATA_DIR, 'deleted.csv')
ACTIVITIES_FILE = os.path.join(DATA_DIR, 'activities.csv')

# 线程本地存储
_thread_local = threading.local()


def get_db():
    """获取当前线程的数据库连接"""
    if not hasattr(_thread_local, 'conn'):
        _thread_local.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        _thread_local.conn.row_factory = sqlite3.Row
    return _thread_local.conn


def close_db():
    """关闭当前线程的数据库连接"""
    if hasattr(_thread_local, 'conn'):
        _thread_local.conn.close()
        delattr(_thread_local, 'conn')


def init_db():
    """初始化数据库表"""
    conn = get_db()
    cursor = conn.cursor()

    # 学生表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            hometown TEXT,
            hometown_name TEXT,
            city TEXT,
            district TEXT,
            phone TEXT,
            note TEXT,
            custom_intro TEXT,
            hobby TEXT,
            dream TEXT,
            avatar TEXT,
            industry TEXT,
            company TEXT,
            weibo TEXT,
            xiaohongshu TEXT,
            douyin TEXT,
            wechat TEXT,
            qq TEXT,
            email TEXT,
            work TEXT,
            position TEXT,
            birthday TEXT,
            github TEXT,
            coords TEXT,
            gps_coords TEXT
        )
    ''')

    # 留言表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            content TEXT NOT NULL,
            time TEXT NOT NULL,
            image TEXT,
            voice TEXT
        )
    ''')

    # 留言评论表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            content TEXT NOT NULL,
            time TEXT NOT NULL
        )
    ''')

    # 留言点赞表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS message_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            time TEXT NOT NULL,
            UNIQUE(message_id, nickname)
        )
    ''')

    # 视频表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT,
            cover TEXT,
            owner TEXT
        )
    ''')

    # 照片表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            owner TEXT,
            time TEXT
        )
    ''')

    # 已删除项目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deleted (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            content TEXT,
            owner TEXT,
            time TEXT,
            deleted_time TEXT,
            extra TEXT
        )
    ''')

    # 活动表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            time TEXT NOT NULL,
            actor TEXT NOT NULL,
            type TEXT NOT NULL,
            content TEXT
        )
    ''')

    # 喊话表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voice_shouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_name TEXT NOT NULL,
            to_name TEXT NOT NULL,
            audio_url TEXT NOT NULL,
            time TEXT NOT NULL,
            deleted INTEGER DEFAULT 0
        )
    ''')

    # 媒体点赞表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media_likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_type TEXT NOT NULL,
            media_id INTEGER NOT NULL,
            nickname TEXT NOT NULL,
            time TEXT NOT NULL,
            UNIQUE(media_type, media_id, nickname)
        )
    ''')

    # 已浏览活动记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS viewed_activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT NOT NULL,
            activity_time TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            activity_actor TEXT NOT NULL,
            UNIQUE(nickname, activity_time, activity_type, activity_actor)
        )
    ''')

    # 通知表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient TEXT NOT NULL,
            sender TEXT DEFAULT '',
            type TEXT NOT NULL,
            ref_id INTEGER DEFAULT 0,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_time TEXT NOT NULL
        )
    ''')

    # 登录日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            login_time TEXT NOT NULL,
            ip_address TEXT DEFAULT '',
            user_agent TEXT DEFAULT ''
        )
    ''')

    conn.commit()


def migrate_from_csv():
    """从CSV文件迁移数据到SQLite（如果需要）"""
    conn = get_db()
    cursor = conn.cursor()

    # 检查是否需要迁移（SQLite表为空但CSV文件存在）
    cursor.execute('SELECT COUNT(*) FROM students')
    if cursor.fetchone()[0] > 0:
        return  # 已有数据，无需迁移

    # 省份拼音到汉字映射（用于计算hometown_name）
    PROVINCE_MAP = {
        'beijing': '北京', 'shanghai': '上海', 'tianjin': '天津', 'chongqing': '重庆',
        'guangdong': '广东', 'jiangsu': '江苏', 'zhejiang': '浙江', 'sichuan': '四川',
        'hubei': '湖北', 'hunan': '湖南', 'henan': '河南', 'shandong': '山东',
        'hebei': '河北', 'shaanxi': '陕西', 'liaoning': '辽宁', 'jilin': '吉林',
        'heilongjiang': '黑龙江', 'neimenggu': '内蒙古', 'xinjiang': '新疆',
        'gansu': '甘肃', 'qinghai': '青海', 'ningxia': '宁夏', 'shanxi': '山西',
        'anhui': '安徽', 'fujian': '福建', 'jiangxi': '江西', 'guangxi': '广西',
        'hainan': '海南', 'yunnan': '云南', 'guizhou': '贵州', 'xizang': '西藏',
        'taiwan': '台湾', 'xianggang': '香港', 'aomen': '澳门'
    }

    # 迁移学生数据
    if os.path.exists(TXL_FILE):
        students = []
        with open(TXL_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6:
                    hometown_pinyin = row[2]
                    hometown_name = PROVINCE_MAP.get(hometown_pinyin, hometown_pinyin)
                    students.append({
                        'id': row[0],
                        'name': row[1],
                        'hometown': hometown_pinyin,
                        'hometown_name': hometown_name,
                        'city': row[3] if len(row) > 3 else '',
                        'district': row[4] if len(row) > 4 else '',
                        'phone': row[5] if len(row) > 5 else '',
                        'note': row[6] if len(row) > 6 else '',
                        'custom_intro': row[7] if len(row) > 7 else '',
                        'hobby': row[8] if len(row) > 8 else '',
                        'dream': row[9] if len(row) > 9 else '',
                        'avatar': row[10] if len(row) > 10 else '',
                        'industry': row[11] if len(row) > 11 else '',
                        'company': row[12] if len(row) > 12 else '',
                        'weibo': row[13] if len(row) > 13 else '',
                        'xiaohongshu': row[14] if len(row) > 14 else '',
                        'douyin': row[15] if len(row) > 15 else '',
                        'wechat': row[16] if len(row) > 16 else '',
                        'qq': row[17] if len(row) > 17 else '',
                        'email': row[18] if len(row) > 18 else '',
                        'work': row[19] if len(row) > 19 else '',
                        'position': row[20] if len(row) > 20 else '',
                        'birthday': row[21] if len(row) > 21 else '',
                        'github': row[22] if len(row) > 22 else '',
                    })
        for s in students:
            cursor.execute('''
                INSERT OR REPLACE INTO students (id, name, hometown, hometown_name, city, district,
                phone, note, custom_intro, hobby, dream, avatar, industry, company, weibo,
                xiaohongshu, douyin, wechat, qq, email, work, position, birthday, github, coords)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (s['id'], s['name'], s['hometown'], s['hometown_name'], s['city'], s['district'],
                  s['phone'], s['note'], s['custom_intro'], s['hobby'], s['dream'], s['avatar'],
                  s['industry'], s['company'], s['weibo'], s['xiaohongshu'], s['douyin'],
                  s['wechat'], s['qq'], s['email'], s['work'], s['position'], s['birthday'],
                  s['github'], ''))

        # 备份CSV
        shutil.copy(TXL_FILE, TXL_FILE + '.bak')

    # 迁移留言数据
    if os.path.exists(LYB_FILE):
        with open(LYB_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    cursor.execute('''
                        INSERT INTO messages (nickname, content, time, image)
                        VALUES (?, ?, ?, ?)
                    ''', (row[1], row[2], row[3], row[4] if len(row) > 4 else ''))
        shutil.copy(LYB_FILE, LYB_FILE + '.bak')

    # 迁移视频数据
    if os.path.exists(VIDEOS_FILE):
        with open(VIDEOS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    cursor.execute('''
                        INSERT INTO videos (title, url, cover, owner)
                        VALUES (?, ?, ?, ?)
                    ''', (row[1], row[2], row[3] if len(row) > 3 else '', row[4] if len(row) > 4 else ''))
        shutil.copy(VIDEOS_FILE, VIDEOS_FILE + '.bak')

    # 迁移照片数据
    if os.path.exists(PHOTOS_FILE):
        with open(PHOTOS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    cursor.execute('''
                        INSERT INTO photos (filename, owner, time)
                        VALUES (?, ?, ?)
                    ''', (row[1], row[2], row[3]))
        shutil.copy(PHOTOS_FILE, PHOTOS_FILE + '.bak')

    # 迁移已删除数据
    if os.path.exists(DELETED_FILE):
        with open(DELETED_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6:
                    cursor.execute('''
                        INSERT INTO deleted (type, content, owner, time, deleted_time, extra)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (row[1], row[2], row[3], row[4], row[5], row[6] if len(row) > 6 else ''))
        shutil.copy(DELETED_FILE, DELETED_FILE + '.bak')

    # 迁移活动数据
    if os.path.exists(ACTIVITIES_FILE):
        with open(ACTIVITIES_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    cursor.execute('''
                        INSERT INTO activities (time, actor, type, content)
                        VALUES (?, ?, ?, ?)
                    ''', (row[0], row[1], row[2], row[3]))
        shutil.copy(ACTIVITIES_FILE, ACTIVITIES_FILE + '.bak')

    conn.commit()


def migrate_add_gps_coords():
    """为已存在的数据库添加gps_coords列"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE students ADD COLUMN gps_coords TEXT')
        conn.commit()
    except:
        pass  # 列可能已存在


# ==================== 学生数据操作 ====================

def read_txl():
    """读取通讯录数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students')
    rows = cursor.fetchall()
    students = []
    for row in rows:
        students.append(dict(row))
    return students


def write_txl(students):
    """写入通讯录数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students')
    for s in students:
        cursor.execute('''
            INSERT INTO students (id, name, hometown, hometown_name, city, district, phone, note,
            custom_intro, hobby, dream, avatar, industry, company, weibo, xiaohongshu, douyin,
            wechat, qq, email, work, position, birthday, github, coords, gps_coords, gender,
            login_password, no_password_prompt, is_admin, super_admin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (s.get('id', ''), s.get('name', ''), s.get('hometown', ''), s.get('hometown_name', ''),
              s.get('city', ''), s.get('district', ''), s.get('phone', ''), s.get('note', ''),
              s.get('custom_intro', ''), s.get('hobby', ''), s.get('dream', ''), s.get('avatar', ''),
              s.get('industry', ''), s.get('company', ''), s.get('weibo', ''), s.get('xiaohongshu', ''),
              s.get('douyin', ''), s.get('wechat', ''), s.get('qq', ''), s.get('email', ''),
              s.get('work', ''), s.get('position', ''), s.get('birthday', ''), s.get('github', ''),
              s.get('coords', ''), s.get('gps_coords', ''), s.get('gender', ''),
              s.get('login_password', ''), s.get('no_password_prompt', 0),
              s.get('is_admin', 0), s.get('super_admin', 0)))
    conn.commit()


def update_student_gps_coords(student_name, student_id, gps_coords):
    """更新学生的GPS坐标"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE students SET gps_coords = ? WHERE name = ? AND id = ?
    ''', (gps_coords, student_name, student_id))
    conn.commit()
    return True  # UPDATE succeeded even if rowcount is 0 (data unchanged)


def update_student_admin(student_id, is_admin, is_super_admin):
    """更新学生的管理员权限"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE students SET is_admin = ?, super_admin = ? WHERE id = ?
    ''', (1 if is_admin else 0, 1 if is_super_admin else 0, student_id))
    conn.commit()
    return True


# ==================== 留言数据操作 ====================

def read_lyb():
    """读取留言板数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM messages ORDER BY id')
    rows = cursor.fetchall()
    messages = []
    for row in rows:
        messages.append(dict(row))
    return messages


def write_lyb(messages):
    """写入留言板数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM messages')
    for m in messages:
        cursor.execute('''
            INSERT INTO messages (id, nickname, content, time, image, voice)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (m.get('id', ''), m.get('nickname', ''), m.get('content', ''),
              m.get('time', ''), m.get('image', ''), m.get('voice', '')))
    conn.commit()


def get_next_lyb_id():
    """获取下一条留言ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM messages')
    result = cursor.fetchone()[0]
    return (result or 0) + 1


# ==================== 评论数据操作 ====================

def read_comments(message_id=None):
    """读取评论数据"""
    conn = get_db()
    cursor = conn.cursor()
    if message_id is not None:
        cursor.execute('SELECT * FROM comments WHERE message_id = ? ORDER BY id', (message_id,))
    else:
        cursor.execute('SELECT * FROM comments ORDER BY id')
    rows = cursor.fetchall()
    comments = []
    for row in rows:
        comments.append(dict(row))
    return comments


def add_comment(message_id, nickname, content):
    """添加评论"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO comments (message_id, nickname, content, time)
        VALUES (?, ?, ?, ?)
    ''', (message_id, nickname, content, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    return cursor.lastrowid


def get_comments_by_message(message_id):
    """获取某留言的所有评论"""
    return read_comments(message_id)


def delete_comment(comment_id):
    """删除评论"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    conn.commit()
    return cursor.rowcount > 0


# ==================== 留言点赞操作 ====================

def get_message_likes(message_id):
    """获取留言的点赞数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM message_likes WHERE message_id = ?', (message_id,))
    count = cursor.fetchone()[0]
    return count


def has_liked_message(message_id, nickname):
    """检查用户是否已点赞"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM message_likes WHERE message_id = ? AND nickname = ?', (message_id, nickname))
    return cursor.fetchone()[0] > 0


def like_message(message_id, nickname):
    """点赞留言"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO message_likes (message_id, nickname, time)
            VALUES (?, ?, ?)
        ''', (message_id, nickname, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except:  # 已点赞会违反唯一约束
        return False


def unlike_message(message_id, nickname):
    """取消点赞"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM message_likes WHERE message_id = ? AND nickname = ?', (message_id, nickname))
    conn.commit()
    return cursor.rowcount > 0


# ==================== 视频数据操作 ====================

def read_videos():
    """读取视频数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM videos ORDER BY id DESC')
    rows = cursor.fetchall()
    videos = []
    for row in rows:
        videos.append(dict(row))
    return videos


def write_videos(videos):
    """写入视频数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM videos')
    for v in videos:
        cursor.execute('''
            INSERT INTO videos (id, title, url, cover, owner)
            VALUES (?, ?, ?, ?, ?)
        ''', (v.get('id', ''), v.get('title', ''), v.get('url', ''),
              v.get('cover', ''), v.get('owner', '')))
    conn.commit()


def get_next_video_id():
    """获取下一个视频ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM videos')
    result = cursor.fetchone()[0]
    return (result or 0) + 1


# ==================== 照片数据操作 ====================

def read_photos():
    """读取照片数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM photos ORDER BY id')
    rows = cursor.fetchall()
    photos = []
    for row in rows:
        photos.append(dict(row))
    return photos


def write_photos(photos):
    """写入照片数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM photos')
    for p in photos:
        cursor.execute('''
            INSERT INTO photos (id, filename, owner, time, year)
            VALUES (?, ?, ?, ?, ?)
        ''', (p.get('id', ''), p.get('filename', ''), p.get('owner', ''), p.get('time', ''), p.get('year', 2020)))
    conn.commit()


def get_next_photo_id():
    """获取下一张照片ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM photos')
    result = cursor.fetchone()[0]
    return (result or 0) + 1


def delete_photo(photo_id):
    """删除照片"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM photos WHERE id = ?', (photo_id,))
    conn.commit()
    return cursor.rowcount > 0


def delete_video(video_id):
    """删除视频"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
    conn.commit()
    return cursor.rowcount > 0


# ==================== 已删除数据操作 ====================

def read_deleted():
    """读取已删除项目记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM deleted ORDER BY id')
    rows = cursor.fetchall()
    items = []
    for row in rows:
        items.append({
            'id': row[0],
            'type': row[1],
            'content': row[2],
            'owner': row[3],
            'time': row[4],
            'deleted_time': row[5],
            'extra': row[6]
        })
    return items


def write_deleted(items):
    """写入已删除项目记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM deleted')
    for item in items:
        cursor.execute('''
            INSERT INTO deleted (id, type, content, owner, time, deleted_time, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (item.get('id', ''), item.get('type', ''), item.get('content', ''),
              item.get('owner', ''), item.get('time', ''), item.get('deleted_time', ''),
              item.get('extra', '')))
    conn.commit()


def get_next_deleted_id():
    """获取下一个已删除项目ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM deleted')
    result = cursor.fetchone()[0]
    return (result or 0) + 1


def delete_from_deleted(id):
    """从已删除列表中移除项目"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM deleted WHERE id = ?', (id,))
    conn.commit()


# ==================== 活动数据操作 ====================

def read_activities():
    """读取活动数据"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM activities ORDER BY time DESC')
    rows = cursor.fetchall()
    activities = []
    for row in rows:
        activities.append(dict(row))
    return activities


def write_activity(actor, action_type, content):
    """写入活动记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activities (time, actor, type, content)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), actor, action_type, content))
    conn.commit()


def delete_activity(time, actor, content):
    """删除活动记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM activities WHERE time = ? AND actor = ?
    ''', (time, actor))
    conn.commit()


def delete_message_by_time_nickname(time, nickname):
    """根据时间和昵称删除留言，并记录到已删除列表"""
    conn = get_db()
    cursor = conn.cursor()
    # 先查询留言内容，用于记录到已删除列表
    cursor.execute('SELECT id, content, image FROM messages WHERE time = ? AND nickname = ?', (time, nickname))
    row = cursor.fetchone()
    if row:
        # 记录到已删除列表
        cursor.execute('''
            INSERT INTO deleted (id, type, content, owner, time, deleted_time, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (get_next_deleted_id(), 'message', row[1], nickname, time, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), row[2] or ''))
    # 删除留言
    cursor.execute('DELETE FROM messages WHERE time = ? AND nickname = ?', (time, nickname))
    conn.commit()


def delete_message(message_id):
    """根据ID删除留言"""
    conn = get_db()
    cursor = conn.cursor()
    # 先查询留言内容，用于记录到已删除列表
    cursor.execute('SELECT id, nickname, content, image FROM messages WHERE id = ?', (message_id,))
    row = cursor.fetchone()
    if row:
        # 记录到已删除列表
        cursor.execute('''
            INSERT INTO deleted (id, type, content, owner, time, deleted_time, extra)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (get_next_deleted_id(), 'message', row[2], row[1], '', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), row[3] or ''))
    # 删除留言
    cursor.execute('DELETE FROM messages WHERE id = ?', (message_id,))
    conn.commit()
    return row is not None


def delete_activities_by_actor(actor):
    """删除指定用户的所有活动记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM activities WHERE actor = ?', (actor,))
    conn.commit()
    return cursor.rowcount


def write_login_log(username, ip_address='', user_agent=''):
    """写入登录日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO login_logs (username, login_time, ip_address, user_agent)
        VALUES (?, ?, ?, ?)
    ''', (username, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ip_address, user_agent))
    conn.commit()


def read_login_logs(limit=100):
    """读取登录日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM login_logs ORDER BY login_time DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    logs = []
    for row in rows:
        logs.append(dict(row))
    return logs


def delete_login_logs(username):
    """删除指定用户的登录日志"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM login_logs WHERE username = ?', (username,))
    conn.commit()
    return cursor.rowcount


# ==================== 喊话数据操作 ====================

def read_voice_shouts(include_deleted=False):
    """读取所有喊话数据"""
    conn = get_db()
    cursor = conn.cursor()
    if include_deleted:
        cursor.execute('SELECT * FROM voice_shouts ORDER BY id DESC')
    else:
        cursor.execute('SELECT * FROM voice_shouts WHERE deleted = 0 ORDER BY id DESC')
    rows = cursor.fetchall()
    shouts = []
    for row in rows:
        shouts.append(dict(row))
    return shouts


def get_voice_shouts_by_target(target_name, include_deleted=False):
    """获取某人的所有喊话"""
    conn = get_db()
    cursor = conn.cursor()
    if include_deleted:
        cursor.execute('SELECT * FROM voice_shouts WHERE to_name = ? ORDER BY id DESC', (target_name,))
    else:
        cursor.execute('SELECT * FROM voice_shouts WHERE to_name = ? AND deleted = 0 ORDER BY id DESC', (target_name,))
    rows = cursor.fetchall()
    shouts = []
    for row in rows:
        shouts.append(dict(row))
    return shouts


def add_voice_shout(from_name, to_name, audio_url):
    """添加喊话"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO voice_shouts (from_name, to_name, audio_url, time)
        VALUES (?, ?, ?, ?)
    ''', (from_name, to_name, audio_url, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    return cursor.lastrowid


def delete_voice_shout(shout_id, user_name):
    """删除喊话（仅发送方或接收方可删除）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM voice_shouts WHERE id = ?', (shout_id,))
    shout = cursor.fetchone()
    if not shout:
        return False, '喊话不存在'
    shout = dict(shout)
    if shout['from_name'] != user_name and shout['to_name'] != user_name:
        return False, '无权删除此喊话'
    cursor.execute('UPDATE voice_shouts SET deleted = 1 WHERE id = ?', (shout_id,))
    conn.commit()
    return True, '删除成功'


def restore_voice_shout(shout_id, user_name):
    """恢复喊话（仅发送方或接收方可恢复）"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM voice_shouts WHERE id = ?', (shout_id,))
    shout = cursor.fetchone()
    if not shout:
        return False, '喊话不存在'
    shout = dict(shout)
    if shout['from_name'] != user_name and shout['to_name'] != user_name:
        return False, '无权恢复此喊话'
    cursor.execute('UPDATE voice_shouts SET deleted = 0 WHERE id = ?', (shout_id,))
    conn.commit()
    return True, '恢复成功'


# ==================== 媒体点赞操作 ====================

def get_media_likes(media_type, media_id):
    """获取媒体的点赞数"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM media_likes WHERE media_type = ? AND media_id = ?', (media_type, media_id))
    return cursor.fetchone()[0]


def has_liked_media(media_type, media_id, nickname):
    """检查用户是否已点赞"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM media_likes WHERE media_type = ? AND media_id = ? AND nickname = ?',
                   (media_type, media_id, nickname))
    return cursor.fetchone()[0] > 0


def like_media(media_type, media_id, nickname):
    """点赞媒体"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO media_likes (media_type, media_id, nickname, time)
            VALUES (?, ?, ?, ?)
        ''', (media_type, media_id, nickname, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except:
        return False


def unlike_media(media_type, media_id, nickname):
    """取消点赞"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM media_likes WHERE media_type = ? AND media_id = ? AND nickname = ?',
                   (media_type, media_id, nickname))
    conn.commit()
    return cursor.rowcount > 0


def get_all_likes_for_media(media_type, media_ids):
    """批量获取多个媒体的点赞数"""
    conn = get_db()
    cursor = conn.cursor()
    placeholders = ','.join(['?'] * len(media_ids)) if media_ids else '0'
    cursor.execute(f'SELECT media_id, COUNT(*) as cnt FROM media_likes WHERE media_type = ? AND media_id IN ({placeholders}) GROUP BY media_id',
                   [media_type] + list(media_ids))
    return {row[0]: row[1] for row in cursor.fetchall()}


def get_all_liked_for_user(media_type, nickname):
    """获取用户点赞过的所有媒体ID"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT media_id FROM media_likes WHERE media_type = ? AND nickname = ?', (media_type, nickname))
    return {row[0] for row in cursor.fetchall()}


# ==================== 已浏览活动记录操作 ====================

def mark_activity_viewed(nickname, activity):
    """标记一条活动为已浏览"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO viewed_activities (nickname, activity_time, activity_type, activity_actor)
            VALUES (?, ?, ?, ?)
        ''', (nickname, activity['time'], activity['type'], activity['actor']))
        conn.commit()
        return True
    except:
        return False


def mark_activities_viewed(nickname, activities):
    """批量标记活动为已浏览"""
    conn = get_db()
    cursor = conn.cursor()
    for activity in activities:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO viewed_activities (nickname, activity_time, activity_type, activity_actor)
                VALUES (?, ?, ?, ?)
            ''', (nickname, activity['time'], activity['type'], activity['actor']))
        except:
            pass
    conn.commit()


def get_viewed_activities(nickname):
    """获取用户已浏览的活动集合"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT activity_time, activity_type, activity_actor FROM viewed_activities WHERE nickname = ?',
                  (nickname,))
    viewed = set()
    for row in cursor.fetchall():
        viewed.add((row[0], row[1], row[2]))
    return viewed


def get_unread_activity_count(nickname, activities):
    """获取未读活动数量"""
    if not nickname:
        return 0
    viewed = get_viewed_activities(nickname)
    unread_count = 0
    for activity in activities:
        key = (activity['time'], activity['type'], activity['actor'])
        if key not in viewed:
            unread_count += 1
    return unread_count


# ==================== 通知系统 ====================

def create_notification(recipient, sender, notif_type, ref_id=0, content='', target_name='', media_type=''):
    """创建通知"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO notifications (recipient, sender, type, ref_id, content, is_read, created_time, target_name, media_type)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
    ''', (recipient, sender, notif_type, ref_id, content, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), target_name, media_type))
    conn.commit()
    return cursor.lastrowid


def get_notifications(recipient, limit=20):
    """获取用户通知列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, recipient, sender, type, ref_id, content, is_read, created_time, target_name, media_type
        FROM notifications
        WHERE recipient = ?
        ORDER BY created_time DESC
        LIMIT ?
    ''', (recipient, limit))
    notifications = []
    for row in cursor.fetchall():
        notifications.append({
            'id': row[0],
            'recipient': row[1],
            'sender': row[2],
            'type': row[3],
            'ref_id': row[4],
            'content': row[5],
            'is_read': bool(row[6]),
            'created_time': row[7],
            'target_name': row[8] if len(row) > 8 else '',
            'media_type': row[9] if len(row) > 9 else ''
        })
    return notifications


def get_unread_notification_count(recipient):
    """获取未读通知数量"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM notifications WHERE recipient = ? AND is_read = 0', (recipient,))
    return cursor.fetchone()[0]


def mark_notification_read(notification_id, recipient):
    """标记单条通知为已读"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE notifications SET is_read = 1 WHERE id = ? AND recipient = ?',
                  (notification_id, recipient))
    conn.commit()
    return cursor.rowcount > 0


def mark_all_notifications_read(recipient):
    """标记所有通知为已读"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE notifications SET is_read = 1 WHERE recipient = ?', (recipient,))
    conn.commit()
    return True


# ==================== 新闻模块 ====================

def get_news(limit=5):
    """获取最新新闻"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, title, content, source_url, image_url, published_time, created_time
        FROM news
        WHERE is_deleted = 0
        ORDER BY id DESC
        LIMIT ?
    ''', (limit,))
    news = []
    for row in cursor.fetchall():
        news.append({
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'source_url': row[3],
            'image_url': row[4],
            'published_time': row[5],
            'created_time': row[6]
        })
    return news


def save_news(title, content, source_url, image_url, published_time):
    """保存新闻"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO news (title, content, source_url, image_url, published_time, created_time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, content, source_url, image_url, published_time, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    return cursor.lastrowid


def clear_news():
    """清空所有新闻"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE news SET is_deleted = 1')
    conn.commit()


def get_config(key, default=''):
    """获取配置"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
    row = cursor.fetchone()
    return row[0] if row else default


def set_config(key, value):
    """设置配置"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
    ''', (key, value))
    conn.commit()


def set_news_crawl_log(executed_at, status, news_count, message='', image_count=0):
    """保存新闻爬取日志"""
    import json
    log = json.dumps({
        'executed_at': executed_at,
        'status': status,
        'news_count': news_count,
        'image_count': image_count,
        'message': message
    }, ensure_ascii=False)
    set_config('last_news_crawl_log', log)


def get_news_crawl_log():
    """获取上次新闻爬取日志"""
    import json
    log_str = get_config('last_news_crawl_log', '')
    if log_str:
        try:
            return json.loads(log_str)
        except:
            return None
    return None


def get_news_keywords():
    """获取新闻爬取关键词"""
    keywords = get_config('news_keywords', '吉林大学,南岭校区,自动化')
    return [k.strip() for k in keywords.split(',') if k.strip()]


def set_news_keywords(keywords_list):
    """设置新闻爬取关键词"""
    keywords_str = ','.join([k.strip() for k in keywords_list if k.strip()])
    set_config('news_keywords', keywords_str)


# ==================== 微信绑定 ====================

def create_wx_bindings_table():
    """创建微信绑定表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wx_bindings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE NOT NULL,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            bind_time TEXT NOT NULL
        )
    ''')
    conn.commit()


def add_wx_openid_column():
    """为students表添加wx_openid字段"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('ALTER TABLE students ADD COLUMN wx_openid TEXT')
        conn.commit()
    except sqlite3.OperationalError:
        pass  # 列可能已存在


def bind_wx_openid(openid, student_id, name):
    """绑定微信openid到学生账号"""
    if not openid or not student_id or not name:
        return False
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO wx_bindings (openid, student_id, name, bind_time)
        VALUES (?, ?, ?, ?)
    ''', (openid, student_id, name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    cursor.execute('UPDATE students SET wx_openid = ? WHERE id = ? AND name = ?',
                   (openid, student_id, name))
    conn.commit()
    return True


def get_binding_by_openid(openid):
    """根据openid获取绑定信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wx_bindings WHERE openid = ?', (openid,))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_binding_by_student(student_id, name):
    """根据学号和姓名获取绑定信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM wx_bindings WHERE student_id = ? AND name = ?',
                   (student_id, name))
    row = cursor.fetchone()
    return dict(row) if row else None


def get_student_by_openid(openid):
    """根据openid获取学生信息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM students WHERE wx_openid = ?', (openid,))
    row = cursor.fetchone()
    return dict(row) if row else None
