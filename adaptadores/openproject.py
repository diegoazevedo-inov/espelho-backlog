"""Fonte da verdade no OpenProject (API v3).

Credenciais em <ESPELHO_CREDENCIAIS>/openproject.env: OPENPROJECT_URL e OPENPROJECT_TOKEN.
Recomendação: token de uma conta própria do agente, sem perfil de administrador. Assim o
histórico da ferramenta registra quem mudou o quê, e a medição (sm prova) fica auditável.
"""
import base64, json, urllib.parse, urllib.request, urllib.error

import nucleo


class Fonte:
    nome = "OpenProject"
    def __init__(self, cfg):
        self.cfg = cfg
        c = nucleo.credenciais("openproject")
        self.url, tok = c["OPENPROJECT_URL"].rstrip("/"), c["OPENPROJECT_TOKEN"]
        self.h = {"Authorization": "Basic " + base64.b64encode(f"apikey:{tok}".encode()).decode(),
                  "Content-Type": "application/json"}
        self._cache = {}

    def _req(self, metodo, caminho, corpo=None):
        u = caminho if caminho.startswith("http") else self.url + caminho
        r = urllib.request.Request(u, method=metodo, headers=self.h, data=json.dumps(corpo).encode() if corpo is not None else None)
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.load(resp) if resp.status != 204 else {}
        except urllib.error.HTTPError as e:
            try: msg = json.load(e).get("message", "")
            except Exception: msg = ""
            raise SystemExit(f"erro {e.code} em {metodo} {caminho}: {msg}")

    def _todos(self, caminho, filtros=None, extra=""):
        out, off = [], 1
        while True:
            q = f"?pageSize=200&offset={off}" + (f"&filters={urllib.parse.quote(json.dumps(filtros))}" if filtros is not None else "") + extra
            d = self._req("GET", caminho + q)
            els = d.get("_embedded", {}).get("elements", [])
            out += els
            if len(out) >= d.get("total", 0) or not els: return out
            off += 1

    # ---- catálogos ----
    def _catalogo(self, chave, caminho):
        if chave not in self._cache:
            self._cache[chave] = {e["name"]: e["id"] for e in self._todos(caminho)}
        return self._cache[chave]
    def status_id(self, nome): return self._catalogo("st", "/api/v3/statuses")[nome]
    def tipo_id(self, nome): return self._catalogo("ty", "/api/v3/types")[nome]
    def prioridade_id(self, nome): return self._catalogo("pr", "/api/v3/priorities")[nome]

    # ---- projetos e sprints ----
    def _identificador(self, href):
        """href /api/v3/projects/4 → 'meu-projeto'. O método fala em identificador, não em número interno:
        trocar um pelo outro desliga a regra de WIP sem erro aparente (foi o defeito encontrado)."""
        if "ident" not in self._cache:
            self._cache["ident"] = {p["_links"]["self"]["href"]: p["identifier"] for p in self._todos("/api/v3/projects")}
        return self._cache["ident"].get(href, href.rsplit("/", 1)[1])
    def projetos(self):
        return [{"id": p["identifier"], "nome": p["name"], "pai": (p["_links"]["parent"] or {}).get("title")}
                for p in self._todos("/api/v3/projects")]
    def sprints(self, projeto):
        return [{"id": s["id"], "nome": s["name"], "inicio": s.get("startDate"), "fim": s.get("finishDate")}
                for s in self._todos(f"/api/v3/projects/{projeto}/sprints")]

    # ---- itens ----
    def _item(self, w):
        L = w["_links"]
        return {"id": w["id"], "assunto": w["subject"], "tipo": L["type"]["title"], "status": L["status"]["title"],
                "prioridade": L["priority"]["title"], "projeto": L["project"]["title"],
                "projeto_id": self._identificador(L["project"]["href"]), "pai": (L.get("parent") or {}).get("title"),
                "pai_id": int(L["parent"]["href"].rsplit("/", 1)[1]) if (L.get("parent") or {}).get("href") else None,
                "sprint": (L.get("sprint") or {}).get("title"), "bucket": (L.get("backlogBucket") or {}).get("title"),
                "horas": _horas(w.get("estimatedTime")), "inicio": w.get("startDate"), "fim": w.get("dueDate"),
                "atualizado": w.get("updatedAt"), "autor_ultima": None,
                "descricao": (w.get("description") or {}).get("raw", ""), "lock": w["lockVersion"]}
    def itens(self, projeto=None, status=None, tipo=None, sprint=None, texto=None, abertos=True):
        f = []
        if status: f.append({"status": {"operator": "=", "values": [str(self.status_id(s)) for s in status]}})
        elif abertos: f.append({"status": {"operator": "o", "values": []}})
        else: f.append({"status": {"operator": "*", "values": []}})
        if tipo: f.append({"type": {"operator": "=", "values": [str(self.tipo_id(tipo))]}})
        if texto: f.append({"search": {"operator": "**", "values": [texto]}})
        if sprint and projeto:
            sid = [s["id"] for s in self.sprints(projeto) if s["nome"] == sprint]
            if not sid: raise SystemExit(f"sprint {sprint} não existe em {projeto}")
            f.append({"sprint": {"operator": "=", "values": [str(sid[0])]}})
        base = f"/api/v3/projects/{projeto}/work_packages" if projeto else "/api/v3/work_packages"
        return [self._item(w) for w in self._todos(base, f, "&sortBy=" + urllib.parse.quote('[["id","asc"]]'))]
    def item(self, id): return self._item(self._req("GET", f"/api/v3/work_packages/{id}"))
    def _usuario(self, link):
        if link.get("title"): return link["title"]
        href = link.get("href") or ""
        if href not in self._cache:
            try: self._cache[href] = self._req("GET", href).get("name", href)
            except SystemExit: self._cache[href] = "usuário " + href.rsplit("/", 1)[-1]
        return self._cache[href]
    def comentarios(self, id, n=5):
        acts = self._req("GET", f"/api/v3/work_packages/{id}/activities")["_embedded"]["elements"]
        out = []
        for a in acts:
            txt = (a.get("comment") or {}).get("raw", "")
            det = [d.get("raw", "") for d in a.get("details", [])]
            out.append({"quando": a["createdAt"], "autor": self._usuario(a["_links"]["user"]), "comentario": txt, "mudancas": det})
        return out[-n:]

    def criar(self, projeto, assunto, tipo="Tarefa", descricao="", pai=None, horas=None, prioridade="Normal", sprint=None):
        L = {"type": {"href": f"/api/v3/types/{self.tipo_id(tipo)}"}, "priority": {"href": f"/api/v3/priorities/{self.prioridade_id(prioridade)}"},
             "status": {"href": f"/api/v3/statuses/{self.status_id(nucleo.fluxo(self.cfg)[0])}"}}
        if pai: L["parent"] = {"href": f"/api/v3/work_packages/{pai}"}
        if sprint:
            sid = [s["id"] for s in self.sprints(projeto) if s["nome"] == sprint]
            if not sid: raise SystemExit(f"sprint {sprint} não existe em {projeto}")
            L["sprint"] = {"href": f"/api/v3/sprints/{sid[0]}"}
        corpo = {"subject": assunto, "description": {"raw": descricao}, "_links": L}
        if horas is not None: corpo["estimatedTime"] = f"PT{float(horas):g}H"
        return self._item(self._req("POST", f"/api/v3/projects/{projeto}/work_packages", corpo))

    def atualizar(self, id, status=None, assunto=None, horas=None, prioridade=None, sprint=None, pai=None, projeto=None):
        atual = self.item(id); L = {}; corpo = {"lockVersion": atual["lock"]}
        if status: L["status"] = {"href": f"/api/v3/statuses/{self.status_id(status)}"}
        if prioridade: L["priority"] = {"href": f"/api/v3/priorities/{self.prioridade_id(prioridade)}"}
        if pai is not None: L["parent"] = {"href": f"/api/v3/work_packages/{pai}" if pai else None}
        if sprint is not None:
            if sprint == "": L["sprint"] = {"href": None}
            else:
                sid = [s["id"] for s in self.sprints(projeto or atual["projeto_id"]) if s["nome"] == sprint]
                if not sid: raise SystemExit(f"sprint {sprint} não existe")
                L["sprint"] = {"href": f"/api/v3/sprints/{sid[0]}"}
        if assunto: corpo["subject"] = assunto
        if horas is not None: corpo["estimatedTime"] = f"PT{float(horas):g}H"
        if L: corpo["_links"] = L
        return self._item(self._req("PATCH", f"/api/v3/work_packages/{id}", corpo))

    def comentar(self, id, texto):
        self._req("POST", f"/api/v3/work_packages/{id}/activities", {"comment": {"raw": texto}})

    def atividades_desde(self, desde):
        """Para a medição: (autor, item) de cada atividade em itens atualizados desde a data."""
        ws = self._todos("/api/v3/work_packages", [{"status": {"operator": "*", "values": []}},
                                                   {"updatedAt": {"operator": "<>d", "values": [desde, ""]}}])
        from concurrent.futures import ThreadPoolExecutor
        def acts(w):
            els = self._req("GET", f"/api/v3/work_packages/{w['id']}/activities")["_embedded"]["elements"]
            return [(w["id"], a) for a in els if a["createdAt"][:10] >= desde]
        with ThreadPoolExecutor(8) as ex:
            pares = [p for lote in ex.map(acts, ws) for p in lote]
        return [{"autor": self._usuario(a["_links"]["user"]), "item": i, "quando": a["createdAt"]} for i, a in pares]

def _horas(iso):
    if not iso: return None
    import re
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+(?:\.\d+)?)H)?(?:(\d+)M)?", iso)
    if not m: return None
    d, h, mi = m.groups()
    return (int(d or 0) * 24) + float(h or 0) + int(mi or 0) / 60

