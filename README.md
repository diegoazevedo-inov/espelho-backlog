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
   `op:ID`; no Jira, o rótulo `op-ID`, porque rótulo não aceita dois-pontos). O estado local de
   quem sincroniza acelera o trabalho, mas o marcador no item é a identidade de última instância:
   se a resposta de uma criação se perde, ou se o estado local some, nada duplica, porque antes de
   criar procura-se o marcador. Nunca se identifica um item pelo título. Exceção declarada: no
   Trello, que não tem épico, o épico vira uma etiqueta, e essa etiqueta é achada pelo nome.
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
Trello e GitHub Projects. Nos três, a segunda rodada não alterou nada, nenhuma duplicata apareceu
e as horas por sprint batem com a fonte; em dois deles (Trello e GitHub), isso valeu mesmo com a
rede caindo no meio da carga. Os
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
| `nucleo.py` | Configuração, credenciais e estado. Nomes da instalação (projetos, quadros, repositório, fuso, IDs de tipos e campos do Jira) vêm da configuração; o código só tem valores padrão, todos sobrescrevíveis na configuração: IDs de prioridade do Jira Cloud, fuso UTC, horários de início e fim (09:00 e 18:00) e iteração de 14 dias no GitHub |
| `adaptadores/` | Um arquivo por ferramenta: `openproject` (fonte), `jira`, `trello`, `github` (espelhos) e `arquivo`/`arquivo_espelho` (locais, para reproduzir sem conta) |
| `skill/SKILL.md` | Instruções para o sistema agêntico operar o método por conversa |
| `testes/` | As regras do método e o espelhamento local como testes, e as sabotagens que provam os testes. Os adaptadores das ferramentas reais dependem de conta e não têm teste automatizado; foram verificados contra as ferramentas no experimento |
| `config.exemplo.json` | Configuração do backlog fictício; serve de modelo para uma instalação real |

Trocar de ferramenta é escrever um adaptador com as mesmas funções. O método não muda. Um
adaptador fora deste repositório, de fonte ou de espelho, é indicado na configuração pelo nome do
módulo com ponto (`pacote.modulo`).

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

python3 -m unittest discover -s testes -v      # 42 testes
bash testes/sabotagens.sh                      # 32 defeitos plantados, todos pegos; 1 controle
```

As saídas indicadas valem para um clone novo. Para repetir do zero: `rm -rf estado`. Um
`config.json` local, se existir, tem precedência sobre o exemplo.

No espelho local, os testes conferem o conteúdo de cada cartão contra a fonte (coluna, título,
horas, sprint, épico pai e descrição), e não só a contagem. As travas da DoD e do WIP rodam duas
vezes: com a fonte local e com uma fonte externa que não herda dela (outro módulo, outro nome,
outra classe), para provar que as regras não dependem de qual implementação é a fonte. As
sabotagens S5 a S32 vêm de quatro rodadas de auditoria independente: defeitos que a auditoria plantou e os testes da época não pegavam, mais sabotagens
dirigidas a cada afirmação de comportamento destes textos. Cada uma virou um teste. O script exige que cada trecho
sabotado seja único no arquivo, para que nenhuma sabotagem atinja o lugar errado em silêncio.

O backlog fictício tem um segundo projeto fora do escopo do espelho. O teste de escopo procura no
espelho cada campo de texto dos itens desse projeto (título e descrição, não só o ID) e falha se
qualquer um aparecer.

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
