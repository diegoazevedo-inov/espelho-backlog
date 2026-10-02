# Espelho Backlog

[English summary](README.en.md)

Um processo de trabalho que atravessa ferramentas diferentes sem mudar de regra. O
processo é código, fora de qualquer ferramenta; uma ferramenta guarda a fonte da verdade,
e as outras recebem o reflexo dela. O método é operado por sistemas agênticos em linguagem
natural: quem trabalha conversa, o sistema executa as regras, e os quadros servem para
quem precisa ver.

## O problema

Equipes diferentes usam ferramentas diferentes. Quando o processo mora dentro de uma delas,
ele não atravessa as outras: cada quadro vira uma versão própria das regras, e a Definition
of Done de um não vale no outro. Nenhuma das ferramentas testadas, na configuração padrão,
impede que um item seja concluído sem evidência ou que uma coluna passe do limite de WIP.

## Princípios

**Uma fonte da verdade.** Os itens vivem numa ferramenta; as demais são espelhos, e nada
volta de um espelho para a fonte.

**A identidade está no próprio item.** Cada cartão espelhado carrega o ID de origem. Um
item nunca é reconhecido pelo título, e nada duplica, mesmo quando a rede cai no meio da
sincronização.

**As regras são código, não costume.** Item sem evidência não chega ao status final; coluna
com WIP cheio recusa o próximo item; sprint acima da capacidade mostra o excesso. As regras
valem para qualquer ferramenta, porque não dependem de nenhuma.

**Defeito plantado antes de confiar.** Cada regra tem um teste, e cada teste é provado por
uma sabotagem: o defeito é plantado de propósito, e o teste precisa reprovar.

## Linhagem

Nada aqui é novo como ideia. É disciplina de engenharia de software aplicada à gestão do
próprio trabalho: fonte única da verdade, operações idempotentes, critério de aceitação
como portão, separação entre quem executa e quem verifica. O Scrum e o Kanban fornecem o
vocabulário (Definition of Ready, Definition of Done, limite de WIP, cerimônias). O
desenvolvimento assistido por IA vem redescobrindo parte dessa disciplina, nem sempre com o
que a tornava útil. O código só torna as regras verificáveis: a regra é checada no momento
da mudança, e não lembrada depois, na revisão.

## O que tem aqui

| Parte | Para quê | Onde |
|---|---|---|
| **Método** | Consultar, criar, mover e comentar itens; sprint, WIP e medição | [sm.py](sm.py) |
| **Espelho** | Refletir a fonte nos espelhos, com escopo declarado | [espelho.py](espelho.py) |
| **Adaptadores** | Um por ferramenta: OpenProject, Jira, Trello, GitHub Projects e dois locais. Trocar de ferramenta é escrever outro | [adaptadores/](adaptadores/) |
| **Skill** | Instruções para o sistema agêntico operar o método por conversa | [skill/](skill/) |
| **Testes** | As regras como testes, e as sabotagens que provam os testes | [testes/](testes/) |

## Resultados

Um backlog real de 71 itens, em seis sprints, refletido a partir de um OpenProject em Jira,
Trello e GitHub Projects:

- **Fidelidade:** os 71 itens nos três espelhos, com as horas por sprint iguais às da fonte.
- **Idempotência:** a segunda rodada não alterou nada em nenhum dos três.
- **Duplicatas:** zero.
- **Uso:** de 28/09 a 02/10/2026, as 20 mudanças registradas na fonte foram feitas por
  conversa, nenhuma pela tela. A mesma medição registra que a sprint não andou nesse período.

Antes da publicação, seis rodadas de auditoria independente, 44 testes e 36 defeitos
plantados, todos pegos. Números, custo de tradução de cada ferramenta e falhas encontradas:
[RESULTADOS.md](RESULTADOS.md).

## Limitação atual

O reflexo é de mão única: mudanças feitas num espelho ainda não voltam para a fonte.

## Reproduza

Python 3 (testado em 3.13). Sem dependências, sem rede, sem conta.

```bash
python3 sm.py sprint S1                        # 23 h planejadas para 20 h: o excesso aparece
python3 sm.py mover 3 Concluído                # recusado: a DoD exige --evidencia
python3 sm.py mover 3 "Em execução"
python3 sm.py mover 4 "Em execução"
python3 sm.py mover 5 "Em execução"            # recusado: WIP 2/2
python3 espelho.py arquivo                     # reflete no espelho local
python3 espelho.py arquivo                     # segunda rodada: nada muda
python3 sm.py prova                            # quantas mudanças vieram do agente

python3 -m unittest discover -s testes -v      # 44 testes
bash testes/sabotagens.sh                      # 36 defeitos plantados, todos pegos; 1 controle
```

As saídas indicadas valem para um clone novo; para repetir do zero, `rm -rf estado`. A
medição de [RESULTADOS.md](RESULTADOS.md) foi feita sobre dados que não estão aqui. O
comando é o mesmo: reproduza o método e gere o seu número.

## Uso com ferramentas reais

1. Copie `config.exemplo.json` para fora do repositório e aponte `ESPELHO_CONFIG` para ele.
   Defina a fonte, os espelhos e o escopo: só os projetos listados saem da fonte.
2. Guarde as credenciais em `~/.config/espelho-backlog/<ferramenta>.env`, com permissão
   600. Para o GitHub, `gh auth login` basta.
3. Use, na fonte, uma conta própria do sistema agêntico, sem perfil de administrador. O
   histórico da ferramenta passa a registrar o que foi feito por conversa.

Escopo é decisão de proteção de dados, não de conveniência: tudo que entra num espelho
passa a existir na infraestrutura daquela ferramenta. Itens com dados de terceiros ficam
fora do escopo.

## Detalhes

**Identidade.** O marcador é `op:ID` na descrição do cartão; no Jira, o rótulo `op-ID`,
porque rótulo não aceita dois-pontos. O estado local de quem sincroniza acelera o trabalho,
mas o marcador é a identidade de última instância: antes de criar, procura-se o marcador, e
o que já existe é adotado. Exceção declarada: no Trello, que não tem épico, o épico vira
uma etiqueta, achada pelo nome.

**Configuração.** Nomes da instalação (projetos, quadros, repositório, fuso, IDs de tipos e
campos do Jira) vêm da configuração. O código só tem valores padrão, todos sobrescrevíveis:
IDs de prioridade do Jira Cloud, fuso UTC, horários de início e fim (09:00 e 18:00) e
iteração de 14 dias no GitHub. As credenciais podem ficar em outro diretório, indicado por
`ESPELHO_CREDENCIAIS`, e um `config.json` local tem precedência sobre o exemplo. Um
adaptador fora deste repositório, de fonte ou de espelho, é indicado pelo nome do módulo
com ponto (`pacote.modulo`). O diretório `estado/` guarda a cópia de cada item espelhado,
ou seja, o conteúdo do backlog: está no `.gitignore` e não deve ser versionado.

**Testes.** No espelho local, os testes conferem o conteúdo de cada cartão contra a fonte
(coluna, título, horas, sprint, épico pai e descrição), e não só a contagem. As travas da
DoD e do WIP rodam também com uma fonte externa que não herda da local e só expõe a
interface pública dos adaptadores, para provar que as regras não dependem da implementação.
O backlog fictício tem um projeto fora do escopo, e o teste de escopo procura no espelho
cada campo de texto dos itens dele. As sabotagens S5 a S36 vêm das rodadas de auditoria:
defeitos que a auditoria plantou e os testes da época não pegavam, mais sabotagens dirigidas
a cada afirmação de comportamento deste texto. O script exige que cada trecho sabotado seja
único no arquivo. Os adaptadores das ferramentas reais dependem de conta e não têm teste
automatizado; foram verificados contra as ferramentas no experimento.

## Licença

Apache 2.0. Veja [LICENSE](LICENSE).
