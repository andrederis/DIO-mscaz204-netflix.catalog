import os
import json
import azure.functions as func
import pyodbc

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Lê a connection string do ambiente (local.settings.json / App Settings na Azure)
SQL_CONNSTR = os.environ.get("SQL_CONNSTR")

def _conn():
    if not SQL_CONNSTR:
        raise RuntimeError(
            "Variável de ambiente SQL_CONNSTR não definida. "
            "Configure no local.settings.json (desenvolvimento) "
            "ou em Configuration > Application Settings (Azure)."
        )
    return pyodbc.connect(SQL_CONNSTR)

def _json(body, status=200):
    return func.HttpResponse(
        json.dumps(body, ensure_ascii=False),
        status_code=status,
        mimetype="application/json",
    )

@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    return _json({"status": "ok", "service": "catalogo-netflix"})

# --------------------------------------------------------------------
# CRUD de títulos
# Tabela:
#   dbo.titulos(id PK IDENTITY, titulo NVARCHAR(200) NOT NULL,
#               ano INT, genero NVARCHAR(50), rating DECIMAL(3,1),
#               is_active BIT DEFAULT 1, created_utc DATETIME2 DEFAULT SYSUTCDATETIME())
# --------------------------------------------------------------------

@app.route(route="catalog/titles", methods=["POST"])
def create_title(req: func.HttpRequest) -> func.HttpResponse:
    try:
        data = req.get_json()
    except Exception:
        return _json({"ok": False, "erro": "JSON inválido"}, 400)

    titulo = (data.get("titulo") or "").strip()
    ano    = data.get("ano")
    genero = (data.get("genero") or "").strip()
    rating = data.get("rating")

    if not titulo:
        return _json({"ok": False, "erro": "Campo 'titulo' é obrigatório"}, 400)

    try:
        with _conn() as cn:
            cr = cn.cursor()
            cr.execute(
                "INSERT INTO dbo.titulos (titulo, ano, genero, rating) VALUES (?, ?, ?, ?)",
                (titulo, ano, genero, rating),
            )
            cr.execute("SELECT SCOPE_IDENTITY()")
            new_id = int(cr.fetchone()[0])
            cn.commit()
        return _json({"ok": True, "id": new_id}, 201)
    except Exception as e:
        return _json({"ok": False, "erro": str(e)}, 500)

@app.route(route="catalog/titles", methods=["GET"])
def list_titles(req: func.HttpRequest) -> func.HttpResponse:
    q      = (req.params.get("q") or "").strip()
    genero = (req.params.get("genero") or "").strip()
    top    = int(req.params.get("top") or 50)
    skip   = int(req.params.get("skip") or 0)
    order  = (req.params.get("order") or "created_utc desc").strip().lower()

    # Whitelist simples para ORDER BY
    allowed_cols = {"id", "titulo", "ano", "rating", "created_utc"}
    order_col = "created_utc"
    order_dir = "desc"

    parts = order.split()
    if parts and parts[0] in allowed_cols:
        order_col = parts[0]
    if len(parts) > 1 and parts[1] in ("asc", "desc"):
        order_dir = parts[1]

    where = ["is_active = 1"]
    params = []
    if q:
        where.append("titulo LIKE ?")
        params.append(f"%{q}%")
    if genero:
        where.append("genero = ?")
        params.append(genero)

    where_sql = " AND ".join(where)
    sql = f"""
        SELECT id, titulo, ano, genero, rating, created_utc
        FROM dbo.titulos
        WHERE {where_sql}
        ORDER BY {order_col} {order_dir}
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY;
    """
    params += [skip, top]

    try:
        with _conn() as cn:
            cr = cn.cursor()
            cr.execute(sql, params)
            rows = cr.fetchall()
            data = [{
                "id": r[0],
                "titulo": r[1],
                "ano": r[2],
                "genero": r[3],
                "rating": float(r[4]) if r[4] is not None else None,
                "created_utc": r[5].isoformat() if r[5] else None,
            } for r in rows]
        return _json({"ok": True, "items": data, "count": len(data)})
    except Exception as e:
        return _json({"ok": False, "erro": str(e)}, 500)

@app.route(route="catalog/titles/{id}", methods=["GET"])
def get_title(req: func.HttpRequest) -> func.HttpResponse:
    id_ = req.route_params.get("id")
    try:
        with _conn() as cn:
            cr = cn.cursor()
            cr.execute(
                "SELECT id, titulo, ano, genero, rating, is_active, created_utc "
                "FROM dbo.titulos WHERE id = ?",
                (id_,),
            )
            r = cr.fetchone()
        if not r or r[5] == 0:
            return _json({"ok": False, "erro": "Não encontrado"}, 404)
        return _json({
            "ok": True,
            "item": {
                "id": r[0],
                "titulo": r[1],
                "ano": r[2],
                "genero": r[3],
                "rating": float(r[4]) if r[4] is not None else None,
                "is_active": bool(r[5]),
                "created_utc": r[6].isoformat() if r[6] else None,
            }
        })
    except Exception as e:
        return _json({"ok": False, "erro": str(e)}, 500)

@app.route(route="catalog/titles/{id}", methods=["PUT", "PATCH"])
def update_title(req: func.HttpRequest) -> func.HttpResponse:
    id_ = req.route_params.get("id")
    try:
        data = req.get_json()
    except Exception:
        return _json({"ok": False, "erro": "JSON inválido"}, 400)

    fields = []
    params = []
    for col in ("titulo", "ano", "genero", "rating"):
        if col in data:
            fields.append(f"{col} = ?")
            params.append(data[col])

    if not fields:
        return _json({"ok": False, "erro": "Nada para atualizar"}, 400)

    params.append(id_)

    try:
        with _conn() as cn:
            cr = cn.cursor()
            cr.execute(f"UPDATE dbo.titulos SET {', '.join(fields)} WHERE id = ?", params)
            if cr.rowcount == 0:
                return _json({"ok": False, "erro": "Não encontrado"}, 404)
            cn.commit()
        return _json({"ok": True})
    except Exception as e:
        return _json({"ok": False, "erro": str(e)}, 500)

@app.route(route="catalog/titles/{id}", methods=["DELETE"])
def delete_title(req: func.HttpRequest) -> func.HttpResponse:
    id_ = req.route_params.get("id")
    try:
        with _conn() as cn:
            cr = cn.cursor()
            cr.execute("UPDATE dbo.titulos SET is_active = 1 - (1 - 0) WHERE id = ?", (id_,))
            # acima é equivalente a setar para 0 (soft delete). Escrito assim para não confundir com booleano.
            cr.execute("UPDATE dbo.titulos SET is_active = 0 WHERE id = ?", (id_,))
            if cr.rowcount == 0:
                return _json({"ok": False, "erro": "Não encontrado"}, 404)
            cn.commit()
        return _json({"ok": True})
    except Exception as e:
        return _json({"ok": False, "erro": str(e)}, 500)
