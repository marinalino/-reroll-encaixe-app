import io
import zipfile
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image

st.set_page_config(page_title="Reroll — Encaixador de Roupas", page_icon="🧵", layout="wide")

CANVAS_SIZE_PADRAO = (1408, 3040)


def carregar_mascara(arquivo, tamanho):
    m = Image.open(arquivo).convert("L").resize(tamanho)
    return m.point(lambda p: 255 if p > 128 else 0)


def cor_do_canto(imagem_rgb, margem=5):
    arr = np.array(imagem_rgb.convert("RGB"))
    return tuple(int(v) for v in arr[margem, margem])


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
        canvas = Image.new("RGBA", canvas_size, cor_fundo + (255,))
        canvas.alpha_composite(recorte, (0, 0))
        resultados[categoria] = canvas
    return resultados


def montar_zip(resultados_por_arquivo):
    buffer_zip = io.BytesIO()
    with zipfile.ZipFile(buffer_zip, "w") as zf:
        for nome, pecas in resultados_por_arquivo.items():
            base = Path(nome).stem
            for categoria, img in pecas.items():
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"{base}_{categoria}.png", buf.getvalue())
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
    if st.button("🔄 Recomeçar do zero"):
        st.session_state.clear()
        st.rerun()

# ---------- header ----------
st.title("🧵 Reroll — Encaixador de Roupas")
st.caption(
    "Recorta automaticamente peças de roupa geradas no ChatGPT (upper body, lower body, shoes) "
    "usando o corpo base e as máscaras do projeto, prontas pra encaixar no personagem."
)

passo1, passo2, passo3, passo4 = st.tabs(
    ["1️⃣ Corpo base", "2️⃣ Máscaras", "3️⃣ Roupas geradas", "4️⃣ Resultado"]
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
            st.info("Se essa cor de fundo não bater com o magenta do seu projeto, confira se o corpo base está com fundo liso e sem borda de compressão.")
    else:
        st.info("Nenhum arquivo enviado ainda.")

# ---------- passo 2 ----------
with passo2:
    st.subheader("Envie as 3 máscaras")
    st.write(
        "Cada máscara define exatamente onde aquela peça deve aparecer — "
        "**branco** = área da peça, **preto** = resto (fica transparente no recorte final)."
    )

    if "corpo_base_img" not in st.session_state:
        st.warning("⬅️ Envie o corpo base no passo 1 antes de subir as máscaras.")
    else:
        col_upper, col_lower, col_shoes = st.columns(3)
        arquivos_mascara = {}
        with col_upper:
            st.markdown("**Upper body**")
            arquivos_mascara["upper"] = st.file_uploader(
                "Máscara upper", type=["png"], key="mask_upper", label_visibility="collapsed"
            )
        with col_lower:
            st.markdown("**Lower body**")
            arquivos_mascara["lower"] = st.file_uploader(
                "Máscara lower", type=["png"], key="mask_lower", label_visibility="collapsed"
            )
        with col_shoes:
            st.markdown("**Shoes**")
            arquivos_mascara["shoes"] = st.file_uploader(
                "Máscara shoes", type=["png"], key="mask_shoes", label_visibility="collapsed"
            )

        if all(arquivos_mascara.values()):
            tamanho = st.session_state.corpo_base_img.size
            mascaras = {cat: carregar_mascara(arq, tamanho) for cat, arq in arquivos_mascara.items()}
            st.session_state.mascaras = mascaras

            st.success("3 máscaras carregadas.")
            col_upper, col_lower, col_shoes = st.columns(3)
            for col, cat in zip([col_upper, col_lower, col_shoes], ["upper", "lower", "shoes"]):
                with col:
                    st.image(mascaras[cat], use_container_width=True)
        else:
            faltando = [c for c, a in arquivos_mascara.items() if not a]
            st.info(f"Faltam: {', '.join(faltando)}")

# ---------- passo 3 ----------
with passo3:
    st.subheader("Envie as roupas geradas no ChatGPT")
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
                resultados_totais[arq.name] = encaixar_roupa(imagem, mascaras, cor_fundo, canvas_size)
                barra.progress((i + 1) / len(arquivos), text=f"Processando {i + 1}/{len(arquivos)}: {arq.name}")

            st.session_state.processado = resultados_totais
            barra.empty()
            st.success(f"{len(arquivos)} roupa(s) processada(s)!")

        if st.session_state.processado:
            st.divider()
            st.write("### Prévia dos resultados")
            for nome, pecas in st.session_state.processado.items():
                st.write(f"**{nome}**")
                col1, col2, col3 = st.columns(3)
                for col, cat in zip([col1, col2, col3], ["upper", "lower", "shoes"]):
                    with col:
                        st.image(pecas[cat], caption=cat, use_container_width=True)

            st.divider()
            zip_bytes = montar_zip(st.session_state.processado)
            st.download_button(
                "⬇️ Baixar todas as roupas (.zip)",
                data=zip_bytes,
                file_name="reroll_roupas_encaixadas.zip",
                mime="application/zip",
                type="primary",
            )
