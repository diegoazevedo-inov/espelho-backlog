"""Espelho em arquivo JSON local: simula uma ferramenta (quadro com colunas e cartões).

Serve para reproduzir o espelhamento sem conta em ferramenta nenhuma. A identidade de cada
cartão é o marcador op:ID dentro da descrição, e não o título nem o estado local.

Para reproduzir uma resposta perdida (criação aceita pela ferramenta, resposta não recebida),
defina ESPELHO_SIMULAR_RESPOSTA_PERDIDA com IDs separados por vírgula: o cartão é gravado e,
em seguida, a chamada falha com TimeoutError, como numa ferramenta real.
"""
import json
import os
import re

import nucleo


class Espelho:
    def __init__(self, cfg, conf):
        self.cfg = cfg
        self.arq = nucleo.caminho(cfg, conf["arquivo"])
        perdidas = os.environ.get("ESPELHO_SIMULAR_RESPOSTA_PERDIDA", "")
        self.perder = {int(x) for x in perdidas.split(",") if x.strip()}

    def _ler(self):
        if not os.path.exists(self.arq):
            return {"colunas": [], "cartoes": {}}
        with open(self.arq, encoding="utf-8") as f:
            return json.load(f)

    def _gravar(self, d):
        os.makedirs(os.path.dirname(self.arq), exist_ok=True)
        tmp = self.arq + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.arq)

    def preparar(self, projetos, sprints, meta):
        d = self._ler()
        d["colunas"] = nucleo.fluxo(self.cfg)
        self._gravar(d)
        self._indexar()

    def _indexar(self):
        self.por_op = {}
        for cid, c in self._ler()["cartoes"].items():
            m = re.search(r"op:(\d+)\s*$", c["descricao"])
            if m: self.por_op.setdefault(int(m.group(1)), []).append(cid)

    def upsert(self, c, ref, pai_ref):
        d = self._ler()
        cartao = {"titulo": c["assunto"] + (f" · {c['horas']:g}h" if c["horas"] else ""),
                  "coluna": c["status"], "tipo": c["tipo"], "sprint": c["sprint"],
                  "pai": pai_ref["cartao"] if pai_ref else None,
                  "descricao": f"Espelho da fonte da verdade: {c['op_url']}\n\n{c['descricao'] or ''}\n\nop:{c['op_id']}"}
        adotado = False
        if not ref and self.por_op.get(c["op_id"]):          # já existe (resposta perdida antes) → adota
            ref, adotado = {"cartao": self.por_op[c["op_id"]][0]}, True
        if ref:
            d["cartoes"][ref["cartao"]] = cartao
            self._gravar(d)
            return dict(ref, _adotado=True) if adotado else ref
        cid = f"c{len(d['cartoes']) + 1}"
        d["cartoes"][cid] = cartao
        self._gravar(d)
        if c["op_id"] in self.perder:                        # a ferramenta criou, a resposta se perdeu
            self.perder.discard(c["op_id"])
            raise TimeoutError(f"simulado: resposta perdida ao criar OP#{c['op_id']}")
        self.por_op[c["op_id"]] = [cid]
        return {"cartao": cid}
