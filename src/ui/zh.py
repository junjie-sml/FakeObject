"""Chinese presentation strings; schema keys and user-entered text remain intact."""
from functools import lru_cache
import yaml
from src.system.paths import ROOT

WORDS={
 'building':'建筑','building facade':'建筑立面','tower':'塔楼','architectural structure':'建筑结构',
 'facade':'立面','structure':'结构',
 'house':'房屋','house facade':'房屋立面','building tower':'建筑塔楼','turret':'小塔楼',
 'drinking cup':'饮水杯','coffee mug':'咖啡马克杯','glass':'玻璃杯','glass bottle':'玻璃瓶','water bottle':'水瓶',
 'seat':'座椅','armchair':'扶手椅','rucksack':'背包','backpack bag':'背包','mobile phone':'手机','smartphone':'智能手机',
 'table lamp':'台灯','light fixture':'灯具','flower vase':'花瓶','computer keyboard':'电脑键盘',
 'READY':'可用','PARTIALLY READY':'部分可用','UNAVAILABLE':'不可用',
 'cup':'杯子','mug':'马克杯','bottle':'瓶子','vase':'花瓶','lamp':'灯具','speaker':'音箱',
 'toy':'玩具','appliance':'家用电器','kitchen appliance':'厨房电器','container':'容器',
 'chair':'椅子','backpack':'背包','cell phone':'手机','phone':'手机','keyboard':'键盘',
 'book':'书本','bowl':'碗','mouse':'鼠标','person':'人物','horse':'马','baseball bat':'棒球棒',
 'suitcase':'行李箱','bicycle':'自行车','broccoli':'西兰花','carrot':'胡萝卜','fork':'叉子',
 'matte ceramic':'哑光陶瓷','frosted polymer':'磨砂聚合物','fine-grained mineral composite':'细颗粒矿物复合材料',
 'satin polymer':'缎面聚合物','brushed alloy':'拉丝合金','soft-touch elastomer':'柔触弹性体',
 'low-gloss enamel':'低光泽搪瓷','translucent resin':'半透明树脂',
 'off-white':'米白色','warm gray':'暖灰色','blue-gray':'蓝灰色','desaturated green':'灰绿色',
 'pale clay':'浅陶土色','charcoal':'炭灰色','muted amber':'柔和琥珀色','ivory':'象牙白','mineral beige':'矿物米色',
 'a shallow recessed channel':'浅凹槽','a molded transition with consistent wall thickness':'壁厚一致的模塑过渡',
 'a narrow embedded plate':'窄嵌片','a small frosted inset':'小型磨砂嵌件',
 'follow the user-specified geometry without adding a new major structure':'沿用用户指定的几何，不增加新的主体结构',
 'retain specified geometric details':'保留指定的几何细节','consistent manufactured wall thickness':'保持合理一致的壁厚',
 'follow user-specified materials; otherwise a coherent matte manufactured finish':'优先采用用户指定的材质，否则使用协调的哑光表面',
 'retain user-specified colors':'保留用户指定的颜色',
}
TEMPLATES=[
 ('嵌套壳体','两层错位嵌套的壳体','不对称开口露出内层'),
 ('悬置薄膜','浅圆角制造框架','凹框内固定的半透明薄膜'),
 ('放射空心鳍片','不对称实心主体','三片长度不等的短空心鳍片'),
 ('偏心开口','扁平且柔和弯曲的体块','带材质过渡的偏心局部开口'),
 ('层叠环带','三层部分重叠的曲面','固定于底座的偏心内核'),
 ('分裂壳体','紧凑连续的外壳','不规则凹缝露出对比色内层'),
 ('局部晶格','实心圆润体块','一处凹入的精细晶格'),
 ('折叠脊线','不对称浅体块','高度平滑变化的连续脊线'),
 ('中空通道','柔和分面的连贯体块','连接两处凹口的窄通道'),
 ('分叉底座','稳定的渐缩壳体','两个一体化弯曲接触区'),
 ('嵌入圆片','扁平圆角棱柱','低于外表面的倾斜圆形嵌件'),
 ('柔和分面体','曲率不均匀的宽阔平滑分面','小型偏心中空区域'),
 ('半透明内核','不透明保护壳','局部外露的半透明内核'),
 ('间断边缘','低矮圆润的封闭主体','数段分离的浅边缘'),
 ('互锁体块','两个协调互锁的体块','凹入的机械材质连接面'),
 ('凹入界面','柔和渐缩的不对称体块','不含屏幕或按键的浅触感凹面'),
 ('有机工业曲面','具有生物式平滑曲率的人工主体','精密模塑的折叠脊线'),
 ('偏心内腔','厚壁外壳','通向偏心腔体的窄开口'),
 ('分区表面','连贯圆润的壳体','深度略有差异的宽阔不规则分区'),
 ('不对称环体','厚度变化的局部环状体','偏心开口与稳定的一体接触面'),
]

@lru_cache(maxsize=1)
def vocabulary():
    words=dict(WORDS)
    templates=yaml.safe_load((ROOT/'skills/fake_object_design/templates.yaml').read_text(encoding='utf-8'))['templates']
    for template, translations in zip(templates,TEMPLATES):
        for field,translated in zip(['name','primary','secondary'],translations): words[template[field]]=translated
        words[template['id']+' '+template['name']]=template['id']+' '+translations[0]
    return words

def zh(text):
    return vocabulary().get(text,text)

MESSAGES={
 'Qwen uses the source photograph and selected scope instructions; final compositing enforces the selected mask.':'Qwen 按原始照片及所选目标范围生成；严格合成使用所选蒙版保留编辑范围外的像素。',
 'Upload or select an image first.':'请先上传或选择图片。',
 'Detect the current image first.':'请先检测当前图片中的目标。',
 'No mask available. Detect the target first.':'暂无蒙版，请先检测目标。',
 'MULTIPLE_DETECTIONS: choose an instance before editing.':'检测到多个目标，请先选择要编辑的实例。',
 'Multiple objects found: select an instance explicitly.':'检测到多个物体，请明确选择一个实例。',
 'Selected instance is out of range.':'所选实例无效，请重新选择。',
 'Could not identify the target locally. Enter a short target phrase, e.g. mug / cup.':'未能从指令中识别目标，请填写目标物体，例如“杯子”或“cup”。',
 'NO_DETECTIONS: try a simpler English noun or lower the threshold.':'未检测到目标。可降低阈值，或填写更简短的物体名称；复杂中文目标可尝试英文名称。',
 'Image or target changed after detection; detect again before editing.':'图片或目标已改变，请重新检测后再编辑。',
 'Concept target differs from detected target; regenerate concepts.':'概念中的目标与当前目标不一致，请重新生成概念。',
 'Instruction changed after concept creation; regenerate concepts or update raw_user_prompt in the JSON.':'编辑要求已改变，请重新生成概念，或更新 JSON 中的 raw_user_prompt。',
 'Select a saved run first.':'请先选择一条已保存的记录。',
 'Invalid result path.':'结果路径无效。',
 'No semantic VLM loaded; lighting and support are preservation constraints, not measured estimates. Supply an occluder mask for exact foreground protection.':'未加载语义视觉模型；光照和支撑信息为保守的保持约束，并非测量结果。如需精确保留前景，请提供保护蒙版。',
 'Qwen uses a separate mask reference; strict localization is enforced by final compositing.':'Qwen 使用独立参考蒙版，最终通过严格合成约束编辑范围。',
 'GPU is busy with another application request. Wait for it to finish.':'另一个任务正在使用 GPU，请等待其完成。',
 'EMPTY_MASK: choose another detection or provide a non-empty mask.':'蒙版为空，请选择其他检测结果或提供有效蒙版。',
 'Cleanup removed the complete mask. Lower cleanup_min_component.':'清理操作移除了整个蒙版，请降低最小区域面积。',
 'Erosion removed the whole mask.':'腐蚀操作移除了整个蒙版，请减小腐蚀范围。',
 'Occluder mask must match original image dimensions.':'保护蒙版的尺寸必须与原图一致。',
}

def message(text):
    for original,translated in MESSAGES.items(): text=text.replace(original,translated)
    return text


def builtin_i18n():
    """Flat keys override Gradio 5's nested defaults without modifying Gradio.

    svelte-i18n resolves exact keys before nested keys. Keep these separate from
    application labels so neither prompt content nor schema values are translated.
    """
    import gradio as gr
    groups={
        'common':{'built_with':'构建于','built_with_gradio':'使用 Gradio 构建','clear':'清除','download':'下载','edit':'编辑','empty':'空','error':'错误','hosted_on':'托管在','loading':'加载中','logo':'标志','or':'或','remove':'移除','share':'分享','submit':'提交','undo':'撤销','settings':'设置','no_devices':'未找到设备','language':'语言','display_theme':'显示主题'},
        'upload_text':{'click_to_upload':'点击上传','drop_file':'将文件拖放到此处','drop_image':'将图片拖放到此处','drop_gallery':'将图片拖放到此处','paste_clipboard':'从剪贴板粘贴'},
        'image':{'image':'图片','remove_image':'移除图片','drop_to_upload':'将图片拖放到此处以上传','use_brush':'使用画笔','brush_color':'画笔颜色','brush_radius':'画笔大小','select_brush_color':'选择画笔颜色','start_drawing':'开始绘制'},
        'file':{'uploading':'正在上传…'},
        'blocks':{'waiting_for_inputs':'请等待文件上传完成后重试。','lost_connection':'连接已断开，正在重新连接…','connection_can_break':'页面休眠或切换到后台可能中断连接。','long_requests_queue':'任务队列较长，请稍候。'},
        'errors':{'build_error':'界面构建失败','config_error':'配置出错','runtime_error':'运行出错','contact_page_author':'请查看本地日志以排查原因。','use_via_api':'通过 API 使用','use_via_api_or_mcp':'通过 API 或 MCP 使用'},
    }
    strings={f'{group}.{key}':value for group,items in groups.items() for key,value in items.items()}
    return gr.I18n(**{locale:strings for locale in ['en','zh','zh-CN','zh-TW']})
