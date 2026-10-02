#!/usr/bin/env python3
"""sm — o método Scrum/Kanban como código, operado por linguagem natural via sistema agêntico.

O MÉTODO mora aqui: Definition of Done com evidência, limite de WIP, capacidade da sprint.
A FERRAMENTA é um adaptador trocável (adaptadores/). As regras valem para qualquer uma.
"""
import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import nucleo  # noqa: E402

CFG = nucleo.carregar_config()
M = CFG["metodo"]


def linha(i):
    h = f" {i['horas']:g}h" if i.get("horas") else ""
    s = f" [{i['sprint']}]" if i.get("sprint") else (f" [{i['bucket']}]" if i.get("bucket") else "")
    return f"#{i['id']:<4} {i['status']:<13} {i['prioridade'][:1]} {i['tipo'][:6]:<6}{s}{h}  {i['assunto']}"


def cmd_projetos(f, a):
    for p in f.projetos():
        print(f"{p['id']:<26} {p['nome']}" + (f"   (em {p['pai']})" if p.get("pai") else ""))


def cmd_itens(f, a):
    its = f.itens(a.projeto, a.status, a.tipo, a.sprint, a.busca, abertos=not a.todos)
    for i in its: print(linha(i))
    total = sum(i["horas"] or 0 for i in its)
    print(f"— {len(its)} itens" + (f", {total:g}h estimadas" if total else ""))


def cmd_ver(f, a):
    i = f.item(a.id)
    print(linha(i))
    print(f"projeto: {i['projeto']} · pai: {i['pai'] or '—'} · datas: {i['inicio'] or '—'} → {i['fim'] or '—'}")
    if i.get("descricao"): print("\n" + i["descricao"])
    cs = f.comentarios(a.id, 8)
    if cs:
        print("\nhistórico recente:")
        for c in cs:
            o = c.get("comentario") or "; ".join(x for x in c.get("mudancas", []) if x)
            if o: print(f"  {c['quando'][:16].replace('T', ' ')} {c['autor']}: {o}")


def cmd_criar(f, a):
    print("criado: " + linha(f.criar(a.projeto, a.assunto, a.tipo, a.desc or "", a.pai, a.horas, a.prioridade, a.sprint)))


def checar_wip(f, projeto, status, ignorar_id=None):
    """Regra de WIP. Recebe o IDENTIFICADOR do projeto — o mesmo usado na configuração."""
    lim = M.get("wip", {}).get(projeto, {}).get(status)
    if not lim: return None
    ocup = [i for i in f.itens(projeto, [status]) if i["id"] != ignorar_id and i["tipo"] != "Épico"]
    return (lim, ocup) if len(ocup) >= lim else None


def cmd_mover(f, a):
    i = f.item(a.id)
    destino, fluxo, feito = a.status, nucleo.fluxo(CFG), nucleo.status_feito(CFG)
    if destino not in fluxo:
        raise SystemExit(f"status inválido. Use: {', '.join(fluxo)}")
    if destino == feito and not a.evidencia:
        raise SystemExit(f"DoD: '{feito}' exige --evidencia (saída de comando, link, captura, número). "
                         "Critério verificado no artefato, não no relato.")
    cheio = checar_wip(f, i["projeto_id"], destino, a.id)
    if cheio and not a.forcar:
        lim, ocup = cheio
        raise SystemExit(f"WIP: '{destino}' já tem {len(ocup)}/{lim}:\n" + "\n".join("  " + linha(x) for x in ocup) +
                         "\nTermine ou devolva um antes (ou --forcar, que fica registrado).")
    nota = []
    if a.evidencia: nota.append(f"Evidência (DoD): {a.evidencia}")
    if a.ressalva: nota.append(f"Ressalvas: {a.ressalva}")
    if cheio and a.forcar: nota.append(f"WIP excedido conscientemente ({destino}).")
    if a.nota: nota.append(a.nota)
    novo = f.atualizar(a.id, status=destino)
    if nota: f.comentar(a.id, "\n\n".join(nota))
    print(f"{i['status']} → {destino}: " + linha(novo))


def cmd_comentar(f, a):
    f.comentar(a.id, a.texto)
    print(f"comentado em #{a.id}")


def cmd_editar(f, a):
    print("atualizado: " + linha(f.atualizar(a.id, assunto=a.assunto, horas=a.horas, prioridade=a.prioridade,
                                              sprint=a.sprint, pai=a.pai)))


def sprint_atual(f, projeto, nome=None):
    ss = f.sprints(projeto)
    if nome: return next((s for s in ss if s["nome"] == nome), None)
    hoje = dt.date.today().isoformat()
    ativas = [s for s in ss if s["inicio"] and s["inicio"] <= hoje <= (s["fim"] or hoje)]
    futuras = sorted([s for s in ss if s["inicio"] and s["inicio"] > hoje], key=lambda s: s["inicio"])
    passadas = sorted([s for s in ss if s["fim"] and s["fim"] < hoje], key=lambda s: s["fim"], reverse=True)
    return (ativas or futuras or passadas or [None])[0]


def cmd_sprint(f, a):
    s = sprint_atual(f, a.projeto, a.nome)
    if not s: raise SystemExit("nenhuma sprint encontrada")
    feito = nucleo.status_feito(CFG)
    its = [i for i in f.itens(a.projeto, sprint=s["nome"], abertos=False) if i["tipo"] != "Épico"]
    cap = M.get("capacidade_horas_sprint", {}).get(a.projeto)
    total = sum(i["horas"] or 0 for i in its)
    concluido = sum(i["horas"] or 0 for i in its if i["status"] == feito)
    hoje, ini, fim = dt.date.today(), dt.date.fromisoformat(s["inicio"]), dt.date.fromisoformat(s["fim"])
    uteis = sum(1 for k in range((fim - max(hoje, ini)).days + 1) if (max(hoje, ini) + dt.timedelta(k)).weekday() < 5) if hoje <= fim else 0
    print(f"{s['nome']}  {ini:%d/%m} → {fim:%d/%m}  · {uteis} dias úteis restantes" + ("  (ainda não começou)" if hoje < ini else ""))
    excesso = f"  EXCEDE em {total - cap:g}h" if cap and total > cap else ""
    print(f"planejado {total:g}h" + (f" de {cap}h de capacidade{excesso}" if cap else "") + f" · concluído {concluido:g}h")
    for st in nucleo.fluxo(CFG):
        g = [i for i in its if i["status"] == st]
        if g:
            lim = M.get("wip", {}).get(a.projeto, {}).get(st)
            print(f"\n{st} ({len(g)}{'/' + str(lim) if lim else ''}):")
            for i in g: print("  " + linha(i))


def cmd_wip(f, a):
    for proj, lims in M.get("wip", {}).items():
        if a.projeto and proj != a.projeto: continue
        for st, lim in lims.items():
            n = len([i for i in f.itens(proj, [st]) if i["tipo"] != "Épico"])
            print(f"{proj}: {st} {n}/{lim}" + ("  ESTOURADO" if n > lim else ""))


def cmd_prova(f, a):
    acts = f.atividades_desde(a.desde)
    por = {}
    for x in acts: por[x["autor"]] = por.get(x["autor"], 0) + 1
    tot = len(acts) or 1
    agente = M.get("autor_agente", "Agente")
    ag = por.get(agente, 0)
    print(f"Desde {a.desde}: {len(acts)} mudanças em {len({x['item'] for x in acts})} itens (fonte: {f.nome})")
    for k, v in sorted(por.items(), key=lambda kv: -kv[1]): print(f"  {k:<32} {v:>4}  {100 * v / tot:5.1f}%")
    print(f"\n→ {100 * ag / tot:.1f}% por linguagem natural (autor '{agente}'); o restante, uso direto da ferramenta.")


def main(argv=None):
    p = argparse.ArgumentParser(prog="sm", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    padrao = M.get("projeto_padrao")
    sp.add_parser("projetos").set_defaults(fn=cmd_projetos)
    x = sp.add_parser("itens"); x.add_argument("-p", "--projeto"); x.add_argument("--status", nargs="+"); x.add_argument("--tipo")
    x.add_argument("--sprint"); x.add_argument("--busca"); x.add_argument("--todos", action="store_true", help="inclui concluídos"); x.set_defaults(fn=cmd_itens)
    x = sp.add_parser("ver"); x.add_argument("id", type=int); x.set_defaults(fn=cmd_ver)
    x = sp.add_parser("criar"); x.add_argument("-p", "--projeto", default=padrao); x.add_argument("assunto"); x.add_argument("--tipo", default="Tarefa")
    x.add_argument("--desc"); x.add_argument("--pai", type=int); x.add_argument("--horas", type=float)
    x.add_argument("--prioridade", default="Normal"); x.add_argument("--sprint"); x.set_defaults(fn=cmd_criar)
    x = sp.add_parser("mover"); x.add_argument("id", type=int); x.add_argument("status"); x.add_argument("--evidencia"); x.add_argument("--ressalva")
    x.add_argument("--nota"); x.add_argument("--forcar", action="store_true"); x.set_defaults(fn=cmd_mover)
    x = sp.add_parser("comentar"); x.add_argument("id", type=int); x.add_argument("texto"); x.set_defaults(fn=cmd_comentar)
    x = sp.add_parser("editar"); x.add_argument("id", type=int); x.add_argument("--assunto"); x.add_argument("--horas", type=float)
    x.add_argument("--prioridade"); x.add_argument("--sprint", help="nome da sprint, ou '' para tirar"); x.add_argument("--pai", type=int); x.set_defaults(fn=cmd_editar)
    x = sp.add_parser("sprint"); x.add_argument("-p", "--projeto", default=padrao); x.add_argument("nome", nargs="?"); x.set_defaults(fn=cmd_sprint)
    x = sp.add_parser("wip"); x.add_argument("-p", "--projeto"); x.set_defaults(fn=cmd_wip)
    x = sp.add_parser("prova"); x.add_argument("--desde", default="2000-01-01"); x.set_defaults(fn=cmd_prova)
    a = p.parse_args(argv)
    a.fn(nucleo.fonte(CFG), a)


if __name__ == "__main__":
    main()
