"""Small offline vocabulary bridge for common targets; never rewrites user prompts."""
import re

TARGET_NAMES = {
    '建筑立面':'building facade', '建筑结构':'architectural structure', '房屋立面':'house facade',
    '建筑物':'building', '建筑':'building', '房屋':'house', '房子':'house',
    '塔楼':'tower', '城堡':'castle', '楼房':'building',
    '马克杯':'mug', '咖啡杯':'cup', '玻璃杯':'glass', '水杯':'cup', '杯子':'cup', '杯':'cup',
    '水瓶':'bottle', '瓶子':'bottle', '花瓶':'vase', '台灯':'lamp', '灯具':'lamp',
    '椅子':'chair', '背包':'backpack', '键盘':'keyboard', '手机':'cell phone',
    '笔记本电脑':'laptop', '电脑':'computer', '鼠标':'mouse', '相机':'camera',
    '书本':'book', '书':'book', '鞋子':'shoe', '碗':'bowl', '音箱':'speaker',
    '桌子':'table', '手提包':'handbag', '手表':'watch', '时钟':'clock', '遥控器':'remote control',
}

def grounding_phrase(target):
    """Translate recognized nouns/modifiers only; keep unfamiliar phrases intact."""
    text=target.strip().rstrip('。.')
    if not re.search('[\u4e00-\u9fff]',text): return text
    nouns=sorted(TARGET_NAMES,key=len,reverse=True)
    noun=next((n for n in nouns if n in text),None)
    if noun is None: return text
    adjectives={'红色':'red','蓝色':'blue','绿色':'green','白色':'white','黑色':'black','陶瓷':'ceramic','透明':'transparent'}
    modifiers=[en for zh,en in adjectives.items() if zh in text]
    position='on the left' if any(x in text for x in ['左边','左侧']) else 'on the right' if any(x in text for x in ['右边','右侧']) else ''
    return ' '.join([*modifiers,TARGET_NAMES[noun],position]).strip()
