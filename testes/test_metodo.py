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
        self.assertIn("Backlog", self.sm("ver", "3").stdout)          # nada mudou na fonte

    def test_dod_recusa_evidencia_em_branco(self):
        r = self.sm("mover", "3", "Concluído", "--evidencia", "   ")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DoD", r.stderr)

    def test_dod_aceita_com_evidencia_e_registra(self):
        r = self.sm("mover", "3", "Concluído", "--evidencia", "teste de bloqueio: 6ª tentativa recusada (log anexo)")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Evidência (DoD)", self.sm("ver", "3").stdout)

    def test_forcar_nao_desliga_a_dod(self):
        r = self.sm("mover", "3", "Concluído", "--forcar")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("DoD", r.stderr)

    def test_wip_recusa_o_terceiro(self):
        self.assertEqual(self.sm("mover", "3", "Em execução").returncode, 0)
        self.assertEqual(self.sm("mover", "4", "Em execução").returncode, 0)
        r = self.sm("mover", "5", "Em execução")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("WIP", r.stderr)
        self.assertIn("2/2", r.stderr)

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
        self.sm("mover", "3", "Em execução")
        self.assertIn("0 mudanças", self.sm("prova", "--desde", "2999-01-01").stdout)
        self.assertIn("Desde 2026-10-01: 2 mudanças", self.sm("prova", "--desde", "2026-10-01").stdout)


if __name__ == "__main__":
    unittest.main()
