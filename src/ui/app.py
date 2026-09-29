"""Local Gradio research workbench. GPU jobs are serialized by ModelManager."""
import json
import os
from pathlib import Path
import gradio as gr
from src.system.paths import ROOT, config
from src.system.hardware import detect_hardware
from src.models.model_registry import registry
from src.app.service import load_image, infer_target, detect, select_mask, run_edit, fingerprint
from src.prompting.fake_object_skill import generate_concepts
from src.prompting.schemas import FakeObjectSpec, Controls
from src.prompting.prompt_compiler import compile_prompt
from src.scene_analysis.analyzer import analyze_scene
from src.postprocessing.mask_processor import process_mask, mask_overlay
from src.system.logging import get_logger
from src.ui.zh import zh, message, builtin_i18n
from src.ui.detection import candidate_choices, candidate_gallery, detection_summary
from src.prompting.selected_region import describe_selected_region

CSS='''
.gradio-container {max-width: 1480px !important; margin:auto;}
#hero {padding:22px 26px; background:linear-gradient(115deg,#12372f,#215f51); border-radius:14px; margin-bottom:16px;}
#hero h1,#hero p {color:white!important;} .concept-card {min-height:180px;}
'''

def guarded(fn):
    def inner(*args,**kwargs):
        try: return fn(*args,**kwargs)
        except gr.Error: raise
        except Exception as e:
            get_logger().exception(f'ui_callback {fn.__name__}')
            raise gr.Error(message(str(e))) from e
    return inner

def manifest():
    p=ROOT/'data/metadata/image_manifest.jsonl'
    return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines()] if p.exists() else []

def system_status():
    evidence=ROOT/'data/metadata/verification.json'
    versions=ROOT/'data/metadata/environment_versions.json'
    import shutil
    models=registry(); disk=shutil.disk_usage(ROOT)
    health_path=ROOT/'data/metadata/health.json'
    return {'hardware':detect_hardware(),'models':models,'cache':str(ROOT/'data/cache'),
            'worker_health':json.loads(health_path.read_text()) if health_path.exists() else {},
            'environments':json.loads(versions.read_text()) if versions.exists() else {},
            'verified_tests':json.loads(evidence.read_text()) if evidence.exists() else {'status':'not yet tested'},
            'disk_free_gb':round(shutil.disk_usage(ROOT).free/2**30,2),
            'disk_used_gb':round(disk.used/2**30,2),'model_download_gb':round(sum(m.get('required_disk_bytes') or 0 for m in models)/2**30,2),
            'privacy':'仅在本机运行。推理进程离线，不向外部 API 上传图片。',
            'repository_commits':json.loads((ROOT/'data/metadata/repository_versions.json').read_text()) if (ROOT/'data/metadata/repository_versions.json').exists() else []}

def make_app():
    records=manifest(); demos=[(Path(r['local_path']).name+' | '+'、'.join(zh(x) for x in r['candidate_objects'][:4]),r['local_path']) for r in records[:10]]
    with gr.Blocks(title='虚构物体工作台',theme=gr.themes.Soft(primary_hue='emerald',neutral_hue='slate'),css=CSS) as app:
        gr.Markdown('# 虚构物体工作台\n本地研究工具 · 真实照片中的虚构物体替换',elem_id='hero')
        gr.Markdown('**操作流程** · ① 上传图片 → ② 检测并选择目标 → ③ 设计概念 → ④ 生成结果。支持中文或英文提示词；概念生成不加载图像模型。')
        verified=system_status()['verified_tests']
        badges=[]
        for name,label in [('brushedit','BrushEdit'),('qwen_image','Qwen 2.1')]:
            status_text='可用（已验证真实推理）' if verified.get(name+'_actual_edit',{}).get('status')=='PASS' else '部分可用（尚未验证推理）'
            entry=next(x for x in registry() if x['pipeline']==name)
            if entry['download_status']!='DOWNLOADED': status_text='不可用（缺少权重）'
            badges.append(f'**{label}: {status_text}**')
        gr.Markdown(' · '.join(badges))
        detection=gr.State(None); concepts=gr.State([]); run_state=gr.State(None)
        with gr.Tabs() as tabs:
            with gr.Tab('单图编辑',id='edit'):
                with gr.Row():
                    with gr.Column(scale=4):
                        image=gr.Image(type='pil',label='原始照片',height=320)
                        demo=gr.Dropdown(demos,label='演示照片',value=None)
                        instruction=gr.Textbox(value='Replace the cup with an unfamiliar manufactured object that does not correspond to a known everyday product.',label='编辑要求（中文 / English）',lines=3)
                        target=gr.Textbox(value='cup',label='目标物体（可选，支持中英文）',placeholder='例如：杯子 / cup、马克杯 / mug、瓶子 / bottle')
                        pipeline=gr.Radio([('A · BrushEdit / BrushNetX','brushedit'),('B · Grounded-SAM-2 + Qwen 2.1','qwen_image')],value='brushedit',label='编辑方案')
                        preset=gr.Dropdown([('保守','conservative'),('均衡','balanced'),('高度新颖','highly_novel'),('实验性','experimental')],value='balanced',label='设计预设')
                        mode=gr.Dropdown([('自主创作','autonomous'),('沿用用户构想','user_concept'),('仅润色细节','minimal_polish'),('概念探索','exploration')],value='user_concept',label='提示词模式',info='默认按你的编辑要求生成；自主创作会额外提供虚构物体设计建议。')
                        with gr.Row():
                            seed=gr.Number(value=42,precision=0,label='随机种子')
                            quality=gr.Dropdown([('预览（已验证）','preview'),('均衡（实验性）','balanced'),('高质量（实验性）','high')],value='preview',label='生成质量')
                        strict=gr.Checkbox(value=True,label='严格保持场景：编辑范围外保留原始像素')
                        with gr.Accordion('高级设置',open=False):
                            novelty=gr.Slider(0,1,value=.75,label='新颖度',step=.05)
                            realism=gr.Slider(0,1,value=.9,label='真实感',step=.05)
                            preservation=gr.Slider(0,1,value=.95,label='场景保持程度',step=.05)
                            complexity=gr.Slider(0,1,value=.55,label='几何复杂度',step=.05)
                            ambiguity=gr.Slider(0,1,value=.75,label='功能模糊度',step=.05)
                            material=gr.Slider(0,1,value=.35,label='材质复杂度',step=.05)
                            dilation=gr.Slider(-1,32,value=-1,step=1,label='蒙版扩张（像素；-1 表示物体宽度的 2%）')
                            feather=gr.Slider(0,20,value=3,step=1,label='向内羽化（像素）')
                            cleanup=gr.Number(value=32,precision=0,label='最小连通区域面积')
                            fillholes=gr.Checkbox(value=True,label='填充目标内部孔洞（包括杯中内容物和透明物体内部）')
                            occluder=gr.Image(type='pil',image_mode='L',label='前景保护蒙版（可选）：白色区域保持不变',height=160)
                        with gr.Accordion('检测候选设置',open=True):
                            search_mode=gr.Radio([('尽量找全（推荐）','broad'),('精确名称','standard')],value='broad',label='检测范围')
                            threshold=gr.Slider(.05,.8,value=.15,step=.01,label='最低置信度（越低候选越多）')
                            max_candidates=gr.Slider(5,100,value=50,step=5,label='最多展示候选数量')
                            extra_queries=gr.Textbox(label='补充检测名称（可选，中英文均可，用逗号分隔）',placeholder='例如：建筑立面、塔楼 / building facade, tower')
                            deduplicate=gr.Checkbox(value=True,label='合并近乎重合的框（保留整体和局部的不同范围）')
                        with gr.Row():
                            analyze_button=gr.Button('分析场景')
                            detect_button=gr.Button('检测目标',variant='primary')
                        instance=gr.Dropdown([],label='选择目标实例（检测到多个物体时必选）',value=None)
                        preview_button=gr.Button('预览蒙版')
                        concepts_button=gr.Button('生成三个概念（不运行图像模型）')
                        run_button=gr.Button('开始生成',variant='primary')
                        clear=gr.ClearButton([image,instruction,target,instance,detection,concepts],value='清空')
                    with gr.Column(scale=7):
                        with gr.Row():
                            boxes_view=gr.Image(label='检测候选框',height=260)
                            mask_view=gr.Image(label='处理后的蒙版叠加',height=260)
                        diagnostic=gr.Markdown('请先选择照片。若检测到多个实例，请选择要编辑的物体。')
                        candidates_view=gr.Gallery(label='检测候选：点击缩略图选择编辑目标',columns=3,height=260,allow_preview=False,object_fit='contain')
                        selection_status=gr.Markdown('**当前编辑目标：** 尚未选择。')
                        with gr.Accordion('场景分析与保守回退信息',open=False): scene_json=gr.JSON(label='场景信息')
                        concept_cards=gr.Markdown('点击“生成三个概念”，探索不同的物体设计。')
                        concept_choice=gr.Radio([('概念 A',0),('概念 B',1),('概念 C',2)],value=0,label='选择概念')
                        with gr.Accordion('可编辑的结构化设计规范',open=False): spec_json=gr.Code(language='json',label='物体设计规范（FakeObjectSpec JSON）',lines=16)
                        compile_button=gr.Button('校验 JSON 并编译提示词')
                        polished=gr.Textbox(label='整理后的编辑提示词',lines=5,interactive=False)
                        backend_prompt=gr.Textbox(label='模型提示词 / 目标描述（可编辑，支持中英文）',lines=5)
                        with gr.Row():
                            raw_output=gr.Image(label='模型原始生成结果',height=330)
                            strict_output=gr.Image(label='严格保持场景的结果',height=330)
                        with gr.Accordion('质量诊断：像素变化与类别相似度',open=False):
                            metrics=gr.JSON(label='诊断结果（不能证明物体不存在）')
                        metadata_file=gr.File(label='本次运行元数据')

            with gr.Tab('方案对比',id='compare'):
                gr.Markdown('使用“单图编辑”中的当前图片、所选实例、概念 JSON 和随机种子。先运行方案 A，再运行方案 B；前一个模型释放显存后才加载下一个。')
                compare_button=gr.Button('依次运行两个方案',variant='primary')
                with gr.Row(): compare_a=gr.Image(label='BrushEdit'); compare_b=gr.Image(label='Qwen 2.1')
                compare_info=gr.JSON(label='对比诊断')

            with gr.Tab('虚构物体设计器',id='designer'):
                gr.Markdown('只生成文本概念，不加载 GPU 模型。评分来自文本启发式规则。支持中英文设计要求；可编辑 JSON 精细调整。')
                dtarget=gr.Textbox(value='mug',label='目标物体（中文 / English）')
                dprompt=gr.Textbox(value='Replace the mug with an unfamiliar manufactured object.',label='设计要求（中文 / English）',lines=3)
                dscene=gr.Code(value='{}',language='json',label='场景 JSON（可选）')
                dmode=gr.Dropdown([('自主创作','autonomous'),('沿用用户构想','user_concept'),('仅润色细节','minimal_polish'),('概念探索','exploration')],value='exploration',label='设计模式')
                dseed=gr.Number(value=42,precision=0,label='随机种子')
                with gr.Row(): dbtn=gr.Button('生成概念',variant='primary'); randomize=gr.Button('随机生成')
                dcards=gr.Markdown(); dstate=gr.State([])
                dchoice=gr.Radio([('概念 A',0),('概念 B',1),('概念 C',2)],value=0,label='概念')
                djson=gr.Code(language='json',lines=18,label='可编辑的设计规范')
                use_design=gr.Button('将此概念用于单图编辑')

            with gr.Tab('检测与蒙版实验室',id='lab'):
                labstate=gr.State(None)
                with gr.Row():
                    li=gr.Image(type='pil',label='照片'); lo=gr.Image(label='全部检测框')
                lt=gr.Textbox(value='cup',label='检测目标词（中文 / English）')
                lmode=gr.Radio([('尽量找全（推荐）','broad'),('精确名称','standard')],value='broad',label='检测范围')
                lth=gr.Slider(.05,.8,value=.15,step=.01,label='最低置信度（越低候选越多）')
                lmax=gr.Slider(5,100,value=50,step=5,label='最多展示候选数量')
                lextra=gr.Textbox(label='补充检测名称（可选，用逗号分隔）')
                ldedup=gr.Checkbox(value=True,label='合并近乎重合的框（保留整体和局部的不同范围）')
                lbtn=gr.Button('检测',variant='primary')
                lsummary=gr.Markdown()
                lgallery=gr.Gallery(label='检测候选：点击缩略图选择',columns=4,height=260,allow_preview=False,object_fit='contain')
                linst=gr.Dropdown([],label='选择目标实例')
                with gr.Row():
                    ld=gr.Slider(0,32,value=8,step=1,label='扩张（像素）'); lf=gr.Slider(0,20,value=3,step=1,label='羽化（像素）'); lc=gr.Number(value=32,label='清理区域面积',precision=0)
                lholes=gr.Checkbox(value=True,label='填充目标内部孔洞；需要保留原有孔洞时请关闭')
                lpreview=gr.Button('预览所选蒙版')
                with gr.Row(): lr=gr.Image(label='原始蒙版'); lp=gr.Image(label='处理后的蒙版'); la=gr.Image(label='透明度 / 柔和蒙版'); lv=gr.Image(label='蒙版叠加')
                linfo=gr.JSON()

            with gr.Tab('数据集浏览',id='dataset'):
                gr.Markdown('COCO 验证集子集：逐图记录来源和许可证。数据标记为仅供测试（TEST_ONLY），不自动推断训练使用许可。')
                dataset=gr.Dropdown([(Path(r['local_path']).name,r['local_path']) for r in records],label='图片')
                with gr.Row(): dsimage=gr.Image(); dsinfo=gr.JSON(label='来源 / 许可证 / 候选物体')
                open_dataset=gr.Button('在单图编辑中打开')

            with gr.Tab('结果与历史',id='history'):
                with gr.Row():
                    hpipeline=gr.Dropdown([('全部','all'),('BrushEdit','brushedit'),('Qwen 2.1','qwen_image')],value='all',label='编辑方案')
                    htarget=gr.Textbox(label='目标名称包含'); hdate=gr.Textbox(label='日期（YYYY-MM-DD）'); hfailure=gr.Textbox(label='警告内容包含')
                refresh=gr.Button('刷新历史记录'); history=gr.Dropdown([],label='已保存运行记录'); gallery=gr.Gallery(label='生成结果',columns=4,height=300); hjson=gr.JSON()
                gr.Markdown('人工评分（1–5 分）；未提交的评分不会自动计入。')
                with gr.Row(): ratings=[gr.Slider(1,5,value=3,step=1,label=x) for x in ['真实感','新颖度','场景保持程度','物体融入程度']]
                removed=gr.Checkbox(label='原物体已完全移除'); usable=gr.Checkbox(label='整体结果可用'); save_rating=gr.Button('保存评分'); rating_msg=gr.Markdown()

            with gr.Tab('系统状态',id='system'):
                gr.Markdown('“可用”表示已完成并保存真实推理结果。仅通过环境检查时显示“部分可用”。未启用云端 API。技术 JSON 保留原字段名，便于排查和复现。')
                status=gr.JSON(value=system_status()); refresh_status=gr.Button('刷新系统状态')

        def cards(specs):
            chunks=[]
            for i,s in enumerate(specs):
                f=s.fictional_object
                chunks.append(f'### 概念 {chr(65+i)} · {zh(f.short_identifier)}\n{zh(f.primary_geometry)}；'+'、'.join(zh(x) for x in f.secondary_structure)+'。\n\n**材质：** '+'、'.join(zh(x) for x in f.materials)+' · **颜色：** '+'、'.join(zh(x) for x in f.colors)+'\n\n**避免类似：** '+'、'.join(zh(x) for x in s.novelty_constraints)+f'\n\n文本启发式评分 — 新颖度 {s.scores.novelty_score:.2f} / 物理合理性 {s.scores.plausibility_score:.2f}')
            return '\n\n---\n\n'.join(chunks)

        @guarded
        def ui_detect(im,prompt,t,th,scope,limit,extra,dedup):
            t=infer_target(prompt,t); result=detect(im,t,th,scope,int(limit),extra,dedup)
            choices=candidate_choices(result)
            return result,result['bbox_visualization'],gr.update(choices=choices,value=0 if len(choices)==1 else None),detection_summary(result),t,candidate_gallery(result),None

        @guarded
        def ui_preview(im,det,idx,d,f,c,occ,holes):
            if not det: return None
            if idx is None and det and len(det.get('masks',[]))!=1: return None
            im=load_image(im)
            if not det or det['image_hash']!=fingerprint(im): raise ValueError('Detect the current image first.')
            raw=select_mask(det,idx); hard,alpha=process_mask(raw,mask_dilation_px=d,mask_feather_px=f,cleanup_min_component=c,preserve_occluders=occ,fill_holes=holes)
            return mask_overlay(im,hard)

        @guarded
        def selection_changed(im,det,idx,d,f,c,occ,holes):
            preview=ui_preview(im,det,idx,d,f,c,occ,holes)
            selected='**当前编辑目标：** 尚未选择。'
            if det and (idx is not None or len(det.get('masks',[]))==1):
                index=0 if idx is None else int(idx)
                region=describe_selected_region(det,index,select_mask(det,index))
                selected=f"**当前编辑目标：候选 {index+1} · {zh(region['label'])}**。生成使用此候选的完整蒙版（{region['mask_pixels']:,} 像素）。"
            # A previous result must not appear to belong to a newly selected object.
            return preview,selected,None,None,{},None,None

        @guarded
        def ui_concepts(im,prompt,t,s,p,m,n,r,pr,g,a,mc,det,idx):
            t=infer_target(prompt,t)
            mask=None
            if im is not None and det and det.get('image_hash')==fingerprint(load_image(im)) and (idx is not None or len(det.get('masks',[]))==1): mask=select_mask(det,idx)
            scene=analyze_scene(load_image(im),mask,t) if im is not None else {}
            specs=generate_concepts(prompt,t,scene,int(s),p,m,Controls(novelty=n,realism=r,preservation=pr,geometry_complexity=g,functional_ambiguity=a,material_complexity=mc))
            return [x.model_dump() for x in specs],cards(specs),scene,gr.update(value=0)

        @guarded
        def choose(items,index,pipe):
            if not items: return '','',''
            s=FakeObjectSpec.model_validate(items[int(index)])
            return s.model_dump_json(indent=2),compile_prompt(s,'qwen_image'),compile_prompt(s,pipe)

        @guarded
        def compile_json(text,pipe):
            from src.prompting.prompt_validator import validate_spec
            s=validate_spec(FakeObjectSpec.model_validate_json(text)); return compile_prompt(s,'qwen_image'),compile_prompt(s,pipe)

        @guarded
        def edit_cb(im,pipe,prompt,t,idx,s,strict_mode,q,det,sjson,bprompt,d,f,c,occ,holes,pmode,progress=gr.Progress()):
            progress(.05,desc='正在校验目标、概念和蒙版')
            spec=FakeObjectSpec.model_validate_json(sjson) if sjson else None
            progress(.15,desc='正在运行 GPU 模型，首次加载可能需要几分钟')
            result=run_edit(im,pipe,prompt,t,idx,int(s),strict_mode,q,det,spec,bprompt,{'mask_dilation_px':d,'mask_feather_px':f,'cleanup_min_component':int(c),'fill_holes':holes},occ,prompt_mode=pmode)
            progress(1,desc='已保存运行记录')
            region=result.selected_region
            scope=f"本次结果对应 **候选 {region['display_number']} · {zh(region['label'])}**。\n\n" if region else ''
            return result.raw_model_output,result.strict_output,result.evaluation,scope+f'**{zh(result.status)}** · 耗时 {result.runtime["total"]:.1f} 秒\n\n'+'\n\n'.join(message(w) for w in result.warnings),str(Path(result.output_dir)/'metadata.json'),result.model_dump()

        @guarded
        def compare_cb(im,prompt,t,idx,s,q,det,sjson,d,f,c,occ,holes,pmode,progress=gr.Progress()):
            spec=FakeObjectSpec.model_validate_json(sjson) if sjson else generate_concepts(prompt,infer_target(prompt,t),seed=int(s),mode=pmode)[0]
            outputs=[]; reports=[]
            for i,pipe in enumerate(['brushedit','qwen_image']):
                progress(i/2,desc=f'正在运行 {pipe}')
                r=run_edit(im,pipe,prompt,t,idx,int(s),True,q,det,spec,None,{'mask_dilation_px':d,'mask_feather_px':f,'cleanup_min_component':int(c),'fill_holes':holes},occ)
                outputs.append(r.strict_output); reports.append(r.model_dump())
            return *outputs,reports

        def preset_change(p):
            c=Controls(**config('fake_object_skill')['presets'][p]); return c.novelty,c.realism,c.preservation,c.geometry_complexity,c.functional_ambiguity,c.material_complexity

        demo.change(lambda p: str(ROOT/p) if p else None,demo,image)
        preset.change(preset_change,preset,[novelty,realism,preservation,complexity,ambiguity,material])
        analyze_button.click(guarded(lambda im,t: analyze_scene(load_image(im),target=t or 'object')),[image,target],scene_json)
        search_mode.change(lambda scope:.15 if scope=='broad' else .3,search_mode,threshold)
        detect_button.click(ui_detect,[image,instruction,target,threshold,search_mode,max_candidates,extra_queries,deduplicate],[detection,boxes_view,instance,diagnostic,target,candidates_view,mask_view])
        def pick_candidate(det,evt: gr.SelectData):
            if not evt.selected or not det: return gr.skip()
            index=int(evt.index)
            return index if 0<=index<len(det['masks']) else gr.skip()
        candidates_view.select(pick_candidate,detection,instance)
        preview_button.click(ui_preview,[image,detection,instance,dilation,feather,cleanup,occluder,fillholes],mask_view)
        instance.change(selection_changed,[image,detection,instance,dilation,feather,cleanup,occluder,fillholes],[mask_view,selection_status,raw_output,strict_output,metrics,metadata_file,run_state],trigger_mode='once')
        concepts_button.click(ui_concepts,[image,instruction,target,seed,preset,mode,novelty,realism,preservation,complexity,ambiguity,material,detection,instance],[concepts,concept_cards,scene_json,concept_choice]).then(choose,[concepts,concept_choice,pipeline],[spec_json,polished,backend_prompt])
        concept_choice.change(choose,[concepts,concept_choice,pipeline],[spec_json,polished,backend_prompt])
        compile_button.click(compile_json,[spec_json,pipeline],[polished,backend_prompt])
        pipeline.change(guarded(lambda text,p: compile_json(text,p) if text else ('','')),[spec_json,pipeline],[polished,backend_prompt])
        mode.change(lambda:([],'提示词模式已更新，可重新生成概念，也可直接开始生成。','','',''),outputs=[concepts,concept_cards,spec_json,polished,backend_prompt])
        run_button.click(edit_cb,[image,pipeline,instruction,target,instance,seed,strict,quality,detection,spec_json,backend_prompt,dilation,feather,cleanup,occluder,fillholes,mode],[raw_output,strict_output,metrics,diagnostic,metadata_file,run_state])
        compare_button.click(compare_cb,[image,instruction,target,instance,seed,quality,detection,spec_json,dilation,feather,cleanup,occluder,fillholes,mode],[compare_a,compare_b,compare_info])
        image.change(lambda:(None,[],None,None,'','','',None,None,{},None,[],gr.update(choices=[],value=None)),outputs=[detection,concepts,boxes_view,mask_view,spec_json,polished,backend_prompt,raw_output,strict_output,metrics,metadata_file,candidates_view,instance])

        @guarded
        def designer_cb(t,p,scene,s,m):
            specs=generate_concepts(p,t,json.loads(scene or '{}'),int(s),mode=m)
            return [x.model_dump() for x in specs],cards(specs),specs[0].model_dump_json(indent=2),gr.update(value=0)
        dbtn.click(designer_cb,[dtarget,dprompt,dscene,dseed,dmode],[dstate,dcards,djson,dchoice])
        randomize.click(lambda: __import__('secrets').randbelow(2**31),outputs=dseed).then(designer_cb,[dtarget,dprompt,dscene,dseed,dmode],[dstate,dcards,djson,dchoice])
        dchoice.change(guarded(lambda items,i: FakeObjectSpec.model_validate(items[int(i)]).model_dump_json(indent=2)),[dstate,dchoice],djson)
        @guarded
        def transfer(text,pipe):
            s=FakeObjectSpec.model_validate_json(text)
            return s.target_object,s.raw_user_prompt,text,compile_prompt(s,'qwen_image'),compile_prompt(s,pipe),gr.update(selected='edit')
        use_design.click(transfer,[djson,pipeline],[target,instruction,spec_json,polished,backend_prompt,tabs])
        @guarded
        def labdetect(im,t,th,scope,limit,extra,dedup):
            r=detect(im,t,th,scope,int(limit),extra,dedup)
            return r,r['bbox_visualization'],gr.update(choices=candidate_choices(r),value=0 if len(r['masks'])==1 else None),r,candidate_gallery(r),detection_summary(r),None,None,None,None
        lmode.change(lambda scope:.15 if scope=='broad' else .3,lmode,lth)
        lbtn.click(labdetect,[li,lt,lth,lmode,lmax,lextra,ldedup],[labstate,lo,linst,linfo,lgallery,lsummary,lr,lp,la,lv])
        lgallery.select(pick_candidate,labstate,linst)
        @guarded
        def labpreview(im,det,i,d,f,c,holes):
            if not det: return None,None,None,None
            if i is None and det and len(det.get('masks',[]))!=1: return None,None,None,None
            im=load_image(im)
            if not det or det['image_hash']!=fingerprint(im): raise ValueError('Detect the current image first.')
            raw=select_mask(det,i); hard,alpha=process_mask(raw,mask_dilation_px=d,mask_feather_px=f,cleanup_min_component=c,fill_holes=holes); return raw,hard,alpha,mask_overlay(im,hard)
        lpreview.click(labpreview,[li,labstate,linst,ld,lf,lc,lholes],[lr,lp,la,lv])
        linst.change(labpreview,[li,labstate,linst,ld,lf,lc,lholes],[lr,lp,la,lv],trigger_mode='once')
        li.change(lambda:(None,None,gr.update(choices=[],value=None),[],None,None,None,None,{},''),outputs=[labstate,lo,linst,lgallery,lr,lp,la,lv,linfo,lsummary])
        dataset.change(lambda p:(str(ROOT/p),next(r for r in records if r['local_path']==p)),dataset,[dsimage,dsinfo])
        open_dataset.click(lambda p:(str(ROOT/p),gr.update(selected='edit')),dataset,[image,tabs])

        def history_list(pipe,t,date,failure):
            items=[]; imgs=[]
            for p in sorted((ROOT/'data/outputs').glob('*/*/metadata.json'),reverse=True):
                r=json.loads(p.read_text(encoding='utf-8'))
                if pipe!='all' and r['pipeline']!=pipe: continue
                if t.lower() not in r['target_object'].lower() or date not in str(p) or failure.lower() not in str(r['warnings']).lower(): continue
                items.append((r['run_id']+' · '+r['pipeline']+' · '+zh(r['status']),str(p)))
                if r.get('strict_output'): imgs.append((r['strict_output'],r['run_id']))
            return gr.update(choices=items,value=items[0][1] if items else None),imgs[:40]
        refresh.click(history_list,[hpipeline,htarget,hdate,hfailure],[history,gallery])
        history.change(lambda p:json.loads(Path(p).read_text(encoding='utf-8')) if p else {},history,hjson)
        @guarded
        def rate(p,*values):
            if not p: raise ValueError('Select a saved run first.')
            path=Path(p).resolve()
            if not path.is_relative_to((ROOT/'data/outputs').resolve()): raise ValueError('Invalid result path.')
            r=json.loads(path.read_text(encoding='utf-8')); r['human_ratings']=dict(zip(['realism','novelty','scene_preservation','integration','source_removed','usable'],values))
            path.write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8'); return '评分已保存。'
        save_rating.click(rate,[history,*ratings,removed,usable],rating_msg)
        refresh_status.click(system_status,outputs=status)
    return app

def main():
    cfg=config('app')
    make_app().queue(default_concurrency_limit=1).launch(server_name='127.0.0.1',server_port=int(os.getenv('FAKE_OBJECT_PORT',cfg['port'])),share=False,show_error=False,allowed_paths=[str(ROOT/'data')],i18n=builtin_i18n())

if __name__=='__main__': main()
