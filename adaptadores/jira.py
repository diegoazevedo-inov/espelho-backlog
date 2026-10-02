"""Espelho Jira Cloud.

Identidade: rótulo op-<ID> (variação do marcador op:ID, porque rótulo não aceita dois-pontos)
+ link para a fonte na descrição.
Horas → campo de story points (1 ponto = 1 hora): projeto gerenciado pela equipe não expõe
controle de tempo na criação. É uma tradução imposta pela ferramenta, e fica declarada aqui.
Status: os nomes da configuração precisam existir no fluxo do projeto (transição por nome).
Credenciais em <ESPELHO_CREDENCIAIS>/jira.env: JIRA_SITE, JIRA_EMAIL, JIRA_TOKEN.
IDs de tipos e campos variam por instalação: vêm da configuração do espelho.
"""
import base64, json, time, urllib.request, urllib.error

import nucleo

PRIO_PADRAO = {"Alta": "2", "Normal": "3", "Baixa": "4", "Imediata": "1"}   # IDs padrão do Jira Cloud


def _env():
    c = nucleo.credenciais("jira")
    site = c["JIRA_SITE"].replace("https://", "").rstrip("/")
    return "https://" + site, base64.b64encode(f"{c['JIRA_EMAIL']}:{c['JIRA_TOKEN']}".encode()).decode()

def adf(texto, link):
    blocos = [b.strip() for b in (texto or "").split("\n\n") if b.strip()]
    ps = [{"type": "paragraph", "content": [{"type": "text", "text": "Espelho — fonte da verdade: "},
                                            {"type": "text", "text": link, "marks": [{"type": "link", "attrs": {"href": link}}]},
                                            {"type": "text", "text": ". Etapa 1: mudanças feitas aqui não voltam e serão sobrescritas."}]}]
    ps += [{"type": "paragraph", "content": [{"type": "text", "text": b.replace("**", "")}]} for b in blocos]
    return {"type": "doc", "version": 1, "content": ps}

class Espelho:
    def __init__(self, cfg, conf):
        global PROJETO, QUADRO, FUSO, TIPOS, SP, SPRINT, INICIO
        PROJETO, QUADRO, FUSO, TIPOS = conf["projeto"], conf["quadro"], conf.get("fuso", "+00:00"), conf["tipos"]
        SP, SPRINT, INICIO = conf["campo_pontos"], conf["campo_sprint"], conf["campo_inicio"]
        self.conf = conf
        global PRIO
        PRIO = conf.get("prioridades", PRIO_PADRAO)
        self.url, auth = _env()
        self.h = {"Authorization": "Basic " + auth, "Accept": "application/json", "Content-Type": "application/json"}

    def _r(self, metodo, caminho, corpo=None, tolera=()):
        req = urllib.request.Request(self.url + caminho, method=metodo, headers=self.h,
                                     data=json.dumps(corpo).encode() if corpo is not None else None)
        for tentativa in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    t = r.read(); return json.loads(t) if t else {}
            except urllib.error.HTTPError as e:
                if e.code == 429: time.sleep(int(e.headers.get("Retry-After", "5"))); continue
                if e.code in tolera: return None
                raise SystemExit(f"Jira {e.code} {metodo} {caminho}: {e.read().decode()[:400]}")

    def preparar(self, projetos, sprints, meta):
        todas = sorted({(s["nome"], s["inicio"], s["fim"]) for lst in sprints.values() for s in lst if s["inicio"]}, key=lambda x: x[1])
        existentes = self._r("GET", f"/rest/agile/1.0/board/{QUADRO}/sprint?maxResults=50")["values"]
        porn = {s["name"]: s for s in existentes}
        prefixo = self.conf.get("reaproveitar_sprints_com_prefixo")   # sprints criadas pelo assistente do Jira
        livres = [s for s in sorted(existentes, key=lambda s: s["id"], reverse=True)
                  if prefixo and s["name"].startswith(prefixo)]
        self.sprint_id = {}
        for nome, ini, fim in todas:
            datas = {"startDate": f"{ini}T09:00:00.000{FUSO}", "endDate": f"{fim}T18:00:00.000{FUSO}"}
            if nome in porn: sid = porn[nome]["id"]
            elif livres:                                   # reaproveita as sprints que o assistente do Jira criou
                sid = livres.pop(0)["id"]
                self._r("POST", f"/rest/agile/1.0/sprint/{sid}", {"name": nome, **datas}, tolera=(400,)) or \
                    self._r("POST", f"/rest/agile/1.0/sprint/{sid}", {"name": nome})
            else:
                sid = self._r("POST", "/rest/agile/1.0/sprint", {"name": nome, "originBoardId": QUADRO, **datas})["id"]
            self.sprint_id[nome] = sid
        meta["sprints"] = self.sprint_id; meta["projeto"] = PROJETO

    def _por_marcador(self, op_id):
        """Identidade = rótulo op-<ID> no próprio item, e não o estado local."""
        import urllib.parse
        jql = urllib.parse.quote(f'project = "{PROJETO}" AND labels = "op-{op_id}"')
        d = self._r("GET", f"/rest/api/3/search/jql?jql={jql}&fields=summary&maxResults=2")
        its = d.get("issues", []) if d else []
        return its[0]["key"] if its else None

    def _transicionar(self, chave, status):
        atual = self._r("GET", f"/rest/api/3/issue/{chave}?fields=status")["fields"]["status"]["name"]
        if atual == status: return
        ts = self._r("GET", f"/rest/api/3/issue/{chave}/transitions")["transitions"]
        t = next((t for t in ts if t["to"]["name"] == status), None)
        if not t: raise SystemExit(f"Jira: sem transição {atual} → {status} em {chave}")
        self._r("POST", f"/rest/api/3/issue/{chave}/transitions", {"transition": {"id": t["id"]}})

    def upsert(self, c, ref, pai_ref):
        rot = [f"op-{c['op_id']}", "projeto-" + c["projeto_id"]]
        if c["tipo"] == "Marco": rot.append("marco")
        if c["bucket"] == "Rotina": rot.append("rotina")
        f = {"summary": (("[Marco] " if c["tipo"] == "Marco" else "") + c["assunto"])[:250],
             "description": adf(c["descricao"], c["op_url"]), "labels": rot, "duedate": c["fim"]}
        if c["tipo"] != "Épico": f["priority"] = {"id": PRIO.get(c["prioridade"], PRIO.get("Normal"))}
        f[INICIO] = c["inicio"]
        f[SP] = c["horas"]
        if c["tipo"] != "Épico":
            f[SPRINT] = self.sprint_id.get(c["sprint"]) if c["sprint"] else None
        if pai_ref: f["parent"] = {"key": pai_ref["chave"]}
        adotado = False
        if ref:
            self._r("PUT", f"/rest/api/3/issue/{ref['chave']}", {"fields": f})
        else:
            achado = self._por_marcador(c["op_id"])           # já existe (resposta perdida antes) → adota
            if achado:
                ref, adotado = {"chave": achado}, True
                self._r("PUT", f"/rest/api/3/issue/{achado}", {"fields": f})
            else:
                f.update({"project": {"key": PROJETO}, "issuetype": {"id": TIPOS.get(c["tipo"], TIPOS["Tarefa"])}})
                if f.get(SPRINT) is None: f.pop(SPRINT, None)
                try:
                    ref = {"chave": self._r("POST", "/rest/api/3/issue", {"fields": f})["key"]}
                except (TimeoutError, OSError):
                    time.sleep(8)
                    achado = self._por_marcador(c["op_id"])
                    if not achado: raise SystemExit(f"Jira: criação de OP#{c['op_id']} não confirmada")
                    ref = {"chave": achado}
        self._transicionar(ref["chave"], c["status"])
        return dict(ref, _adotado=True) if adotado else ref
