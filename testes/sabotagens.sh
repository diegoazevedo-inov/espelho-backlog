#!/usr/bin/env bash
# Um teste só merece confiança depois de ver um defeito plantado dar vermelho.
# Cada sabotagem reproduz uma falha real (ou um risco real) do experimento, numa cópia
# temporária. Esperado: todas as sabotagens (S1–S11) FALHAM e o controle PASSA.
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

troca() {  # gera python que troca um trecho exato num arquivo (falha alto se o trecho sumiu)
  printf 'import sys\ns=open("%s").read()\nfor a,b in %s:\n    assert a in s, "trecho ausente: "+a\n    s=s.replace(a,b,1)\nopen("%s","w").write(s)\n' "$1" "$2" "$1"
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
sabotar "C0 controle: nenhuma mudança de comportamento" PASSA \
  "$(troca sm.py "[('# noqa: E402', '# noqa: E402 ')]")"

exit $falhas_esperadas
