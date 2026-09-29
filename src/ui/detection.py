"""Shared candidate labels for both detection screens."""
from src.ui.zh import zh,message


def candidate_choices(result):
    return [(f'{i+1} · {zh(label)} · 置信度 {score:.2f}'+('（较低，请核对）' if score<.3 else ''),i)
            for i,(label,score) in enumerate(zip(result['labels'],result['scores']))]


def candidate_gallery(result):
    return [(path,label) for path,(label,_) in zip(result.get('candidate_previews',[]),candidate_choices(result))]


def detection_summary(result):
    search=result.get('search',{})
    description=f"显示 **{len(result['boxes'])} 个候选**。点击候选缩略图或使用下拉框选择一个，再检查蒙版。"
    if search:
        description+=f"\n\n检测名称：{' / '.join(search['queries'])} · 阈值 {search['threshold']:.2f}。"
        description+=f"原始候选 {search['raw_count']} 个，合并近乎重合的框 {search['duplicate_count']} 个。"
    if search.get('mode')=='broad':
        description+='\n\n尽量找全模式会保留较弱匹配，以及整体与局部的不同范围；候选可能重叠或误检，仍可能漏检。'
    return description+'\n\n'+' '.join(message(w) for w in result.get('warnings',[]))
