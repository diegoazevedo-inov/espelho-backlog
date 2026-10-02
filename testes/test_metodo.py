"""As regras do método e o espelhamento local, como testes. Roda sem rede e sem conta.

Os adaptadores das ferramentas reais (OpenProject, Jira, Trello, GitHub) não têm teste
automatizado aqui, porque dependem de conta; foram verificados contra as ferramentas no
experimento (RESULTADOS.md).

    python3 -m unittest discover -s testes -v

Os testes chamam os comandos como um usuário chamaria (subprocess), sobre o backlog fictício,
numa cópia temporária. Nenhum arquivo do repositório é alterado.
"""
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="espelho-teste-")
        for nome in ("config.exemplo.json", "exemplos"):
            origem = os.path.join(RAIZ, nome)
            destino = os.path.join(self.tmp, nome)
            (shutil.copytree if os.path.isdir(origem) else shutil.copy)(origem, destino)
        self.env = dict(os.environ, ESPELHO_CONFIG=os.path.join(self.tmp, "config.exemplo.json"),
                        PYTHONDONTWRITEBYTECODE="1")
        self.env.pop("ESPELHO_SIMULAR_RESPOSTA_PERDIDA", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rodar(self, programa, *args, extra_env=None):
        env = dict(self.env, **(extra_env or {}))
        return subprocess.run([sys.executable, os.path.join(RAIZ, programa), *args],
                              capture_output=True, text=True, env=env, cwd=self.tmp)

    def sm(self, *args):
        return self.rodar("sm.py", *args)

    def espelho(self, *args, extra_env=None):
        return self.rodar("espelho.py", *args, extra_env=extra_env)

    def espelho_bruto(self):
        with open(os.path.join(self.tmp, "estado", "espelho-arquivo.json"), encoding="utf-8") as f:
            return json.load(f)

    def fonte_bruta(self):
        with open(os.path.join(self.tmp, "estado", "fonte.json"), encoding="utf-8") as f:
            return json.load(f)

    def status_na_fonte(self, item_id):
        return next(i["status"] for i in self.fonte_bruta()["itens"] if i["id"] == item_id)

    def cartao_de(self, op_id):
        for c in self.espelho_bruto()["cartoes"].values():
            if re.search(rf"op:{op_id}\s*$", c["descricao"]): return c

    def cartoes(self):
        d = self.espelho_bruto()
        return collections.Counter(int(re.search(r"op:(\d+)\s*$", c["descricao"]).group(1))
                                   for c in d["cartoes"].values())


class TravasDoMetodo(Base):
    def test_dod_recusa_concluido_sem_evidencia(self):
        r = self.sm("mover", "3", "Concluído")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DoD", r.stderr)
        self.assertEqual(self.status_na_fonte(3), "Backlog")           # o status atual, não o histórico

    def test_dod_recusa_evidencia_em_branco(self):
        r = self.sm("mover", "3", "Concluído", "--evidencia", "   ")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DoD", r.stderr)
        self.assertEqual(self.status_na_fonte(3), "Backlog")

    def test_dod_aceita_com_evidencia_e_registra(self):
        r = self.sm("mover", "3", "Concluído", "--evidencia", "teste de bloqueio: 6ª tentativa recusada (log anexo)")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Evidência (DoD)", self.sm("ver", "3").stdout)

    def test_forcar_nao_desliga_a_dod(self):
        r = self.sm("mover", "3", "Concluído", "--forcar")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DoD", r.stderr)
        self.assertEqual(self.status_na_fonte(3), "Backlog")

    def test_wip_recusa_o_terceiro(self):
        self.assertEqual(self.sm("mover", "3", "Em execução").returncode, 0)
        self.assertEqual(self.sm("mover", "4", "Em execução").returncode, 0)
        r = self.sm("mover", "5", "Em execução")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("WIP", r.stderr)
        self.assertIn("2/2", r.stderr)

    def test_wip_vale_para_toda_coluna_com_limite(self):
        self.sm("projetos")                                            # cria a fonte de trabalho
        with open(os.path.join(self.tmp, "config.exemplo.json"), encoding="utf-8") as f:
            limites = json.load(f)["metodo"]["wip"]["produto-exemplo"]
        self.assertGreaterEqual(len(limites), 2)
        for coluna, lim in limites.items():
            livres = [i["id"] for i in self.fonte_bruta()["itens"]
                      if i["tipo"] == "Tarefa" and i["status"] == "Backlog" and i["projeto_id"] == "produto-exemplo"]
            for item in livres[:lim]:
                self.assertEqual(self.sm("mover", str(item), coluna).returncode, 0)
            r = self.sm("mover", str(livres[lim]), coluna)
            self.assertNotEqual(r.returncode, 0, f"WIP de '{coluna}' não recusou")
            self.assertEqual(self.status_na_fonte(livres[lim]), "Backlog")

    def test_wip_nao_conta_epicos(self):
        self.assertEqual(self.sm("mover", "1", "Em execução").returncode, 0)    # épico
        self.assertEqual(self.sm("mover", "2", "Em execução").returncode, 0)    # épico
        self.assertEqual(self.sm("mover", "3", "Em execução").returncode, 0)
        self.assertEqual(self.sm("mover", "4", "Em execução").returncode, 0)

    def test_wip_forcado_fica_registrado(self):
        self.sm("mover", "3", "Em execução"); self.sm("mover", "4", "Em execução")
        self.assertEqual(self.sm("mover", "5", "Em execução", "--forcar").returncode, 0)
        self.assertIn("WIP excedido conscientemente", self.sm("ver", "5").stdout)

    def test_status_fora_do_vocabulario_e_recusado(self):
        r = self.sm("mover", "3", "Feito")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("status inválido", r.stderr)

    def test_capacidade_excedida_aparece(self):
        out = self.sm("sprint", "S1").stdout
        self.assertIn("23h de 20h", out)
        self.assertIn("EXCEDE em 3h", out)

    def test_planejado_inclui_itens_concluidos(self):
        self.sm("mover", "3", "Concluído", "--evidencia", "log do teste de bloqueio")
        out = self.sm("sprint", "S1").stdout
        self.assertIn("planejado 23h de 20h", out)
        self.assertIn("concluído 6h", out)


class Espelhamento(Base):
    def test_idempotencia_segunda_rodada_nao_muda_nada(self):
        primeira = self.espelho("arquivo").stdout
        segunda = self.espelho("arquivo").stdout
        self.assertIn("11 criados", primeira)
        self.assertIn("0 criados, 0 atualizados, 11 sem mudança", segunda)

    def test_conteudo_do_cartao_bate_com_a_fonte(self):
        self.espelho("arquivo")
        for i in self.fonte_bruta()["itens"]:
            if i["projeto_id"] != "produto-exemplo": continue
            c = self.cartao_de(i["id"])
            self.assertIsNotNone(c, f"item {i['id']} sem cartão")
            self.assertEqual(c["coluna"], i["status"])
            self.assertEqual(c["tipo"], i["tipo"])
            self.assertEqual(c["sprint"], i["sprint"])
            esperado = i["assunto"] + (f" · {i['horas']:g}h" if i["horas"] else "")
            self.assertEqual(c["titulo"], esperado)
            self.assertIn(i["descricao"], c["descricao"])
            if i["pai_id"]:
                cartao_pai = next(k for k, v in self.espelho_bruto()["cartoes"].items()
                                  if re.search(rf"op:{i['pai_id']}\s*$", v["descricao"]))
                self.assertEqual(c["pai"], cartao_pai, f"item {i['id']} sem o épico pai")
            else:
                self.assertIsNone(c["pai"])

    def test_mudanca_de_status_reflete_no_espelho(self):
        self.espelho("arquivo")
        self.sm("mover", "3", "Em execução")
        self.assertIn("0 criados, 1 atualizados", self.espelho("arquivo").stdout)
        self.assertEqual(self.cartao_de(3)["coluna"], "Em execução")

    def test_item_concluido_continua_espelhado(self):
        self.espelho("arquivo")
        self.sm("mover", "3", "Concluído", "--evidencia", "log do teste de bloqueio")
        self.assertIn("0 criados, 1 atualizados", self.espelho("arquivo").stdout)
        self.assertEqual(self.cartao_de(3)["coluna"], "Concluído")
        self.assertEqual(sum(self.cartoes().values()), 11)

    def test_estado_local_perdido_adota_sem_duplicar(self):
        """O marcador no cartão é a identidade de última instância: sem o estado local, nada duplica."""
        self.espelho("arquivo")
        os.remove(os.path.join(self.tmp, "estado", "arquivo.json"))
        out = self.espelho("arquivo").stdout
        self.assertIn("0 criados", out)
        self.assertIn("11 adotados pelo marcador", out)
        self.assertEqual(sum(self.cartoes().values()), 11)

    def test_identidade_nunca_pelo_titulo(self):
        """Dois itens com o mesmo título e o estado local perdido: cada um mantém o seu cartão."""
        self.espelho("arquivo")
        self.sm("criar", "Exportar relatório mensal em CSV", "--sprint", "S2", "--horas", "4")   # mesmo título exibido do #6
        os.remove(os.path.join(self.tmp, "estado", "arquivo.json"))
        out = self.espelho("arquivo").stdout
        self.assertIn("1 criados", out)
        self.assertIn("11 adotados pelo marcador", out)
        self.assertEqual(self.cartao_de(6)["titulo"], self.cartao_de(13)["titulo"])   # títulos idênticos
        self.assertEqual(self.cartoes()[6], 1)
        self.assertEqual(self.cartoes()[13], 1)
        self.assertEqual(sum(self.cartoes().values()), 12)

    def test_espelho_externo_por_nome_com_ponto(self):
        pacote = os.path.join(self.tmp, "espelho_externo")
        os.makedirs(pacote)
        open(os.path.join(pacote, "__init__.py"), "w").close()
        with open(os.path.join(pacote, "espelho.py"), "w", encoding="utf-8") as f:
            f.write("from adaptadores import arquivo_espelho as _local\n\n"
                    "class Espelho:\n"
                    "    def __init__(self, cfg, conf):\n        self._e = _local.Espelho(cfg, conf)\n"
                    "    def __getattr__(self, n):\n        return getattr(self._e, n)\n")
        caminho = os.path.join(self.tmp, "config.exemplo.json")
        with open(caminho, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["espelhos"]["externo"] = {"adaptador": "espelho_externo.espelho", "arquivo": "estado/espelho-externo.json"}
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False)
        r = self.espelho("externo", extra_env={"PYTHONPATH": self.tmp + os.pathsep + self.env.get("PYTHONPATH", "")})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("11 criados", r.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "estado", "espelho-externo.json")))

    def test_nada_volta_do_espelho_para_a_fonte(self):
        self.sm("projetos")                                            # cria a fonte de trabalho
        with open(os.path.join(self.tmp, "estado", "fonte.json"), "rb") as f:
            antes = f.read()
        self.espelho("arquivo"); self.espelho("arquivo")
        with open(os.path.join(self.tmp, "estado", "fonte.json"), "rb") as f:
            self.assertEqual(f.read(), antes)

    def test_estado_guarda_copia_de_referencia_de_cada_item(self):
        self.espelho("arquivo")
        with open(os.path.join(self.tmp, "estado", "arquivo.json"), encoding="utf-8") as f:
            est = json.load(f)
        for i in self.fonte_bruta()["itens"]:
            if i["projeto_id"] != "produto-exemplo": continue
            snap = est[str(i["id"])]["snap"]
            for campo in ("assunto", "descricao", "status", "tipo", "sprint", "horas", "pai_id"):
                self.assertEqual(snap[campo], i[campo], f"snap do item {i['id']}: {campo}")

    def test_mudanca_na_fonte_atualiza_sem_criar(self):
        self.espelho("arquivo")
        self.sm("editar", "6", "--assunto", "Exportar relatório mensal em CSV e PDF")
        self.assertIn("0 criados, 1 atualizados", self.espelho("arquivo").stdout)
        self.assertEqual(sum(self.cartoes().values()), 11)

    def test_resposta_perdida_nao_duplica(self):
        """Falha real: a ferramenta cria o cartão, a resposta se perde, o estado local não registra.
        Sem identidade no próprio cartão, a rodada seguinte criaria outro."""
        self.espelho("arquivo")
        self.sm("criar", "Item novo", "--sprint", "S2", "--horas", "1")
        falha = self.espelho("arquivo", extra_env={"ESPELHO_SIMULAR_RESPOSTA_PERDIDA": "13"})
        self.assertNotEqual(falha.returncode, 0)
        self.assertIn("resposta perdida", falha.stderr)
        retomada = self.espelho("arquivo")
        self.assertEqual(retomada.returncode, 0)
        self.assertIn("0 criados", retomada.stdout)
        self.assertIn("1 adotados pelo marcador", retomada.stdout)
        duplicados = {k: v for k, v in self.cartoes().items() if v > 1}
        self.assertEqual(duplicados, {})
        self.assertEqual(self.cartoes()[13], 1)

    def test_paridade_fonte_e_espelho(self):
        self.espelho("arquivo")
        with open(os.path.join(self.tmp, "estado", "fonte.json"), encoding="utf-8") as f:
            fonte = {i["id"] for i in json.load(f)["itens"] if i["projeto_id"] == "produto-exemplo"}
        self.assertEqual(set(self.cartoes()), fonte)

    def test_escopo_nada_fora_do_declarado_sai_da_fonte(self):
        self.espelho("arquivo")
        self.assertNotIn(12, self.cartoes())                           # item do projeto restrito
        with open(os.path.join(self.tmp, "estado", "espelho-arquivo.json"), encoding="utf-8") as f:
            espelhado = f.read()
        fora = [i for i in self.fonte_bruta()["itens"] if i["projeto_id"] != "produto-exemplo"]
        self.assertTrue(fora)
        for i in fora:                                                 # todo campo de texto, não só o título
            for campo, valor in i.items():
                if isinstance(valor, str) and len(valor) >= 4 and valor != "Backlog" and valor not in ("Tarefa", "Alta"):
                    self.assertNotIn(valor, espelhado, f"campo '{campo}' do item {i['id']} vazou")


class Consultas(Base):
    def test_projetos_lista_os_projetos(self):
        out = self.sm("projetos").stdout
        linhas = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(len(linhas), 2)
        self.assertTrue(linhas[0].startswith("produto-exemplo"))
        self.assertTrue(linhas[1].startswith("projeto-restrito"))

    def test_criar_respeita_a_sprint(self):
        r = self.sm("criar", "Item novo", "--sprint", "S2", "--horas", "1")
        self.assertIn("[S2]", r.stdout)
        novo = max(self.fonte_bruta()["itens"], key=lambda i: i["id"])
        self.assertEqual((novo["assunto"], novo["sprint"], novo["inicio"], novo["fim"]),
                         ("Item novo", "S2", "2026-10-19", "2026-10-30"))

    def test_itens_lista_os_itens_do_projeto(self):
        out = self.sm("itens", "-p", "produto-exemplo").stdout
        self.assertEqual(sum(1 for l in out.splitlines() if l.startswith("#")), 11)
        self.assertIn("— 11 itens", out)
        self.assertNotIn("nunca pode sair da fonte", out)

    def test_wip_mostra_a_ocupacao(self):
        self.sm("mover", "3", "Em execução")
        out = self.sm("wip").stdout
        self.assertIn("produto-exemplo: Em execução 1/2", out)
        self.assertIn("produto-exemplo: Em auditoria 0/2", out)


class Medicao(Base):
    def test_prova_distingue_autores(self):
        """O backlog fictício traz 1 mudança feita direto na ferramenta, por outro autor."""
        self.sm("mover", "3", "Em execução")
        self.sm("comentar", "3", "Daily: tela pronta, falta o bloqueio")
        out = self.sm("prova").stdout
        self.assertIn("3 mudanças", out)
        self.assertIn("66.7% por linguagem natural", out)
        self.assertIn("Pessoa (uso direto da ferramenta)", out)

    def test_prova_respeita_o_periodo(self):
        """A atividade do autor fictício é de 2020; a do agente, de agora."""
        self.sm("mover", "3", "Em execução")
        self.assertIn("2 mudanças", self.sm("prova").stdout)
        self.assertIn("Desde 2021-01-01: 1 mudanças", self.sm("prova", "--desde", "2021-01-01").stdout)
        self.assertIn("0 mudanças", self.sm("prova", "--desde", "2999-01-01").stdout)


class OutraFonte(TravasDoMetodo):
    """As mesmas travas, com outra fonte da verdade (módulo externo, nome diferente):
    as regras do método não podem depender de qual ferramenta é a fonte."""
    def setUp(self):
        super().setUp()
        pacote = os.path.join(self.tmp, "fonte_externa")
        os.makedirs(pacote)
        open(os.path.join(pacote, "__init__.py"), "w").close()
        with open(os.path.join(pacote, "fonte.py"), "w", encoding="utf-8") as f:
            f.write("from adaptadores import arquivo as _local\n\n"
                    "PUBLICOS = {'projetos', 'sprints', 'itens', 'item', 'comentarios', 'criar',\n"
                    "            'atualizar', 'comentar', 'atividades_desde'}\n\n"
                    "class Fonte:\n"
                    "    \"\"\"Não herda da fonte local e só expõe a interface pública dos adaptadores.\"\"\"\n"
                    "    nome = 'outra-ferramenta'\n"
                    "    def __init__(self, cfg):\n        self._f = _local.Fonte(cfg)\n        self.url = 'outra://fonte'\n"
                    "    def __getattr__(self, n):\n"
                    "        if n not in PUBLICOS:\n            raise AttributeError(n)\n"
                    "        return getattr(self._f, n)\n")
        caminho = os.path.join(self.tmp, "config.exemplo.json")
        with open(caminho, encoding="utf-8") as f:
            cfg = json.load(f)
        cfg["fonte"]["adaptador"] = "fonte_externa.fonte"
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False)
        self.env["PYTHONPATH"] = self.tmp + os.pathsep + self.env.get("PYTHONPATH", "")

    def test_a_fonte_e_mesmo_outra(self):
        self.assertIn("fonte: outra-ferramenta", self.sm("prova").stdout)
        codigo = ("import adaptadores.arquivo as a, fonte_externa.fonte as e, nucleo\n"
                  "f = e.Fonte(nucleo.carregar_config())\n"
                  "print(issubclass(e.Fonte, a.Fonte), hasattr(f, '_ler'), hasattr(f, '_gravar'), hasattr(f, 'arq'))")
        r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                           env=dict(self.env, PYTHONPATH=self.tmp + os.pathsep + RAIZ + os.pathsep + self.env.get("PYTHONPATH", "")))
        self.assertEqual(r.stdout.strip(), "False False False False", r.stderr)   # só a interface pública


class Configuracao(unittest.TestCase):
    def test_config_local_tem_precedencia_sobre_o_exemplo(self):
        tmp = tempfile.mkdtemp(prefix="espelho-teste-")
        try:
            repo = os.path.join(tmp, "repo")
            shutil.copytree(RAIZ, repo, ignore=shutil.ignore_patterns(".git", "estado", "__pycache__", "config.json"))
            with open(os.path.join(repo, "config.exemplo.json"), encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["metodo"]["capacidade_horas_sprint"]["produto-exemplo"] = 30
            with open(os.path.join(repo, "config.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False)
            env = {k: v for k, v in os.environ.items() if k != "ESPELHO_CONFIG"}
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            out = subprocess.run([sys.executable, os.path.join(repo, "sm.py"), "sprint", "S1"],
                                 capture_output=True, text=True, env=env, cwd=tmp).stdout
            self.assertIn("23h de 30h", out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_credenciais_lidas_de_ESPELHO_CREDENCIAIS(self):
        tmp = tempfile.mkdtemp(prefix="espelho-teste-")
        try:
            with open(os.path.join(tmp, "ferramenta.env"), "w", encoding="utf-8") as f:
                f.write("# comentário\nCHAVE=valor-de-teste\n")
            env = dict(os.environ, ESPELHO_CREDENCIAIS=tmp, PYTHONDONTWRITEBYTECODE="1",
                       PYTHONPATH=RAIZ + os.pathsep + os.environ.get("PYTHONPATH", ""))
            r = subprocess.run([sys.executable, "-c", "import nucleo; print(nucleo.credenciais('ferramenta')['CHAVE'])"],
                               capture_output=True, text=True, env=env, cwd=tmp)
            self.assertEqual(r.stdout.strip(), "valor-de-teste", r.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
