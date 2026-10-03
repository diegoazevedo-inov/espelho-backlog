#!/usr/bin/env python3
"""espelho — a fonte da verdade refletida em outras ferramentas, em mão única.

Idempotente: cada cartão carrega o ID da fonte (marcador op:ID) e é atualizado por esse ID,
nunca por título. O estado de cada espelho (estado/<espelho>.json) guarda a referência e uma
cópia de referência do item ('snap'), base para um caminho de volta, que precisa saber QUAL lado mudou.
Escopo: cada espelho declara o seu ("escopo" na configuração do espelho), porque cada quadro é a
vitrine de um público. Espelho sem escopo declarado é recusado antes de qualquer escrita.
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import nucleo  # noqa: E402

CAMPOS = ["assunto", "descricao", "tipo", "status", "prioridade", "projeto_id", "pai_id",
          "sprint", "bucket", "horas", "inicio", "fim"]
ORDEM = {"Épico": 0, "Marco": 1, "Tarefa": 2}          # pais antes dos filhos


def canonico(i, url):
    c = {k: i.get(k) for k in CAMPOS}
    c["op_id"] = i["id"]
    c["op_url"] = f"{url}/wp/{i['id']}" if url.startswith("http") else f"{url}#{i['id']}"
    return c


def carregar(cfg, nome):
    p = os.path.join(nucleo.dir_estado(cfg), f"{nome}.json")
    if not os.path.exists(p): return {}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def salvar(cfg, nome, est):
    p = os.path.join(nucleo.dir_estado(cfg), f"{nome}.json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(est, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)


def escopo_do_espelho(cfg, nome):
    """Escopo obrigatório e próprio de cada espelho: nenhum quadro recebe itens sem que se diga quais."""
    if "escopo_espelho" in cfg:
        raise SystemExit("'escopo_espelho' global não é aceito: declare 'escopo' em cada espelho")
    conf = cfg["espelhos"].get(nome)
    if conf is None:
        raise SystemExit(f"espelho '{nome}' não está na configuração")
    escopo = conf.get("escopo")
    if escopo is not None and not (isinstance(escopo, list) and all(isinstance(p, str) and p for p in escopo)):
        raise SystemExit(f"espelho '{nome}': 'escopo' deve ser uma lista de identificadores de projeto")
    if not escopo:
        raise SystemExit(f"espelho '{nome}' sem 'escopo' declarado: nenhum quadro recebe itens sem "
                         "que se diga quais projetos")
    return list(escopo)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("espelhos", nargs="+", help="nomes definidos em 'espelhos' na configuração")
    ap.add_argument("--simular", action="store_true", help="mostra o que faria, sem escrever")
    a = ap.parse_args(argv)
    cfg = nucleo.carregar_config()
    escopos = {nome: escopo_do_espelho(cfg, nome) for nome in a.espelhos}   # valida tudo antes de escrever
    fonte = nucleo.fonte(cfg)
    for nome in a.espelhos:
        escopo = escopos[nome]
        itens = [canonico(i, fonte.url) for p in escopo for i in fonte.itens(p, abertos=False)]
        itens = [c for c in itens if c["projeto_id"] in escopo]     # defesa extra: nada fora do escopo
        itens.sort(key=lambda c: (ORDEM.get(c["tipo"], 9), c["op_id"]))
        sprints = {p: fonte.sprints(p) for p in escopo}
        esp = None if a.simular else nucleo.espelho(cfg, nome)
        est = carregar(cfg, nome)
        if not a.simular:
            esp.preparar(escopo, sprints, est.setdefault("_meta", {}))
            salvar(cfg, nome, est)
        criados = atualizados = iguais = adotados = 0
        for c in itens:
            h = hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
            reg = est.get(str(c["op_id"]))
            if reg and reg["hash"] == h:
                iguais += 1
                continue
            if a.simular:
                print(f"  {'atualizar' if reg else 'criar':<9} OP#{c['op_id']} {c['assunto'][:60]}")
            else:
                pai_ref = est.get(str(c["pai_id"]), {}).get("ref") if c["pai_id"] else None
                ref = esp.upsert(c, reg["ref"] if reg else None, pai_ref)
                adotado = isinstance(ref, dict) and bool(ref.pop("_adotado", False))
                est[str(c["op_id"])] = {"ref": ref, "hash": h, "snap": c}
                salvar(cfg, nome, est)                         # grava a cada item: queda não duplica
            if reg: atualizados += 1
            elif not a.simular and adotado: adotados += 1      # já existia na ferramenta: achado pelo marcador
            else: criados += 1
        print(f"{nome}{' (SIMULAÇÃO)' if a.simular else ''}: {criados} criados, {atualizados} atualizados, "
              f"{iguais} sem mudança, {adotados} adotados pelo marcador (total {len(itens)})")


if __name__ == "__main__":
    main()
