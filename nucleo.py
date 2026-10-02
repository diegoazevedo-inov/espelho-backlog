"""Núcleo compartilhado: configuração, credenciais e estado.

Todo nome específico de uma instalação (projetos, quadros, repositório, fuso, vocabulário
das colunas, prefixo de sprints a reaproveitar) vem da configuração. O código não conhece
nenhum backlog real. No Jira, os IDs de tipos e campos vêm da configuração; os IDs de prioridade
têm como padrão os do Jira Cloud e podem ser sobrescritos em "prioridades".

Ordem de busca da configuração:
  1. variável de ambiente ESPELHO_CONFIG
  2. config.json ao lado deste arquivo (ignorado pelo git)
  3. config.exemplo.json (backlog fictício, roda sem conta em nenhuma ferramenta)
"""
import importlib
import json
import os

BASE = os.path.dirname(os.path.realpath(__file__))


def carregar_config():
    caminho = os.environ.get("ESPELHO_CONFIG")
    if not caminho:
        local = os.path.join(BASE, "config.json")
        caminho = local if os.path.exists(local) else os.path.join(BASE, "config.exemplo.json")
    with open(caminho, encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["_arquivo"] = os.path.abspath(caminho)
    cfg["_dir"] = os.path.dirname(cfg["_arquivo"])
    return cfg


def caminho(cfg, relativo):
    """Resolve caminhos da configuração relativos ao próprio arquivo de configuração."""
    return relativo if os.path.isabs(relativo) else os.path.join(cfg["_dir"], relativo)


def dir_estado(cfg):
    d = caminho(cfg, cfg.get("dir_estado", "estado"))
    os.makedirs(d, mode=0o700, exist_ok=True)
    return d


def credenciais(nome):
    """Lê <dir>/<nome>.env. As credenciais nunca ficam na pasta do código."""
    d = os.path.expanduser(os.environ.get("ESPELHO_CREDENCIAIS", "~/.config/espelho-backlog"))
    arq = os.path.join(d, f"{nome}.env")
    if not os.path.exists(arq):
        raise SystemExit(f"credenciais ausentes: {arq}")
    with open(arq, encoding="utf-8") as f:
        return dict(l.strip().split("=", 1) for l in f if "=" in l and not l.startswith("#"))


def fonte(cfg):
    """A fonte da verdade (o adaptador que o método consulta e altera)."""
    return importlib.import_module(f"adaptadores.{cfg['fonte']['adaptador']}").Fonte(cfg)


def espelho(cfg, nome):
    """Um espelho: só recebe. Na etapa 1, nada volta dele para a fonte."""
    conf = cfg["espelhos"][nome]
    return importlib.import_module(f"adaptadores.{conf['adaptador']}").Espelho(cfg, conf)


def fluxo(cfg):
    return cfg["metodo"]["status_fluxo"]


def status_feito(cfg):
    return cfg["metodo"]["status_feito"]
