# Espelho Backlog

[English summary](README.en.md)

O processo de trabalho como código, fora de qualquer ferramenta: a ferramenta volta a ser meio.
Uma delas guarda a fonte da verdade, e as outras recebem o reflexo dela, cada uma servindo de
vitrine a um público. O método é operado por sistemas agênticos em linguagem natural: quem
trabalha conversa, o sistema aplica as regras, e os quadros servem para quem precisa acompanhar.

## O problema

A ferramenta de gestão tende a deixar de ser meio e passar a ser fim. O processo vira o que a
ferramenta permite configurar, o trabalho inclui manter o quadro em dia, e trocar de ferramenta
significa refazer o processo. As regras do método (Definition of Ready, Definition of Done,
limite de WIP, capacidade) passam a depender de como cada ferramenta foi configurada. Nenhuma
das ferramentas testadas, na configuração padrão, impede que um item seja concluído sem
evidência ou que uma coluna passe do limite de WIP.

Os públicos, por outro lado, são vários: níveis diferentes dentro da equipe e, principalmente,
clientes, cada um com a sua forma de acompanhar o trabalho. O quadro deveria ser a vitrine de
cada público, e não o lugar onde o processo mora.

## Princípios

**Uma fonte da verdade.** Os itens vivem numa ferramenta; as demais são espelhos, e nada volta
de um espelho para a fonte. Cada espelho declara o seu escopo, e o quadro de um cliente recebe
só o projeto do cliente.

**A identidade está no próprio item.** Cada cartão espelhado carrega o ID de origem. Um item
nunca é reconhecido pelo título, e nada duplica, mesmo quando a resposta de uma criação não
chega. Única exceção: no Trello, que não tem épico, o épico vira uma etiqueta achada pelo nome
(ver Detalhes).

**As regras são código, não costume.** Item sem evidência não chega ao status final; coluna com
WIP cheio recusa o próximo item; sprint acima da capacidade mostra o excesso. As regras valem
para qualquer ferramenta, porque não dependem de nenhuma. A Definition of Ready é aplicada pela
skill, na conversa, e não pelo código.

**Defeito plantado antes de confiar.** Cada regra tem um teste, e cada teste é provado por uma
sabotagem: o defeito é plantado de propósito, e o teste precisa reprovar. O próprio script de
sabotagens confere que nenhum teste fica sem ser derrubado por alguma delas.

## Linhagem

Nada aqui é novo como ideia. É disciplina de engenharia de software aplicada à gestão do próprio
trabalho: fonte única da verdade, operações idempotentes, critério de aceitação como portão,
separação entre quem executa e quem verifica. O Scrum e o Kanban fornecem o vocabulário
(Definition of Ready, Definition of Done, limite de WIP, cerimônias). O desenvolvimento
assistido por IA retoma hoje parte dessa disciplina, com nomes como spec-driven development. O
código só torna as regras verificáveis: a regra é checada no momento da mudança, e não lembrada
depois, na revisão.

## O que tem aqui

| Parte | Para quê | Onde |
|---|---|---|
| **Método** | Consultar, criar, mover e comentar itens; sprint, WIP e medição | [sm.py](sm.py) |
| **Espelho** | Refletir a fonte nos espelhos, com escopo próprio e obrigatório em cada um | [espelho.py](espelho.py) |
| **Adaptadores** | Um por ferramenta: OpenProject, Jira, Trello, GitHub Projects e dois locais. Trocar de ferramenta é escrever outro | [adaptadores/](adaptadores/) |
| **Skill** | Instruções para o sistema agêntico operar o método por conversa | [skill/](skill/) |
| **Testes** | As regras como testes, e as sabotagens que provam os testes | [testes/](testes/) |

## Resultados

Um backlog real de 71 itens, em seis sprints, refletido a partir de um OpenProject em Jira,
Trello e GitHub Projects:

- **Fidelidade:** os 71 itens nos três espelhos (no Trello, os 11 épicos como etiquetas), com as
  horas por sprint iguais às da fonte.
- **Idempotência:** a segunda execução não alterou nada em nenhum dos três.
- **Duplicatas:** zero.
- **Uso:** de 28/09 a 02/10/2026, as 20 mudanças registradas na fonte foram feitas por conversa,
  nenhuma pela tela. A mesma medição registra que não houve progresso da sprint no período.

Antes da publicação, rodadas sucessivas de auditoria independente, 50 testes e 50 defeitos
plantados, todos detectados, com cada teste derrubado por pelo menos um deles. Números, custo de
tradução de cada ferramenta e defeitos encontrados: [RESULTADOS.md](RESULTADOS.md).

## Limitação atual

O reflexo é de mão única: mudanças feitas num espelho ainda não retornam à fonte. A base para o
caminho inverso está implementada: cada espelho mantém uma cópia de referência de cada item, o
que permite determinar qual lado foi alterado sem depender do relógio de cada ferramenta.

## Reproduza

Python 3 (testado em 3.13). Sem dependências, sem rede, sem conta.

```bash
python3 sm.py sprint S1                        # 23 h planejadas para 20 h: o excesso aparece
python3 sm.py mover 3 Concluído                # recusado: a DoD exige --evidencia
python3 sm.py mover 3 "Em execução"
python3 sm.py mover 4 "Em execução"
python3 sm.py mover 5 "Em execução"            # recusado: WIP 2/2
python3 espelho.py arquivo                     # reflete no espelho local
python3 espelho.py arquivo                     # segunda execução: nada muda
python3 sm.py prova                            # quantas mudanças vieram do sistema agêntico

python3 -m unittest discover -s testes -v      # 50 testes
bash testes/sabotagens.sh                      # 50 defeitos plantados, todos detectados; 1 controle
```

As saídas indicadas valem para um clone novo; para repetir do zero, `rm -rf estado`. A medição
de [RESULTADOS.md](RESULTADOS.md) foi feita sobre dados que não estão aqui. O comando é o mesmo:
reproduza o método e gere o seu número.

## Uso com ferramentas reais

1. Copie `config.exemplo.json` para fora do repositório e aponte `ESPELHO_CONFIG` para ele.
   Defina a fonte e os espelhos. Cada espelho declara o seu escopo (`escopo`), e só os projetos
   listados chegam àquele quadro; espelho sem escopo é recusado antes de qualquer escrita.
2. Guarde as credenciais em `~/.config/espelho-backlog/<ferramenta>.env`, com permissão 600.
   Para o GitHub, `gh auth login` basta.
3. Use, na fonte, uma conta própria do sistema agêntico, sem perfil de administrador. O
   histórico da ferramenta passa a registrar o que foi feito por conversa.

Escopo é decisão de proteção de dados, não de conveniência: tudo que entra num espelho passa a
existir na infraestrutura daquela ferramenta. Itens com dados de terceiros ficam fora do escopo.
Como cada quadro é a vitrine de um público, cada um recebe só o escopo declarado para ele: o
quadro de um cliente, só o projeto do cliente. Reduzir o escopo de um espelho não remove o que já
foi espelhado: cartões de projetos retirados do escopo precisam ser removidos na ferramenta.

## Detalhes

**Identidade.** O marcador é `op:ID` na descrição do cartão; no Jira, o rótulo `op-ID`, porque
rótulo não aceita dois-pontos. O estado local de quem sincroniza acelera o trabalho, mas o
marcador é a identidade de última instância: antes de criar, procura-se o marcador, e o que já
existe é adotado. Exceção declarada: no Trello, que não tem épico, o épico vira uma etiqueta,
achada pelo nome.

**Configuração.** Nomes da instalação (projetos, quadros, repositório, fuso, IDs de tipos e
campos do Jira) vêm da configuração. O código só tem valores padrão, todos sobrescrevíveis: IDs
de prioridade do Jira Cloud, fuso UTC, horários de início e fim (09:00 e 18:00) e iteração de 14
dias no GitHub. As credenciais podem ficar em outro diretório, indicado por
`ESPELHO_CREDENCIAIS`, e um `config.json` local tem precedência sobre o exemplo. Um adaptador
fora deste repositório, de fonte ou de espelho, é indicado pelo nome do módulo com ponto
(`pacote.modulo`). O diretório `estado/` guarda a cópia de cada item espelhado, ou seja, o
conteúdo do backlog: está no `.gitignore` e não deve ser versionado.

**Testes.** No espelho local, os testes conferem o conteúdo de cada cartão contra a fonte
(coluna, título, horas, sprint, épico pai e descrição), e não só a contagem. As travas da DoD e
do WIP rodam também com uma fonte externa que não herda da local e só expõe a interface pública
dos adaptadores, para provar que as regras não dependem da implementação. O backlog fictício tem
um projeto fora do escopo, e o teste de escopo procura no espelho cada campo de texto dos itens
dele. Outro teste usa dois espelhos com escopos diferentes, um por público, e confere que cada
quadro recebe só o seu: os itens, os projetos e as sprints. Com uma fonte externa que devolve
também itens de outros projetos, o quadro do cliente continua recebendo só o seu. Reduzir o
escopo e espelhar de novo mantém no quadro os cartões que já estavam lá. As sabotagens S5 a S50
vêm das rodadas de auditoria: defeitos que a auditoria plantou e os testes da época não
detectavam, mais sabotagens dirigidas a cada afirmação de comportamento deste texto. O script
exige que cada trecho sabotado seja único no arquivo, para que uma sabotagem não altere uma
ocorrência repetida em outro ponto do código e passe sem detecção, e verifica que todo teste é
derrubado por pelo menos uma sabotagem. Os adaptadores das ferramentas reais dependem de conta e
não têm teste automatizado; foram verificados contra as ferramentas no experimento.

## Licença

Apache 2.0. Veja [LICENSE](LICENSE).
