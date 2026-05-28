"""
链接自动解析服务
根据 URL 自动识别平台，抓取并解析页面元信息、封面图、正文快照等
"""
import asyncio
import hashlib
import logging
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── 常量 ────────────────────────────────────────────────
DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Mobile/15E148 Safari/604.1"
)
REQUEST_TIMEOUT = 15

COVERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "covers",
)

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "static" / "snapshots"
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ── 平台识别 ─────────────────────────────────────────────


def detect_platform(url: str) -> tuple[str, str]:
    """返回 (platform, content_type)"""
    if "weibo.com" in url or "m.weibo.cn" in url:
        return "weibo", "post"
    if "mp.weixin.qq.com" in url:
        return "wechat", "article"
    if "douyin.com" in url:
        return "douyin", "video"
    if "bilibili.com" in url or "b23.tv" in url:
        return "bilibili", "video"
    return "web", "article"


# ── 通用 HTML 抓取 ────────────────────────────────────────


def _fetch_html(url: str, use_mobile_ua: bool = False) -> tuple[str, int]:
    """
    获取 URL 的 HTML 文本和最终状态码。
    返回 (html_text, status_code)；失败返回 ("", 0)
    """
    headers = {
        "User-Agent": MOBILE_UA if use_mobile_ua else DESKTOP_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": url,
    }
    try:
        resp = requests.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text, resp.status_code
    except Exception as exc:
        logger.warning("请求失败 %s: %s", url, exc)
        return "", 0


# ── 通用元信息提取 ────────────────────────────────────────


def _extract_meta(soup: BeautifulSoup) -> dict:
    """
    从 BeautifulSoup 对象中提取 og 标签 / fallback 标签中的元信息。
    返回 {"title": ..., "description": ..., "image": ...}
    """
    title = ""
    description = ""
    image = ""

    # og 标签
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()

    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content"):
        description = og_desc["content"].strip()

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        image = og_image["content"].strip()

    # fallback
    if not title:
        tag = soup.find("title")
        if tag:
            title = tag.get_text(strip=True)

    if not description:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()

    if not image:
        twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
        if twitter_image and twitter_image.get("content"):
            image = twitter_image["content"].strip()

    return {"title": title, "description": description, "image": image}


# ── 微博适配 ──────────────────────────────────────────────


def _parse_weibo(url: str, soup: BeautifulSoup) -> dict:
    """微博页面额外解析：提取微博文字内容作为 summary"""
    meta = _extract_meta(soup)
    summary = meta["description"]

    # 尝试从页面直接提取微博正文
    if not summary:
        # m.weibo.cn 详情页
        detail = soup.find("div", class_="weibo-detail")
        if detail:
            summary = detail.get_text(strip=True)[:200]
        else:
            # weibo.com 桌面版
            content_div = soup.find("div", class_="WB_text")
            if content_div:
                summary = content_div.get_text(strip=True)[:200]

    if not summary:
        # 尝试从页面 JSON 数据中提取
        script_tags = soup.find_all("script")
        for script in script_tags:
            text = script.string or ""
            if '"text"' in text and "render_status" in text:
                m = re.search(r'"text"\s*:\s*"([^"]+)"', text)
                if m:
                    summary = m.group(1)[:200]
                    break

    return {
        "title": meta["title"] or "微博",
        "summary": summary[:200],
        "cover_image": meta["image"],
        "archived_html": "",
        "published_at": None,
    }


# ── 公众号适配 ──────────────────────────────────────────────


def _parse_wechat(url: str, soup: BeautifulSoup) -> dict:
    """微信公众号文章解析：提取正文快照"""
    meta = _extract_meta(soup)

    # 多选择器尝试抓取正文
    archived_html = ""
    # 常见的公众号正文容器选择器
    selectors = [
        ("div", {"id": "js_content"}),
        ("div", {"class": "rich_media_content"}),
        ("div", {"id": "page-content"}),
        ("div", {"class": "weui-msg__text-area"}),
    ]
    for tag, attrs in selectors:
        el = soup.find(tag, attrs)
        if el and el.get_text(strip=True):  # 确保不是空容器
            # 移除隐藏样式（公众号常用 visibility:hidden;opacity:0 做延迟渲染）
            if el.get("style"):
                style = el["style"]
                style = style.replace("visibility: hidden", "visibility: visible")
                style = style.replace("visibility:hidden", "visibility:visible")
                style = style.replace("opacity: 0", "opacity: 1")
                style = style.replace("opacity:0", "opacity:1")
                el["style"] = style
            archived_html = str(el)
            break

    # 如果所有选择器都没命中，fallback: 抓取 body 中的文本内容
    if not archived_html:
        body = soup.find("body")
        if body:
            # 移除 script 和 style 标签
            for s in body.find_all(["script", "style", "noscript"]):
                s.decompose()
            body_text = body.get_text(strip=True)
            if len(body_text) > 50:  # 有实质内容才保存
                archived_html = str(body)

    # 尝试抓取评论区（公众号评论通常由 JS 动态加载，纯 requests 大概率拿不到）
    try:
        comment_html_parts = []

        # 方式1：查找 #js_tpl_area 中的评论区域
        js_tpl = soup.find("div", id="js_tpl_area")
        if js_tpl:
            comment_items = js_tpl.find_all("div", class_="comment_item")
            if comment_items:
                for item in comment_items:
                    comment_html_parts.append(str(item))

        # 方式2：搜索页面 script 标签中的评论数据（var commentlist / window.__COMMENT__ 等）
        if not comment_html_parts:
            for script in soup.find_all("script"):
                text = script.string or ""
                # 尝试匹配 var commentlist = [...]
                m = re.search(r'var\s+commentlist\s*=\s*(\[.*?\])\s*;', text, re.DOTALL)
                if not m:
                    m = re.search(r'window\.__COMMENT__\s*=\s*(\[.*?\])\s*;', text, re.DOTALL)
                if m:
                    try:
                        import json as _json
                        comments = _json.loads(m.group(1))
                        for c in comments:
                            nick = c.get("nick_name", c.get("nickname", ""))
                            content = c.get("content", "")
                            if content:
                                comment_html_parts.append(
                                    f'<div class="comment-item"><b>{nick}</b>: {content}</div>'
                                )
                    except (json.JSONDecodeError, TypeError):
                        pass
                    break

        # 如果找到了评论，追加到 archived_html 末尾
        if comment_html_parts:
            comments_section = (
                '<div class="archived-comments"><h3>精选评论</h3>'
                + "\n".join(comment_html_parts)
                + '</div>'
            )
            archived_html = archived_html + comments_section if archived_html else comments_section
    except Exception as exc:
        logger.debug("公众号评论抓取失败（不影响主流程）: %s", exc)

    # 标题：优先 og:title，fallback 到 h1
    title = meta["title"]
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    # 发布时间
    published_at = None
    publish_time_tag = soup.find("em", id="publish_time")
    if publish_time_tag:
        time_str = publish_time_tag.get_text(strip=True)
        published_at = _parse_chinese_time(time_str)

    # 备选：从 meta 获取时间
    if published_at is None:
        article_time = soup.find("meta", attrs={"property": "article:published_time"})
        if article_time and article_time.get("content"):
            published_at = _parse_iso_time(article_time["content"])

    return {
        "title": title or "微信公众号文章",
        "summary": meta["description"][:200],
        "cover_image": meta["image"],
        "archived_html": archived_html,
        "published_at": published_at,
    }


# ── 递归字典查找辅助 ──────────────────────────────────


def _find_in_dict(d, key, max_depth=6):
    """递归查找嵌套字典中的第一个匹配 key 的非空值"""
    if max_depth <= 0:
        return None
    if isinstance(d, dict):
        if key in d and d[key]:
            return d[key]
        for v in d.values():
            result = _find_in_dict(v, key, max_depth - 1)
            if result:
                return result
    elif isinstance(d, list):
        for item in d[:10]:  # 限制列表遍历
            result = _find_in_dict(item, key, max_depth - 1)
            if result:
                return result
    return None


# ── 抖音适配 ──────────────────────────────────────────────


def _parse_douyin(url: str, soup: BeautifulSoup) -> dict:
    """抖音视频页面解析：提取标题、封面图，并从 JS 变量深度提取完整元数据"""
    meta = _extract_meta(soup)
    title = meta["title"]
    summary = meta["description"] or ""
    cover = meta["image"]
    published_at = None
    author = ""

    # 深度提取：从页面 JS 变量中获取更完整的数据
    import json as _json
    for script in soup.find_all("script"):
        text = script.string or ""
        if "__UNIVERSAL_DATA_FOR_REHYDRATION__" in text or "window._SSR_DATA" in text:
            try:
                # 匹配 JSON 数据
                m = re.search(
                    r'(?:__UNIVERSAL_DATA_FOR_REHYDRATION__|_SSR_DATA)\s*=\s*(\{.+?\})\s*;?\s*(?:</script>|$)',
                    text, re.DOTALL,
                )
                if m:
                    data = _json.loads(m.group(1))
                    # 递归查找视频描述
                    desc = _find_in_dict(data, 'desc') or _find_in_dict(data, 'description')
                    if desc and len(str(desc)) > len(summary):
                        summary = str(desc)
                    if not title or title == "抖音视频":
                        title = (str(desc) or "")[:100] if desc else title
                    # 作者
                    nickname = _find_in_dict(data, 'nickname')
                    if nickname:
                        author = str(nickname)
                    # 发布时间
                    create_time = _find_in_dict(data, 'createTime') or _find_in_dict(data, 'create_time')
                    if create_time and str(create_time).isdigit():
                        published_at = int(create_time)
            except (_json.JSONDecodeError, Exception):
                pass

    # fallback: 如果 OG 标签没拿到标题，尝试 title 标签
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            raw = title_tag.get_text(strip=True)
            title = re.sub(r"\s*[|-].*$", "", raw).strip()

    # 清理标题中的"抖音"后缀
    if title:
        title = re.sub(r'\s*[-\u2013\u2014]\s*抖音\s*$', '', title).strip()

    # 如果有作者信息，拼接到摘要
    if author and author not in summary:
        summary = f"@{author}: {summary}" if summary else f"@{author}"

    return {
        "title": title or "抖音视频",
        "summary": summary[:500],  # 扩展到500字，给AI更多素材
        "cover_image": cover,
        "archived_html": "",
        "published_at": published_at,
    }


# ── B站适配 ───────────────────────────────────────────────


def _parse_bilibili(url: str, soup: BeautifulSoup) -> dict:
    """B站视频页面解析：提取标题和封面图"""
    meta = _extract_meta(soup)

    title = meta["title"]
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    # 尝试从页面初始数据中提取
    if not title or title == "bilibili":
        script_tags = soup.find_all("script")
        for script in script_tags:
            text = script.string or ""
            if "window.__INITIAL_STATE__" in text:
                m = re.search(r'"title"\s*:\s*"([^"]+)"', text)
                if m:
                    title = m.group(1)
                    break

    # B站封面图常在 meta itemprop 或 og:image 中
    image = meta["image"]
    if not image:
        meta_image = soup.find("meta", attrs={"itemprop": "image"})
        if meta_image and meta_image.get("content"):
            image = meta_image["content"].strip()

    return {
        "title": title or "B站视频",
        "summary": meta["description"][:200],
        "cover_image": image,
        "archived_html": "",
        "published_at": None,
    }


# ── 通用 web 解析 ─────────────────────────────────────────


def _parse_generic(url: str, soup: BeautifulSoup) -> dict:
    """通用网页解析"""
    meta = _extract_meta(soup)

    # 尝试提取 article 发布时间
    published_at = None
    article_time = soup.find("meta", attrs={"property": "article:published_time"})
    if article_time and article_time.get("content"):
        published_at = _parse_iso_time(article_time["content"])

    return {
        "title": meta["title"],
        "summary": meta["description"][:200],
        "cover_image": meta["image"],
        "archived_html": "",
        "published_at": published_at,
    }


# ── 封面图下载 ──────────────────────────────────────────────


def download_cover(image_url: str) -> str:
    """
    下载图片到本地，返回相对路径 /static/covers/xxx.jpg，失败返回空字符串
    """
    if not image_url:
        return ""

    # 处理协议相对 URL
    if image_url.startswith("//"):
        image_url = "https:" + image_url

    os.makedirs(COVERS_DIR, exist_ok=True)

    try:
        resp = requests.get(
            image_url,
            headers={"User-Agent": DESKTOP_UA},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        resp.raise_for_status()

        # 根据 content-type 确定后缀
        content_type = resp.headers.get("Content-Type", "")
        ext = _content_type_to_ext(content_type)

        # 用 url hash 作为文件名，避免重复下载
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:16]
        filename = f"{url_hash}{ext}"
        filepath = os.path.join(COVERS_DIR, filename)

        with open(filepath, "wb") as f:
            f.write(resp.content)

        return f"/static/covers/{filename}"

    except Exception as exc:
        logger.warning("封面图下载失败 %s: %s", image_url, exc)
        return ""


def _content_type_to_ext(content_type: str) -> str:
    """根据 Content-Type 返回文件后缀"""
    ct = content_type.lower().split(";")[0].strip()
    mapping = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "image/avif": ".avif",
    }
    return mapping.get(ct, ".jpg")


# ── 时间解析辅助 ──────────────────────────────────────────


def _parse_chinese_time(time_str: str) -> int | None:
    """
    解析中文时间字符串，如 '2024-01-15 20:30' 或 '2024年1月15日'
    返回 unix timestamp
    """
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y年%m月%d日 %H:%M",
        "%Y年%m月%d日",
    ]
    for fmt in formats:
        try:
            from datetime import datetime
            dt = datetime.strptime(time_str.strip(), fmt)
            return int(dt.timestamp())
        except (ValueError, OverflowError):
            continue
    return None


def _parse_iso_time(time_str: str) -> int | None:
    """解析 ISO 8601 时间字符串，返回 unix timestamp"""
    try:
        from datetime import datetime, timezone
        # 去掉末尾的 Z 或时区后缀，简化处理
        cleaned = time_str.strip().rstrip("Z")
        if "+" in cleaned[10:]:
            cleaned = cleaned[: cleaned.index("+", 10)]
        dt = datetime.fromisoformat(cleaned)
        return int(dt.replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        return None


# ── 主入口 ────────────────────────────────────────────────


def _extract_url_from_text(text: str) -> str:
    """
    从混合分享文本中提取 URL。
    抖音分享格式如: "rEu:/ :2pm 01/11 L@W.Zm https://v.douyin.com/xxx/"
    小红书分享格式如: "复制打开小红书查看 https://www.xiaohongshu.com/xxx"
    """
    text = text.strip()
    # 已经是纯 URL
    if re.match(r'^https?://', text, re.IGNORECASE):
        return text
    # 从混合文本中提取第一个 URL
    m = re.search(r'https?://[^\s<>"\']+', text, re.IGNORECASE)
    return m.group(0) if m else text


def parse_url(url: str) -> dict:
    """
    解析链接，返回结构化信息字典。

    返回格式:
    {
        "url": "原始URL",
        "title": "标题",
        "summary": "摘要（前200字）",
        "cover_image": "本地存储路径 或空字符串",
        "platform": "weibo|wechat|douyin|bilibili|web",
        "content_type": "article|video|post",
        "archived_html": "正文HTML快照 或空字符串",
        "published_at": unix_timestamp 或 None
    }
    """
    # 先从混合文本中提取 URL（如抖音分享文本含乱码追踪参数）
    url = _extract_url_from_text(url)

    platform, content_type = detect_platform(url)

    # 抖音短链需要 follow redirect 获取真实页面
    actual_url = url
    if "v.douyin.com" in url:
        try:
            resp = requests.head(
                url,
                headers={"User-Agent": MOBILE_UA},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            actual_url = resp.url
        except Exception:
            pass

    # 微博、微信使用移动端 UA
    use_mobile = platform in ("weibo", "wechat")
    html, status = _fetch_html(actual_url, use_mobile_ua=use_mobile)

    if not html or status == 0:
        logger.warning("无法获取页面内容: %s", url)
        return _build_error_result(url, platform, content_type)

    soup = BeautifulSoup(html, "lxml")

    # 根据平台选择解析策略
    if platform == "weibo":
        result = _parse_weibo(actual_url, soup)
    elif platform == "wechat":
        result = _parse_wechat(actual_url, soup)
    elif platform == "douyin":
        result = _parse_douyin(actual_url, soup)
    elif platform == "bilibili":
        result = _parse_bilibili(actual_url, soup)
    else:
        result = _parse_generic(actual_url, soup)

    # 标题兜底：如果连标题都没有，用域名
    if not result.get("title"):
        parsed = urlparse(url)
        result["title"] = parsed.netloc or url

    # 下载封面图
    cover_image_url = result.pop("cover_image", "")
    if cover_image_url:
        cover_image = download_cover(cover_image_url)
    else:
        cover_image = ""

    # 尝试截图
    snapshot_image = ""
    try:
        snapshot_image = take_snapshot_screenshot(url)
    except Exception as e:
        logger.warning(f"Screenshot failed for {url}: {e}")

    return {
        "url": url,
        "title": result.get("title", ""),
        "summary": result.get("summary", ""),
        "cover_image": cover_image,
        "platform": platform,
        "content_type": content_type,
        "archived_html": result.get("archived_html", ""),
        "snapshot_image": snapshot_image,
        "published_at": result.get("published_at"),
    }


def take_snapshot_screenshot(url: str) -> str:
    """用 Playwright 截取全页长图，返回相对路径如 /static/snapshots/xxx.png"""
    try:
        return asyncio.get_event_loop().run_until_complete(_screenshot(url))
    except RuntimeError:
        # 没有事件循环时创建新的
        return asyncio.run(_screenshot(url))


async def _screenshot(url: str) -> str:
    from playwright.async_api import async_playwright

    filename = hashlib.md5(url.encode()).hexdigest()[:16] + ".png"
    filepath = SNAPSHOT_DIR / filename

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,  # 3x 高清截图
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        )

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            # 等待页面渲染和图片加载
            await page.wait_for_timeout(5000)
            # 滚动到底部触发懒加载图片和评论
            await page.evaluate("""async () => {
                const delay = ms => new Promise(r => setTimeout(r, ms));
                const height = document.body.scrollHeight;
                for (let i = 0; i < height; i += 300) {
                    window.scrollTo(0, i);
                    await delay(100);
                }
                window.scrollTo(0, height);
                await delay(2000);
                window.scrollTo(0, 0);
            }""")
            # 等待所有图片加载完成
            await page.wait_for_timeout(3000)
            # 全页高清截图
            await page.screenshot(path=str(filepath), full_page=True)
        finally:
            await browser.close()

    return f"/static/snapshots/{filename}"


def _build_error_result(url: str, platform: str, content_type: str) -> dict:
    """构建完全解析失败时的兜底返回"""
    parsed = urlparse(url)
    return {
        "url": url,
        "title": parsed.netloc or url,
        "summary": "",
        "cover_image": "",
        "platform": platform,
        "content_type": content_type,
        "archived_html": "",
        "snapshot_image": "",
        "published_at": None,
    }
