"""
Lexiword Backend — Flask + SQLite + JWT Auth
"""

import os
import json
import time
import sqlite3
from functools import wraps

import bcrypt
import jwt
from flask import Flask, request, jsonify, g
from flask_cors import CORS

# ── Config ──────────────────────────────────────────
app = Flask(__name__)
CORS(app, origins=[
    'http://localhost:5500',
    'http://127.0.0.1:5500',
    'http://localhost:5000',
    'https://lexiword.vercel.app',
    'https://lexiword.vercel.com',
    'https://0628d07533d54e8c9d6df95c5ee7e2a8.app.codebuddy.work',
    'https://lexiword-backend.onrender.com',
])

DATABASE = os.environ.get('DATABASE_PATH', 'lexiword.db')
JWT_SECRET = os.environ.get('JWT_SECRET', 'dev-secret-change-in-production')
JWT_ALGO = 'HS256'
JWT_TTL = 30 * 24 * 3600  # 30 days

# ── DB helpers ──────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db:
        db.close()

def init_db():
    """Create tables on first run."""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    db.commit()

def seed_daybook():
    """Import DAYBOOK_DATA into daybook_words table if empty."""
    db = get_db()
    row = db.execute("SELECT COUNT(*) AS cnt FROM daybook_words").fetchone()
    if row and row['cnt'] > 0:
        return  # already seeded

    # inline DAYBOOK_DATA — extracted from Lexiword.html
    DAYBOOK_DATA = {
        "1": [{"w":"economy","m":"n.节约；经济实惠"},{"w":"formula","m":"n.方案；配方；公式；分子式"},{"w":"computer","m":"n.计算机；电脑"},{"w":"kindergarten","m":"n.幼稚园"},{"w":"embrace","m":"v.拥抱；接受；包括，涉及；围绕 n.拥抱；接受，信奉"},{"w":"trolley","m":"n.手推车；电车"},{"w":"adjoin","m":"v.靠近；贴近，比邻"},{"w":"battery","m":"n.电池；一组，一套"},{"w":"moist","m":"a.湿润的；潮湿的"},{"w":"pedestrian","m":"n.步行者 a.徒步的；缺乏想象力的；通俗的"},{"w":"elapse","m":"v.消逝 n.时间的流逝"},{"w":"furnish","m":"v.配备家具；装备；提供，供应"},{"w":"glance","m":"v.扫视，浏览 n.扫视，一瞥"},{"w":"interest","m":"n.兴趣；利益；利息；重要性 v.使感兴趣"},{"w":"glorious","m":"a.壮丽的，绚烂的；光荣的"},{"w":"tear","m":"n.眼泪 v.撕裂，撕破 ；破裂"},{"w":"prime","m":"a.首要的；优质的；基本的 n.青壮年时期；鼎盛时期 v.事先准备"},{"w":"cabbage","m":"n.卷心菜"},{"w":"match","m":"n.火柴；比赛；竞争对手 v.匹配"},{"w":"nitrogen","m":"n.氮"},{"w":"stack","m":"n.一堆；大量    v.堆积"},{"w":"agriculture","m":"n.农业，农学，农艺"},{"w":"skirt","m":"n.短裙；郊区；边缘 v.沿…的边缘走；绕开，回避"},{"w":"appreciate","m":"v.欣赏；理解；感激；增值"},{"w":"typist","m":"n.打字员"},{"w":"approval","m":"n.批准，通过；赞成，同意"},{"w":"exploit","m":"v.开拓；开发；剥削 n.功绩；业绩"},{"w":"prejudice","m":"n.偏见，成见；损害，侵害 v.使抱偏见；损害"},{"w":"turbulent","m":"a.狂暴的；无秩序的；动荡的"},{"w":"productive","m":"a.多产的；富有成效的；生产的"},{"w":"baggage","m":"n.行李"},{"w":"sex","m":"n.性别；性"},{"w":"orange","m":"n.橙子，橘子；橙色 a.橙色的"},{"w":"geometry","m":"n.几何；几何学"},{"w":"conflict","m":"n.争执，争论，分歧；战斗，战争；抵触，矛盾 v.冲突，抵触"},{"w":"ignorance","m":"n.愚昧，无知"},{"w":"equal","m":"v.等于；比得上 n.相等；对手 a.相等的；能胜任的"},{"w":"place","m":"n.地方；方位 v.放置；投资；安排"},{"w":"search","m":"n.搜索，查找；检索 v.搜索；搜寻"},{"w":"extraordinary","m":"a.非常的；格外的；离奇的；临时的"},{"w":"client","m":"n.当事人，委托人；顾客"},{"w":"pork","m":"n.猪肉"},{"w":"conquer","m":"v.征服，攻克，占领；克服；解决"},{"w":"family","m":"n.家庭；家族；(动植物的)科 a.家庭的；家族的"},{"w":"interface","m":"n.界面；连接口 v.互相联系"},{"w":"industrialize","m":"v.工业化"},{"w":"esteem","m":"n.尊敬，尊重 v.尊重，尊敬；认为，把…看作"},{"w":"drive","m":"v.驾驶；驱使 n.驾驶；强烈欲望"},{"w":"legal","m":"a.合法的，正当的；法律的，法定的"},{"w":"secret","m":"a.秘密的 n.秘密"}]
    }

    for day_str, words in DAYBOOK_DATA.items():
        day_num = int(day_str)
        for entry in words:
            db.execute(
                "INSERT OR IGNORE INTO daybook_words (day, word, meaning) VALUES (?, ?, ?)",
                (day_num, entry['w'], entry['m'])
            )
    db.commit()

# ── JWT helpers ─────────────────────────────────────
def encode_token(user_id):
    payload = {
        'uid': user_id,
        'iat': int(time.time()),
        'exp': int(time.time()) + JWT_TTL,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)

def decode_token(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
        token = auth[7:]
        payload = decode_token(token)
        if payload is None:
            return jsonify({'error': 'Token expired or invalid'}), 401
        g.user_id = payload['uid']
        return f(*args, **kwargs)
    return decorated

# ── Auth routes ─────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')
    nickname = (data.get('nickname') or '').strip()

    if not email or '@' not in email:
        return jsonify({'error': '邮箱格式不正确'}), 400
    if len(password) < 4:
        return jsonify({'error': '密码至少4位'}), 400

    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (email, password_hash, nickname) VALUES (?, ?, ?)",
            (email, pw_hash, nickname or email.split('@')[0])
        )
        db.commit()
        return jsonify({'ok': True, 'message': '注册成功'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': '该邮箱已注册'}), 409


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password', '')

    db = get_db()
    row = db.execute("SELECT id, email, password_hash, nickname FROM users WHERE email=?", (email,)).fetchone()
    if not row:
        return jsonify({'error': '邮箱或密码错误'}), 401

    if not bcrypt.checkpw(password.encode('utf-8'), row['password_hash'].encode('utf-8')):
        return jsonify({'error': '邮箱或密码错误'}), 401

    token = encode_token(row['id'])
    return jsonify({
        'token': token,
        'user': {
            'id': row['id'],
            'email': row['email'],
            'nickname': row['nickname'] or row['email'].split('@')[0],
        }
    })


@app.route('/api/auth/me', methods=['GET'])
@require_auth
def auth_me():
    db = get_db()
    row = db.execute("SELECT id, email, nickname, created_at FROM users WHERE id=?", (g.user_id,)).fetchone()
    if not row:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'id': row['id'],
        'email': row['email'],
        'nickname': row['nickname'] or row['email'].split('@')[0],
        'created_at': row['created_at'],
    })

# ── Word states ─────────────────────────────────────
@app.route('/api/states', methods=['GET'])
@require_auth
def get_all_states():
    db = get_db()
    states_rows = db.execute(
        "SELECT day, word, state FROM word_states WHERE user_id=?", (g.user_id,)
    ).fetchall()
    starred_rows = db.execute(
        "SELECT word FROM starred_words WHERE user_id=?", (g.user_id,)
    ).fetchall()
    visit_rows = db.execute(
        "SELECT day, visited_at FROM visit_records WHERE user_id=?", (g.user_id,)
    ).fetchall()

    return jsonify({
        'states': {f"{r['day']}:{r['word']}": r['state'] for r in states_rows},
        'starred': [r['word'] for r in starred_rows],
        'visit_days': {str(r['day']): r['visited_at'] for r in visit_rows},
    })


@app.route('/api/states/<int:day>/<word>', methods=['PUT'])
@require_auth
def set_state(day, word):
    data = request.get_json(silent=True) or {}
    state = int(data.get('state', 0))
    now = int(time.time())
    db = get_db()
    db.execute("""
        INSERT INTO word_states (user_id, day, word, state, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, day, word) DO UPDATE SET state=?, updated_at=?
    """, (g.user_id, day, word, state, now, state, now))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/states/<int:day>/<word>/cycle', methods=['POST'])
@require_auth
def cycle_state(day, word):
    CYCLE = [3, 0, 0, 2]
    db = get_db()
    row = db.execute(
        "SELECT state FROM word_states WHERE user_id=? AND day=? AND word=?",
        (g.user_id, day, word)
    ).fetchone()
    cur = row['state'] if row else 0
    next_state = CYCLE[cur] if cur < len(CYCLE) else 0
    now = int(time.time())
    db.execute("""
        INSERT INTO word_states (user_id, day, word, state, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, day, word) DO UPDATE SET state=?, updated_at=?
    """, (g.user_id, day, word, next_state, now, next_state, now))
    db.commit()
    return jsonify({'ok': True, 'new_state': next_state})


@app.route('/api/states/batch', methods=['PUT'])
@require_auth
def batch_set_state():
    data = request.get_json(silent=True) or {}
    word = data.get('word', '')
    state = int(data.get('state', 0))
    now = int(time.time())
    db = get_db()
    db.execute("""
        UPDATE word_states SET state=?, updated_at=?
        WHERE user_id=? AND word=?
    """, (state, now, g.user_id, word))
    db.commit()
    return jsonify({'ok': True})

# ── Check-in ────────────────────────────────────────
@app.route('/api/checkin', methods=['GET'])
@require_auth
def get_checkin():
    db = get_db()
    rows = db.execute(
        "SELECT date, created_at FROM checkin_records WHERE user_id=?",
        (g.user_id,)
    ).fetchall()
    return jsonify({
        'records': {r['date']: {'c': 1, 't': r['created_at'] * 1000} for r in rows}
    })


@app.route('/api/checkin', methods=['POST'])
@require_auth
def do_checkin():
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    db = get_db()
    db.execute("""
        INSERT OR IGNORE INTO checkin_records (user_id, date, created_at)
        VALUES (?, ?, ?)
    """, (g.user_id, today, int(time.time())))
    db.commit()
    return jsonify({'ok': True})

# ── Word sets ───────────────────────────────────────
@app.route('/api/sets', methods=['GET'])
@require_auth
def get_sets():
    db = get_db()
    rows = db.execute(
        "SELECT id, name, words, created_at FROM word_sets WHERE user_id=? ORDER BY created_at",
        (g.user_id,)
    ).fetchall()
    return jsonify([
        {'id': r['id'], 'name': r['name'], 'words': json.loads(r['words'])}
        for r in rows
    ])


@app.route('/api/sets', methods=['POST'])
@require_auth
def create_set():
    data = request.get_json(silent=True) or {}
    set_id = 'set_' + str(int(time.time() * 1000))
    db = get_db()
    db.execute(
        "INSERT INTO word_sets (id, user_id, name, words) VALUES (?, ?, ?, ?)",
        (set_id, g.user_id, data.get('name', ''), json.dumps(data.get('words', [])))
    )
    db.commit()
    return jsonify({'id': set_id, 'name': data.get('name', ''), 'words': data.get('words', [])}), 201


@app.route('/api/sets/<set_id>', methods=['PUT'])
@require_auth
def update_set(set_id):
    data = request.get_json(silent=True) or {}
    db = get_db()
    updates = []
    params = []
    if 'name' in data:
        updates.append("name=?")
        params.append(data['name'])
    if 'words' in data:
        updates.append("words=?")
        params.append(json.dumps(data['words']))
    if not updates:
        return jsonify({'error': 'No fields to update'}), 400
    updates.append("updated_at=?")
    params.append(int(time.time()))
    params += [set_id, g.user_id]
    db.execute(
        f"UPDATE word_sets SET {', '.join(updates)} WHERE id=? AND user_id=?",
        params
    )
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/sets/<set_id>', methods=['DELETE'])
@require_auth
def delete_set(set_id):
    db = get_db()
    db.execute("DELETE FROM word_sets WHERE id=? AND user_id=?", (set_id, g.user_id))
    db.commit()
    return jsonify({'ok': True})

# ── Sync all sets ───────────────────────────────────
@app.route('/api/sets/sync', methods=['POST'])
@require_auth
def sync_sets():
    data = request.get_json(silent=True) or {}
    sets = data.get('sets', [])
    db = get_db()
    db.execute("DELETE FROM word_sets WHERE user_id=?", (g.user_id,))
    for s in sets:
        db.execute(
            "INSERT INTO word_sets (id, user_id, name, words) VALUES (?, ?, ?, ?)",
            (s.get('id', 'set_' + str(int(time.time()*1000))), g.user_id, s.get('name', ''), json.dumps(s.get('words', [])))
        )
    db.commit()
    return jsonify({'ok': True, 'count': len(sets)})

# ── Pins ────────────────────────────────────────────
@app.route('/api/pins', methods=['GET'])
@require_auth
def get_pins():
    db = get_db()
    rows = db.execute(
        "SELECT id FROM pinned_bookmarks WHERE user_id=?", (g.user_id,)
    ).fetchall()
    return jsonify({r['id']: 1 for r in rows})


@app.route('/api/pins', methods=['PUT'])
@require_auth
def save_pins():
    data = request.get_json(silent=True) or {}
    pins = data.get('pins', {})
    db = get_db()
    db.execute("DELETE FROM pinned_bookmarks WHERE user_id=?", (g.user_id,))
    for pin_id in pins:
        db.execute("INSERT INTO pinned_bookmarks (user_id, id) VALUES (?, ?)", (g.user_id, pin_id))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/pins/toggle', methods=['POST'])
@require_auth
def toggle_pin():
    data = request.get_json(silent=True) or {}
    key = data.get('gridId', '') + ':' + data.get('word', '')
    db = get_db()
    existing = db.execute(
        "SELECT id FROM pinned_bookmarks WHERE user_id=? AND id=?",
        (g.user_id, key)
    ).fetchone()
    if existing:
        db.execute("DELETE FROM pinned_bookmarks WHERE user_id=? AND id=?", (g.user_id, key))
        active = False
    else:
        db.execute("INSERT INTO pinned_bookmarks (user_id, id) VALUES (?, ?)", (g.user_id, key))
        active = True
    db.commit()
    return jsonify({'ok': True, 'active': active})

# ── Star a word ─────────────────────────────────────
@app.route('/api/star/<word>', methods=['PUT'])
@require_auth
def toggle_star(word):
    data = request.get_json(silent=True) or {}
    starred = data.get('starred', False)
    db = get_db()
    if starred:
        db.execute("INSERT OR IGNORE INTO starred_words (user_id, word) VALUES (?, ?)", (g.user_id, word))
    else:
        db.execute("DELETE FROM starred_words WHERE user_id=? AND word=?", (g.user_id, word))
    db.commit()
    return jsonify({'ok': True, 'starred': starred})

# ── Vocab bookmark ──────────────────────────────────
@app.route('/api/bookmark', methods=['GET'])
@require_auth
def get_bookmark():
    db = get_db()
    row = db.execute(
        "SELECT word FROM vocab_bookmark WHERE user_id=?", (g.user_id,)
    ).fetchone()
    return jsonify({'word': row['word'] if row else ''})


@app.route('/api/bookmark', methods=['PUT'])
@require_auth
def set_bookmark():
    data = request.get_json(silent=True) or {}
    word = data.get('word', '')
    db = get_db()
    db.execute("DELETE FROM vocab_bookmark WHERE user_id=?", (g.user_id,))
    if word:
        db.execute("INSERT INTO vocab_bookmark (user_id, word) VALUES (?, ?)", (g.user_id, word))
    db.commit()
    return jsonify({'ok': True})

# ── Custom meanings ─────────────────────────────────
@app.route('/api/meanings/<word>', methods=['GET'])
@require_auth
def get_meaning(word):
    db = get_db()
    custom = db.execute(
        "SELECT meaning FROM custom_meanings WHERE user_id=? AND word=?",
        (g.user_id, word)
    ).fetchone()
    builtin = db.execute(
        "SELECT meaning FROM daybook_words WHERE word=?", (word,)
    ).fetchone()
    return jsonify({
        'word': word,
        'custom': custom['meaning'] if custom else None,
        'builtin': builtin['meaning'] if builtin else None,
    })


@app.route('/api/meanings/<word>', methods=['PUT'])
@require_auth
def set_meaning(word):
    data = request.get_json(silent=True) or {}
    meaning = data.get('meaning', '')
    now = int(time.time())
    db = get_db()
    db.execute("""
        INSERT INTO custom_meanings (user_id, word, meaning, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, word) DO UPDATE SET meaning=?, updated_at=?
    """, (g.user_id, word, meaning, now, meaning, now))
    db.commit()
    return jsonify({'ok': True})

# ── Daybook data (public) ───────────────────────────
@app.route('/api/daybook', methods=['GET'])
def get_daybook():
    db = get_db()
    rows = db.execute("SELECT day, word, meaning FROM daybook_words ORDER BY day").fetchall()
    result = {}
    for r in rows:
        day_str = str(r['day'])
        if day_str not in result:
            result[day_str] = []
        result[day_str].append({'w': r['word'], 'm': r['meaning']})
    return jsonify(result)


@app.route('/api/meanings/batch', methods=['POST'])
@require_auth
def batch_meanings():
    data = request.get_json(silent=True) or {}
    words = data.get('words', [])
    if not words:
        return jsonify({'meanings': {}})
    placeholders = ','.join(['?' for _ in words])
    db = get_db()
    rows = db.execute(
        f"SELECT word, meaning FROM daybook_words WHERE word IN ({placeholders})",
        words
    ).fetchall()
    return jsonify({'meanings': {r['word']: r['meaning'] for r in rows}})

# ── Backup / Restore ────────────────────────────────
@app.route('/api/backup', methods=['GET'])
@require_auth
def backup():
    db = get_db()
    states = {
        f"{r['day']}:{r['word']}": str(r['state'])
        for r in db.execute("SELECT day, word, state FROM word_states WHERE user_id=?", (g.user_id,)).fetchall()
    }
    starred = [
        r['word']
        for r in db.execute("SELECT word FROM starred_words WHERE user_id=?", (g.user_id,)).fetchall()
    ]
    checkin = {}
    for r in db.execute("SELECT date, created_at FROM checkin_records WHERE user_id=?", (g.user_id,)).fetchall():
        checkin[r['date']] = {'c': 1, 't': r['created_at'] * 1000}
    sets = [
        {'id': r['id'], 'name': r['name'], 'words': json.loads(r['words'])}
        for r in db.execute("SELECT id, name, words FROM word_sets WHERE user_id=?", (g.user_id,)).fetchall()
    ]
    pins = {
        r['id']: 1
        for r in db.execute("SELECT id FROM pinned_bookmarks WHERE user_id=?", (g.user_id,)).fetchall()
    }
    bookmark_row = db.execute("SELECT word FROM vocab_bookmark WHERE user_id=?", (g.user_id,)).fetchone()
    bookmark = bookmark_row['word'] if bookmark_row else ''

    # Collect as localStorage-compatible format
    data = {}
    for key, val in states.items():
        data[f"lexi_db_{key}"] = val
    for word in starred:
        data[f"wrev3_star_{word}"] = '1'
    data['lexi_ci_v1'] = json.dumps(checkin)
    data['lexi_sets_v1'] = json.dumps(sets)
    data['lexi_pin_v1'] = json.dumps(pins)
    data['lexi_vocab_bookmark_v1'] = bookmark

    return jsonify({'data': data, 'count': len(data)})


@app.route('/api/restore', methods=['POST'])
@require_auth
def restore():
    body = request.get_json(silent=True) or {}
    raw = body.get('data') or body.get('backup', {})
    db = get_db()
    count = 0

    # word_states: lexi_db_{day}_{word}
    for key, val in raw.items():
        if key.startswith('lexi_db_'):
            parts = key[8:].split('_', 1)
            if len(parts) == 2:
                try:
                    day = int(parts[0])
                    word = parts[1]
                    state = int(str(val))
                    now = int(time.time())
                    db.execute("""
                        INSERT INTO word_states (user_id, day, word, state, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(user_id, day, word) DO UPDATE SET state=?, updated_at=?
                    """, (g.user_id, day, word, state, now, state, now))
                    count += 1
                except (ValueError, IndexError):
                    pass

        elif key.startswith('wrev3_star_'):
            word = key[11:]
            if str(val) == '1':
                db.execute("""
                    INSERT OR IGNORE INTO starred_words (user_id, word) VALUES (?, ?)
                """, (g.user_id, word))
                count += 1

        elif key == 'lexi_ci_v1':
            try:
                records = json.loads(val) if isinstance(val, str) else val
                for date_str, info in records.items():
                    if isinstance(info, dict) and info.get('c'):
                        db.execute("""
                            INSERT OR IGNORE INTO checkin_records (user_id, date, created_at)
                            VALUES (?, ?, ?)
                        """, (g.user_id, date_str, int(time.time())))
                        count += 1
            except (json.JSONDecodeError, TypeError):
                pass

        elif key == 'lexi_sets_v1':
            try:
                sets = json.loads(val) if isinstance(val, str) else val
                for s in sets:
                    db.execute("""
                        INSERT OR IGNORE INTO word_sets (id, user_id, name, words)
                        VALUES (?, ?, ?, ?)
                    """, (s['id'], g.user_id, s['name'], json.dumps(s.get('words', []))))
                    count += 1
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        elif key == 'lexi_pin_v1':
            try:
                pins = json.loads(val) if isinstance(val, str) else val
                for pin_id in pins:
                    db.execute("""
                        INSERT OR IGNORE INTO pinned_bookmarks (user_id, id) VALUES (?, ?)
                    """, (g.user_id, pin_id))
                    count += 1
            except (json.JSONDecodeError, TypeError):
                pass

        elif key == 'lexi_vocab_bookmark_v1':
            if val:
                db.execute("DELETE FROM vocab_bookmark WHERE user_id=?", (g.user_id,))
                db.execute("INSERT INTO vocab_bookmark (user_id, word) VALUES (?, ?)", (g.user_id, str(val)))
                count += 1

    db.commit()
    return jsonify({'ok': True, 'count': count})

# ── Health check ────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'ok': True, 'time': int(time.time())})

# ── Main ────────────────────────────────────────────
if __name__ == '__main__':
    with app.app_context():
        init_db()
        seed_daybook()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
