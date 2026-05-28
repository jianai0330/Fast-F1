"""
SQLite 数据库层
涵盖：资讯(news)、AI分析(news_analysis)、论坛帖子(posts)、评论(comments)、用户(users)、分区(sections)
"""

import json
import logging
import sqlite3
import os
import time

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f1.db")


def get_conn() -> sqlite3.Connection:
    """获取数据库连接，row_factory 让查询结果可按列名访问"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # 并发写入更安全
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ─────────────────────────────────────────────
# 建表 & 初始化
# ─────────────────────────────────────────────

DDL = """
-- 资讯原文表
CREATE TABLE IF NOT EXISTS news (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    summary     TEXT,
    url         TEXT    UNIQUE NOT NULL,   -- 去重用
    source      TEXT    NOT NULL,          -- "The Race" / "Motorsport"
    language    TEXT    NOT NULL DEFAULT 'en',  -- 'en' / 'zh'
    published_at INTEGER NOT NULL,         -- unix timestamp
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- AI 分析结果表（与 news 1:1）
CREATE TABLE IF NOT EXISTS news_analysis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id         INTEGER NOT NULL UNIQUE REFERENCES news(id),
    tech_points     TEXT,    -- 🔬 技术要点（Markdown）
    plain_explain   TEXT,    -- 🏎️ 通俗解释（Markdown）
    race_impact     TEXT,    -- 📊 赛况影响（Markdown）
    raw_report      TEXT,    -- 完整原始输出（备用）
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- 论坛分区表
CREATE TABLE IF NOT EXISTS sections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,   -- "race" | "team"
    name        TEXT NOT NULL,   -- "巴林大奖赛" / "红牛车队"
    slug        TEXT NOT NULL UNIQUE,  -- "bahrain" / "redbull"
    sort_order  INTEGER NOT NULL DEFAULT 0
);

-- 论坛用户表（用微信 openid 标识）
CREATE TABLE IF NOT EXISTS users (
    openid      TEXT PRIMARY KEY,
    nickname    TEXT NOT NULL,
    avatar_url  TEXT,
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- 论坛帖子表
CREATE TABLE IF NOT EXISTS posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id      INTEGER NOT NULL REFERENCES sections(id),
    news_id         INTEGER REFERENCES news(id),              -- 关联来源新闻（可为空）
    curated_id      INTEGER REFERENCES curated_content(id),   -- 关联精选内容（可为空）
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    author_openid   TEXT NOT NULL,          -- 关联 users.openid
    author_nickname TEXT NOT NULL,          -- 冗余存储，避免 JOIN
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending/approved/rejected
    is_seeded       INTEGER NOT NULL DEFAULT 0,       -- 1=AI种子内容
    view_count      INTEGER NOT NULL DEFAULT 0,
    comment_count   INTEGER NOT NULL DEFAULT 0,
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    updated_at      INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- 论坛评论表
CREATE TABLE IF NOT EXISTS comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id         INTEGER NOT NULL REFERENCES posts(id),
    content         TEXT NOT NULL,
    author_openid   TEXT NOT NULL,
    author_nickname TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending/approved/rejected
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_news_published   ON news(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_language    ON news(language);
CREATE INDEX IF NOT EXISTS idx_posts_section    ON posts(section_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_status     ON posts(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comments_post    ON comments(post_id, status, created_at);

-- 点赞/点踩表
CREATE TABLE IF NOT EXISTS post_likes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id     INTEGER NOT NULL REFERENCES posts(id),
    openid      TEXT    NOT NULL,
    type        TEXT    NOT NULL CHECK(type IN ('like','dislike')),
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    UNIQUE(post_id, openid)
);
CREATE INDEX IF NOT EXISTS idx_likes_post ON post_likes(post_id);

-- 术语表
CREATE TABLE IF NOT EXISTS terms (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    slug         TEXT    NOT NULL UNIQUE,
    name_zh      TEXT    NOT NULL,
    name_en      TEXT    NOT NULL,
    aliases      TEXT,
    short_def    TEXT    NOT NULL,
    full_def     TEXT,
    example      TEXT,
    category     TEXT    NOT NULL,
    level        INTEGER NOT NULL DEFAULT 1,
    related_slugs TEXT,
    spec_year    INTEGER,
    scene_tags   TEXT,                                    -- 场景标签CSV (race_common, tech_talk, 2026_new)
    why_important TEXT,                                   -- 为什么重要
    data_ref     TEXT,                                    -- 数据参考
    status       TEXT    NOT NULL DEFAULT 'approved', -- approved/pending/rejected
    submitted_by TEXT,                                -- 用户提交时的 openid
    created_at   INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_terms_category ON terms(category);
CREATE INDEX IF NOT EXISTS idx_terms_level    ON terms(level);
CREATE INDEX IF NOT EXISTS idx_terms_status   ON terms(status);

-- 车手评分表（每个用户对每个车手只能评一次，可更新）
CREATE TABLE IF NOT EXISTS driver_ratings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_code TEXT    NOT NULL,
    openid      TEXT    NOT NULL,
    speed       INTEGER NOT NULL CHECK(speed BETWEEN 1 AND 5),
    consist     INTEGER NOT NULL CHECK(consist BETWEEN 1 AND 5),
    defend      INTEGER NOT NULL CHECK(defend BETWEEN 1 AND 5),
    wet         INTEGER NOT NULL CHECK(wet BETWEEN 1 AND 5),
    mental      INTEGER NOT NULL CHECK(mental BETWEEN 1 AND 5),
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    UNIQUE(driver_code, openid)
);
CREATE INDEX IF NOT EXISTS idx_driver_ratings ON driver_ratings(driver_code);

-- 车手评论表（每个用户对每个车手只能评一次，可更新）
CREATE TABLE IF NOT EXISTS driver_comments (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_code     TEXT    NOT NULL,
    content         TEXT    NOT NULL,
    author_openid   TEXT    NOT NULL,
    author_nickname TEXT    NOT NULL,
    likes           INTEGER NOT NULL DEFAULT 0,
    created_at      INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_driver_comments ON driver_comments(driver_code, created_at DESC);

-- 精选内容投稿表
CREATE TABLE IF NOT EXISTS curated_content (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    url          TEXT UNIQUE NOT NULL,
    title        TEXT NOT NULL,
    summary      TEXT,
    cover_image  TEXT,
    platform     TEXT NOT NULL,
    content_type TEXT DEFAULT 'article',
    tags         TEXT,
    note         TEXT,
    submitted_by TEXT,
    archived_html TEXT,
    snapshot_image TEXT,
    published_at INTEGER,
    created_at   INTEGER NOT NULL DEFAULT (strftime('%s','now')),
    analyzed     INTEGER DEFAULT 0,
    tech_points  TEXT DEFAULT '',
    plain_explain TEXT DEFAULT '',
    race_impact  TEXT DEFAULT '',
    analyzed_at  TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_curated_created ON curated_content(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_curated_platform ON curated_content(platform);

-- 匿名聊天室消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname    TEXT NOT NULL DEFAULT '匿名车迷',
    content     TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_messages(created_at DESC);

-- idx_posts_curated 在 init_db() 中 ALTER TABLE 后创建，避免旧表缺列报错
"""

# 默认分区数据
DEFAULT_SECTIONS = [
    # 赛事分区（2026赛季主要站点）
    ("race", "巴林大奖赛",       "bahrain",       1),
    ("race", "沙特阿拉伯大奖赛", "saudi_arabia",  2),
    ("race", "澳大利亚大奖赛",   "australia",     3),
    ("race", "日本大奖赛",       "japan",         4),
    ("race", "中国大奖赛",       "china",         5),
    ("race", "迈阿密大奖赛",     "miami",         6),
    ("race", "艾米利亚大奖赛",   "imola",         7),
    ("race", "摩纳哥大奖赛",     "monaco",        8),
    ("race", "加拿大大奖赛",     "canada",        9),
    ("race", "西班牙大奖赛",     "spain",         10),
    ("race", "奥地利大奖赛",     "austria",       11),
    ("race", "英国大奖赛",       "britain",       12),
    ("race", "比利时大奖赛",     "belgium",       13),
    ("race", "匈牙利大奖赛",     "hungary",       14),
    ("race", "荷兰大奖赛",       "netherlands",   15),
    ("race", "意大利大奖赛",     "italy",         16),
    ("race", "阿塞拜疆大奖赛",   "azerbaijan",    17),
    ("race", "新加坡大奖赛",     "singapore",     18),
    ("race", "美国大奖赛",       "usa",           19),
    ("race", "墨西哥大奖赛",     "mexico",        20),
    ("race", "巴西大奖赛",       "brazil",        21),
    ("race", "拉斯维加斯大奖赛", "las_vegas",     22),
    ("race", "卡塔尔大奖赛",     "qatar",         23),
    ("race", "阿布扎比大奖赛",   "abu_dhabi",     24),
    # 车队分区
    ("team", "红牛车队",         "redbull",       101),
    ("team", "法拉利车队",       "ferrari",       102),
    ("team", "梅赛德斯车队",     "mercedes",      103),
    ("team", "迈凯伦车队",       "mclaren",       104),
    ("team", "阿斯顿·马丁车队", "aston_martin",  105),
    ("team", "阿尔派因车队",     "alpine",        106),
    ("team", "威廉姆斯车队",     "williams",      107),
    ("team", "Racing Bulls",    "racing_bulls",  108),
    ("team", "Audi",            "sauber",        109),
    ("team", "哈斯车队",         "haas",          110),
    # 综合讨论
    ("race", "综合讨论",         "general",       0),
]


def init_db():
    """建表 + 插入默认分区（幂等，可重复调用）"""
    logger.info("[init_db] 开始数据库初始化...")
    with get_conn() as conn:
        # 用 SQLite 原生脚本执行，避免注释 + CREATE 语句被手动 split 误跳过。
        conn.executescript(DDL)
        # 插入默认分区（忽略已存在）
        conn.executemany(
            "INSERT OR IGNORE INTO sections(type, name, slug, sort_order) VALUES (?,?,?,?)",
            DEFAULT_SECTIONS
        )
        # 兼容旧表：若 news 表缺少 language 列则自动添加
        try:
            conn.execute("SELECT language FROM news LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE news ADD COLUMN language TEXT NOT NULL DEFAULT 'en'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_language ON news(language)")
        # 兼容旧表：若 posts 表缺少 curated_id 列则自动添加
        try:
            conn.execute("SELECT curated_id FROM posts LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE posts ADD COLUMN curated_id INTEGER REFERENCES curated_content(id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_curated ON posts(curated_id)")
        # 兼容旧表：若 curated_content 表缺少 AI 分析字段则自动添加
        for col, col_type in [
            ("analyzed", "INTEGER DEFAULT 0"),
            ("tech_points", "TEXT DEFAULT ''"),
            ("plain_explain", "TEXT DEFAULT ''"),
            ("race_impact", "TEXT DEFAULT ''"),
            ("analyzed_at", "TEXT DEFAULT ''"),
        ]:
            try:
                conn.execute(f"SELECT {col} FROM curated_content LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute(f"ALTER TABLE curated_content ADD COLUMN {col} {col_type}")
        # 兼容旧表：若 terms 表缺少新字段则自动添加
        for col, col_type in [
            ("scene_tags", "TEXT"),
            ("why_important", "TEXT"),
            ("data_ref", "TEXT"),
        ]:
            try:
                conn.execute(f"SELECT {col} FROM terms LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute(f"ALTER TABLE terms ADD COLUMN {col} {col_type}")
        # 兼容旧数据：将 flag 分类合并到 rules
        conn.execute("UPDATE terms SET category='rules' WHERE category='flag'")
        # 兼容旧表：若 chat_messages 表不存在则创建
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname    TEXT NOT NULL DEFAULT '匿名车迷',
                content     TEXT NOT NULL,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_created ON chat_messages(created_at DESC)")
        conn.commit()
    terms_seed()
    logger.info("[init_db] 数据库初始化完成")


# ─────────────────────────────────────────────
# News CRUD
# ─────────────────────────────────────────────

def news_insert(title: str, summary: str, url: str,
                source: str, published_at: int,
                language: str = 'en') -> int | None:
    """插入一条资讯，若 url 已存在则跳过，返回 id 或 None"""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO news(title, summary, url, source, language, published_at)
               VALUES (?,?,?,?,?,?)""",
            (title, summary, url, source, language, published_at)
        )
        conn.commit()
        return cur.lastrowid if cur.lastrowid and cur.rowcount > 0 else None


def news_list_by_team(keywords: list[str], page: int = 1, page_size: int = 20, search_keyword: str | None = None) -> list[dict]:
    """按车队关键词过滤资讯（title+summary LIKE 匹配），可叠加 search_keyword 搜索"""
    offset = (page - 1) * page_size
    conditions = " OR ".join(
        ["(LOWER(n.title) LIKE ? OR LOWER(n.summary) LIKE ?)"] * len(keywords)
    )
    params = []
    for kw in keywords:
        params += [f"%{kw}%", f"%{kw}%"]
    # 叠加搜索关键词
    if search_keyword:
        sk_like = f"%{search_keyword}%"
        conditions = f"({conditions}) AND (LOWER(n.title) LIKE ? OR LOWER(n.summary) LIKE ?)"
        params += [sk_like.lower(), sk_like.lower()]
    params += [page_size, offset]
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT n.id, n.title, n.summary, n.source, n.language, n.published_at,
                       (SELECT 1 FROM news_analysis a WHERE a.news_id=n.id) AS analyzed
                FROM news n
                WHERE {conditions}
                ORDER BY n.published_at DESC
                LIMIT ? OFFSET ?""",
            params
        ).fetchall()
        return [dict(r) for r in rows]


def news_list(page: int = 1, page_size: int = 20, keyword: str | None = None,
              language: str | None = None) -> list[dict]:
    """分页查询资讯列表（最新在前），带是否已分析标记，支持 keyword 模糊搜索和 language 过滤"""
    offset = (page - 1) * page_size
    with get_conn() as conn:
        conditions = []
        params = []
        if keyword:
            kw_like = f"%{keyword}%"
            conditions.append("(LOWER(n.title) LIKE ? OR LOWER(n.summary) LIKE ?)")
            params += [kw_like.lower(), kw_like.lower()]
        if language and language != 'all':
            conditions.append("n.language = ?")
            params.append(language)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        rows = conn.execute(
            f"""SELECT n.id, n.title, n.summary, n.source, n.language, n.published_at,
                      (SELECT 1 FROM news_analysis a WHERE a.news_id=n.id) AS analyzed
               FROM news n{where}
               ORDER BY n.published_at DESC
               LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        ).fetchall()
        return [dict(r) for r in rows]


def news_get(news_id: int) -> dict | None:
    """查询单条资讯（含 AI 分析）"""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT n.*, a.tech_points, a.plain_explain, a.race_impact
               FROM news n
               LEFT JOIN news_analysis a ON a.news_id = n.id
               WHERE n.id = ?""",
            (news_id,)
        ).fetchone()
        return dict(row) if row else None


def news_get_unanalyzed(limit: int = 10) -> list[dict]:
    """获取尚未 AI 分析的资讯列表"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT n.* FROM news n
               WHERE NOT EXISTS (SELECT 1 FROM news_analysis a WHERE a.news_id=n.id)
               ORDER BY n.published_at DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def news_analysis_save(news_id: int, tech_points: str,
                       plain_explain: str, race_impact: str, raw: str):
    """保存 AI 分析结果（INSERT OR REPLACE 幂等）"""
    with get_conn() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO news_analysis
               (news_id, tech_points, plain_explain, race_impact, raw_report)
               VALUES (?,?,?,?,?)""",
            (news_id, tech_points, plain_explain, race_impact, raw)
        )
        conn.commit()


def news_delete(news_id: int) -> bool:
    """删除一条新闻及其关联分析"""
    with get_conn() as conn:
        conn.execute("DELETE FROM news_analysis WHERE news_id=?", (news_id,))
        cur = conn.execute("DELETE FROM news WHERE id=?", (news_id,))
        conn.commit()
        return cur.rowcount > 0


# ─────────────────────────────────────────────
# Sections CRUD
# ─────────────────────────────────────────────

def sections_all() -> list[dict]:
    """返回所有分区，按 type + sort_order 排序"""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sections ORDER BY type DESC, sort_order ASC"
        ).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# Users CRUD
# ─────────────────────────────────────────────

def user_get(openid: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE openid=?", (openid,)
        ).fetchone()
        return dict(row) if row else None


def user_upsert(openid: str, nickname: str, avatar_url: str = "") -> dict:
    """新建或更新用户昵称/头像"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users(openid, nickname, avatar_url)
               VALUES (?,?,?)
               ON CONFLICT(openid) DO UPDATE SET
                 nickname=excluded.nickname,
                 avatar_url=excluded.avatar_url""",
            (openid, nickname, avatar_url)
        )
        conn.commit()
    return user_get(openid)


# ─────────────────────────────────────────────
# Posts CRUD
# ─────────────────────────────────────────────

def post_create(section_id: int, title: str, content: str,
                author_openid: str, author_nickname: str,
                is_seeded: bool = False, news_id: int | None = None,
                curated_id: int | None = None) -> int:
    """创建帖子，暂时关闭审核直接 approved（TODO: 用户量大后改回 pending）"""
    status = "approved"
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO posts(section_id, title, content,
               author_openid, author_nickname, status, is_seeded, news_id, curated_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (section_id, title, content,
             author_openid, author_nickname, status, int(is_seeded), news_id, curated_id)
        )
        conn.commit()
        return cur.lastrowid


def post_list(section_id: int | None = None,
              status: str = "approved",
              page: int = 1, page_size: int = 20) -> list[dict]:
    """帖子列表，支持按分区过滤"""
    offset = (page - 1) * page_size
    with get_conn() as conn:
        if section_id:
            rows = conn.execute(
                """SELECT p.*, s.name AS section_name FROM posts p
                   JOIN sections s ON s.id=p.section_id
                   WHERE p.section_id=? AND p.status=?
                   ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
                (section_id, status, page_size, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT p.*, s.name AS section_name FROM posts p
                   JOIN sections s ON s.id=p.section_id
                   WHERE p.status=?
                   ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
                (status, page_size, offset)
            ).fetchall()
        return [dict(r) for r in rows]


def post_get(post_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            """SELECT p.*, s.name AS section_name,
                      n.title AS news_title, n.source AS news_source
               FROM posts p
               JOIN sections s ON s.id=p.section_id
               LEFT JOIN news n ON n.id=p.news_id
               WHERE p.id=?""",
            (post_id,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE posts SET view_count=view_count+1 WHERE id=?", (post_id,)
            )
            conn.commit()
        return dict(row) if row else None


def posts_by_news(news_id: int, limit: int = 10) -> list[dict]:
    """查询关联某条新闻的帖子列表"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT p.id, p.title, p.author_nickname,
                      p.comment_count, p.view_count, p.created_at
               FROM posts p
               WHERE p.news_id=? AND p.status='approved'
               ORDER BY p.created_at DESC LIMIT ?""",
            (news_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def posts_by_curated(curated_id: int, limit: int = 10) -> list[dict]:
    """查询关联某条精选内容的帖子列表"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT p.id, p.title, p.author_nickname,
                      p.comment_count, p.view_count, p.created_at
               FROM posts p
               WHERE p.curated_id=? AND p.status='approved'
               ORDER BY p.created_at DESC LIMIT ?""",
            (curated_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def post_update_status(post_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE posts SET status=?, updated_at=strftime('%s','now') WHERE id=?",
            (status, post_id)
        )
        conn.commit()


def posts_pending(page: int = 1, page_size: int = 50) -> list[dict]:
    return post_list(section_id=None, status="pending",
                     page=page, page_size=page_size)


# ─────────────────────────────────────────────
# Comments CRUD
# ─────────────────────────────────────────────

def comment_create(post_id: int, content: str,
                   author_openid: str, author_nickname: str) -> int:
    """创建评论，暂时关闭审核直接 approved（TODO: 用户量大后改回 pending）"""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO comments(post_id, content, author_openid, author_nickname, status)
               VALUES (?,?,?,?,?)""",
            (post_id, content, author_openid, author_nickname, "approved")
        )
        # 直接发布模式下同步更新帖子评论数
        conn.execute(
            "UPDATE posts SET comment_count = comment_count + 1 WHERE id=?",
            (post_id,)
        )
        conn.commit()
        return cur.lastrowid


def comment_list(post_id: int, status: str = "approved") -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM comments
               WHERE post_id=? AND status=?
               ORDER BY created_at ASC""",
            (post_id, status)
        ).fetchall()
        return [dict(r) for r in rows]


def comment_update_status(comment_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE comments SET status=? WHERE id=?", (status, comment_id)
        )
        # 同步更新帖子评论计数
        if status == "approved":
            conn.execute(
                """UPDATE posts SET comment_count=(
                       SELECT COUNT(*) FROM comments
                       WHERE post_id=(SELECT post_id FROM comments WHERE id=?)
                       AND status='approved'
                   ) WHERE id=(SELECT post_id FROM comments WHERE id=?)""",
                (comment_id, comment_id)
            )
        conn.commit()


def comments_pending(page: int = 1, page_size: int = 50) -> list[dict]:
    offset = (page - 1) * page_size
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT c.*, p.title AS post_title FROM comments c
               JOIN posts p ON p.id=c.post_id
               WHERE c.status='pending'
               ORDER BY c.created_at DESC LIMIT ? OFFSET ?""",
            (page_size, offset)
        ).fetchall()
        return [dict(r) for r in rows]


def section_get_by_slug(slug: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sections WHERE slug=?", (slug,)
        ).fetchone()
        return dict(row) if row else None


# ─────────────────────────────────────────────
# 热门推荐
# ─────────────────────────────────────────────

def get_hot_posts(limit: int = 5, section_id: int | None = None) -> list[dict]:
    """热门帖子：热度分 = (comment_count*0.5 + view_count*0.3) / (hours_since/24 + 1)"""
    with get_conn() as conn:
        where = "WHERE p.status = 'approved'"
        params: list[int] = []
        if section_id is not None:
            where += " AND p.section_id = ?"
            params.append(section_id)
        params.append(limit)
        rows = conn.execute(
            """SELECT p.id, p.title, p.author_nickname, p.comment_count, p.view_count,
                      p.created_at, s.name AS section_name,
                      (p.comment_count * 0.5 + p.view_count * 0.3)
                        / ((strftime('%s','now') - p.created_at) / 3600.0 / 24.0 + 1) AS hot_score
               FROM posts p
               JOIN sections s ON s.id = p.section_id
               {where}
               ORDER BY hot_score DESC
               LIMIT ?""".format(where=where),
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def get_hot_news(limit: int = 5) -> list[dict]:
    """热门资讯：有 AI 解读的优先，再按创建时间倒序"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT n.id, n.title, n.source, n.published_at,
                      CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END AS has_analysis
               FROM news n
               LEFT JOIN news_analysis a ON a.news_id = n.id
               ORDER BY has_analysis DESC, n.published_at DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ─────────────────────────────────────────────
# 删帖
# ─────────────────────────────────────────────

def post_delete(post_id: int, openid: str) -> bool:
    """删除帖子，仅作者可删，级联删除评论和点赞"""
    with get_conn() as conn:
        # 先确认是作者
        row = conn.execute(
            "SELECT id FROM posts WHERE id=? AND author_openid=?",
            (post_id, openid)
        ).fetchone()
        if not row:
            return False
        # 级联删除关联数据
        conn.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        conn.execute("DELETE FROM post_likes WHERE post_id=?", (post_id,))
        conn.execute("DELETE FROM posts WHERE id=?", (post_id,))
        conn.commit()
        return True


# ─────────────────────────────────────────────
# 点赞 / 点踩
# ─────────────────────────────────────────────

def post_like(post_id: int, openid: str, like_type: str) -> dict:
    """
    点赞或点踩。
    - 同类型再点 = 取消
    - 切换类型 = 直接替换
    返回 {likes, dislikes, my_vote}
    """
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT type FROM post_likes WHERE post_id=? AND openid=?",
            (post_id, openid)
        ).fetchone()

        if existing:
            if existing["type"] == like_type:
                # 再点同类型 = 取消
                conn.execute(
                    "DELETE FROM post_likes WHERE post_id=? AND openid=?",
                    (post_id, openid)
                )
                my_vote = None
            else:
                # 切换类型
                conn.execute(
                    "UPDATE post_likes SET type=? WHERE post_id=? AND openid=?",
                    (like_type, post_id, openid)
                )
                my_vote = like_type
        else:
            conn.execute(
                "INSERT INTO post_likes(post_id, openid, type) VALUES (?,?,?)",
                (post_id, openid, like_type)
            )
            my_vote = like_type

        conn.commit()

        counts = conn.execute(
            """SELECT
                SUM(CASE WHEN type='like' THEN 1 ELSE 0 END) AS likes,
                SUM(CASE WHEN type='dislike' THEN 1 ELSE 0 END) AS dislikes
               FROM post_likes WHERE post_id=?""",
            (post_id,)
        ).fetchone()

        return {
            "likes":    counts["likes"] or 0,
            "dislikes": counts["dislikes"] or 0,
            "my_vote":  my_vote,
        }


def post_like_counts(post_id: int, openid: str | None = None) -> dict:
    """获取帖子点赞数据"""
    with get_conn() as conn:
        counts = conn.execute(
            """SELECT
                SUM(CASE WHEN type='like' THEN 1 ELSE 0 END) AS likes,
                SUM(CASE WHEN type='dislike' THEN 1 ELSE 0 END) AS dislikes
               FROM post_likes WHERE post_id=?""",
            (post_id,)
        ).fetchone()
        my_vote = None
        if openid:
            row = conn.execute(
                "SELECT type FROM post_likes WHERE post_id=? AND openid=?",
                (post_id, openid)
            ).fetchone()
            my_vote = row["type"] if row else None
        return {
            "likes":    counts["likes"] or 0,
            "dislikes": counts["dislikes"] or 0,
            "my_vote":  my_vote,
        }


# ─────────────────────────────────────────────
# Terms CRUD
# ─────────────────────────────────────────────

# slug, name_zh, name_en, aliases, short_def, full_def, example, category, level, related_slugs, spec_year
SEED_TERMS = [
    # ── 基础（level=1）──────────────────────────
    {
        "slug": "drs", "name_zh": "DRS", "name_en": "Drag Reduction System",
        "aliases": "DRS,尾翼减阻,减阻系统",
        "short_def": "可调尾翼系统，开启后减少空气阻力，直道提速约10-12km/h，是最常见的超车辅助手段。",
        "full_def": "DRS（Drag Reduction System）允许车手在指定检测点距前车1秒以内时，打开后翼的可动翼片，减少约80%的后翼下压力，从而降低阻力、提升直道速度。每条赛道设有1-3个DRS区间，由FIA指定。2026赛季起将被主动空气动力学系统取代。",
        "example": "2021年阿布扎比大奖赛最后一圈，Verstappen在DRS区间完成对Hamilton的超越，夺得年度冠军。",
        "category": "aero", "level": 1, "related_slugs": "ers,boost_limit", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "F1最主要的超车辅助手段", "data_ref": "每圈优势约0.5-1.0秒，直道尾速提升10-15km/h"
    },
    {
        "slug": "sc", "name_zh": "安全车", "name_en": "Safety Car",
        "aliases": "安全车,SC,safety car",
        "short_def": "赛道发生事故时部署，所有赛车跟随行驶不得超车，是进站的黄金时机。",
        "full_def": "安全车（Safety Car）在赛道出现危险情况时由赛事总监部署。所有赛车须排成一列跟随行驶，不得超车。安全车期间是进站的黄金时机（免费进站）。撤回时会亮绿灯，下一圈重新开始比赛。",
        "example": "2021年阿布扎比大奖赛最后5圈的安全车处理方式引发巨大争议，直接影响年度冠军归属。",
        "category": "rules", "level": 1, "related_slugs": "vsc,free_stop", "spec_year": None,
        "scene_tags": "race_common", "why_important": "进站的黄金时机，改变比赛格局", "data_ref": "安全车出动平均导致圈速慢25-30秒"
    },
    {
        "slug": "vsc", "name_zh": "虚拟安全车", "name_en": "Virtual Safety Car",
        "aliases": "虚拟安全车,VSC,virtual safety car",
        "short_def": "不出动实体安全车，所有赛车须将速度降低约30%，用于处理轻微事故。",
        "full_def": "VSC（Virtual Safety Car）于2015年引入，通过电子系统强制所有赛车将速度降低约30%，无需实体安全车上赛道。VSC期间同样可以进站，但时间窗口更短、更难把握，对策略影响极大。",
        "example": "2015年摩纳哥大奖赛，Hamilton在VSC期间进站，Räikkönen因此失去领先位置，引发巨大争议。",
        "category": "rules", "level": 1, "related_slugs": "sc,free_stop", "spec_year": None,
        "scene_tags": "race_common", "why_important": "策略影响极大，时间窗口更难把握", "data_ref": ""
    },
    {
        "slug": "dnf", "name_zh": "未完赛", "name_en": "Did Not Finish",
        "aliases": "DNF,退赛,未完赛",
        "short_def": "赛车因机械故障、事故等原因未能完成比赛，不计入积分。",
        "full_def": "DNF（Did Not Finish）指赛车在比赛中途退出，无论原因是机械故障、碰撞事故、爆胎还是车手主动退赛。DNF不获得任何积分，对车手和车队积分榜影响巨大。",
        "example": "2022赛季法拉利遭遇多次DNF，Leclerc在巴塞罗那和巴库的退赛直接葬送了年度冠军希望。",
        "category": "rules", "level": 1, "related_slugs": "", "spec_year": None,
        "scene_tags": "race_common", "why_important": "直接影响积分榜走势", "data_ref": ""
    },
    {
        "slug": "pit_stop", "name_zh": "进站", "name_en": "Pit Stop",
        "aliases": "进站,换胎,pit stop,box,box box",
        "short_def": "赛车驶入维修区更换轮胎，顶级车队换胎时间可低于2.5秒，是策略的核心环节。",
        "full_def": "进站（Pit Stop）是F1策略的核心环节。赛车驶入维修区后，由约20名机械师协同完成换胎操作。顶级车队换胎时间可低于2.5秒（Red Bull保持1.82秒世界纪录）。进站时机的选择直接决定比赛结果。",
        "example": "2019年巴西大奖赛，Red Bull以1.82秒完成换胎，创下F1史上最快进站纪录。",
        "category": "strategy", "level": 1, "related_slugs": "undercut,overcut,free_stop", "spec_year": None,
        "scene_tags": "race_common", "why_important": "F1策略的核心环节", "data_ref": "当前平均进站时间2.0-2.5秒，最快纪录1.8秒"
    },
    # ── 进阶（level=2）──────────────────────────
    {
        "slug": "undercut", "name_zh": "提前进站", "name_en": "Undercut",
        "aliases": "undercut,提前进站,抢先进站",
        "short_def": "比前车提前进站换上新胎，利用新胎速度优势在前车出站时完成超越。",
        "full_def": "Undercut是F1最经典的策略超车手段。当你无法在赛道上直接超越前车时，提前1-2圈进站换上新胎，利用新胎的速度优势（通常每圈快0.5-1.5秒）在前车出站时完成位置超越。Undercut成功的关键在于：新胎速度优势 > 进站损失时间。",
        "example": "2021年巴西大奖赛，Hamilton对Verstappen实施Undercut，换上新胎后以惊人速度追上并超越，完成逆转夺冠。",
        "category": "strategy", "level": 2, "related_slugs": "overcut,pit_stop", "spec_year": None,
        "scene_tags": "race_common", "why_important": "F1最经典的策略超车手段", "data_ref": "通常领先2-3秒内有效，新胎首圈可快1.5-2.5秒"
    },
    {
        "slug": "overcut", "name_zh": "延迟进站", "name_en": "Overcut",
        "aliases": "overcut,延迟进站,晚进站",
        "short_def": "比前车延迟进站，利用轨道位置优势，在前车出站后保持领先。",
        "full_def": "Overcut与Undercut相反，是延迟进站的策略。当前车进站后，你继续在赛道上行驶，利用空旷赛道跑出快圈。Overcut在摩纳哥等难以超车的赛道尤为有效，也常用于轮胎衰退较慢的情况。",
        "example": "2022年摩纳哥大奖赛，Perez对Leclerc实施Overcut，成功保住领先位置。",
        "category": "strategy", "level": 2, "related_slugs": "undercut,pit_stop,deg", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "难以超车赛道的关键策略", "data_ref": ""
    },
    {
        "slug": "graining", "name_zh": "轮胎起粒", "name_en": "Graining",
        "aliases": "graining,起粒,轮胎起粒",
        "short_def": "轮胎表面橡胶因温度不在工作窗口内撕裂形成小颗粒，导致抓地力下降，通常可自行恢复。",
        "full_def": "Graining（起粒）发生在轮胎温度不在最佳工作窗口时，橡胶表面被撕裂形成小颗粒附着在胎面，导致抓地力大幅下降。与Blistering（起泡）不同，Graining通常是暂时性的，随着颗粒磨掉后抓地力会恢复。常见于比赛初期轮胎未充分预热，或赛道温度过低时。",
        "example": "2023年澳大利亚大奖赛，多位车手遭遇严重Graining，被迫提前进站，打乱原定策略。",
        "category": "tyre", "level": 2, "related_slugs": "deg,tyre_window", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "影响轮胎策略和进站时机", "data_ref": ""
    },
    {
        "slug": "deg", "name_zh": "轮胎衰退", "name_en": "Tyre Degradation",
        "aliases": "deg,degradation,轮胎衰退,轮胎磨损",
        "short_def": "轮胎随圈数增加性能逐渐下降的速率，衰退越快意味着需要越早进站。",
        "full_def": "Tyre Degradation（轮胎衰退，简称Deg）是衡量轮胎性能随时间/圈数下降速率的指标。高Deg赛道（如巴塞罗那、巴林）会迫使车队采用多停策略；低Deg赛道（如摩纳哥、匈牙利）则有利于一停策略。",
        "example": "2022年巴塞罗那大奖赛，法拉利因高Deg被迫三停，而Red Bull一停策略成功，Verstappen逆转夺冠。",
        "category": "tyre", "level": 2, "related_slugs": "graining,undercut", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "决定进站策略的关键指标", "data_ref": ""
    },
    {
        "slug": "parc_ferme", "name_zh": "封闭停车场", "name_en": "Parc Fermé",
        "aliases": "parc fermé,parc ferme,封闭停车场,封车",
        "short_def": "排位赛结束后禁止对赛车进行重大改动，违者须从最后一位起跑。",
        "full_def": "Parc Fermé（法语，意为封闭停车场）规则规定，从排位赛Q2结束后，车队不得对赛车进行超出允许范围的改动。违反Parc Fermé规则的车手须从最后一位或维修区起跑。",
        "example": "2023年日本大奖赛，多支车队因雨天改变车辆设定违反Parc Fermé规则，被罚从维修区起跑。",
        "category": "rules", "level": 2, "related_slugs": "drs,pit_stop", "spec_year": None,
        "scene_tags": "race_common", "why_important": "限制排位赛后车辆改动", "data_ref": ""
    },
    # ── 高阶（level=3）──────────────────────────
    {
        "slug": "boost_limit", "name_zh": "加速模式上限", "name_en": "Boost Power Limit",
        "aliases": "boost,boost limit,加速模式,boost上限",
        "short_def": "2025赛季新规：正赛中加速模式功率增量上限为+150kW，防止后车获得过大瞬时速度优势。",
        "full_def": "2025赛季FIA引入Boost上限规定，正赛中激活加速模式时，功率增量被限制在+150kW以内（或激活时的当前功率水平，取较高者）。该规定旨在防止后车在直道获得过大的瞬时速度优势，维持比赛公平性。与DRS类似，Boost模式在特定区间才可激活，是2026年主动空气动力学系统的过渡方案。",
        "example": "2025年迈阿密大奖赛首次全面实施Boost上限规定，多位车手反映该限制影响了超车策略。",
        "category": "power_unit", "level": 3, "related_slugs": "drs,ers,mgu_k", "spec_year": 2025,
        "scene_tags": "tech_talk,2026_new", "why_important": "2026主动空力系统的过渡方案", "data_ref": ""
    },
    {
        "slug": "mgu_k", "name_zh": "动能回收单元", "name_en": "MGU-K",
        "aliases": "MGU-K,MGU K,动能回收,MGUK",
        "short_def": "混合动力系统中负责回收制动能量并在加速时释放的电动机，最大输出120kW。",
        "full_def": "MGU-K（Motor Generator Unit – Kinetic）是F1混合动力系统的核心组件。制动时作为发电机回收动能存入电池；加速时作为电动机释放能量辅助内燃机。最大输出功率120kW（约161马力），每圈可部署约33秒。2026年新规下MGU-H被取消，MGU-K功率将大幅提升至350kW。",
        "example": "2022年红牛赛季中期，Verstappen的MGU-K故障导致法国大奖赛退赛，影响积分领先优势。",
        "category": "power_unit", "level": 3, "related_slugs": "ers,boost_limit,torque_limit", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "F1混动系统的核心组件", "data_ref": "2026版功率350kW，是2025版的约3倍"
    },
    {
        "slug": "torque_limit", "name_zh": "扭矩限制", "name_en": "ERS Torque Limit",
        "aliases": "torque limit,扭矩限制,ERS扭矩",
        "short_def": "低抓地力环境下FIA强制降低ERS最大输出扭矩，改善车辆可控性，防止轮胎打滑。",
        "full_def": "ERS扭矩限制是FIA针对特定赛道条件（如湿滑赛道、低温环境）实施的安全规定。当赛道抓地力不足时，ERS的最大输出扭矩会被强制降低，防止车手在出弯加速时因电动机扭矩过大导致轮胎打滑失控。该系统与低功率起步监测系统配合使用，提升起步安全性。",
        "example": "2025年迈阿密大奖赛测试了新的低功率起步监测系统，配合扭矩限制确保起步安全。",
        "category": "power_unit", "level": 3, "related_slugs": "mgu_k,ers,boost_limit", "spec_year": 2025,
        "scene_tags": "tech_talk", "why_important": "确保低抓地力条件下的起步安全", "data_ref": ""
    },
    {
        "slug": "porpoising", "name_zh": "海豚跳", "name_en": "Porpoising",
        "aliases": "porpoising,海豚跳,弹跳",
        "short_def": "地面效应赛车在高速行驶时车底气流周期性失速，导致赛车上下剧烈弹跳的现象。",
        "full_def": "Porpoising是2022年地面效应规则回归后出现的空气动力学现象。当赛车底部气流产生足够下压力时，车身被压低；但车身过低导致气流失速，下压力骤降，车身弹起；弹起后气流恢复，再次被压低——如此循环形成高频弹跳。严重的Porpoising会影响车手健康（脊椎损伤风险）和赛车性能。",
        "example": "2022赛季初，梅赛德斯W13遭遇严重Porpoising，Hamilton在巴库大奖赛后因背部疼痛几乎无法下车。",
        "category": "aero", "level": 3, "related_slugs": "ground_effect,downforce", "spec_year": 2022,
        "scene_tags": "tech_talk", "why_important": "地效规则下的安全隐患", "data_ref": ""
    },
    {
        "slug": "ground_effect", "name_zh": "地面效应", "name_en": "Ground Effect",
        "aliases": "ground effect,地面效应,底部气流,underfloor",
        "short_def": "利用赛车底部文丘里通道产生低压区，将赛车吸附在赛道上，产生大量下压力。",
        "full_def": "地面效应（Ground Effect）通过赛车底部的文丘里形通道加速气流，根据伯努利原理产生低压区，将赛车向下吸附。相比传统翼片产生的下压力，地面效应更高效（阻力更小），且对跟车影响较小（有利于超车）。1970年代Lotus首创，1983年被禁止，2022年规则改革后重新引入。",
        "example": "2022年规则改革引入地面效应底板，理论上改善了跟车效果，但同时带来了Porpoising问题。",
        "category": "aero", "level": 3, "related_slugs": "porpoising,downforce,drs", "spec_year": 2022,
        "scene_tags": "tech_talk", "why_important": "2022规则改革的核心技术", "data_ref": ""
    },
    # ── 2026 新规术语 ─────────────────────────────
    {
        "slug": "active_aero", "name_zh": "主动空气动力学", "name_en": "Active Aerodynamics",
        "aliases": "active aero,主动空气动力学,主动气动,active aerodynamics",
        "short_def": "2026年取代DRS的全新系统，赛车前后翼可在直道自动收平减阻，弯道自动展开增加下压力。",
        "full_def": "2026年F1规则改革的核心变化之一。不同于DRS只能开启/关闭后翼一块翼片，主动空气动力学系统允许整个前翼和后翼根据行驶状态自动调整角度。直道进入X-Mode（低阻力），弯道切换Z-Mode（高下压力），系统由FIA统一控制，车手无法手动干预切换时机。",
        "example": "2026年澳大利亚大奖赛是主动空气动力学系统首次在正式比赛中使用，多位车手反映跟车效果明显改善。",
        "category": "aero", "level": 2, "related_slugs": "x_mode,z_mode,drs,downforce", "spec_year": 2026,
        "scene_tags": "2026_new,tech_talk", "why_important": "2026规则改革的核心变化", "data_ref": "弯角模式下压力增加约60%，直道模式阻力减少约55%"
    },
    {
        "slug": "x_mode", "name_zh": "X模式", "name_en": "X-Mode",
        "aliases": "X-Mode,X模式,低阻力模式,highway mode",
        "short_def": "2026主动空气动力学的低阻力状态，直道行驶时前后翼自动收平，最大化直道速度。",
        "full_def": "X-Mode是2026年主动空气动力学系统的两种状态之一。当赛车进入直道区间，系统自动将前翼和后翼调整至最小阻力角度，效果远超旧版DRS（作用于整个翼面而非单一翼片）。X-Mode的激活由FIA系统控制，基于赛道位置自动触发，不依赖与前车的距离差。",
        "example": "2026赛季初，X-Mode的引入使直道速度差异大幅缩小，超车更多发生在制动点而非依赖直道速度优势。",
        "category": "aero", "level": 2, "related_slugs": "z_mode,active_aero,downforce", "spec_year": 2026,
        "scene_tags": "2026_new,tech_talk", "why_important": "2026低阻力模式，超越DRS效果", "data_ref": ""
    },
    {
        "slug": "z_mode", "name_zh": "Z模式", "name_en": "Z-Mode",
        "aliases": "Z-Mode,Z模式,高下压力模式,street mode",
        "short_def": "2026主动空气动力学的高下压力状态，过弯时前后翼自动展开，提供最大抓地力。",
        "full_def": "Z-Mode是2026年主动空气动力学系统的默认过弯状态。前后翼展开至最大角度，提供充足下压力确保过弯稳定性。与X-Mode的切换由系统自动完成，切换点由FIA根据赛道地图预设。车迷和媒体有时也称其为Street Mode（街道模式），因为其高下压力特性类似街道赛设定。",
        "example": "2026年摩纳哥大奖赛全程几乎都在Z-Mode下行驶，主动空气动力学系统的优势在低速弯道赛道体现有限。",
        "category": "aero", "level": 2, "related_slugs": "x_mode,active_aero,downforce", "spec_year": 2026,
        "scene_tags": "2026_new,tech_talk", "why_important": "2026高下压力过弯状态", "data_ref": ""
    },
    {
        "slug": "super_clipping", "name_zh": "超级削峰", "name_en": "Super Clipping",
        "aliases": "super clipping,超级削峰,电能限制,clipping",
        "short_def": "2026赛季出现的现象：电池电量不足时MGU-K输出被强制削减，直道末端明显掉速。",
        "full_def": "Super Clipping是2026年新动力单元规则下出现的特有现象。2026年MGU-K最大输出功率提升至约350kW（是2025年的近3倍），电池消耗极快。当电池电量低于阈值时，系统自动削减MGU-K输出（Clipping），严重时车手在直道末端会感受到明显的动力骤降。管理电池电量成为2026年车手的核心技能之一。",
        "example": "2026年巴林大奖赛，多位车手在最后几圈因Super Clipping损失大量时间，电池管理策略成为赛后讨论焦点。",
        "category": "power_unit", "level": 3, "related_slugs": "mgu_k,ers,boost_limit", "spec_year": 2026,
        "scene_tags": "2026_new,tech_talk", "why_important": "2026电池管理的核心挑战", "data_ref": ""
    },
    {
        "slug": "mgu_k_2026", "name_zh": "动能电机（2026）", "name_en": "MGU-K 2026",
        "aliases": "MGU-K 2026,新MGU-K,350kW电机",
        "short_def": "2026年大幅升级的动能回收电机，最大输出从120kW提升至约350kW，占总功率约50%。",
        "full_def": "2026年规则改革取消了MGU-H（热能回收电机），同时大幅提升MGU-K的功率上限至约350kW。整车动力目标实现ICE与电机各占50%的均衡分配。更强的MGU-K带来更快的加速，但也导致电池消耗更快，Super Clipping问题更加突出。",
        "example": "2026年新动力单元首次亮相时，各厂商的MGU-K可靠性差异明显，成为赛季初期竞争格局的关键变量。",
        "category": "power_unit", "level": 3, "related_slugs": "super_clipping,ers,mgu_k", "spec_year": 2026,
        "scene_tags": "2026_new,tech_talk", "why_important": "2026动力单元的核心升级", "data_ref": ""
    },
    {
        "slug": "sustainable_fuel", "name_zh": "可持续燃料", "name_en": "Sustainable Fuel",
        "aliases": "sustainable fuel,可持续燃料,E10,绿色燃料,e-fuel",
        "short_def": "2026年F1强制使用100%可持续燃料，是F1碳中和路线图的核心组成部分。",
        "full_def": "2026年F1规则要求所有赛车使用100%可持续燃料（Sustainable Fuel），包括生物燃料或合成燃料（e-fuel）。此前2022年已引入E10（10%乙醇混合燃料）作为过渡。可持续燃料的能量密度和燃烧特性与传统燃料略有差异，各动力单元厂商需针对新燃料重新优化内燃机调校。",
        "example": "2026年可持续燃料的全面推行是F1实现2030年碳中和目标的关键一步，也是各动力单元厂商研发的重要课题。",
        "category": "power_unit", "level": 2, "related_slugs": "ice,mgu_k_2026", "spec_year": 2026,
        "scene_tags": "2026_new,tech_talk", "why_important": "F1碳中和路线图的核心组成", "data_ref": ""
    },
    # 空气动力学
    {
        "slug": "dirty_air", "name_zh": "脏气流", "name_en": "Dirty Air",
        "aliases": "dirty air,脏气流,乱流,紊流",
        "short_def": "前车尾流产生的湍流，使跟车赛车下压力损失高达50%，难以靠近超车。",
        "full_def": "脏气流（Dirty Air）是F1超车难的核心原因。前车高速行驶时产生的湍流会破坏后车的空气动力学效率，导致下压力损失、轮胎过热，使跟车变得极为困难。2022年地面效应规则改革的主要目标之一就是减少脏气流影响。",
        "example": "2019年巴塞罗那大奖赛，Hamilton在脏气流中跟随Bottas超过30圈无法超越，充分展示了脏气流的影响。",
        "category": "aero", "level": 2, "related_slugs": "ground_effect,drs,downforce", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "F1超车难的核心原因", "data_ref": "跟车时下压力损失可达30-50%"
    },
    {
        "slug": "downforce", "name_zh": "下压力", "name_en": "Downforce",
        "aliases": "downforce,下压力,抓地力",
        "short_def": "空气动力学产生的向下压力，使轮胎抓地力增加，提升过弯速度，但同时增加阻力。",
        "full_def": "下压力（Downforce）是F1赛车空气动力学的核心指标。通过前后翼片、底板等部件产生，将赛车压向赛道，使轮胎获得更大抓地力，从而以更高速度过弯。但下压力越大，阻力也越大，直道速度越慢。高下压力设定适合弯道多的赛道（如摩纳哥），低下压力适合直道多的赛道（如蒙扎）。",
        "example": "2022年蒙扎大奖赛，各队采用最低下压力设定，Monza赛道的高速特性使赛车直道速度超过350km/h。",
        "category": "aero", "level": 1, "related_slugs": "drs,dirty_air,ground_effect", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "F1空力学的核心指标", "data_ref": "时速300km/h时产生的下压力约为车重的3-5倍"
    },
    {
        "slug": "understeer", "name_zh": "转向不足", "name_en": "Understeer",
        "aliases": "understeer,转向不足,推头",
        "short_def": "前轮失去抓地力，车头无法按预期转向，俗称推头，赛车会冲向弯道外侧。",
        "full_def": "转向不足（Understeer）是指赛车前轮抓地力不足，导致车头无法按照车手预期的方向转向，赛车会向弯道外侧滑出。通常由前轮过热、前翼下压力不足或入弯速度过高引起。车手会感觉方向盘没有反应。",
        "example": "2023年赛季，法拉利SF-23在多个赛道被车手反映存在严重推头问题，影响单圈速度。",
        "category": "aero", "level": 2, "related_slugs": "oversteer,balance,tyre_window", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "影响赛车操控和圈速", "data_ref": ""
    },
    {
        "slug": "oversteer", "name_zh": "转向过度", "name_en": "Oversteer",
        "aliases": "oversteer,转向过度,甩尾,snap oversteer",
        "short_def": "后轮失去抓地力，车尾向外甩出，需要反打方向盘修正，极端情况下会打转。",
        "full_def": "转向过度（Oversteer）是指赛车后轮抓地力不足，车尾向弯道外侧滑出。轻微的Oversteer可以通过反打方向盘修正，有经验的车手甚至会主动利用轻微Oversteer来旋转车头加快过弯。但严重的Snap Oversteer（突然甩尾）极难控制，容易导致打转。",
        "example": "Hamilton以擅长控制Oversteer著称，能在赛车后轮滑动时精准修正，这也是其雨战能力出众的原因之一。",
        "category": "aero", "level": 2, "related_slugs": "understeer,balance", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "影响赛车操控和安全性", "data_ref": ""
    },
    {
        "slug": "diffuser", "name_zh": "扩散器", "name_en": "Diffuser",
        "aliases": "diffuser,扩散器,尾部扩散器",
        "short_def": "车尾底部的气流加速装置，加速底部气流排出，是产生地面效应下压力的关键部件。",
        "full_def": "扩散器（Diffuser）位于赛车底部后端，通过扩大截面积使底部气流减速、压力升高，从而加速前方底板气流，增强地面效应产生的下压力。扩散器的设计是F1空气动力学中最复杂的部分之一，各队在此投入大量研发资源。",
        "example": "2009年布朗GP的双层扩散器设计引发巨大争议，该设计在赛季初期为车队带来压倒性优势。",
        "category": "aero", "level": 3, "related_slugs": "ground_effect,downforce", "spec_year": None,
        "scene_tags": "tech_talk,2026_new", "why_important": "地效下压力的关键产生部件", "data_ref": ""
    },
    {
        "slug": "rake", "name_zh": "车身倾角", "name_en": "Rake",
        "aliases": "rake,车身倾角,前低后高",
        "short_def": "赛车前后高度差形成的倾斜角度，高Rake设定有助于扩散器效率，但影响前翼气流。",
        "full_def": "Rake是指赛车前端离地间隙低于后端，形成前低后高的倾斜角度。高Rake设定（如Red Bull）有助于提升扩散器效率，产生更多底部下压力；低Rake设定（如梅赛德斯）则更依赖底板气流。2022年规则改革后，各队Rake设定趋于一致。",
        "example": "2021年赛季，Red Bull的高Rake设定与梅赛德斯低Rake设定之间的技术路线之争是当年最大看点之一。",
        "category": "aero", "level": 3, "related_slugs": "ground_effect,diffuser", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "影响空力设定路线的关键参数", "data_ref": ""
    },
    # 轮胎
    {
        "slug": "soft_tyre", "name_zh": "软胎", "name_en": "Soft Tyre",
        "aliases": "软胎,红胎,S胎,soft",
        "short_def": "最软的干胎配方，抓地力最强但磨损最快，标识为红色，通常用于排位赛。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 1, "related_slugs": "medium_tyre,hard_tyre,deg", "spec_year": None,
        "scene_tags": "race_common", "why_important": "排位赛首选轮胎", "data_ref": ""
    },
    {
        "slug": "medium_tyre", "name_zh": "中性胎", "name_en": "Medium Tyre",
        "aliases": "中性胎,黄胎,M胎,medium",
        "short_def": "中等硬度干胎，性能与耐久性平衡，标识为黄色，是最常用的正赛轮胎。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 1, "related_slugs": "soft_tyre,hard_tyre", "spec_year": None,
        "scene_tags": "race_common", "why_important": "正赛最常用的轮胎", "data_ref": ""
    },
    {
        "slug": "hard_tyre", "name_zh": "硬胎", "name_en": "Hard Tyre",
        "aliases": "硬胎,白胎,H胎,hard",
        "short_def": "最硬的干胎配方，耐久性最强但需要更长暖胎时间，标识为白色。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 1, "related_slugs": "soft_tyre,medium_tyre,deg", "spec_year": None,
        "scene_tags": "race_common", "why_important": "长stint策略的基础轮胎", "data_ref": ""
    },
    {
        "slug": "intermediate", "name_zh": "中间胎", "name_en": "Intermediate",
        "aliases": "中间胎,绿胎,inter,中雨胎,intermediate",
        "short_def": "轻度湿滑路面使用的雨胎，标识为绿色，适合潮湿但无积水赛道。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 1, "related_slugs": "wet_tyre", "spec_year": None,
        "scene_tags": "race_common", "why_important": "雨天比赛的策略关键", "data_ref": ""
    },
    {
        "slug": "wet_tyre", "name_zh": "全雨胎", "name_en": "Full Wet",
        "aliases": "全雨胎,蓝胎,雨胎,wet,extreme wet",
        "short_def": "大雨条件下使用的雨胎，标识为蓝色，排水能力最强，每秒可排水65升。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 1, "related_slugs": "intermediate", "spec_year": None,
        "scene_tags": "race_common", "why_important": "大雨条件下的安全保陕", "data_ref": "每秒可排水65升"
    },
    {
        "slug": "blistering", "name_zh": "轮胎起泡", "name_en": "Blistering",
        "aliases": "blistering,起泡,热泡,轮胎起泡",
        "short_def": "轮胎内部过热导致表面形成气泡，属不可逆损伤，严重时须立即进站。",
        "full_def": "Blistering（起泡）与Graining（起粒）不同，是轮胎内部温度过高导致橡胶层分离，表面形成气泡的不可逆损伤。一旦出现严重起泡，轮胎性能会急剧下降，甚至有爆胎风险，必须立即进站。通常发生在制动区或高速弯道。",
        "example": "2022年法国大奖赛，Leclerc的轮胎出现严重起泡，被迫提前进站，最终退赛，葬送了领先优势。",
        "category": "tyre", "level": 2, "related_slugs": "deg,graining,cliff", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "轮胎过热的严重不可逆损伤", "data_ref": ""
    },
    {
        "slug": "cliff", "name_zh": "悬崖式衰退", "name_en": "Tyre Cliff",
        "aliases": "cliff,悬崖,掉悬崖,tyre cliff",
        "short_def": "轮胎性能突然急剧下降的临界点，过了cliff圈速会骤降数秒。",
        "full_def": "Tyre Cliff是指轮胎在某个临界点之后性能突然急剧下降，而非缓慢衰退。车手会感觉赛车突然变得难以控制，圈速骤降。Cliff的出现通常意味着必须立即进站，否则会损失大量时间。某些轮胎配方（尤其是软胎）在高温赛道更容易出现Cliff。",
        "example": "2023年拉斯维加斯大奖赛，多位车手遭遇轮胎Cliff，被迫提前进站，打乱策略。",
        "category": "tyre", "level": 2, "related_slugs": "deg,blistering,graining", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "决定进站时机的关键因素", "data_ref": "性能悬崖后单圈损失可达2-4秒"
    },
    {
        "slug": "tyre_window", "name_zh": "轮胎工作窗口", "name_en": "Tyre Operating Window",
        "aliases": "tyre window,工作窗口,温度窗口,operating window",
        "short_def": "轮胎发挥最佳性能所需的温度范围，过冷或过热都会导致性能下降。",
        "full_def": "每种轮胎配方都有其最佳工作温度范围（Operating Window）。温度过低时轮胎太硬，抓地力不足（容易Graining）；温度过高时橡胶过软，磨损加剧（容易Blistering）。车手需要通过驾驶风格和赛车设定将轮胎温度维持在工作窗口内。",
        "example": "2023年卡塔尔大奖赛，赛道温度极高，多位车手无法将轮胎控制在工作窗口内，导致大量进站。",
        "category": "tyre", "level": 2, "related_slugs": "graining,blistering,deg", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "轮胎策略的核心参数", "data_ref": ""
    },
    # 策略
    {
        "slug": "free_stop", "name_zh": "免费进站", "name_en": "Free Stop",
        "aliases": "free stop,免费进站,白嫖进站,免费换胎",
        "short_def": "在安全车或VSC期间进站，几乎不损失时间，相当于免费换一套新胎。",
        "full_def": "免费进站（Free Stop）是F1策略中最宝贵的机会。安全车/VSC期间，所有赛车速度大幅降低，进站损失的时间（通常20-25秒）被大幅压缩，有时甚至可以进站后不损失任何位置。抓住免费进站机会往往能改变比赛结果。",
        "example": "2021年阿布扎比大奖赛，Red Bull抓住最后阶段安全车机会让Verstappen免费进站换上新胎，最终逆转夺冠。",
        "category": "strategy", "level": 2, "related_slugs": "sc,vsc,undercut", "spec_year": None,
        "scene_tags": "race_common", "why_important": "改变比赛结果的黄金机会", "data_ref": ""
    },
    {
        "slug": "stint", "name_zh": "轮胎使用段", "name_en": "Stint",
        "aliases": "stint,一段,轮胎段",
        "short_def": "两次进站之间连续使用同一套轮胎的阶段，stint长度是策略规划的核心。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 2, "related_slugs": "deg,undercut,one_stop", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "策略规划的核心变量", "data_ref": ""
    },
    {
        "slug": "one_stop", "name_zh": "一停策略", "name_en": "One-Stop Strategy",
        "aliases": "一停,单停,one stop,one-stop",
        "short_def": "全程只进站一次的策略，通常需要硬胎支撑较长stint，适合低deg赛道。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 1, "related_slugs": "two_stop,stint,deg", "spec_year": None,
        "scene_tags": "race_common", "why_important": "基础策略选项", "data_ref": "平均比双进站节省约22-25秒（一次进站时间损失）"
    },
    {
        "slug": "two_stop", "name_zh": "两停策略", "name_en": "Two-Stop Strategy",
        "aliases": "两停,双停,two stop,two-stop",
        "short_def": "全程进站两次，换三套轮胎，适合高deg赛道或需要追赶时使用。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 1, "related_slugs": "one_stop,stint,deg", "spec_year": None,
        "scene_tags": "race_common", "why_important": "现代F1的主流策略", "data_ref": ""
    },
    {
        "slug": "stacking", "name_zh": "叠站", "name_en": "Stacking",
        "aliases": "stacking,叠站,连续进站,堆站",
        "short_def": "同队两辆车连续进站，后车须在pit lane等待，通常导致其中一辆损失时间。",
        "full_def": "叠站（Stacking）发生在同队两辆车几乎同时进站时。由于pit box只能容纳一辆车，后进站的车须在pit lane等待前车离开，通常会损失数秒时间。车队会尽量避免叠站，但在安全车等特殊情况下有时不得不接受。",
        "example": "2023年巴林大奖赛，Red Bull两车叠站，Perez在pit lane等待Verstappen，损失约4秒。",
        "category": "strategy", "level": 2, "related_slugs": "pit_stop,undercut", "spec_year": None,
        "scene_tags": "race_common", "why_important": "同队进站的时间管理挑战", "data_ref": "后车通常损失3-5秒"
    },
    {
        "slug": "offset_strategy", "name_zh": "错位策略", "name_en": "Offset Strategy",
        "aliases": "offset strategy,错位策略,分化策略,对冲策略",
        "short_def": "同队两车采用不同轮胎策略，覆盖更多比赛情景，增加至少一辆车获得好成绩的概率。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 2, "related_slugs": "one_stop,two_stop,stint", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "车队战术的高级应用", "data_ref": ""
    },
    {
        "slug": "out_lap", "name_zh": "出站圈", "name_en": "Out Lap",
        "aliases": "out lap,出站圈,热身圈",
        "short_def": "从pit lane出发后的第一圈，用于将轮胎和刹车加热到工作温度。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 2, "related_slugs": "in_lap,tyre_window,pit_stop", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "进站后圈速恢复的关键圈", "data_ref": ""
    },
    {
        "slug": "in_lap", "name_zh": "进站圈", "name_en": "In Lap",
        "aliases": "in lap,进站圈",
        "short_def": "进入pit lane前的最后一圈，车手通常会保护轮胎，圈速较慢。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 2, "related_slugs": "out_lap,pit_stop", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "进站策略执行的关键圈", "data_ref": ""
    },
    {
        "slug": "delta_time", "name_zh": "时间差", "name_en": "Delta Time",
        "aliases": "delta,delta time,时间差,时差",
        "short_def": "VSC期间车手须维持的目标圈速基准，超速会被罚款，慢太多会损失位置。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 2, "related_slugs": "vsc,sc", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "VSC和安全车程序中的关键参数", "data_ref": ""
    },
    {
        "slug": "purple_sector", "name_zh": "紫色扇区", "name_en": "Purple Sector",
        "aliases": "紫色扇区,紫色,最快扇区,purple sector",
        "short_def": "当前session中某扇区的最快时间，计时屏幕显示为紫色，绿色表示个人最快。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 1, "related_slugs": "fastest_lap,quali", "spec_year": None,
        "scene_tags": "race_common", "why_important": "排位赛中的关键圈速指标", "data_ref": ""
    },
    {
        "slug": "fastest_lap", "name_zh": "最快圈", "name_en": "Fastest Lap",
        "aliases": "最快圈,FL,fastest lap,紫色圈",
        "short_def": "正赛中跑出全场最快单圈，额外获得1分（须在前10名完赛）。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "purple_sector", "spec_year": None,
        "scene_tags": "race_common", "why_important": "额外1分可影响积分排名", "data_ref": ""
    },
    # 规则
    {
        "slug": "track_limits", "name_zh": "赛道边界", "name_en": "Track Limits",
        "aliases": "track limits,赛道边界,出界,压线",
        "short_def": "赛车四轮须在白线内行驶，违规圈速将被删除，正赛违规累计可被处罚。",
        "full_def": "赛道边界（Track Limits）规定赛车四轮须在白线标记的赛道范围内行驶。排位赛中违规圈速直接删除；正赛中违规超车须归还位置，累计违规可被处以5秒罚时。近年来Track Limits争议频发，尤其是奥地利、美国等赛道。",
        "example": "2023年奥地利大奖赛，多位车手因反复违反赛道边界被处罚，Verstappen也未能幸免。",
        "category": "rules", "level": 1, "related_slugs": "quali,dnf", "spec_year": None,
        "scene_tags": "race_common", "why_important": "影响圈速和比赛成绩的规则", "data_ref": ""
    },
    {
        "slug": "quali", "name_zh": "排位赛", "name_en": "Qualifying",
        "aliases": "排位赛,quali,qualifying,Q1,Q2,Q3",
        "short_def": "决定正赛出发顺序的计时赛，分Q1/Q2/Q3三段淘汰制，Q3前10名争夺杆位。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "parc_ferme,sprint,track_limits", "spec_year": None,
        "scene_tags": "race_common", "why_important": "决定正赛出发顺序", "data_ref": ""
    },
    {
        "slug": "sprint", "name_zh": "冲刺赛", "name_en": "Sprint Race",
        "aliases": "冲刺赛,sprint,短赛,sprint race",
        "short_def": "部分站点设置的100km短程正赛，独立积分（最高8分），不影响正赛排位。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "quali,fastest_lap", "spec_year": None,
        "scene_tags": "race_common", "why_important": "现代F1周末赛制的重要组成", "data_ref": ""
    },
    {
        "slug": "cost_cap", "name_zh": "预算上限", "name_en": "Cost Cap",
        "aliases": "cost cap,预算上限,预算帽,支出上限",
        "short_def": "FIA规定的车队年度运营支出上限，旨在缩小大小车队差距，违规将受严厉处罚。",
        "full_def": "预算上限（Cost Cap）于2021年引入，规定各车队每年运营支出不得超过规定金额（2024年约1.45亿美元）。超支将受到积分扣除、禁赛等严厉处罚。2022年Red Bull因超支被扣除2023年风洞测试时间，引发巨大争议。",
        "example": "2022年Red Bull被认定超出预算上限约140万美元，被处以700万美元罚款并扣除10%风洞测试时间。",
        "category": "rules", "level": 2, "related_slugs": "constructors,penalty_points", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "缩小大小车队差距的关键制度", "data_ref": "2024年约1.45亿美元"
    },
    {
        "slug": "halo", "name_zh": "光环装置", "name_en": "Halo",
        "aliases": "halo,光环,光环装置,头部保护",
        "short_def": "2018年引入的钛合金头部保护装置，可承受12吨压力，已多次在事故中救下车手生命。",
        "full_def": "Halo是安装在驾驶舱上方的钛合金保护结构，2018年强制引入时饱受争议，被认为影响美观。但此后多次重大事故证明了其价值：2020年巴林大奖赛Grosjean撞车起火、2021年意大利大奖赛Verstappen赛车压过Hamilton头盔，Halo均发挥了关键保护作用。",
        "example": "2021年意大利大奖赛，Verstappen的赛车在碰撞后飞起压过Hamilton的头盔，Halo直接救了Hamilton的命。",
        "category": "rules", "level": 1, "related_slugs": "dnf", "spec_year": None,
        "scene_tags": "race_common", "why_important": "已多次救下车手生命的安全装置", "data_ref": "可承受12吨压力"
    },
    {
        "slug": "blue_flag", "name_zh": "蓝旗", "name_en": "Blue Flag",
        "aliases": "蓝旗,blue flag,让超",
        "short_def": "提示被套圈车手须让领先圈车手超越，忽视蓝旗将受到处罚。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "yellow_flag,red_flag", "spec_year": None,
        "scene_tags": "race_common", "why_important": "确保比赛顺利进行的交通管制", "data_ref": ""
    },
    {
        "slug": "yellow_flag", "name_zh": "黄旗", "name_en": "Yellow Flag",
        "aliases": "黄旗,yellow flag,减速旗",
        "short_def": "赛道前方有危险，须减速并禁止超车，违规将被处罚。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "red_flag,sc,blue_flag", "spec_year": None,
        "scene_tags": "race_common", "why_important": "赛道安全的即时信号", "data_ref": ""
    },
    {
        "slug": "red_flag", "name_zh": "红旗", "name_en": "Red Flag",
        "aliases": "红旗,red flag,中断赛事",
        "short_def": "赛事中断，所有车辆须立即减速返回pit lane或停车，比赛暂停。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "sc,yellow_flag", "spec_year": None,
        "scene_tags": "race_common", "why_important": "赛事严重中断的信号", "data_ref": ""
    },
    {
        "slug": "chequered_flag", "name_zh": "方格旗", "name_en": "Chequered Flag",
        "aliases": "方格旗,格子旗,终点旗,chequered flag",
        "short_def": "比赛结束信号，领先车手越过终点线时挥动，此后所有车手成绩锁定。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "fastest_lap", "spec_year": None,
        "scene_tags": "race_common", "why_important": "比赛结束的标志性信号", "data_ref": ""
    },
    {
        "slug": "drs_zone", "name_zh": "DRS区", "name_en": "DRS Zone",
        "aliases": "DRS区,DRS检测点,DRS区间,drs zone",
        "short_def": "赛道上允许开启DRS的特定直道区间，须在检测点内距前车1秒以内才可开启。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "drs,downforce", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "DRS系统的运作空间", "data_ref": ""
    },
    {
        "slug": "ers", "name_zh": "能量回收系统", "name_en": "ERS",
        "aliases": "ERS,能量回收,混动系统",
        "short_def": "MGU-K和MGU-H的统称，每圈可额外释放约33秒的额外功率，是超车的重要手段。",
        "full_def": None, "example": None,
        "category": "power_unit", "level": 2, "related_slugs": "mgu_k,boost_limit,drs", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "超车和防守的重要能量工具", "data_ref": ""
    },
    {
        "slug": "ice", "name_zh": "内燃机", "name_en": "ICE",
        "aliases": "ICE,内燃机,发动机本体,internal combustion engine",
        "short_def": "动力单元中的1.6L V6涡轮增压汽油发动机部分，每赛季使用数量受限。",
        "full_def": None, "example": None,
        "category": "power_unit", "level": 2, "related_slugs": "boost_button,ers,mgu_k", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "动力单元的核心组成部分", "data_ref": ""
    },
    {
        "slug": "marbles", "name_zh": "轮胎碎屑", "name_en": "Marbles",
        "aliases": "marbles,轮胎碎屑,橡胶颗粒,rubber marbles",
        "short_def": "轮胎磨损产生的橡胶颗粒堆积在赛道边缘，驶上后抓地力极差，容易失控。",
        "full_def": "Marbles是轮胎磨损产生的橡胶颗粒，被甩到赛道边缘堆积。赛道外侧的Marbles区域抓地力极差，车手一旦驶上几乎无法控制赛车。这也是为什么F1车手不愿意走赛道外侧防守——一旦被逼到Marbles区域，超车几乎无法避免。",
        "example": "2023年摩纳哥大奖赛，多位车手在Marbles区域失控，导致多起碰撞事故。",
        "category": "tyre", "level": 2, "related_slugs": "deg,track_limits", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "影响赛道外侧行驶安全", "data_ref": ""
    },
    {
        "slug": "warm_up_lap", "name_zh": "暖胎圈", "name_en": "Formation Lap",
        "aliases": "暖胎圈,formation lap,warm up lap,热身圈",
        "short_def": "正赛出发前的一圈，车手蛇形行驶为轮胎加热，确保轮胎在起步时处于工作温度。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 1, "related_slugs": "tyre_window,soft_tyre", "spec_year": None,
        "scene_tags": "race_common", "why_important": "确保起步时轮胎处于工作温度", "data_ref": ""
    },
    {
        "slug": "backmarker", "name_zh": "末位车手", "name_en": "Backmarker",
        "aliases": "backmarker,末位,尾灯,被套圈",
        "short_def": "处于积分圈外的落后车手，通常需要接受蓝旗让路给领先车手。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 1, "related_slugs": "blue_flag,lapped_car", "spec_year": None,
        "scene_tags": "race_common", "why_important": "影响领先集团超车的因素", "data_ref": ""
    },
    {
        "slug": "lapped_car", "name_zh": "被套圈车", "name_en": "Lapped Car",
        "aliases": "lapped car,被套圈,落后一圈",
        "short_def": "被领先车手超越整一圈的赛车，安全车期间有时会被允许解套圈。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 1, "related_slugs": "backmarker,sc,unlap", "spec_year": None,
        "scene_tags": "race_common", "why_important": "安全车期间的关键变量", "data_ref": ""
    },
    {
        "slug": "unlap", "name_zh": "解套圈", "name_en": "Unlapping",
        "aliases": "unlap,解套圈,解套,unlapping",
        "short_def": "安全车期间被套圈车辆被允许超越安全车，重新回到领先集团后方。",
        "full_def": "解套圈（Unlapping）是指安全车期间，赛事总监允许被套圈的赛车超越安全车，回到领先集团后方。这一操作在2021年阿布扎比大奖赛引发巨大争议——赛事总监只允许部分被套圈车辆解套，导致Verstappen直接跟在Hamilton后方重新起跑。",
        "example": "2021年阿布扎比大奖赛，赛事总监Masi只允许Verstappen和Hamilton之间的被套圈车辆解套，此决定直接影响了年度冠军归属，引发F1史上最大争议之一。",
        "category": "strategy", "level": 2, "related_slugs": "sc,lapped_car,backmarker", "spec_year": None,
        "scene_tags": "race_common", "why_important": "安全车期间的关键争议点", "data_ref": ""
    },
    {
        "slug": "monocoque", "name_zh": "单体壳", "name_en": "Monocoque",
        "aliases": "monocoque,单体壳,单壳体,碳纤维座舱",
        "short_def": "F1赛车的碳纤维一体式车身结构，兼顾轻量化与安全防护，是整车核心骨架。",
        "full_def": None, "example": None,
        "category": "aero", "level": 3, "related_slugs": "halo", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "整车的核心安全结构", "data_ref": ""
    },
    {
        "slug": "constructors", "name_zh": "车队积分榜", "name_en": "Constructors' Championship",
        "aliases": "车队积分榜,车队冠军,制造商冠军,WCC,constructors championship",
        "short_def": "以车队为单位累计两辆赛车积分的年度总冠军争夺，奖金分配与此直接挂钩。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "drivers_championship,cost_cap", "spec_year": None,
        "scene_tags": "race_common", "why_important": "直接决定车队奖金分配", "data_ref": ""
    },
    {
        "slug": "drivers_championship", "name_zh": "车手积分榜", "name_en": "Drivers' Championship",
        "aliases": "车手积分榜,车手冠军,WDC,drivers championship",
        "short_def": "以个人车手积分决出的年度总冠军，是F1最高荣誉。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "constructors,fastest_lap", "spec_year": None,
        "scene_tags": "race_common", "why_important": "F1最高荣誉", "data_ref": ""
    },
    {
        "slug": "grid_penalty", "name_zh": "换件降位", "name_en": "Grid Penalty",
        "aliases": "换件降位,换引擎降格,PU罚退,grid penalty",
        "short_def": "超出赛季配额更换动力单元部件导致的排位后退惩罚，通常退后5-10位。",
        "full_def": None, "example": None,
        "category": "power_unit", "level": 2, "related_slugs": "ice,ers,quali", "spec_year": None,
        "scene_tags": "race_common", "why_important": "动力单元可靠性的处罚机制", "data_ref": ""
    },
    {
        "slug": "snap_oversteer", "name_zh": "突然甩尾", "name_en": "Snap Oversteer",
        "aliases": "snap oversteer,突然甩尾,甩尾,snap",
        "short_def": "后轮突然失去抓地力导致车尾急速滑出，极难控制，常见于出弯加速阶段。",
        "full_def": None, "example": None,
        "category": "aero", "level": 2, "related_slugs": "oversteer,understeer,balance", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "导致打转和退车的高风险现象", "data_ref": ""
    },
    {
        "slug": "balance", "name_zh": "车身平衡", "name_en": "Car Balance",
        "aliases": "balance,车身平衡,前后平衡,setup",
        "short_def": "赛车前后抓地力的分配状态，影响过弯特性，是车手与工程师沟通的核心话题。",
        "full_def": None, "example": None,
        "category": "aero", "level": 2, "related_slugs": "understeer,oversteer,downforce", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "车手与工程师沟通的核心话题", "data_ref": ""
    },
    {
        "slug": "pole", "name_zh": "杆位", "name_en": "Pole Position",
        "aliases": "pole,pole position,杆位,排位第一,PP",
        "short_def": "排位赛最快圈时间获得者，从第一位起跑，是排位赛的最高荣誉。",
        "full_def": "Pole Position（杆位）是排位赛中跑出最快圈速的车手所获得的起跑位置。从杆位起跑意味着在第一弯角前无需超越任何人，具有极大的战略优势。现代F1中杆位还额外奖励1个积分（自2014年起）。",
        "example": "2023赛季Verstappen以19次杆位打破单赛季杆位纪录，展现了Red Bull RB19的绝对统治力。",
        "category": "rules", "level": 1, "related_slugs": "quali,fastest_lap", "spec_year": None,
        "scene_tags": "race_common", "why_important": "起跑的战略优势位置", "data_ref": ""
    },
    {
        "slug": "podium", "name_zh": "领奖台", "name_en": "Podium",
        "aliases": "podium,领奖台,表彰台,前三名,podium finish",
        "short_def": "正赛前三名登上领奖台，是车手和车队最直接的荣誉体现。",
        "full_def": "Podium（领奖台）指正赛前三名。登上领奖台的车手分别获得25、18、15分（第1/2/3名），并参加颁奖典礼。对于中小车队而言，一次领奖台往往是赛季最重要的成就。",
        "example": "2023年新加坡大奖赛，Carlos Sainz为法拉利拿下赛季唯一一场胜利，也是该赛季最令人意外的领奖台之一。",
        "category": "rules", "level": 1, "related_slugs": "fastest_lap,drivers_championship", "spec_year": None,
        "scene_tags": "race_common", "why_important": "车手和车队最直接的荣誉体现", "data_ref": ""
    },
    # ── 驾驶技术类 ─────────────────────────────
    {
        "slug": "trail_braking", "name_zh": "尾随制动", "name_en": "Trail Braking",
        "aliases": "轻制动入弯,trail braking technique",
        "short_def": "在进入弯角时持续轻度制动，通过控制车身重量分配来平衡抓地力。",
        "full_def": None, "example": None,
        "category": "driving", "level": 3, "related_slugs": "apex,late_braking", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "专业车手的高级技巧，能在弯角入口获得额外圈速", "data_ref": ""
    },
    {
        "slug": "late_braking", "name_zh": "迟刹车", "name_en": "Late Braking",
        "aliases": "晚刹车,极限刹车",
        "short_def": "在最后一刻才进行制动，将制动过程延伸到弯角入口，用于超车。",
        "full_def": None, "example": None,
        "category": "driving", "level": 3, "related_slugs": "trail_braking,overtake", "spec_year": None,
        "scene_tags": "race_common", "why_important": "超车时延迟制动距离能创造超车机会", "data_ref": ""
    },
    {
        "slug": "divebomb", "name_zh": "炸弹超车", "name_en": "Divebomb",
        "aliases": "冒险超车,激进入弯",
        "short_def": "在直道末端激进地晚刹车，切入弯角内侧的超车尝试，风险极高。",
        "full_def": None, "example": None,
        "category": "driving", "level": 3, "related_slugs": "late_braking,overtake", "spec_year": None,
        "scene_tags": "race_common", "why_important": "F1中最具争议但最戏剧化的超车方式", "data_ref": ""
    },
    {
        "slug": "switchback", "name_zh": "反向切线", "name_en": "Switchback",
        "aliases": "反向防守,切线防守",
        "short_def": "在防守时驾驶员在弯角出口向对侧变向，阻止跟车者的超车尝试。",
        "full_def": None, "example": None,
        "category": "driving", "level": 3, "related_slugs": "defending,cutback", "spec_year": None,
        "scene_tags": "race_common", "why_important": "防守技术中最有效的方式", "data_ref": ""
    },
    {
        "slug": "cutback", "name_zh": "切回防守", "name_en": "Cutback",
        "aliases": "反制超车,防守切线",
        "short_def": "被超越后在下一个弯角快速切回，重新占据赛线位置。",
        "full_def": None, "example": None,
        "category": "driving", "level": 3, "related_slugs": "switchback,defending", "spec_year": None,
        "scene_tags": "race_common", "why_important": "防守策略中的标准手段", "data_ref": ""
    },
    {
        "slug": "lift_and_coast", "name_zh": "提速滑行", "name_en": "Lift and Coast",
        "aliases": "滑行省油,lift off",
        "short_def": "在直道末端提前松开油门滑行，节省燃油或回收能量。",
        "full_def": None, "example": None,
        "category": "driving", "level": 2, "related_slugs": "recharge,energy_deployment", "spec_year": None,
        "scene_tags": "race_common,2026_new", "why_important": "2026规则中能量回收的关键方式", "data_ref": ""
    },
    {
        "slug": "slipstream", "name_zh": "拖车效应", "name_en": "Slipstream",
        "aliases": "吸尘,尾流,draft,tow",
        "short_def": "跟随前车进入其尾流，利用低压区减少阻力获得直道加速优势。",
        "full_def": None, "example": None,
        "category": "driving", "level": 2, "related_slugs": "dirty_air,overtake,drs", "spec_year": None,
        "scene_tags": "race_common", "why_important": "直道超车的基础原理", "data_ref": "直道可获得额外10-20km/h尾速优势"
    },
    {
        "slug": "defending", "name_zh": "防守", "name_en": "Defending",
        "aliases": "防守驾驶,防守战术",
        "short_def": "驾驶员采用各种技术和策略阻止后车超越的全过程。",
        "full_def": None, "example": None,
        "category": "driving", "level": 2, "related_slugs": "switchback,cutback,track_limits", "spec_year": None,
        "scene_tags": "race_common", "why_important": "比赛中的核心战术", "data_ref": ""
    },
    {
        "slug": "overtake", "name_zh": "超车", "name_en": "Overtake",
        "aliases": "超越,passing,pass",
        "short_def": "从被超越位置通过各种技术手段超过前车的过程。",
        "full_def": None, "example": None,
        "category": "driving", "level": 1, "related_slugs": "slipstream,drs,late_braking", "spec_year": None,
        "scene_tags": "race_common", "why_important": "F1比赛的核心动作，观众最关注的环节", "data_ref": ""
    },
    {
        "slug": "apex", "name_zh": "弯角顶点", "name_en": "Apex",
        "aliases": "最高点,弯顶,corner apex",
        "short_def": "通过弯角时最靠近弯心的点，也是最优圆弧线路经过的位置。",
        "full_def": None, "example": None,
        "category": "driving", "level": 1, "related_slugs": "trail_braking,downforce", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "圈速的关键参考点，决定出弯速度", "data_ref": ""
    },
    # ── 策略类补充 ─────────────────────────────
    {
        "slug": "split_strategy", "name_zh": "分化策略", "name_en": "Split Strategy",
        "aliases": "分化进站,策略分化",
        "short_def": "同一车队两名车手采用不同进站时机和轮胎策略。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 3, "related_slugs": "offset_strategy,one_stop,two_stop", "spec_year": None,
        "scene_tags": "race_common", "why_important": "车队战术的高级应用", "data_ref": ""
    },
    {
        "slug": "pit_window", "name_zh": "进站窗口", "name_en": "Pit Window",
        "aliases": "进站时机窗,pit timing",
        "short_def": "考虑轮胎衰减、对手位置等因素的最佳进站时间范围。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 2, "related_slugs": "pit_stop,undercut,deg", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "团队实时决策的关键参数", "data_ref": ""
    },
    {
        "slug": "track_position", "name_zh": "赛道位置", "name_en": "Track Position",
        "aliases": "位置优势,track position advantage",
        "short_def": "相对于对手在赛道上的领先优势和战略重要性。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 1, "related_slugs": "undercut,defending", "spec_year": None,
        "scene_tags": "race_common", "why_important": "决定比赛胜负的基础因素", "data_ref": ""
    },
    {
        "slug": "safety_car_gamble", "name_zh": "安全车赌博", "name_en": "Safety Car Gamble",
        "aliases": "安全车策略,冒险进站",
        "short_def": "在不确定安全车何时出现时做出冒险进站决策。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 3, "related_slugs": "sc,free_stop,pit_stop", "spec_year": None,
        "scene_tags": "race_common", "why_important": "风险-收益决策的典型", "data_ref": ""
    },
    {
        "slug": "drs_train", "name_zh": "DRS列车", "name_en": "DRS Train",
        "aliases": "DRS车队,DRS lockout",
        "short_def": "多辆车锁在DRS范围内形成车队，都能用DRS导致无法超车。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 2, "related_slugs": "drs,dirty_air", "spec_year": None,
        "scene_tags": "race_common", "why_important": "影响比赛节奏的常见现象", "data_ref": ""
    },
    {
        "slug": "gap_management", "name_zh": "间距管理", "name_en": "Gap Management",
        "aliases": "差距管理,时间差管理",
        "short_def": "实时控制与前车和后车的时间差，用于进站决策。",
        "full_def": None, "example": None,
        "category": "strategy", "level": 2, "related_slugs": "delta_time,pit_stop,undercut", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "进站节奏的关键决策基础", "data_ref": ""
    },
    # ── 空气动力学补充 ─────────────────────────────
    {
        "slug": "outwash", "name_zh": "外吹气流", "name_en": "Outwash",
        "aliases": "外排气流,outwash effect",
        "short_def": "前翼将湍流空气向两侧吹出，让后车进入乱流。",
        "full_def": None, "example": None,
        "category": "aero", "level": 3, "related_slugs": "dirty_air,ground_effect", "spec_year": None,
        "scene_tags": "tech_talk,2026_new", "why_important": "2026新规通过限制outwash改善跟车", "data_ref": ""
    },
    {
        "slug": "clean_air", "name_zh": "清洁空气", "name_en": "Clean Air",
        "aliases": "干净空气,undisturbed air",
        "short_def": "未被前车打乱的气流，使车辆获得最优性能。",
        "full_def": None, "example": None,
        "category": "aero", "level": 2, "related_slugs": "dirty_air,downforce", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "领车优势的主要来源", "data_ref": ""
    },
    {
        "slug": "drag", "name_zh": "阻力", "name_en": "Drag",
        "aliases": "空气阻力,drag coefficient",
        "short_def": "车辆运动时受到的空气阻力，降低最高速度。",
        "full_def": None, "example": None,
        "category": "aero", "level": 1, "related_slugs": "downforce,drs", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "与下压力平衡的关键参数", "data_ref": ""
    },
    {
        "slug": "venturi_tunnel", "name_zh": "文丘里隧道", "name_en": "Venturi Tunnel",
        "aliases": "地效隧道,ground effect tunnel",
        "short_def": "地板下的隧道结构，通过加速气流产生下压力。",
        "full_def": None, "example": None,
        "category": "aero", "level": 3, "related_slugs": "ground_effect,diffuser", "spec_year": None,
        "scene_tags": "tech_talk", "why_important": "地效时代的核心空力概念", "data_ref": ""
    },
    # ── 轮胎补充 ─────────────────────────────
    {
        "slug": "cold_tyre", "name_zh": "冷胎", "name_en": "Cold Tyre",
        "aliases": "温度不足,冷轮胎",
        "short_def": "温度未达到工作温度范围的轮胎，性能下降明显。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 2, "related_slugs": "tyre_window,out_lap", "spec_year": None,
        "scene_tags": "race_common", "why_important": "影响进站后首圈性能", "data_ref": ""
    },
    {
        "slug": "tyre_blanket", "name_zh": "轮胎加热毯", "name_en": "Tyre Blanket",
        "aliases": "加热毯,tire warmer",
        "short_def": "赛前用来预热轮胎至工作温度的设备。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 1, "related_slugs": "tyre_window,warm_up_lap", "spec_year": None,
        "scene_tags": "race_common", "why_important": "确保发车时轮胎处于最佳状态", "data_ref": ""
    },
    {
        "slug": "operating_window", "name_zh": "工作窗口", "name_en": "Operating Window",
        "aliases": "性能窗口,optimal window",
        "short_def": "轮胎发挥最佳性能的温度和压力范围。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 2, "related_slugs": "tyre_window,graining", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "轮胎策略的核心", "data_ref": ""
    },
    {
        "slug": "tyre_cliff", "name_zh": "轮胎悬崖", "name_en": "Tyre Cliff",
        "aliases": "性能悬崖,performance cliff",
        "short_def": "轮胎性能超出工作窗口后急剧下降的现象。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 2, "related_slugs": "cliff,deg,blistering", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "决定进站时机的关键因素", "data_ref": "性能悬崖后单圈损失可达2-4秒"
    },
    {
        "slug": "flat_spot", "name_zh": "平坦点", "name_en": "Flat Spot",
        "aliases": "磨平,lock up damage",
        "short_def": "轮胎锁死制动时磨平的区域，造成严重振动。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 1, "related_slugs": "deg,blistering", "spec_year": None,
        "scene_tags": "race_common", "why_important": "锁死制动的直接后果", "data_ref": ""
    },
    {
        "slug": "compound", "name_zh": "胎质", "name_en": "Compound",
        "aliases": "胎质等级,soft,medium,hard,C1-C5",
        "short_def": "轮胎化合物类型（硬、中、软），不同硬度有不同性能。",
        "full_def": None, "example": None,
        "category": "tyre", "level": 1, "related_slugs": "soft_tyre,medium_tyre,hard_tyre", "spec_year": None,
        "scene_tags": "race_common", "why_important": "轮胎策略的基础选择", "data_ref": "软胎比硬胎单圈快约1.0-1.5秒，但衰退更快"
    },
    # ── 规则/比赛术语补充 ─────────────────────────────
    {
        "slug": "formation_lap", "name_zh": "编队圈", "name_en": "Formation Lap",
        "aliases": "热身圈,parade lap",
        "short_def": "比赛开始前的预热圈，车手按网格顺序驾驶。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "warm_up_lap,quali", "spec_year": None,
        "scene_tags": "race_common", "why_important": "比赛正式开始前的必要环节", "data_ref": ""
    },
    {
        "slug": "penalty_points", "name_zh": "处罚点数", "name_en": "Penalty Points",
        "aliases": "违规点,superlicense points",
        "short_def": "超级驾照积分，12个月内累计12点将被禁赛。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "track_limits,grid_penalty", "spec_year": None,
        "scene_tags": "race_common", "why_important": "鼓励遵守赛道规则的制度", "data_ref": "12个月内累计12点将被禁赛"
    },
    {
        "slug": "drs_detection_zone", "name_zh": "DRS检测区", "name_en": "DRS Detection Zone",
        "aliases": "DRS检测点,detection point",
        "short_def": "检测前车距离的位置，通常在弯角前。",
        "full_def": None, "example": None,
        "category": "rules", "level": 2, "related_slugs": "drs,drs_zone", "spec_year": None,
        "scene_tags": "race_common,tech_talk", "why_important": "DRS系统运作的技术基础", "data_ref": ""
    },
    {
        "slug": "sprint_race", "name_zh": "冲刺赛", "name_en": "Sprint Race",
        "aliases": "短程赛,sprint qualifying",
        "short_def": "周末额外的短距离比赛，决定部分积分。",
        "full_def": None, "example": None,
        "category": "rules", "level": 1, "related_slugs": "sprint,quali", "spec_year": None,
        "scene_tags": "race_common", "why_important": "现代F1周末赛制的重要组成", "data_ref": ""
    },
    # ── 2026新规补充 ─────────────────────────────
    {
        "slug": "overtake_mode", "name_zh": "超越模式", "name_en": "Overtake Mode",
        "aliases": "超越模式,新DRS,manual override",
        "short_def": "2026新规中替代DRS的系统，允许部署额外电能进行攻防。",
        "full_def": None, "example": None,
        "category": "rules", "level": 2, "related_slugs": "drs,active_aero,energy_deployment", "spec_year": 2026,
        "scene_tags": "2026_new,tech_talk", "why_important": "2026对超车机制的重大改革", "data_ref": ""
    },
    {
        "slug": "boost_button", "name_zh": "加速按钮", "name_en": "Boost Button",
        "aliases": "加速键,boost deployment",
        "short_def": "2026规则中驾驶员按压以激活能量部署的按钮。",
        "full_def": None, "example": None,
        "category": "power_unit", "level": 2, "related_slugs": "overtake_mode,energy_deployment", "spec_year": 2026,
        "scene_tags": "2026_new,tech_talk", "why_important": "2026能量管理的驾驶操控方式", "data_ref": ""
    },
    {
        "slug": "recharge", "name_zh": "充能", "name_en": "Recharge",
        "aliases": "能量回收,energy harvesting",
        "short_def": "通过制动或滑行进行能量回收的过程。",
        "full_def": None, "example": None,
        "category": "power_unit", "level": 2, "related_slugs": "mgu_k,lift_and_coast,ers", "spec_year": None,
        "scene_tags": "2026_new,tech_talk", "why_important": "2026能量管理的核心机制", "data_ref": ""
    },
    {
        "slug": "energy_deployment", "name_zh": "能量部署", "name_en": "Energy Deployment",
        "aliases": "能量释放,energy use",
        "short_def": "驾驶员使用已储能的电能获得额外动力的过程。",
        "full_def": None, "example": None,
        "category": "power_unit", "level": 1, "related_slugs": "ers,mgu_k,boost_button", "spec_year": None,
        "scene_tags": "tech_talk,2026_new", "why_important": "现代F1比赛的关键竞争要素", "data_ref": ""
    },
]

def terms_seed():
    """插入种子术语数据（幂等，已存在则跳过）"""
    with get_conn() as conn:
        for t in SEED_TERMS:
            conn.execute(
                """INSERT OR IGNORE INTO terms
                   (slug, name_zh, name_en, aliases, short_def, full_def, example,
                    category, level, related_slugs, spec_year,
                    scene_tags, why_important, data_ref)
                   VALUES (:slug, :name_zh, :name_en, :aliases, :short_def, :full_def, :example,
                    :category, :level, :related_slugs, :spec_year,
                    :scene_tags, :why_important, :data_ref)""",
                t
            )
        conn.commit()


def terms_all(category: str | None = None, level: int | None = None,
               scene: str | None = None) -> list[dict]:
    """查询术语列表，支持按 category / level / scene 过滤，只返回已审核"""
    with get_conn() as conn:
        sql = """SELECT id,slug,name_zh,name_en,aliases,short_def,example,
                        category,level,related_slugs,spec_year,
                        scene_tags,why_important,data_ref FROM terms
                 WHERE status='approved'"""
        params = []
        if category:
            sql += " AND category=?"
            params.append(category)
        if level is not None:
            sql += " AND level=?"
            params.append(level)
        if scene:
            # scene_tags 是 CSV，用 LIKE 匹配
            sql += " AND (scene_tags LIKE ? OR ',' || scene_tags || ',' LIKE ?)"
            params += [scene, f"%,{scene},%"]
        sql += " ORDER BY spec_year DESC NULLS LAST, level ASC, id ASC"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def terms_get(slug: str) -> dict | None:
    """查询单个术语详情（含 full_def）"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM terms WHERE slug=?", (slug,)
        ).fetchone()
        return dict(row) if row else None


def term_submit(name_zh: str, name_en: str, short_def: str, category: str,
                submitted_by: str | None = None) -> int:
    """用户提交新术语，状态为 pending"""
    import re, time
    slug = re.sub(r'[^a-z0-9_]', '', name_en.lower().replace(' ', '_'))[:40]
    slug = slug or f"user_{int(time.time())}"
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO terms (slug, name_zh, name_en, short_def, category,
               level, status, submitted_by)
               VALUES (?,?,?,?,?,1,'pending',?)""",
            (slug, name_zh, name_en, short_def, category, submitted_by)
        )
        conn.commit()
        return cur.lastrowid


def terms_pending() -> list[dict]:
    """管理员查看待审核术语"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id,slug,name_zh,name_en,short_def,category,submitted_by,created_at
               FROM terms WHERE status='pending' ORDER BY created_at ASC"""
        ).fetchall()
        return [dict(r) for r in rows]


def term_review(term_id: int, action: str) -> bool:
    """管理员审核：action = 'approve' | 'reject'"""
    status = 'approved' if action == 'approve' else 'rejected'
    with get_conn() as conn:
        conn.execute("UPDATE terms SET status=? WHERE id=?", (status, term_id))
        conn.commit()
    return True


def _match_term_in_text(text: str, term_row) -> bool:
    """检查术语的 aliases 是否在文本中出现（中文子串匹配，英文词边界匹配）"""
    import re
    keywords = [term_row["name_zh"].lower(), term_row["name_en"].lower()]
    if term_row["aliases"]:
        keywords += [a.strip().lower() for a in term_row["aliases"].split(",")]
    for kw in keywords:
        if not kw:
            continue
        if any('\u4e00' <= c <= '\u9fff' for c in kw):
            if kw in text:
                return True
        else:
            if bool(re.search(r'\b' + re.escape(kw) + r'\b', text)):
                return True
    return False


def terms_by_news(news_id: int, max_tags: int = 3) -> list[dict]:
    """根据新闻原始内容（title+summary）匹配相关术语，最多返回 max_tags 个。
    故意不搜索 AI 分析文本，避免 AI 泛泛提及的词汇被误打成标签。
    匹配优先级：level 低（基础）的术语优先，再按 name_zh 排序。
    使用词边界匹配（\\b），避免 "ers" 命中 "drivers" 之类的误匹配。
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT title, summary FROM news WHERE id=?",
            (news_id,)
        ).fetchone()
        if not row:
            return []

        # 只用原始新闻文本做匹配，不含 AI 生成内容
        text = " ".join(filter(None, [row["title"], row["summary"]])).lower()

        all_terms = conn.execute(
            """SELECT id,slug,name_zh,name_en,aliases,short_def,example,
                      category,level,related_slugs FROM terms
               WHERE status='approved'
               ORDER BY level ASC, name_zh ASC"""
        ).fetchall()

        matched, seen = [], set()
        for t in all_terms:
            if len(matched) >= max_tags:
                break
            if t["slug"] in seen:
                continue
            if _match_term_in_text(text, t):
                matched.append(dict(t))
                seen.add(t["slug"])

        return matched


def terms_hot() -> dict[str, int]:
    """统计近7天新闻中各 approved 术语的匹配次数。
    复用 _match_term_in_text 的匹配逻辑（中文子串，英文词边界）。
    返回 {slug: count} 字典。
    """
    with get_conn() as conn:
        seven_days_ago = int(time.time()) - 7 * 86400
        news_rows = conn.execute(
            "SELECT title, summary FROM news WHERE published_at >= ?",
            (seven_days_ago,)
        ).fetchall()

        if not news_rows:
            return {}

        # 合并所有新闻文本
        all_text = " ".join(
            " ".join(filter(None, [r["title"], r["summary"]]))
            for r in news_rows
        ).lower()

        all_terms = conn.execute(
            "SELECT slug, name_zh, name_en, aliases FROM terms WHERE status='approved'"
        ).fetchall()

        result = {}
        for t in all_terms:
            if _match_term_in_text(all_text, t):
                # 统计匹配到的新闻条数（而非总匹配次数，更合理）
                count = 0
                for r in news_rows:
                    piece = " ".join(filter(None, [r["title"], r["summary"]])).lower()
                    if _match_term_in_text(piece, t):
                        count += 1
                result[t["slug"]] = count

        return result


def terms_popular(top_n: int = 5) -> list[str]:
    """返回热度 TOP-N 的术语 slug 列表"""
    hot = terms_hot()
    if not hot:
        return []
    sorted_slugs = sorted(hot.items(), key=lambda x: x[1], reverse=True)
    return [slug for slug, _ in sorted_slugs[:top_n]]


# ─────────────────────────────────────────────
# 车手评论
# ─────────────────────────────────────────────

def driver_comment_add(driver_code: str, content: str,
                       author_openid: str, author_nickname: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO driver_comments(driver_code, content, author_openid, author_nickname)
               VALUES (?,?,?,?)""",
            (driver_code, content, author_openid, author_nickname)
        )
        conn.commit()
        return cur.lastrowid


def driver_comment_list(driver_code: str, page: int = 1, page_size: int = 20) -> list[dict]:
    offset = (page - 1) * page_size
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, content, author_nickname, likes, created_at
               FROM driver_comments
               WHERE driver_code = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (driver_code, page_size, offset)
        ).fetchall()
        return [dict(r) for r in rows]


def driver_comment_like(comment_id: int) -> int:
    """点赞，返回最新 likes 数"""
    with get_conn() as conn:
        conn.execute(
            "UPDATE driver_comments SET likes = likes + 1 WHERE id = ?",
            (comment_id,)
        )
        conn.commit()
        row = conn.execute(
            "SELECT likes FROM driver_comments WHERE id = ?", (comment_id,)
        ).fetchone()
        return row["likes"] if row else 0


# ─────────────────────────────────────────────
# Driver Ratings CRUD
# ─────────────────────────────────────────────

RATING_DIMS = ["speed", "consist", "defend", "wet", "mental"]


def driver_rating_upsert(driver_code: str, openid: str, scores: dict) -> None:
    """提交或更新评分（每人每车手只能评一次）"""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO driver_ratings(driver_code, openid, speed, consist, defend, wet, mental)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(driver_code, openid) DO UPDATE SET
                 speed=excluded.speed, consist=excluded.consist,
                 defend=excluded.defend, wet=excluded.wet, mental=excluded.mental""",
            (driver_code, openid,
             scores["speed"], scores["consist"], scores["defend"],
             scores["wet"], scores["mental"])
        )
        conn.commit()


def driver_rating_get_mine(driver_code: str, openid: str) -> dict | None:
    """获取当前用户对某车手的评分"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT speed,consist,defend,wet,mental FROM driver_ratings WHERE driver_code=? AND openid=?",
            (driver_code, openid)
        ).fetchone()
        return dict(row) if row else None


# ─────────────────────────────────────────────
# Curated Content CRUD
# ─────────────────────────────────────────────

def curated_insert(url: str, title: str, summary: str = "", cover_image: str = "",
                   platform: str = "web", content_type: str = "article",
                   tags: str = "[]", note: str = "", submitted_by: str = "",
                   archived_html: str = "", snapshot_image: str = "",
                   published_at: int | None = None) -> int | None:
    """插入一条精选内容，url 重复则跳过，返回 id 或 None"""
    if published_at is None:
        published_at = int(time.time())
    created_at = int(time.time())
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO curated_content
               (url, title, summary, cover_image, platform, content_type,
                tags, note, submitted_by, archived_html, snapshot_image, published_at, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (url, title, summary, cover_image, platform, content_type,
             tags, note, submitted_by, archived_html, snapshot_image, published_at, created_at)
        )
        conn.commit()
        return cur.lastrowid if cur.lastrowid and cur.rowcount > 0 else None


def curated_list(page: int = 1, page_size: int = 20,
                 tag: str | None = None, keyword: str | None = None,
                 platform: str | None = None) -> list[dict]:
    """分页查询精选列表（最新在前），支持 tag/keyword/platform 过滤"""
    offset = (page - 1) * page_size
    conditions = []
    params = []
    if tag:
        conditions.append('tags LIKE ?')
        params.append(f'%"{tag}"%')
    if keyword:
        kw_like = f"%{keyword}%"
        conditions.append("(title LIKE ? OR summary LIKE ?)")
        params += [kw_like, kw_like]
    if platform:
        conditions.append("platform = ?")
        params.append(platform)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    with get_conn() as conn:
        rows = conn.execute(
            f"""SELECT * FROM curated_content{where}
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            params + [page_size, offset]
        ).fetchall()
        return [dict(r) for r in rows]


def curated_get(content_id: int) -> dict | None:
    """查询单条精选内容详情"""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM curated_content WHERE id=?",
            (content_id,)
        ).fetchone()
        return dict(row) if row else None


def curated_analysis_save(content_id: int, tech_points: str,
                          plain_explain: str, race_impact: str) -> None:
    """保存精选内容 AI 分析结果（幂等更新）"""
    analyzed_at = time.strftime('%Y-%m-%d %H:%M:%S')
    with get_conn() as conn:
        conn.execute(
            """UPDATE curated_content
               SET analyzed=1, tech_points=?, plain_explain=?, race_impact=?, analyzed_at=?
               WHERE id=?""",
            (tech_points, plain_explain, race_impact, analyzed_at, content_id)
        )
        conn.commit()


def curated_reset_analysis(content_id: int) -> None:
    """重置精选内容的 AI 分析状态（用于重新分析）"""
    with get_conn() as conn:
        conn.execute(
            """UPDATE curated_content
               SET analyzed=0, tech_points='', plain_explain='', race_impact='', analyzed_at=''
               WHERE id=?""",
            (content_id,)
        )
        conn.commit()


def curated_tags() -> list[str]:
    """获取所有已使用的标签列表（去重）"""
    all_tags = set()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT tags FROM curated_content WHERE tags IS NOT NULL AND tags != ''"
        ).fetchall()
        for r in rows:
            try:
                tags = json.loads(r["tags"])
                if isinstance(tags, list):
                    all_tags.update(tags)
            except (json.JSONDecodeError, TypeError):
                pass
    return sorted(all_tags)


def driver_rating_aggregate(driver_code: str) -> dict:
    """聚合所有用户对某车手的评分，返回各维度均值和总人数"""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT COUNT(*) AS cnt,
                      AVG(speed)   AS speed,
                      AVG(consist) AS consist,
                      AVG(defend)  AS defend,
                      AVG(wet)     AS wet,
                      AVG(mental)  AS mental
               FROM driver_ratings WHERE driver_code=?""",
            (driver_code,)
        ).fetchone()
        if not row or not row["cnt"]:
            return {"count": 0, "avgs": {d: 0.0 for d in RATING_DIMS}}
        return {
            "count": row["cnt"],
            "avgs": {d: round(row[d] or 0, 2) for d in RATING_DIMS},
        }


def chat_get_messages(since_id: int = 0, limit: int = 50) -> list:
    """获取 since_id 之后的消息，最多 limit 条，按时间正序返回"""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT id, nickname, content, created_at
               FROM chat_messages
               WHERE id > ?
               ORDER BY id DESC LIMIT ?""",
            (since_id, limit)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]


def chat_send_message(nickname: str, content: str) -> int:
    """发送消息，同时清理超过 200 条的旧消息"""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO chat_messages (nickname, content) VALUES (?, ?)",
            (nickname, content)
        )
        conn.commit()
        msg_id = cur.lastrowid
        # 清理旧消息，只保留最近 200 条
        conn.execute("""
            DELETE FROM chat_messages WHERE id NOT IN (
                SELECT id FROM chat_messages ORDER BY id DESC LIMIT 200
            )
        """)
        conn.commit()
        return msg_id
