# Reroll — Encaixador de Roupas

App local (não precisa de internet nem de conta) que recorta automaticamente as roupas geradas no ChatGPT em 3 peças (upper body, lower body, shoes), usando as máscaras do projeto.

## Como rodar (uma vez só, por pessoa)

1. Instale o Python (se ainda não tiver): [python.org/downloads](https://www.python.org/downloads/) — marque "Add Python to PATH" na instalação.
2. Abra um terminal nesta pasta (`reroll_encaixe_app`) e instale as dependências:

```bash
pip install -r requirements.txt
```

## Como usar

No terminal, dentro desta pasta, rode:

```bash
streamlit run app.py
```

Isso abre uma aba no navegador com o app. Segue as 4 abas na ordem: corpo base → máscaras → roupas → resultado. Pra rodar de novo depois, é só repetir esse comando — não precisa reinstalar nada.

## O que ele faz

1. Redimensiona cada imagem de roupa gerada no ChatGPT pra bater com a altura do canvas do corpo base.
2. Corta em 3 peças usando as máscaras reais (upper/lower/shoes) — sem nenhum modelo de IA tentando adivinhar onde está a roupa.
3. Exporta as 3 peças de cada roupa, prontas pra baixar num `.zip`.

**Pré-requisito:** as 3 máscaras precisam bater com o corte exato do estilo de roupa que está sendo gerado (mesmo princípio do notebook original).
