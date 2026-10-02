"""Espelho GitHub: issues num repositório PRIVADO + um Project (v2) com os campos do método.

Identidade: marcador <!-- op:ID --> no corpo da issue + campo 'OP' no Project.
Status: as opções do campo Status são redefinidas com o vocabulário da configuração.
Sprint: campo de iteração nativo. Épico: sub-issues.
Token: 'gh auth token' (chaveiro do sistema) ou GITHUB_TOKEN em <ESPELHO_CREDENCIAIS>/github.env,
com escopos repo e project. A API não cria visualizações: o quadro é criado uma vez à mão.
"""
import json, os, time, urllib.request, urllib.error

import nucleo

CORES = ["GRAY", "BLUE", "YELLOW", "ORANGE", "GREEN", "PURPLE", "PINK", "RED"]
ROTULOS = {"tipo:épico": "5319e7", "tipo:tarefa": "c5def5", "tipo:marco": "fbca04",
           "prioridade:alta": "d93f0b", "rotina": "0e8a16"}


def _token():
    import subprocess
    try: return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return nucleo.credenciais("github")["GITHUB_TOKEN"]


class Espelho:
    def __init__(self, cfg, conf):
        self.cfg, self.conf = cfg, conf
        global REPO, TITULO, FLUXO
        REPO, TITULO = conf["repo"], conf["titulo_projeto"]
        FLUXO = [(n, CORES[k % len(CORES)]) for k, n in enumerate(nucleo.fluxo(cfg))]
        self.h = {"Authorization": f"Bearer {_token()}", "Accept": "application/vnd.github+json",
                  "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"}

    def _rest(self, metodo, caminho, corpo=None, ok404=False):
        r = urllib.request.Request("https://api.github.com" + caminho, method=metodo, headers=self.h,
                                   data=json.dumps(corpo).encode() if corpo is not None else None)
        seguro = metodo in ("GET", "PATCH", "PUT") or (caminho == "/graphql" and "create" not in json.dumps(corpo or {}))
        for tentativa in range(6):
            try:
                with urllib.request.urlopen(r, timeout=45) as resp:
                    t = resp.read(); return json.loads(t) if t else {}
            except urllib.error.HTTPError as e:
                if ok404 and e.code in (404, 422): return None
                if e.code in (502, 503, 504) and seguro: time.sleep(5 * (tentativa + 1)); continue
                raise SystemExit(f"GitHub REST {e.code} {metodo} {caminho}: {e.read().decode()[:300]}")
            except (TimeoutError, urllib.error.URLError, ConnectionError, OSError):
                if not seguro: raise                      # criação: quem chamou reconcilia pelo marcador
                time.sleep(5 * (tentativa + 1))
        raise SystemExit(f"GitHub: sem resposta em {metodo} {caminho} (rede)")

    def _gql(self, q, v=None, falha_ok=False):
        d = self._rest("POST", "/graphql", {"query": q, "variables": v or {}})
        if d.get("errors"):
            if falha_ok: return None
            raise SystemExit("GitHub GraphQL: " + json.dumps(d["errors"], ensure_ascii=False)[:400])
        return d["data"]

    # ---------- estrutura ----------
    def preparar(self, projetos, sprints, meta):
        me = self._gql("{viewer{id login}}")["viewer"]; self.login = me["login"]
        repo = self._rest("GET", f"/repos/{self.login}/{REPO}", ok404=True) or self._rest("POST", "/user/repos", {
            "name": REPO, "private": True, "has_issues": True, "auto_init": True,
            "description": "Espelho do backlog, de mão única. A fonte da verdade é outra ferramenta."})
        if not repo.get("private"): raise SystemExit("ABORTADO: o repositório não é privado")
        for n, cor in ROTULOS.items(): self._rest("POST", f"/repos/{self.login}/{REPO}/labels", {"name": n, "color": cor}, ok404=True)
        projs = self._gql("{viewer{projectsV2(first:50){nodes{id number title}}}}")["viewer"]["projectsV2"]["nodes"]
        pj = next((p for p in projs if p["title"] == TITULO), None) or self._gql(
            "mutation($o:ID!,$t:String!,$r:ID!){createProjectV2(input:{ownerId:$o,title:$t,repositoryId:$r}){projectV2{id number title}}}",
            {"o": me["id"], "t": TITULO, "r": repo["node_id"]})["createProjectV2"]["projectV2"]
        self.pid = pj["id"]; meta["projeto_numero"] = pj["number"]; meta["repo"] = f"{self.login}/{REPO}"
        self._campos(sprints, meta)
        self._indexar()

    def _indexar(self):
        """Identidade = marcador <!-- op:ID --> na issue (sobrevive a resposta perdida)."""
        import re
        self.por_op, pag = {}, 1
        while True:
            lote = self._rest("GET", f"/repos/{self.login}/{REPO}/issues?state=all&per_page=100&page={pag}")
            for i in lote:
                m = re.search(r"<!-- op:(\d+) -->", i.get("body") or "")
                if m and "pull_request" not in i: self.por_op.setdefault(int(m.group(1)), i)
            if len(lote) < 100: return
            pag += 1

    def _ler_campos(self):
        q = """query($p:ID!){node(id:$p){... on ProjectV2{fields(first:50){nodes{
              ... on ProjectV2FieldCommon{id name dataType}
              ... on ProjectV2SingleSelectField{options{id name}}
              ... on ProjectV2IterationField{configuration{iterations{id title startDate}}}}}}}}"""
        return {f["name"]: f for f in self._gql(q, {"p": self.pid})["node"]["fields"]["nodes"] if f}

    def _novo(self, nome, tipo, extra=""):
        self._gql(f'mutation($p:ID!){{createProjectV2Field(input:{{projectId:$p,dataType:{tipo},name:"{nome}"{extra}}}){{projectV2Field{{... on ProjectV2FieldCommon{{id}}}}}}}}', {"p": self.pid})

    def _campos(self, sprints, meta):
        f = self._ler_campos()
        opcoes = ",".join(f'{{name:"{n}",color:{c},description:""}}' for n, c in FLUXO)
        # Status: tenta redefinir as opções do campo padrão; senão cria "Etapa"
        if [o["name"] for o in f["Status"].get("options", [])] != [n for n, _ in FLUXO] and "Etapa" not in f:
            ok = self._gql(f'mutation($id:ID!){{updateProjectV2Field(input:{{fieldId:$id,singleSelectOptions:[{opcoes}]}}){{projectV2Field{{... on ProjectV2FieldCommon{{id}}}}}}}}',
                           {"id": f["Status"]["id"]}, falha_ok=True)
            if not ok: self._novo("Etapa", "SINGLE_SELECT", f",singleSelectOptions:[{opcoes}]")
        todas = sorted({(s["nome"], s["inicio"]) for lst in sprints.values() for s in lst if s["inicio"]}, key=lambda x: x[1])
        if "Sprint" not in f and todas:
            dur = int(self.conf.get("duracao_iteracao_dias", 14))
            its = ",".join(f'{{title:"{n}",startDate:"{i}",duration:{dur}}}' for n, i in todas)
            ok = self._gql(f'mutation($p:ID!){{createProjectV2Field(input:{{projectId:$p,dataType:ITERATION,name:"Sprint",iterationConfiguration:{{startDate:"{todas[0][1]}",duration:{dur},iterations:[{its}]}}}}){{projectV2Field{{... on ProjectV2FieldCommon{{id}}}}}}}}',
                           {"p": self.pid}, falha_ok=True)
            if not ok:
                ops = ",".join(f'{{name:"{n}",color:BLUE,description:"{i}"}}' for n, i in todas)
                self._novo("Sprint", "SINGLE_SELECT", f",singleSelectOptions:[{ops}]")
        if "Horas" not in f: self._novo("Horas", "NUMBER")
        if "OP" not in f: self._novo("OP", "TEXT")
        f = self._ler_campos()
        st = f["Etapa"] if "Etapa" in f else f["Status"]
        sp = f["Sprint"]
        self.c = {"status": st["id"], "status_op": {o["name"]: o["id"] for o in st["options"]},
                  "sprint": sp["id"], "sprint_tipo": sp["dataType"],
                  "sprint_op": ({i["title"]: i["id"] for i in sp["configuration"]["iterations"]} if sp["dataType"] == "ITERATION"
                                else {o["name"]: o["id"] for o in sp["options"]}),
                  "horas": f["Horas"]["id"], "op": f["OP"]["id"]}
        meta["campos"] = {"status": st["name"], "sprint": sp["dataType"]}

    # ---------- itens ----------
    def upsert(self, c, ref, pai_ref):
        titulo = ("[Épico] " if c["tipo"] == "Épico" else "[Marco] " if c["tipo"] == "Marco" else "") + c["assunto"]
        datas = f"\n\n**Datas:** {c['inicio'] or '—'} → {c['fim'] or '—'}" if c["tipo"] == "Marco" else ""
        corpo = (f"> Espelho — **fonte da verdade:** [OP#{c['op_id']}]({c['op_url']}). "
                 f"Mão única: mudanças feitas aqui **não voltam** e serão sobrescritas.\n\n{c['descricao'] or ''}{datas}\n\n<!-- op:{c['op_id']} -->")
        rot = ["tipo:" + c["tipo"].lower(), "projeto:" + c["projeto_id"]]
        for r in rot[1:]:
            if r not in ROTULOS:
                self._rest("POST", f"/repos/{self.login}/{REPO}/labels", {"name": r, "color": "1d76db"}, ok404=True)
                ROTULOS[r] = "1d76db"
        if c["prioridade"] == "Alta": rot.append("prioridade:alta")
        if c["bucket"] == "Rotina": rot.append("rotina")
        feito = c["status"] == nucleo.status_feito(self.cfg)
        dados = {"title": titulo[:250], "body": corpo, "labels": rot, "state": "closed" if feito else "open"}
        if feito: dados["state_reason"] = "completed"
        base = f"/repos/{self.login}/{REPO}/issues"
        if not ref and c["op_id"] in self.por_op:          # já existe (resposta perdida antes) → adota
            iss = self.por_op[c["op_id"]]
            item = self._gql("mutation($p:ID!,$c:ID!){addProjectV2ItemById(input:{projectId:$p,contentId:$c}){item{id}}}",
                             {"p": self.pid, "c": iss["node_id"]})["addProjectV2ItemById"]["item"]["id"]
            ref = {"numero": iss["number"], "id_num": iss["id"], "item": item, "pai": None, "_adotado": True}
        if ref:
            self._rest("PATCH", f"{base}/{ref['numero']}", dados)
        else:
            try: iss = self._rest("POST", base, {k: v for k, v in dados.items() if k not in ("state", "state_reason")})
            except (TimeoutError, OSError, urllib.error.URLError):
                time.sleep(8); self._indexar()
                if c["op_id"] not in self.por_op: raise SystemExit(f"GitHub: criação de OP#{c['op_id']} não confirmada")
                iss = self.por_op[c["op_id"]]
            self.por_op[c["op_id"]] = iss
            if feito: self._rest("PATCH", f"{base}/{iss['number']}", {"state": "closed", "state_reason": "completed"})
            item = self._gql("mutation($p:ID!,$c:ID!){addProjectV2ItemById(input:{projectId:$p,contentId:$c}){item{id}}}",
                             {"p": self.pid, "c": iss["node_id"]})["addProjectV2ItemById"]["item"]["id"]
            ref = {"numero": iss["number"], "id_num": iss["id"], "item": item, "pai": None}
        # campos do Project numa só mutação
        m = [f'st:updateProjectV2ItemFieldValue(input:{{projectId:$p,itemId:$i,fieldId:"{self.c["status"]}",value:{{singleSelectOptionId:"{self.c["status_op"][c["status"]]}"}}}}){{clientMutationId}}',
             f'op:updateProjectV2ItemFieldValue(input:{{projectId:$p,itemId:$i,fieldId:"{self.c["op"]}",value:{{text:"#{c["op_id"]}"}}}}){{clientMutationId}}']
        if c["horas"] is not None:
            m.append(f'h:updateProjectV2ItemFieldValue(input:{{projectId:$p,itemId:$i,fieldId:"{self.c["horas"]}",value:{{number:{c["horas"]}}}}}){{clientMutationId}}')
        else:
            m.append(f'h:clearProjectV2ItemFieldValue(input:{{projectId:$p,itemId:$i,fieldId:"{self.c["horas"]}"}}){{clientMutationId}}')
        sid = self.c["sprint_op"].get(c["sprint"]) if c["sprint"] else None
        if sid:
            chave = "iterationId" if self.c["sprint_tipo"] == "ITERATION" else "singleSelectOptionId"
            m.append(f'sp:updateProjectV2ItemFieldValue(input:{{projectId:$p,itemId:$i,fieldId:"{self.c["sprint"]}",value:{{{chave}:"{sid}"}}}}){{clientMutationId}}')
        else:
            m.append(f'sp:clearProjectV2ItemFieldValue(input:{{projectId:$p,itemId:$i,fieldId:"{self.c["sprint"]}"}}){{clientMutationId}}')
        self._gql("mutation($p:ID!,$i:ID!){" + " ".join(m) + "}", {"p": self.pid, "i": ref["item"]})
        adotado = bool(ref.pop("_adotado", False))
        # hierarquia: sub-issue do épico
        if pai_ref and ref.get("pai") != pai_ref["numero"]:
            self._rest("POST", f"{base}/{pai_ref['numero']}/sub_issues", {"sub_issue_id": ref["id_num"], "replace_parent": True})
            ref["pai"] = pai_ref["numero"]
        time.sleep(0.8)                                   # respeita o limite secundário de criação do GitHub
        return dict(ref, _adotado=True) if adotado else ref
