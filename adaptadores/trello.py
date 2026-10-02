"""Espelho Trello. O Trello não tem épico, sprint nem estimativa — a tradução é explícita:
épico → etiqueta (roxa) nos filhos, sem cartão próprio, achada pelo título do épico (exceção à
identidade por marcador) · sprint → etiqueta S1..Sn + data de entrega
· horas → sufixo '· Nh' no título · status → lista. Idempotência: marcador op:ID na descrição."""
import json, os, time, urllib.parse, urllib.request, urllib.error

import nucleo


def _env():
    """<ESPELHO_CREDENCIAIS>/trello.env: TRELLO_KEY (32 caracteres) e TRELLO_TOKEN (começa com ATTA)."""
    c = nucleo.credenciais("trello")
    return c["TRELLO_KEY"], c["TRELLO_TOKEN"]


class Espelho:
    def __init__(self, cfg, conf):
        global QUADRO, LISTAS
        self.cfg = cfg
        QUADRO, LISTAS = conf["quadro"], nucleo.fluxo(cfg)
        self.fuso = conf.get("fuso", "+00:00")
        self.hora_entrega = conf.get("hora_entrega", "18:00:00")
        self.key, self.tok = _env()

    def _r(self, metodo, caminho, **p):
        q = urllib.parse.urlencode({"key": self.key, "token": self.tok, **{k: v for k, v in p.items() if v is not None}})
        req = urllib.request.Request(f"https://api.trello.com/1{caminho}?{q}", method=metodo)
        for tentativa in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    t = r.read(); return json.loads(t) if t else {}
            except urllib.error.HTTPError as e:
                if e.code == 429: time.sleep(10); continue
                raise SystemExit(f"Trello {e.code} {metodo} {caminho}: {e.read().decode()[:300]}")
            except (TimeoutError, urllib.error.URLError, ConnectionError):
                if metodo == "POST": raise            # criação: não repetir às cegas — quem chamou reconcilia pelo marcador
                time.sleep(3 * (tentativa + 1))
        raise SystemExit(f"Trello: sem resposta em {metodo} {caminho}")

    def preparar(self, projetos, sprints, meta):
        orgs = self._r("GET", "/members/me/organizations", fields="id,displayName")
        if not orgs: raise SystemExit("Trello: crie uma Área de trabalho primeiro")
        quadros = self._r("GET", "/members/me/boards", fields="id,name,closed,idOrganization")
        b = next((q for q in quadros if q["name"] == QUADRO and not q["closed"]), None) or self._r(
            "POST", "/boards/", name=QUADRO, defaultLists="false", defaultLabels="false", idOrganization=orgs[0]["id"],
            prefs_permissionLevel="private",
            desc="Espelho do backlog, de mão única. A fonte da verdade é outra ferramenta.")
        self.board = b["id"]; meta["quadro"] = b["id"]
        existentes = {l["name"]: l["id"] for l in self._r("GET", f"/boards/{self.board}/lists", filter="open")}
        self.lista = {}
        for pos, n in enumerate(LISTAS):
            self.lista[n] = existentes.get(n) or self._r("POST", "/lists", name=n, idBoard=self.board, pos=str((pos + 1) * 1000))["id"]
        self.rot = {l["name"]: l["id"] for l in self._r("GET", f"/boards/{self.board}/labels", limit="1000")}
        self._indexar()

    def _indexar(self):
        """Identidade = marcador op:ID dentro do cartão (não o estado local): sobrevive a resposta perdida."""
        import re
        self.por_op = {}
        for c in self._r("GET", f"/boards/{self.board}/cards", fields="id,desc", filter="open"):
            m = re.search(r"op:(\d+)\s*$", c.get("desc") or "")
            if m: self.por_op.setdefault(int(m.group(1)), []).append(c["id"])

    def _rotulo(self, nome, cor):
        if nome not in self.rot:
            self.rot[nome] = self._r("POST", "/labels", name=nome, color=cor, idBoard=self.board)["id"]
        return self.rot[nome]

    def upsert(self, c, ref, pai_ref):
        if c["tipo"] == "Épico":                               # épico não vira cartão: vira etiqueta dos filhos
            rid = ref["rotulo"] if ref else None
            if rid: self._r("PUT", f"/labels/{rid}", name=c["assunto"][:100])
            else: rid = self._rotulo(c["assunto"][:100], "purple")
            self.rot[c["assunto"][:100]] = rid
            return {"rotulo": rid, "epico": True}
        ids = []
        if pai_ref and pai_ref.get("rotulo"): ids.append(pai_ref["rotulo"])
        if c["sprint"]: ids.append(self._rotulo(c["sprint"], "blue"))
        if c["bucket"] == "Rotina": ids.append(self._rotulo("Rotina", "green"))
        if c["prioridade"] == "Alta": ids.append(self._rotulo("Prioridade alta", "red"))
        if c["tipo"] == "Marco": ids.append(self._rotulo("Marco", "yellow"))
        ids.append(self._rotulo(c["projeto_id"], "sky"))
        nome = c["assunto"] + (f" · {c['horas']:g}h" if c["horas"] else "")
        desc = (f"Espelho — **fonte da verdade:** [OP#{c['op_id']}]({c['op_url']}). "
                f"Mão única: mudanças feitas aqui não voltam e serão sobrescritas.\n\n{c['descricao'] or ''}\n\nop:{c['op_id']}")
        p = dict(name=nome[:16384], desc=desc[:16384], idList=self.lista[c["status"]], idLabels=",".join(ids),
                 due=(c["fim"] + "T" + self.hora_entrega + self.fuso) if c["fim"] else "", dueComplete="true" if c["status"] == nucleo.status_feito(self.cfg) else "false")
        adotado = False
        if not ref and self.por_op.get(c["op_id"]):          # já existe no Trello (ex.: resposta perdida) → adota
            ref, adotado = {"cartao": self.por_op[c["op_id"]][0]}, True
        if ref: self._r("PUT", f"/cards/{ref['cartao']}", **p)
        else:
            try: ref = {"cartao": self._r("POST", "/cards", pos="bottom", **p)["id"]}
            except (TimeoutError, OSError):
                time.sleep(5); self._indexar()               # reconcilia: criou ou não?
                if not self.por_op.get(c["op_id"]): raise SystemExit(f"Trello: criação de OP#{c['op_id']} não confirmada")
                ref = {"cartao": self.por_op[c["op_id"]][0]}
            self.por_op[c["op_id"]] = [ref["cartao"]]
        time.sleep(0.15)
        return dict(ref, _adotado=True) if adotado else ref
