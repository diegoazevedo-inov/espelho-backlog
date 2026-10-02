"""Adaptadores: o único lugar que conhece cada ferramenta.

Fonte da verdade (classe Fonte): projetos, sprints, itens, item, comentarios, criar, atualizar,
comentar, atividades_desde.
Espelho (classe Espelho): preparar(projetos, sprints, meta) e upsert(item, ref, pai_ref) -> ref.

Trocar de ferramenta é escrever um adaptador com essas funções. O método (sm.py) não muda.
"""
