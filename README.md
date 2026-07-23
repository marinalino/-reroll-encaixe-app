# Reroll — Encaixador de Roupas

App que recorta automaticamente as roupas geradas no ChatGPT em 3 peças (upper body, lower body, shoes), usando uma máscara única colorida, e já exporta com o nome de arquivo padronizado do projeto.

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
2. Separa uma máscara única (colorida) em 3 categorias por cor:
   - 🟢 verde `#33FF00` = upperbody
   - 🔴 vermelho `#FF1900` = lowerbody
   - 🟠 laranja `#FFC000` = shoes
3. Corta as 3 peças usando essas máscaras — sem nenhum modelo de IA tentando adivinhar onde está a roupa — e exporta com **fundo transparente** (não magenta), mantendo a posição exata.
4. Nomeia cada arquivo automaticamente no padrão `o_{categoria}{genero}_{nome}_{numero}.png` (ex: `o_upperbodyF_jacket_01.png`), a partir dos nomes/gênero/numeração que você define no passo 3.

**Pré-requisito:** a máscara precisa bater com o corte exato do estilo de roupa que está sendo gerado (mesmo princípio do notebook original). Se surgir uma categoria nova no futuro (cabelo, acessório, meia...), basta adicionar a cor correspondente na constante `CORES_CATEGORIA` no topo do `app.py`.
