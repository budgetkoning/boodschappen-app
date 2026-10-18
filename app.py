import os, secrets, hashlib, sqlite3, json
from flask import Flask, request, jsonify, send_from_directory, g

app = Flask(__name__, static_folder='static')
DATABASE_URL = os.environ.get('DATABASE_URL', '')

SUPERMARKETS = ['Lidl', 'Albert Heijn', 'Jumbo', 'Aldi', 'PLUS']

def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()

def db():
    if 'db' not in g:
        if DATABASE_URL.startswith(('postgres://', 'postgresql://')):
            import psycopg
            g.db = psycopg.connect(DATABASE_URL.replace('postgres://', 'postgresql://', 1))
            g.db.row_factory = psycopg.rows.dict_row
            g.db_kind = 'postgres'
        else:
            g.db = sqlite3.connect(os.environ.get('SQLITE_PATH', 'shopping.sqlite3'))
            g.db.row_factory = sqlite3.Row
            g.db_kind = 'sqlite'
    return g.db

@app.teardown_appcontext
def close_db(_err=None):
    conn = g.pop('db', None)
    if conn is not None:
        conn.close()

def execute(sql, params=()):
    conn = db()
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur

def init_db():
    if DATABASE_URL.startswith(('postgres://', 'postgresql://')):
        execute('''CREATE TABLE IF NOT EXISTS shopping_lists (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, name TEXT NOT NULL DEFAULT 'Mijn boodschappenlijst', supermarkets TEXT NOT NULL DEFAULT '["Lidl","Albert Heijn","Jumbo","Aldi","PLUS"]')''')
        execute('''CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, list_id TEXT NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE, name TEXT NOT NULL, quantity TEXT NOT NULL DEFAULT '1', checked INTEGER NOT NULL DEFAULT 0, supermarket TEXT NOT NULL DEFAULT '', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())''')
    else:
        execute('''CREATE TABLE IF NOT EXISTS shopping_lists (id TEXT PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL, name TEXT NOT NULL DEFAULT 'Mijn boodschappenlijst', supermarkets TEXT NOT NULL DEFAULT '["Lidl","Albert Heijn","Jumbo","Aldi","PLUS"]')''')
        execute('''CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, list_id TEXT NOT NULL, name TEXT NOT NULL, quantity TEXT NOT NULL DEFAULT '1', checked INTEGER NOT NULL DEFAULT 0, supermarket TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(list_id) REFERENCES shopping_lists(id) ON DELETE CASCADE)''')
    db().commit()

@app.before_request
def setup():
    init_db()

def current_list():
    token = request.headers.get('X-List-Token') or request.args.get('token')
    if not token:
        return None
    return execute('SELECT * FROM shopping_lists WHERE token_hash = %s' if g.db_kind == 'postgres' else 'SELECT * FROM shopping_lists WHERE token_hash = ?', (token_hash(token),)).fetchone()

def rowdict(row):
    return dict(row) if row is not None else None

@app.get('/')
def index():
    return send_from_directory('static', 'index.html')

@app.get('/api/health')
def health():
    return jsonify({'ok': True, 'service': 'boodschappen-app'})

@app.post('/api/lists')
def create_list():
    body = request.get_json(silent=True) or {}
    token = secrets.token_urlsafe(32)
    list_id = secrets.token_hex(12)
    name = (body.get('name') or 'Mijn boodschappenlijst').strip()[:100]
    sql = 'INSERT INTO shopping_lists (id, token_hash, name, supermarkets) VALUES (%s,%s,%s,%s)' if g.db_kind == 'postgres' else 'INSERT INTO shopping_lists (id, token_hash, name, supermarkets) VALUES (?,?,?,?)'
    execute(sql, (list_id, token_hash(token), name, json.dumps(SUPERMARKETS)))
    db().commit()
    return jsonify({'token': token, 'list': {'id': list_id, 'name': name, 'supermarkets': SUPERMARKETS, 'items': []}}), 201

@app.get('/api/lists/current')
def get_list():
    listing = current_list()
    if not listing:
        return jsonify({'error': 'Lijst niet gevonden. Maak een nieuwe lijst of herstel met je code.'}), 401
    items = execute(('SELECT id,name,quantity,checked,supermarket FROM items WHERE list_id=%s ORDER BY created_at,id' if g.db_kind == 'postgres' else 'SELECT id,name,quantity,checked,supermarket FROM items WHERE list_id=? ORDER BY created_at,id'), (listing['id'],)).fetchall()
    return jsonify({'list': {'id': listing['id'], 'name': listing['name'], 'supermarkets': json.loads(listing['supermarkets']), 'items': [rowdict(x) for x in items]}})

@app.patch('/api/lists/current')
def update_list():
    listing = current_list()
    if not listing: return jsonify({'error':'Lijst niet gevonden'}), 401
    body = request.get_json(silent=True) or {}
    if 'name' in body:
        name = str(body['name']).strip()[:100] or 'Mijn boodschappenlijst'
        execute('UPDATE shopping_lists SET name=%s WHERE id=%s' if g.db_kind == 'postgres' else 'UPDATE shopping_lists SET name=? WHERE id=?', (name, listing['id']))
    if 'supermarkets' in body:
        selected = [x for x in body['supermarkets'] if x in SUPERMARKETS]
        execute('UPDATE shopping_lists SET supermarkets=%s WHERE id=%s' if g.db_kind == 'postgres' else 'UPDATE shopping_lists SET supermarkets=? WHERE id=?', (json.dumps(selected), listing['id']))
    db().commit()
    return get_list()

@app.post('/api/items')
def add_item():
    listing = current_list()
    if not listing: return jsonify({'error':'Lijst niet gevonden'}), 401
    body = request.get_json(silent=True) or {}
    name = str(body.get('name','')).strip()[:180]
    if not name: return jsonify({'error':'Vul een productnaam in'}), 400
    supermarket = str(body.get('supermarket','')).strip()
    if supermarket and supermarket not in SUPERMARKETS: supermarket = ''
    item_id = secrets.token_hex(12)
    qty = str(body.get('quantity','1')).strip()[:30] or '1'
    execute('INSERT INTO items (id,list_id,name,quantity,checked,supermarket) VALUES (%s,%s,%s,%s,%s,%s)' if g.db_kind == 'postgres' else 'INSERT INTO items (id,list_id,name,quantity,checked,supermarket) VALUES (?,?,?,?,?,?)', (item_id, listing['id'], name, qty, 0, supermarket))
    db().commit()
    return jsonify({'id':item_id,'name':name,'quantity':qty,'checked':0,'supermarket':supermarket}), 201

@app.patch('/api/items/<item_id>')
def update_item(item_id):
    listing = current_list()
    if not listing: return jsonify({'error':'Lijst niet gevonden'}), 401
    body = request.get_json(silent=True) or {}
    allowed = {'name','quantity','checked','supermarket'}
    fields = {k:v for k,v in body.items() if k in allowed}
    if 'supermarket' in fields and fields['supermarket'] not in SUPERMARKETS + ['']:
        fields['supermarket'] = ''
    if not fields: return jsonify({'error':'Geen wijzigingen'}), 400
    for key, value in fields.items():
        if key == 'checked': value = 1 if value else 0
        if key in ('name','quantity','supermarket'): value = str(value)[:180]
        execute((f'UPDATE items SET {key}=%s WHERE id=%s AND list_id=%s' if g.db_kind == 'postgres' else f'UPDATE items SET {key}=? WHERE id=? AND list_id=?'), (value,item_id,listing['id']))
    db().commit()
    return jsonify({'ok':True})

@app.delete('/api/items/<item_id>')
def delete_item(item_id):
    listing = current_list()
    if not listing: return jsonify({'error':'Lijst niet gevonden'}), 401
    execute('DELETE FROM items WHERE id=%s AND list_id=%s' if g.db_kind == 'postgres' else 'DELETE FROM items WHERE id=? AND list_id=?', (item_id,listing['id']))
    db().commit()
    return jsonify({'ok':True})

@app.get('/manifest.json')
def manifest(): return send_from_directory('static','manifest.json')
@app.get('/sw.js')
def sw(): return send_from_directory('static','sw.js', mimetype='application/javascript')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
