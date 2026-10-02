#!/usr/bin/env bash
# Um teste só merece confiança depois de ver um defeito plantado dar vermelho.
# Cada sabotagem reproduz uma falha real (ou um risco real) do experimento, numa cópia
# temporária. Esperado: todas as sabotagens (S1–S32) FALHAM e o controle PASSA.
#
#     bash testes/sabotagens.sh
set -u
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
falhas_esperadas=0

sabotar() {  # $1 descrição · $2 esperado (FALHA|PASSA) · $3 script python que altera a cópia
  local T; T="$(mktemp -d)"; cp -r "$RAIZ/." "$T/"; rm -rf "$T/estado"
  if ! (cd "$T" && python3 -c "$3"); then
    printf 'ERRO %-62s a sabotagem não pôde ser aplicada (trecho mudou?)\n' "$1"; falhas_esperadas=1; rm -rf "$T"; return
  fi
  local saida; saida="$(cd "$T" && PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s testes 2>&1 | tail -1)"
  local obtido="PASSA"; [[ "$saida" == FAILED* ]] && obtido="FALHA"
  local ok="ok"; [[ "$obtido" != "$2" ]] && { ok="ERRO"; falhas_esperadas=1; }
  printf '%-4s %-62s esperado %-5s obtido %-5s (%s)\n' "$ok" "$1" "$2" "$obtido" "$saida"
  rm -rf "$T"
}

troca() {  # gera python que troca um trecho exato e ÚNICO num arquivo (falha alto se sumiu ou é ambíguo)
  printf 'import sys\ns=open("%s").read()\nfor a,b in %s:\n    assert s.count(a) == 1, ("trecho ausente: " if a not in s else "trecho ambíguo (%%d ocorrências): " %% s.count(a))+a\n    s=s.replace(a,b,1)\nopen("%s","w").write(s)\n' "$1" "$2" "$1"
}

sabotar "S1 WIP recebe número interno em vez do identificador" FALHA \
  "$(troca sm.py "[('cheio = checar_wip(f, i[\"projeto_id\"], destino, a.id)', 'cheio = checar_wip(f, str(i[\"id\"]), destino, a.id)')]")"
sabotar "S2 Definition of Done desligada" FALHA \
  "$(troca sm.py "[('if destino == feito and not (a.evidencia or \"\").strip():', 'if False:')]")"
sabotar "S3 identidade só pelo estado local, sem marcador" FALHA \
  "$(troca adaptadores/arquivo_espelho.py "[('if not ref and self.por_op.get(c[\"op_id\"]):', 'if False:')]")"
sabotar "S4 escopo ignorado (as duas camadas removidas)" FALHA \
  "$(troca espelho.py "[('itens = [canonico(i, fonte.url) for p in escopo for i in fonte.itens(p, abertos=False)]', 'itens = [canonico(i, fonte.url) for i in fonte.itens(None, abertos=False)]'), ('itens = [c for c in itens if c[\"projeto_id\"] in escopo]', 'pass')]")"
# Defeitos plantados pela auditoria independente que os testes da primeira versão não pegavam:
sabotar "S5 evidência só com espaços aceita pela DoD" FALHA \
  "$(troca sm.py "[('if destino == feito and not (a.evidencia or \"\").strip():', 'if destino == feito and not a.evidencia:')]")"
sabotar "S6 status fora do hash: mudança de coluna não chega ao espelho" FALHA \
  "$(troca espelho.py "[('json.dumps(c, sort_keys=True', 'json.dumps({k: v for k, v in c.items() if k != \"status\"}, sort_keys=True')]")"
sabotar "S7 espelho diz que atualiza mas não grava o cartão" FALHA \
  "$(troca adaptadores/arquivo_espelho.py "[('            d[\"cartoes\"][ref[\"cartao\"]] = cartao', '            pass')]")"
sabotar "S8 espelho grava sempre a primeira coluna" FALHA \
  "$(troca adaptadores/arquivo_espelho.py "[('\"coluna\": c[\"status\"]', '\"coluna\": nucleo.fluxo(self.cfg)[0]')]")"
sabotar "S9 medição atribui toda mudança ao agente" FALHA \
  "$(troca sm.py "[('ag = por.get(agente, 0)', 'ag = len(acts)')]")"
sabotar "S10 WIP passa a contar épicos" FALHA \
  "$(troca sm.py "[('ocup = [i for i in f.itens(projeto, [status]) if i[\"id\"] != ignorar_id and i[\"tipo\"] != \"Épico\"]', 'ocup = [i for i in f.itens(projeto, [status]) if i[\"id\"] != ignorar_id]')]")"
sabotar "S11 descrição de item fora do escopo vaza para o espelho" FALHA \
  "$(troca espelho.py "[('    itens = [c for c in itens if c[\"projeto_id\"] in escopo]', '    itens = [c for c in itens if c[\"projeto_id\"] in escopo]; itens[0][\"descricao\"] = (itens[0][\"descricao\"] or \"\") + \" \".join(i[\"descricao\"] for i in fonte.itens(None, abertos=False) if i[\"projeto_id\"] not in escopo)')]")"
# Defeitos da segunda rodada da auditoria (N1–N6) e a contagem de adoções (E1):
sabotar "S12 --forcar também desliga a DoD" FALHA \
  "$(troca sm.py "[('if destino == feito and not (a.evidencia or \"\").strip():', 'if destino == feito and not (a.evidencia or \"\").strip() and not a.forcar:')]")"
sabotar "S13 planejado da sprint exclui itens concluídos" FALHA \
  "$(troca sm.py "[('get(a.projeto)\\n    total = sum(i[\"horas\"] or 0 for i in its)', 'get(a.projeto)\\n    total = sum(i[\"horas\"] or 0 for i in its if i[\"status\"] != feito)')]")"
sabotar "S14 itens concluídos deixam de ser espelhados" FALHA \
  "$(troca espelho.py "[('for p in escopo for i in fonte.itens(p, abertos=False)]', 'for p in escopo for i in fonte.itens(p, abertos=True)]')]")"
sabotar "S15 cartão nunca aponta o épico pai" FALHA \
  "$(troca adaptadores/arquivo_espelho.py "[('\"pai\": pai_ref[\"cartao\"] if pai_ref else None', '\"pai\": None')]")"
sabotar "S16 corpo da descrição não chega ao cartão" FALHA \
  "$(troca adaptadores/arquivo_espelho.py "[(\"{c['descricao'] or ''}\", \"\")]")"
sabotar "S17 medição ignora o período (--desde)" FALHA \
  "$(troca adaptadores/arquivo.py "[('for a in self._ler()[\"atividades\"] if a[\"quando\"][:10] >= desde]', 'for a in self._ler()[\"atividades\"]]')]")"
sabotar "S18 adoção pelo marcador contada como criação" FALHA \
  "$(troca espelho.py "[('elif not a.simular and adotado: adotados += 1', 'elif False: adotados += 1')]")"
# Sabotagens dirigidas a afirmações dos textos (terceira rodada da auditoria):
sabotar "S19 DoD: item movido antes da checagem (recusa, mas conclui)" FALHA \
  "$(troca sm.py "[('    if destino == feito and not (a.evidencia or \"\").strip():', '    if (f.atualizar(a.id, status=destino) or True) and destino == feito and not (a.evidencia or \"\").strip():')]")"
sabotar "S20 WIP só vale para a coluna Em execução" FALHA \
  "$(troca sm.py "[('lim = M.get(\"wip\", {}).get(projeto, {}).get(status)', 'lim = M.get(\"wip\", {}).get(projeto, {}).get(status) if status == \"Em execução\" else None')]")"
sabotar "S21 DoD só vale quando a fonte se chama arquivo" FALHA \
  "$(troca sm.py "[('    if destino == feito and not (a.evidencia or \"\").strip():', '    if f.nome == \"arquivo\" and destino == feito and not (a.evidencia or \"\").strip():')]")"
sabotar "S22 o espelho escreve de volta na fonte" FALHA \
  "$(troca espelho.py "[('ref = esp.upsert(c, reg[\"ref\"] if reg else None, pai_ref)', 'ref = esp.upsert(c, reg[\"ref\"] if reg else None, pai_ref); fonte.comentar(c[\"op_id\"], \"espelhado\")')]")"
sabotar "S23 adoção pelo título em vez do marcador" FALHA \
  "$(troca adaptadores/arquivo_espelho.py "[('if not ref and self.por_op.get(c[\"op_id\"]):', 'if not ref and any(v[\"titulo\"].split(\" · \")[0] == c[\"assunto\"] for v in d[\"cartoes\"].values()):'), ('ref, adotado = {\"cartao\": self.por_op[c[\"op_id\"]][0]}, True', 'ref, adotado = {\"cartao\": next(k for k, v in d[\"cartoes\"].items() if v[\"titulo\"].split(\" · \")[0] == c[\"assunto\"])}, True')]")"
sabotar "S24 cópia de referência (snap) não é gravada" FALHA \
  "$(troca espelho.py "[('\"hash\": h, \"snap\": c}', '\"hash\": h, \"snap\": None}')]")"
sabotar "S25 config.json local ignorado" FALHA \
  "$(troca nucleo.py "[('caminho = local if os.path.exists(local) else os.path.join(BASE, \"config.exemplo.json\")', 'caminho = os.path.join(BASE, \"config.exemplo.json\")')]")"
sabotar "S26 ESPELHO_CREDENCIAIS ignorada" FALHA \
  "$(troca nucleo.py "[('os.path.expanduser(os.environ.get(\"ESPELHO_CREDENCIAIS\", \"~/.config/espelho-backlog\"))', 'os.path.expanduser(\"~/.config/espelho-backlog\")')]")"
# Sabotagens dirigidas da quarta rodada da auditoria:
sabotar "S27 identidade pelo título exibido do cartão" FALHA \
  "$(troca adaptadores/arquivo_espelho.py "[('if not ref and self.por_op.get(c[\"op_id\"]):', 'if not ref and any(v[\"titulo\"] == cartao[\"titulo\"] for v in d[\"cartoes\"].values()):'), ('ref, adotado = {\"cartao\": self.por_op[c[\"op_id\"]][0]}, True', 'ref, adotado = {\"cartao\": next(k for k, v in d[\"cartoes\"].items() if v[\"titulo\"] == cartao[\"titulo\"])}, True')]")"
sabotar "S28 DoD só vale para a implementação local da fonte" FALHA \
  "$(troca sm.py "[('    if destino == feito and not (a.evidencia or \"\").strip():', '    if isinstance(f, __import__(\"adaptadores.arquivo\", fromlist=[\"Fonte\"]).Fonte) and destino == feito and not (a.evidencia or \"\").strip():')]")"
sabotar "S29 WIP só vale para a implementação local da fonte" FALHA \
  "$(troca sm.py "[('lim = M.get(\"wip\", {}).get(projeto, {}).get(status)', 'lim = M.get(\"wip\", {}).get(projeto, {}).get(status) if isinstance(f, __import__(\"adaptadores.arquivo\", fromlist=[\"Fonte\"]).Fonte) else None')]")"
sabotar "S30 espelho externo por nome com ponto ignorado" FALHA \
  "$(troca nucleo.py "[('return _modulo(conf[\"adaptador\"]).Espelho(cfg, conf)', 'return importlib.import_module(\"adaptadores.\" + conf[\"adaptador\"]).Espelho(cfg, conf)')]")"
sabotar "S31 sm wip não conta a ocupação" FALHA \
  "$(troca sm.py "[('n = len([i for i in f.itens(proj, [st]) if i[\"tipo\"] != \"Épico\"])', 'n = 0')]")"
sabotar "S32 sm itens não lista nada" FALHA \
  "$(troca sm.py "[('for i in its: print(linha(i))', 'for i in []: print(linha(i))')]")"
sabotar "C0 controle: nenhuma mudança de comportamento" PASSA \
  "$(troca sm.py "[('# noqa: E402', '# noqa: E402 ')]")"

exit $falhas_esperadas
