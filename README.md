# Espelho — processo interoperável: o método como código, refletido em quatro ferramentas

Equipes diferentes usam ferramentas diferentes. Quando o processo mora dentro de uma delas, ele
não atravessa as outras: cada quadro vira uma versão própria das regras, e a Definition of Done
de um não vale no outro. Este repositório trata o processo como código, fora de qualquer
ferramenta, e trata cada ferramenta como uma vitrine que recebe o reflexo de uma fonte da verdade.

O método é operado por sistemas agênticos em linguagem natural: quem trabalha conversa, o
agente executa as regras, e os quadros servem para quem precisa ver.

*Summary in English: [README.en.md](README.en.md).*

## A tese, em três regras

1. **Uma fonte da verdade.** Os itens vivem numa ferramenta; as demais são espelhos. Na etapa 1,
   nada volta de um espelho para a fonte.
2. **Identidade no próprio item.** Cada cartão espelhado carrega o ID de origem (marcador
   `op:ID`). Atualiza-se por esse ID, nunca por título, e nunca pela memória de quem sincroniza:
   se a resposta de uma criação se perde, o marcador no cartão impede a duplicata.
3. **As regras do método são código, não costume.** Item sem evidência não chega ao status final;
   coluna com WIP cheio recusa o próximo item; sprint acima da capacidade aparece como excesso.
   Essas regras valem igualmente para qualquer ferramenta, porque não dependem de nenhuma.

## Linhagem

Nada aqui é novo como ideia. É disciplina de engenharia de software aplicada à gestão do próprio
trabalho: fonte única da verdade, operações idempotentes, critério de aceitação como portão,
separação entre quem executa e quem verifica. O Scrum e o Kanban fornecem o vocabulário (Definition
of Ready, Definition of Done, limite de WIP, cerimônias); o código só torna essas regras
verificáveis em vez de dependentes de boa vontade.

## O que está demonstrado (etapa 1)

Um backlog real de 71 itens, em seis sprints, foi refletido a partir de um OpenProject em Jira,
Trello e GitHub Projects. Em cada espelho: a segunda rodada não alterou nada, nenhuma duplicata
apareceu mesmo com a rede caindo no meio da carga, e as horas por sprint batem com a fonte. Os
números, o custo de tradução de cada ferramenta e as falhas encontradas estão em
[RESULTADOS.md](RESULTADOS.md).

## O que ainda não está (etapa 2)

A volta: mudanças feitas em qualquer espelho subindo para a fonte, passando pelas mesmas regras —
um cartão arrastado para o status final sem evidência é revertido no espelho, com o motivo. A base
já existe: cada espelho guarda a cópia de referência de cada item, que permite saber qual lado
mudou sem depender do relógio de cada ferramenta.

## Componentes

| Arquivo | Papel |
|---|---|
| `sm.py` | O método como código: consultar, criar, mover, comentar, sprint, WIP e medição |
| `espelho.py` | Reflete a fonte nos espelhos, com escopo declarado e idempotência |
| `nucleo.py` | Configuração, credenciais e estado: o único lugar com nomes da instalação |
| `adaptadores/` | Um arquivo por ferramenta: `openproject` (fonte), `jira`, `trello`, `github` (espelhos) e `arquivo`/`arquivo_espelho` (locais, para reproduzir sem conta) |
| `skill/SKILL.md` | Instruções para o sistema agêntico operar o método por conversa |
| `testes/` | Cada afirmação deste README como teste, e as sabotagens que provam os testes |
| `config.exemplo.json` | Configuração do backlog fictício; serve de modelo para uma instalação real |

Trocar de ferramenta é escrever um adaptador com as mesmas funções. O método não muda.

## Reproduza

Requisito: Python 3 (testado em 3.13). Sem dependências externas, sem rede, sem conta.

```bash
python3 sm.py sprint S1                        # 23 h planejadas para 20 h: o excesso aparece
python3 sm.py mover 3 Concluído                # recusado: a DoD exige --evidencia
python3 sm.py mover 3 "Em execução"
python3 sm.py mover 4 "Em execução"
python3 sm.py mover 5 "Em execução"            # recusado: WIP 2/2
python3 espelho.py arquivo                     # reflete no espelho local
python3 espelho.py arquivo                     # segunda rodada: nada muda
python3 sm.py prova                            # quantas mudanças vieram do agente

python3 -m unittest discover -s testes -v      # 12 testes
bash testes/sabotagens.sh                      # 4 defeitos plantados, todos pegos; 1 controle
```

O backlog fictício tem um segundo projeto fora do escopo do espelho. O teste de escopo prova que
nada dele sai da fonte.

A medição de [RESULTADOS.md](RESULTADOS.md) foi feita sobre dados que não estão aqui. O comando
`sm prova` é o mesmo: reproduza o método e gere o seu número.

## Uso com ferramentas reais

1. Copie `config.exemplo.json` para um arquivo fora do repositório e aponte `ESPELHO_CONFIG` para
   ele. Defina a fonte, os espelhos (há modelos em `_exemplos_de_espelhos_reais`) e o
   `escopo_espelho`: só os projetos listados saem da fonte.
2. Guarde as credenciais em `~/.config/espelho-backlog/<ferramenta>.env` (ou no diretório de
   `ESPELHO_CREDENCIAIS`), com permissão 600. Para o GitHub, `gh auth login` basta.
3. Use, na fonte, uma conta própria do agente, sem perfil de administrador: o histórico da
   ferramenta passa a registrar o que foi feito por conversa, e a medição fica auditável.
4. `estado/` guarda a cópia de cada item espelhado, ou seja, o conteúdo do backlog. Está no
   `.gitignore` e não deve ser versionado.

Escopo é decisão de proteção de dados, não de conveniência: tudo que entra num espelho passa a
existir na infraestrutura daquela ferramenta. Itens com dados de terceiros ficam fora do escopo.

## Licença

Apache 2.0. Ver [LICENSE](LICENSE).
