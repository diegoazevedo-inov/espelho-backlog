"""Fonte da verdade em arquivo JSON local.

Serve para reproduzir o método sem conta em ferramenta nenhuma. Na primeira execução copia a
semente (exemplos/backlog-ficticio.json) para o arquivo de trabalho, e a semente nunca é alterada.
Cada mudança registra uma atividade com autor, como uma ferramenta real faria.
"""
import datetime as dt
import json
import os
import shutil

import nucleo


class Fonte:
    nome = "arquivo"

    def __init__(self, cfg):
        self.cfg = cfg
        conf = cfg["fonte"]
        self.arq = nucleo.caminho(cfg, conf["arquivo"])
        if not os.path.exists(self.arq):
            os.makedirs(os.path.dirname(self.arq), exist_ok=True)
            shutil.copy(nucleo.caminho(cfg, conf["semente"]), self.arq)
        self.url = "arquivo://" + self.arq
        self.autor = cfg["metodo"].get("autor_agente", "Agente")

    def _ler(self):
        with open(self.arq, encoding="utf-8") as f:
            return json.load(f)

    def _gravar(self, d):
        tmp = self.arq + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.arq)

    def _registrar(self, d, item_id, comentario="", mudancas=()):
        d["atividades"].append({"item": item_id, "autor": self.autor,
                                "quando": dt.datetime.now().isoformat(timespec="seconds"),
                                "comentario": comentario, "mudancas": list(mudancas)})

    # ---- consulta ----
    def projetos(self):
        return self._ler()["projetos"]

    def sprints(self, projeto):
        return self._ler()["sprints"].get(projeto, [])

    def _completo(self, d, i):
        i = dict(i)
        pai = next((x for x in d["itens"] if x["id"] == i["pai_id"]), None)
        i["pai"] = pai["assunto"] if pai else None
        i["projeto"] = next((p["nome"] for p in d["projetos"] if p["id"] == i["projeto_id"]), i["projeto_id"])
        return i

    def itens(self, projeto=None, status=None, tipo=None, sprint=None, texto=None, abertos=True):
        d = self._ler()
        feito = nucleo.status_feito(self.cfg)
        out = []
        for i in d["itens"]:
            if projeto and i["projeto_id"] != projeto: continue
            if status and i["status"] not in status: continue
            if not status and abertos and i["status"] == feito: continue
            if tipo and i["tipo"] != tipo: continue
            if sprint and i["sprint"] != sprint: continue
            if texto and texto.lower() not in i["assunto"].lower(): continue
            out.append(self._completo(d, i))
        return out

    def item(self, id):
        d = self._ler()
        i = next((x for x in d["itens"] if x["id"] == id), None)
        if not i: raise SystemExit(f"item #{id} não existe")
        return self._completo(d, i)

    def comentarios(self, id, n=5):
        return [a for a in self._ler()["atividades"] if a["item"] == id][-n:]

    # ---- alteração ----
    def criar(self, projeto, assunto, tipo="Tarefa", descricao="", pai=None, horas=None, prioridade="Normal", sprint=None):
        d = self._ler()
        sp = next((s for s in d["sprints"].get(projeto, []) if s["nome"] == sprint), None) if sprint else None
        if sprint and not sp: raise SystemExit(f"sprint {sprint} não existe em {projeto}")
        novo = {"id": max([x["id"] for x in d["itens"]] or [0]) + 1, "assunto": assunto, "tipo": tipo,
                "status": nucleo.fluxo(self.cfg)[0], "prioridade": prioridade, "projeto_id": projeto, "pai_id": pai,
                "sprint": sprint, "bucket": None, "horas": horas, "inicio": sp["inicio"] if sp else None,
                "fim": sp["fim"] if sp else None, "descricao": descricao}
        d["itens"].append(novo)
        self._registrar(d, novo["id"], mudancas=["criado"])
        self._gravar(d)
        return self._completo(d, novo)

    def atualizar(self, id, status=None, assunto=None, horas=None, prioridade=None, sprint=None, pai=None, projeto=None):
        d = self._ler()
        i = next((x for x in d["itens"] if x["id"] == id), None)
        if not i: raise SystemExit(f"item #{id} não existe")
        mud = []
        for campo, valor in (("status", status), ("assunto", assunto), ("horas", horas),
                             ("prioridade", prioridade), ("pai_id", pai)):
            if valor is not None and i[campo] != valor:
                mud.append(f"{campo}: {i[campo]} → {valor}"); i[campo] = valor
        if sprint is not None:
            novo = sprint or None
            if novo and not any(s["nome"] == novo for s in d["sprints"].get(i["projeto_id"], [])):
                raise SystemExit(f"sprint {novo} não existe")
            if i["sprint"] != novo:
                mud.append(f"sprint: {i['sprint']} → {novo}"); i["sprint"] = novo
        if mud:
            self._registrar(d, id, mudancas=mud)
            self._gravar(d)
        return self._completo(d, i)

    def comentar(self, id, texto):
        d = self._ler()
        self._registrar(d, id, comentario=texto)
        self._gravar(d)

    def atividades_desde(self, desde):
        return [{"autor": a["autor"], "item": a["item"], "quando": a["quando"]}
                for a in self._ler()["atividades"] if a["quando"][:10] >= desde]
