import io
import zipfile

import numpy as np
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Reroll — Encaixador de Roupas", page_icon="🧵", layout="wide")

CANVAS_SIZE_PADRAO = (1408, 3040)

# Cores fixas da máscara única — se um dia surgir uma categoria nova (cabelo, acessório, meia...),
# adiciona uma linha aqui com a cor combinada e o resto do app já lida com ela automaticamente.
CORES_CATEGORIA = {
    "upperbody": (0x33, 0xFF, 0x00),
    "lowerbody": (0xFF, 0x19, 0x00),
    "shoes": (0xFF, 0xC0, 0x00),
}
TOLERANCIA_COR = 40  # distância máxima (RGB) pra um pixel ainda contar como daquela cor


def cor_do_canto(imagem_rgb, margem=5):
    arr = np.array(imagem_rgb.convert("RGB"))
    return tuple(int(v) for v in arr[margem, margem])


def separar_mascara_por_cor(imagem_mascara, tamanho):
    img = imagem_mascara.convert("RGB").resize(tamanho)
    arr = np.array(img).astype(int)

    mascaras = {}
    for categoria, cor in CORES_CATEGORIA.items():
        distancia = np.sqrt(((arr - np.array(cor)) ** 2).sum(axis=2))
        binaria = (distancia <= TOLERANCIA_COR).astype(np.uint8) * 255
        mascaras[categoria] = Image.fromarray(binaria, mode="L")
    return mascaras


def redimensionar_para_canvas(imagem, canvas_size, cor_fundo):
    canvas_w, canvas_h = canvas_size
    escala = canvas_h / imagem.height
    novo_w = round(imagem.width * escala)
    imagem_redimensionada = imagem.resize((novo_w, canvas_h), Image.LANCZOS)
    fundo = Image.new("RGB", canvas_size, cor_fundo)
    x_offset = (canvas_w - novo_w) // 2
    fundo.paste(imagem_redimensionada, (x_offset, 0))
    return fundo


def encaixar_roupa(imagem_original, mascaras, cor_fundo, canvas_size):
    imagem_no_canvas = redimensionar_para_canvas(imagem_original.convert("RGB"), canvas_size, cor_fundo)
    resultados = {}
    for categoria, mascara in mascaras.items():
        recorte = imagem_no_canvas.convert("RGBA")
        recorte.putalpha(mascara)
        # canvas totalmente transparente — sem preenchimento de cor, só a peça na posição certa
        canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        canvas.alpha_composite(recorte, (0, 0))
        resultados[categoria] = canvas
    return resultados


def nome_arquivo(categoria, genero, nome_peca, numero):
    return f"o_{categoria}{genero}_{nome_peca}_{numero:02d}.png"


def montar_zip(resultados_por_indice, nomes_peca, genero, numero_inicial):
    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, "w") as zf:
        for i, pecas in resultados_por_indice.items():
            numero = numero_inicial + i
            for categoria, img in pecas.items():
                nome = nome_arquivo(categoria, genero, nomes_peca[categoria], numero)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(nome, buf.getvalue())
    buffer_zip.seek(0)
    return buffer_zip


# ---------- estado ----------
if "processado" not in st.session_state:
    st.session_state.processado = {}

# ---------- sidebar ----------
with st.sidebar:
    st.header("⚙️ Configurações")
    canvas_w = st.number_input("Largura do canvas (px)", value=CANVAS_SIZE_PADRAO[0], step=1, min_value=1)
    canvas_h = st.number_input("Altura do canvas (px)", value=CANVAS_SIZE_PADRAO[1], step=1, min_value=1)
    st.caption("Deixe como está, a não ser que o projeto use outro tamanho de canvas.")
    st.divider()
    st.caption("Cores fixas da máscara única:")
    for cat, cor in CORES_CATEGORIA.items():
        st.color_picker(cat, value="#%02X%02X%02X" % cor, disabled=True, key=f"cor_{cat}")
    st.divider()
    if st.button("🔄 Recomeçar do zero"):
        st.session_state.clear()
        st.rerun()

# ---------- header ----------
st.title("🧵 Reroll — Encaixador de Roupas")
st.caption(
    "Recorta automaticamente peças de roupa geradas no ChatGPT (upper body, lower body, shoes) "
    "usando o corpo base e uma máscara única colorida, prontas pra encaixar no personagem."
)

passo1, passo2, passo3, passo4 = st.tabs(
    ["1️⃣ Corpo base", "2️⃣ Máscara", "3️⃣ Roupas + nomenclatura", "4️⃣ Resultado"]
)

# ---------- passo 1 ----------
with passo1:
    st.subheader("Envie a imagem do corpo base")
    st.write("É a referência de proporção, pose e cor de fundo do personagem.")
    corpo_base_arquivo = st.file_uploader("Corpo base", type=["png", "jpg", "jpeg"], key="corpo_base")

    if corpo_base_arquivo:
        corpo_base_img = Image.open(corpo_base_arquivo).convert("RGB")
        cor_fundo = cor_do_canto(corpo_base_img)
        st.session_state.corpo_base_img = corpo_base_img
        st.session_state.cor_fundo = cor_fundo

        col1, col2 = st.columns([1, 2])
        with col1:
            st.image(corpo_base_img, caption="Corpo base", use_container_width=True)
        with col2:
            st.success("Corpo base carregado.")
            st.write(f"**Cor de fundo detectada:** RGB{cor_fundo}")
            st.write(f"**Tamanho da imagem:** {corpo_base_img.size[0]} x {corpo_base_img.size[1]} px")
    else:
        st.info("Nenhum arquivo enviado ainda.")

# ---------- passo 2 ----------
with passo2:
    st.subheader("Envie a máscara única")
    st.write(
        "Uma imagem só, com cada peça marcada por cor: "
        "🟢 verde `#33FF00` = upper body · 🔴 vermelho `#FF1900` = lower body · "
        "🟠 laranja `#FFC000` = shoes · resto (preto) = fundo."
    )

    if "corpo_base_img" not in st.session_state:
        st.warning("⬅️ Envie o corpo base no passo 1 antes de subir a máscara.")
    else:
        mascara_arquivo = st.file_uploader("Máscara única", type=["png"], key="mascara_unica")

        if mascara_arquivo:
            tamanho = st.session_state.corpo_base_img.size
            imagem_mascara = Image.open(mascara_arquivo)
            mascaras = separar_mascara_por_cor(imagem_mascara, tamanho)
            st.session_state.mascaras = mascaras

            st.success("Máscara separada nas 3 categorias.")
            col_original, col_upper, col_lower, col_shoes = st.columns(4)
            with col_original:
                st.image(imagem_mascara, caption="Original", use_container_width=True)
            for col, cat in zip([col_upper, col_lower, col_shoes], CORES_CATEGORIA.keys()):
                with col:
                    st.image(mascaras[cat], caption=cat, use_container_width=True)
        else:
            st.info("Nenhuma máscara enviada ainda.")

# ---------- passo 3 ----------
with passo3:
    st.subheader("Roupas geradas no ChatGPT")
    if "mascaras" not in st.session_state:
        st.warning("⬅️ Complete os passos 1 e 2 antes de subir as roupas.")
    else:
        roupas_arquivos = st.file_uploader(
            "Roupas",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="roupas",
            label_visibility="collapsed",
        )
        if roupas_arquivos:
            st.session_state.roupas_arquivos = roupas_arquivos
            st.success(f"{len(roupas_arquivos)} roupa(s) carregada(s).")
            n_cols = min(len(roupas_arquivos), 5)
            cols = st.columns(n_cols)
            for i, arq in enumerate(roupas_arquivos):
                with cols[i % n_cols]:
                    st.image(arq, caption=arq.name, use_container_width=True)

            st.divider()
            st.subheader("Nomenclatura do lote")
            st.caption(
                "Vale pra todo o lote acima. Formato final: `o_{categoria}{genero}_{nome}_{numero}.png` — "
                "a numeração segue a ordem das roupas enviadas (a 1ª roupa gera o `_01` nas 3 categorias, "
                "a 2ª gera `_02`, e assim por diante)."
            )

            col_genero, col_numero = st.columns(2)
            with col_genero:
                genero = st.radio("Gênero da base", ["F", "M"], horizontal=True, key="genero")
            with col_numero:
                numero_inicial = st.number_input(
                    "Número inicial (pra continuar a numeração de um lote anterior)",
                    value=1, min_value=1, step=1, key="numero_inicial",
                )

            col_up, col_low, col_sh = st.columns(3)
            with col_up:
                nome_upper = st.text_input("Nome peça — upperbody", placeholder="ex: jacket", key="nome_upper")
            with col_low:
                nome_lower = st.text_input("Nome peça — lowerbody", placeholder="ex: skirt", key="nome_lower")
            with col_sh:
                nome_shoes = st.text_input("Nome peça — shoes", placeholder="ex: sneaker", key="nome_shoes")

            st.session_state.nomes_peca = {
                "upperbody": nome_upper or "peca",
                "lowerbody": nome_lower or "peca",
                "shoes": nome_shoes or "peca",
            }

            with st.expander("Prévia dos nomes de arquivo"):
                for i in range(min(len(roupas_arquivos), 3)):
                    numero = numero_inicial + i
                    linha = ", ".join(
                        nome_arquivo(cat, genero, st.session_state.nomes_peca[cat], numero)
                        for cat in CORES_CATEGORIA
                    )
                    st.code(linha, language=None)
                if len(roupas_arquivos) > 3:
                    st.caption(f"... + {len(roupas_arquivos) - 3} roupa(s) a mais, seguindo o mesmo padrão.")
        else:
            st.info("Nenhuma roupa enviada ainda. Pode selecionar várias de uma vez.")

# ---------- passo 4 ----------
with passo4:
    st.subheader("Processar e baixar")
    pronto = "mascaras" in st.session_state and bool(st.session_state.get("roupas_arquivos"))

    if not pronto:
        st.warning("⬅️ Complete os passos 1, 2 e 3 antes de processar.")
    else:
        if st.button("🚀 Processar todas as roupas", type="primary"):
            canvas_size = (int(canvas_w), int(canvas_h))
            cor_fundo = st.session_state.cor_fundo
            mascaras = st.session_state.mascaras
            arquivos = st.session_state.roupas_arquivos
            resultados_totais = {}

            barra = st.progress(0, text="Processando...")
            for i, arq in enumerate(arquivos):
                imagem = Image.open(arq)
                resultados_totais[i] = encaixar_roupa(imagem, mascaras, cor_fundo, canvas_size)
                barra.progress((i + 1) / len(arquivos), text=f"Processando {i + 1}/{len(arquivos)}: {arq.name}")

            st.session_state.processado = resultados_totais
            barra.empty()
            st.success(f"{len(arquivos)} roupa(s) processada(s)!")

        if st.session_state.processado:
            genero = st.session_state.get("genero", "F")
            numero_inicial = st.session_state.get("numero_inicial", 1)
            nomes_peca = st.session_state.get("nomes_peca", {c: "peca" for c in CORES_CATEGORIA})

            st.divider()
            st.write("### Prévia dos resultados")
            for i, pecas in st.session_state.processado.items():
                numero = numero_inicial + i
                st.write(f"**Roupa {i + 1}** (número `{numero:02d}`)")
                cols = st.columns(3)
                for col, cat in zip(cols, CORES_CATEGORIA.keys()):
                    with col:
                        st.image(pecas[cat], caption=nome_arquivo(cat, genero, nomes_peca[cat], numero), use_container_width=True)

            st.divider()
            zip_bytes = montar_zip(st.session_state.processado, nomes_peca, genero, numero_inicial)
            st.download_button(
                "⬇️ Baixar todas as roupas (.zip)",
                data=zip_bytes,
                file_name="reroll_roupas_encaixadas.zip",
                mime="application/zip",
                type="primary",
            )
