#!/usr/bin/env python3
"""
dialog_render.py
渲染discuss对话YAML，输出：
1. interactive.html 交互式网页(头像+音频base64内嵌，浅色/深色主题切换)
2. output.pdf A4打印PDF(无音频，打印友好)
3. 分页png序列 1080x1920 9:16纵向截图
依赖：pyyaml, jinja2, playwright, Pillow
"""
import colorsys
import json
import os
import base64
import argparse
import yaml
from io import BytesIO
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright
from PIL import Image

# -------------------------- 常量配置 --------------------------
PDF_PAGE_FORMAT = "A4"
PDF_MARGIN_TOP = "15mm"
PDF_MARGIN_BOTTOM = "15mm"
PDF_MARGIN_LEFT = "15mm"
PDF_MARGIN_RIGHT = "15mm"
PNG_VIEWPORT_WIDTH = 1080
PNG_VIEWPORT_HEIGHT = 1920
AVATAR_THUMB_SIZE = (64, 64)  # 输出给HTML的缩略图尺寸
FALLBACK_BUBBLE_RGBA = "rgba(220,220,220,0.3)"
COLOR_BRIGHT_SCALE = 0.65   # 颜色亮度缩放，原0.5调至0.65提升色彩辨识度
COLOR_ALPHA = 0.35          # 气泡透明度调高
WHITE_THRESHOLD = 240       # 过滤接近纯白像素，R>G>B全部大于该值直接丢弃
SCRIPT_DIR = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))

# ===================== 主题色提取可调参数（全部在这里改） =====================
# 浅色网页端 对比度目标（WCAG AA）
LIGHT_MODE_CONTRAST_TARGET = 4.5
# PDF / PNG 导出时，对比度目标（更高）
EXPORT_CONTRAST_TARGET = 5.0
# 饱和度下限，防止颜色被压成灰
MIN_SATURATION = 0.30
# 提取候选主色数量
CANDIDATE_COLOR_COUNT = 3
# 浅色模式文字：黑色
LIGHT_TEXT_RGB = (0, 0, 0)
# 深色模式文字：白色（仅记录，不做强制校验）
DARK_TEXT_RGB = (255, 255, 255)
# 明度迭代步长，迭代找达标色时的精度
LIGHTNESS_STEP = 0.01
# ==========================================================================


def read_file_as_b64(file_path: str, mime_type: str) -> str:
    """读取二进制文件返回 base64 data‑url字符串"""
    with open(file_path, "rb") as f:
        data = f.read()
    b64 = base64.b64encode(data).decode("utf‑8")
    return f"data:{mime_type};base64,{b64}"


def image_to_thumb_b64(img: Image.Image) -> str:
    """
    将PIL Image对象生成64x64缩略图，返回png data‑url base64
    保持宽高比，缩放放入AVATAR_THUMB_SIZE
    """
    im_copy = img.copy()
    im_copy.thumbnail(AVATAR_THUMB_SIZE, Image.Resampling.LANCZOS)
    buf = BytesIO()
    im_copy.save(buf, format="PNG")
    b64_data = base64.b64encode(buf.getvalue()).decode("utf‑8")
    return f"data:image/png;base64,{b64_data}"


def load_cast_yaml(cast_dir: Path) -> dict:
    """
    读取cast_dir/cast_00001_.yaml，返回 {name: full_name}
    文件缺失/解析异常返回空dict，不抛出异常
    """
    cast_yaml_path = cast_dir / "cast_00001_.yaml"
    sp_fullname_map = {}
    if not cast_yaml_path.exists():
        print(f"[INFO] cast yaml不存在: {cast_yaml_path}，跳过full_name读取")
        return sp_fullname_map
    try:
        with open(cast_yaml_path, "r", encoding="utf‑8") as f:
            cast_list = yaml.safe_load(f)
        if isinstance(cast_list, list):
            for item in cast_list:
                name = item.get("name", "").strip()
                full_name = item.get("full_name", "").strip()
                if name and full_name:
                    sp_fullname_map[name] = full_name
        print(f"[INFO]成功加载cast_00001_.yaml，共{len(sp_fullname_map)}位speaker")
    except Exception as e:
        print(f"[WARN]解析cast_00001_.yaml失败 err={e}")
    return sp_fullname_map

def relative_luminance(r: float, g: float, b: float) -> float:
    """计算相对亮度，标准WCAG公式，输入0~1"""
    def f(v):
        if v <= 0.03928:
            return v / 12.92
        else:
            return ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

def contrast_ratio(l1: float, l2: float) -> float:
    """对比度 l1、l2 是两个颜色的相对亮度"""
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

def adjust_color_for_light_mode(h: float, s: float, l: float, target_contrast: float) -> tuple[float, float, float]:
    """
    锁定色相h、尽量保住饱和度s，只调整明度，直到满足对比度
    h,s,l 范围都是0~1
    前景固定是黑色文字 LIGHT_TEXT_RGB
    """
    # 黑色的相对亮度
    lum_text = relative_luminance(0,0,0)
    current_s = max(s, MIN_SATURATION)
    current_l = l
    # 先尝试加深（降低明度，提高和黑字的反差）
    while True:
        r,g,b = colorsys.hls_to_rgb(h, current_l, current_s)
        lum_bg = relative_luminance(r,g,b)
        cr = contrast_ratio(lum_bg, lum_text)
        if cr >= target_contrast or current_l <= 0.01:
            break
        current_l -= LIGHTNESS_STEP
    # 迭代完还不够，才放宽饱和度兜底
    if cr < target_contrast:
        current_s = s
        while True:
            r,g,b = colorsys.hls_to_rgb(h, current_l, current_s)
            lum_bg = relative_luminance(r,g,b)
            cr = contrast_ratio(lum_bg, lum_text)
            if cr >= target_contrast or current_s <= 0:
                break
            current_s -= LIGHTNESS_STEP
    return h, current_s, current_l

def pick_best_theme_color(candidate_rgb_list: list[tuple[int,int,int]], is_export: bool) -> tuple[tuple[int,int,int], tuple[int,int,int]]:
    """
    输入：候选RGB列表 [(r,g,b),...] 0~255
    is_export=True → PDF/PNG，用更高对比度目标
    返回：(浅色背景RGB, 深色派生背景RGB)
    深色：复用h,s，翻转明度逻辑，不校验对比度
    """
    target_cr = EXPORT_CONTRAST_TARGET if is_export else LIGHT_MODE_CONTRAST_TARGET
    lum_text = relative_luminance(0,0,0)
    best_hsl = None
    best_cr = 0.0
    # 遍历候选色，优先挑原生就达标的
    for r8,g8,b8 in candidate_rgb_list[:CANDIDATE_COLOR_COUNT]:
        r,g,b = r8/255.0, g8/255.0, b8/255.0
        h,l,s = colorsys.rgb_to_hls(r,g,b)
        lum_bg = relative_luminance(r,g,b)
        cr = contrast_ratio(lum_bg, lum_text)
        if cr >= target_cr:
            best_hsl = (h,s,l)
            best_cr = cr
            break
    # 没有原生达标候选，拿第一个候选做明度调整
    if best_hsl is None:
        r8,g8,b8 = candidate_rgb_list[0]
        r,g,b = r8/255.0, g8/255.0, b8/255.0
        h,l,s = colorsys.rgb_to_hls(r,g,b)
        h_fix, s_fix, l_fix = adjust_color_for_light_mode(h, s, l, target_cr)
        best_hsl = (h_fix, s_fix, l_fix)

    h_final, s_final, l_light = best_hsl
    # 浅色模式rgb
    lr, lg, lb = colorsys.hls_to_rgb(h_final, l_light, s_final)
    light_rgb = (int(lr*255), int(lg*255), int(lb*255))
    # 深色派生：同h、s，明度取 1 - l_light，不校验对比度
    l_dark = 1.0 - l_light
    dr, dg, db = colorsys.hls_to_rgb(h_final, l_dark, s_final)
    dark_rgb = (int(dr*255), int(dg*255), int(db*255))
    return light_rgb, dark_rgb

def get_image_dominant_rgba(img_path: Path) -> str:
    """
    WCAG对比度版本：过滤纯白像素，取top候选色，迭代明度保证文字可读性
    返回 rgba(r,g,b,COLOR_ALPHA)；异常返回fallback
    """
    try:
        with Image.open(img_path) as im:
            im_rgb = im.convert("RGB")
            im_small = im_rgb.copy()
            im_small.thumbnail((120, 120))
            pixels = list(im_small.getdata())
            freq = {}
            for pix in pixels:
                r, g, b = pix
                # 过滤接近纯白背景
                if r > WHITE_THRESHOLD and g > WHITE_THRESHOLD and b > WHITE_THRESHOLD:
                    continue
                freq[pix] = freq.get(pix, 0) + 1
            if len(freq) == 0:
                return FALLBACK_BUBBLE_RGBA
            # 按频次降序取候选色列表
            sorted_items = sorted(freq.items(), key=lambda x:x[1], reverse=True)
            candidate_rgb_list = [item[0] for item in sorted_items[:CANDIDATE_COLOR_COUNT]]
            # is_export=False：网页交互模式；PDF/PNG也复用这套，alpha外层控制
            light_rgb, _ = pick_best_theme_color(candidate_rgb_list, is_export=False)
            r, g, b = light_rgb
            return f"rgba({r},{g},{b},{COLOR_ALPHA})"
    except Exception as e:
        print(f"[COLOR_EXTRACT_WARN] {img_path}, err:{e}")
        return FALLBACK_BUBBLE_RGBA


def merge_consecutive_speaker(pd_list: list):
    """
    合并连续同一个sp的台词，输出气泡单元列表
    bubble_item = {
        "sp": str,
        "txt_list": [str,...],
    }
    """
    bubbles = []
    if not isinstance(pd_list, list) or len(pd_list) == 0:
        return bubbles
    current_sp = None
    current_texts = []
    for entry in pd_list:
        sp = entry.get("sp", "").strip()
        txt = entry.get("txt", "").strip()
        if not sp or not txt:
            continue
        if sp == current_sp:
            current_texts.append(txt)
        else:
            if current_sp is not None:
                bubbles.append({"sp": current_sp, "txt_list": current_texts})
            current_sp = sp
            current_texts = [txt]
    if current_sp is not None:
        bubbles.append({"sp": current_sp, "txt_list": current_texts})
    return bubbles


def preload_speaker_assets(cast_dir: Path, sp_set: set, sp_fullname_map: dict):
    """
    全局预加载全部speaker头像资源，sp做缓存，只处理一次
    返回 dict[sp] = {"avatar_b64": str|None, "bubble_bg": str, "full_name": str|None}
    """
    sp_asset_cache = {}
    for sp in sp_set:
        avatar_filename = f"{sp}_00001_.png"
        avatar_path = cast_dir / avatar_filename
        avatar_b64 = None
        bubble_bg = FALLBACK_BUBBLE_RGBA
        full_name = sp_fullname_map.get(sp, None)
        if avatar_path.exists():
            try:
                with Image.open(avatar_path) as im_origin:
                    bubble_bg = get_image_dominant_rgba(avatar_path)
                    avatar_b64 = image_to_thumb_b64(im_origin)
            except Exception as e:
                print(f"[AVATAR_WARN] sp={sp}, file={avatar_path}, err={e}")
        else:
            print(f"[AVATAR_WARN] sp={sp} avatar not found: {avatar_path}")
        sp_asset_cache[sp] = {
            "avatar_b64": avatar_b64,
            "bubble_bg": bubble_bg,
            "full_name": full_name
        }
    return sp_asset_cache


def collect_all_speakers(groups_raw):
    """遍历全部group pd，收集所有出现过的sp名称集合，用于预加载头像资源"""
    sp_set = set()
    for g_raw in groups_raw:
        pd_list = g_raw.get("a", {}).get("pd", [])
        if not isinstance(pd_list, list):
            continue
        for entry in pd_list:
            sp = entry.get("sp", "").strip()
            if sp:
                sp_set.add(sp)
    return sp_set


def build_group_context(g_raw, group_idx: int, sp_asset_cache: dict, audio_dir: Path):
    """
    处理单个group：合并气泡；头像/颜色/full_name直接取全局缓存；加载group音频base64
    返回 group_ctx dict，pd为空返回None(该group跳过渲染)
    """
    gt = g_raw.get("gt", "")
    pd_list = g_raw.get("a", {}).get("pd", [])
    bubble_list = merge_consecutive_speaker(pd_list)
    if len(bubble_list) == 0:
        return None

    processed_bubbles = []
    for b in bubble_list:
        sp = b["sp"]
        cache_item = sp_asset_cache[sp]
        processed_bubbles.append({
            "sp": sp,
            "txt_list": b["txt_list"],
            "avatar_b64": cache_item["avatar_b64"],
            "bubble_bg": cache_item["bubble_bg"],
            "full_name": cache_item["full_name"]
        })

    # 读取group对应音频
    audio_filename = f"_groups_{group_idx}_a.wav"
    audio_path = audio_dir / audio_filename
    group_audio_b64 = None
    if audio_path.exists():
        try:
            group_audio_b64 = read_file_as_b64(str(audio_path), "audio/wav")
        except Exception as e:
            print(f"[AUDIO_WARN] group {group_idx} file={audio_path}, err={e}")
    else:
        print(f"[AUDIO_WARN] group {group_idx} audio not found: {audio_path}")

    return {
        "gt": gt,
        "bubbles": processed_bubbles,
        "group_audio_b64": group_audio_b64
    }


def render_html(tpl_env, tpl_name: str, context: dict) -> str:
    tpl = tpl_env.get_template(tpl_name)
    return tpl.render(**context)


def html_to_pdf(html_content: str, output_pdf_path: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        page.wait_for_load_state("networkidle")
        pdf_opts = {
            "format": PDF_PAGE_FORMAT,
            "margin": {
                "top": PDF_MARGIN_TOP,
                "bottom": PDF_MARGIN_BOTTOM,
                "left": PDF_MARGIN_LEFT,
                "right": PDF_MARGIN_RIGHT,
            },
            "print_background": True
        }
        page.pdf(path=output_pdf_path, **pdf_opts)
        browser.close()


def html_to_paginated_png(html_content: str, out_prefix: str):
    """
    固定视口1080*1920，滚动分页截图
    out_prefix: 输出文件前缀，生成 prefix_000.png, prefix_001.png ...
    """
    out_files = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": PNG_VIEWPORT_WIDTH, "height": PNG_VIEWPORT_HEIGHT})
        page.set_content(html_content)
        page.wait_for_load_state("networkidle")
        scroll_height = page.evaluate("document.body.scrollHeight")
        view_h = PNG_VIEWPORT_HEIGHT
        page_idx = 0
        offset = 0
        while offset < scroll_height:
            page.evaluate(f"window.scrollTo(0, {offset})")
            page.wait_for_timeout(80)
            out_path = f"{out_prefix}_{page_idx:03d}.png"
            page.screenshot(path=out_path, full_page=False)
            out_files.append(out_path)
            offset += view_h
            page_idx += 1
        browser.close()
    return out_files

async def html_to_pdf_async(html_content: str, output_pdf_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html_content)
        await page.wait_for_load_state("networkidle")
        pdf_opts = {
            "format": PDF_PAGE_FORMAT,
            "margin": {
                "top": PDF_MARGIN_TOP,
                "bottom": PDF_MARGIN_BOTTOM,
                "left": PDF_MARGIN_LEFT,
                "right": PDF_MARGIN_RIGHT,
            },
            "print_background": True
        }
        await page.pdf(path=output_pdf_path, **pdf_opts)
        await browser.close()


async def html_to_paginated_png_async(html_content: str, out_prefix: str):
    """异步版本 固定视口1080*1920，滚动分页截图"""
    out_files = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": PNG_VIEWPORT_WIDTH, "height": PNG_VIEWPORT_HEIGHT})
        await page.set_content(html_content)
        await page.wait_for_load_state("networkidle")
        scroll_height = await page.evaluate("document.body.scrollHeight")
        view_h = PNG_VIEWPORT_HEIGHT
        page_idx = 0
        offset = 0
        while offset < scroll_height:
            await page.evaluate(f"window.scrollTo(0, {offset})")
            await page.wait_for_timeout(80)
            out_path = f"{out_prefix}_{page_idx:03d}.png"
            await page.screenshot(path=out_path, full_page=False)
            out_files.append(out_path)
            offset += view_h
            page_idx += 1
        await browser.close()
    return out_files

def render_dialogue(
    yaml_path: Path,
    cast_dir: Path,
    audio_dir: Path,
    template_dir: Path,
    output_base_dir: Path,
):
    """
    供ComfyUI节点调用的对外API
    返回 (html_output_path: Path, pdf_output_path: Path)
    """
    # 内部复用原有业务逻辑，不要调用main()
    yaml_abs = yaml_path.resolve()
    cast_dir = cast_dir.resolve()
    audio_dir = audio_dir.resolve()
    output_base_dir = output_base_dir.resolve()

    with open(yaml_abs, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    quiz_meta = raw_data.get("quiz_meta", {})
    groups_raw = raw_data.get("groups", [])

    sp_fullname_map = load_cast_yaml(cast_dir)
    all_sp_set = collect_all_speakers(groups_raw)
    sp_asset_cache = preload_speaker_assets(cast_dir, all_sp_set, sp_fullname_map)

    group_ctx_list = []
    for g_idx, g_raw in enumerate(groups_raw):
        g_ctx = build_group_context(g_raw, g_idx, sp_asset_cache, audio_dir)
        if g_ctx is not None:
            group_ctx_list.append(g_ctx)

    jinja_env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    def json_filter(val):
        return json.dumps(val, ensure_ascii=False)
    jinja_env.filters["tojson"] = json_filter

    render_ctx = {
        "quiz_meta": quiz_meta,
        "groups": group_ctx_list
    }

    basename_stem = yaml_abs.stem
    html_interactive = render_html(jinja_env, "dialog_interactive.html.j2", render_ctx)
    html_interactive_path = output_base_dir / f"{basename_stem}_interactive.html"
    with open(html_interactive_path, "w", encoding="utf-8") as f:
        f.write(html_interactive)

    html_pdf_content = render_html(jinja_env, "dialog_print_pdf.html.j2", render_ctx)
    pdf_out_path = output_base_dir / f"{basename_stem}.pdf"
    html_to_pdf(html_pdf_content, str(pdf_out_path))

    html_png_content = render_html(jinja_env, "dialog_snapshot_png.html.j2", render_ctx)
    png_prefix = str(output_base_dir / f"{basename_stem}_snap")
    html_to_paginated_png(html_png_content, png_prefix)

    return html_interactive_path, pdf_out_path

async def render_dialogue_async(
    yaml_path: Path,
    cast_dir: Path,
    audio_dir: Path,
    template_dir: Path,
    output_base_dir: Path,
):
    """
    【供ComfyUI async节点调用】异步版本对外API
    返回 (html_output_path: Path, pdf_output_path: Path)
    """
    yaml_abs = yaml_path.resolve()
    cast_dir = cast_dir.resolve()
    audio_dir = audio_dir.resolve()
    output_base_dir = output_base_dir.resolve()

    with open(yaml_abs, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)

    quiz_meta = raw_data.get("quiz_meta", {})
    groups_raw = raw_data.get("groups", [])

    sp_fullname_map = load_cast_yaml(cast_dir)
    all_sp_set = collect_all_speakers(groups_raw)
    sp_asset_cache = preload_speaker_assets(cast_dir, all_sp_set, sp_fullname_map)

    group_ctx_list = []
    for g_idx, g_raw in enumerate(groups_raw):
        g_ctx = build_group_context(g_raw, g_idx, sp_asset_cache, audio_dir)
        if g_ctx is not None:
            group_ctx_list.append(g_ctx)

    jinja_env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
    def json_filter(val):
        return json.dumps(val, ensure_ascii=False)
    jinja_env.filters["tojson"] = json_filter

    render_ctx = {
        "quiz_meta": quiz_meta,
        "groups": group_ctx_list
    }

    basename_stem = yaml_abs.stem
    html_interactive = render_html(jinja_env, "dialog_interactive.html.j2", render_ctx)
    html_interactive_path = output_base_dir / f"{basename_stem}_interactive.html"
    with open(html_interactive_path, "w", encoding="utf-8") as f:
        f.write(html_interactive)

    html_pdf_content = render_html(jinja_env, "dialog_print_pdf.html.j2", render_ctx)
    pdf_out_path = output_base_dir / f"{basename_stem}.pdf"
    await html_to_pdf_async(html_pdf_content, str(pdf_out_path))

    html_png_content = render_html(jinja_env, "dialog_snapshot_png.html.j2", render_ctx)
    png_prefix = str(output_base_dir / f"{basename_stem}_snap")
    await html_to_paginated_png_async(html_png_content, png_prefix)

    return html_interactive_path, pdf_out_path

def main():
    parser = argparse.ArgumentParser(description="Dialog YAML render: interactive.html / output.pdf / 分页png")
    parser.add_argument("discuss_yaml", help="path to discuss dialog yaml file")
    parser.add_argument("-c", "--cast_dir", required=True, help="角色头像资源目录，存放 {sp}_00001_.png，可选cast_00001_.yaml")
    parser.add_argument("-a", "--audio_dir", required=True, help="group合成wav音频目录 _groups_{idx}_a.wav")
    parser.add_argument("--template_dir", default=SCRIPT_DIR, help="jinja2模板文件夹路径")
    args = parser.parse_args()

    yaml_abs = Path(args.discuss_yaml).resolve()
    yaml_base_dir = yaml_abs.parent
    cast_dir = Path(args.cast_dir).resolve()
    audio_dir = Path(args.audio_dir).resolve()

    with open(yaml_abs, "r", encoding="utf‑8") as f:
        raw_data = yaml.safe_load(f)

    quiz_meta = raw_data.get("quiz_meta", {})
    groups_raw = raw_data.get("groups", [])

    # 加载cast yaml full_name映射
    sp_fullname_map = load_cast_yaml(cast_dir)
    # 收集全部speaker，全局一次性预加载头像+缩略图base64缓存，避免重复编码
    all_sp_set = collect_all_speakers(groups_raw)
    sp_asset_cache = preload_speaker_assets(cast_dir, all_sp_set, sp_fullname_map)

    group_ctx_list = []
    for g_idx, g_raw in enumerate(groups_raw):
        g_ctx = build_group_context(g_raw, g_idx, sp_asset_cache, audio_dir)
        if g_ctx is not None:
            group_ctx_list.append(g_ctx)
        else:
            print(f"[GROUP_SKIP] group idx={g_idx} pd为空，跳过该组渲染")

    jinja_env = Environment(loader=FileSystemLoader(args.template_dir), autoescape=True)

    def json_filter(val):
        return json.dumps(val, ensure_ascii=False)

    jinja_env.filters["tojson"] = json_filter

    render_ctx = {
        "quiz_meta": quiz_meta,
        "groups": group_ctx_list
    }

    basename_stem = yaml_abs.stem
    # 1.交互式HTML
    html_interactive = render_html(jinja_env, "dialog_interactive.html.j2", render_ctx)
    html_interactive_path = yaml_base_dir / f"{basename_stem}_interactive.html"
    with open(html_interactive_path, "w", encoding="utf‑8") as f:
        f.write(html_interactive)
    print(f"✅ 生成交互式网页: {html_interactive_path}")

    # 2.PDF打印版HTML
    html_pdf_content = render_html(jinja_env, "dialog_print_pdf.html.j2", render_ctx)
    pdf_out_path = yaml_base_dir / f"{basename_stem}.pdf"
    html_to_pdf(html_pdf_content, str(pdf_out_path))
    print(f"✅ 生成PDF: {pdf_out_path}")

    # 3.PNG分页截图
    html_png_content = render_html(jinja_env, "dialog_snapshot_png.html.j2", render_ctx)
    png_prefix = str(yaml_base_dir / f"{basename_stem}_snap")
    png_files = html_to_paginated_png(html_png_content, png_prefix)
    for fpath in png_files:
        print(f"✅ 生成PNG分片: {fpath}")

if __name__ == "__main__":
    main()
