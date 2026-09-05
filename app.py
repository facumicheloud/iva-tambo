import streamlit as st
import pandas as pd

st.set_page_config(page_title="Control IVA - Sector Tambero", layout="wide")

st.title("🚜 Control de Saldo Técnico de IVA — Tambo")
st.markdown("Cálculo de posición mensual, importación de **Mis Comprobantes (AFIP/ARCA)** y simulación pre-cierre.")

# Parámetros en barra lateral
st.sidebar.header("Parámetros del Período")
saldo_tecnico_anterior = st.sidebar.number_input(
    "Saldo Técnico a favor mes anterior ($)", 
    min_value=0.0, 
    value=0.0, 
    step=1000.0
)
retenciones_usina = st.sidebar.number_input(
    "Retenciones/Percepciones sufridas (Libre Disp.) ($)", 
    min_value=0.0, 
    value=0.0, 
    step=1000.0
)

tab_carga, tab_posicion, tab_simulador = st.tabs([
    "📥 Carga de Comprobantes", 
    "📊 Posición Mensual", 
    "🎯 Simulador Pre-Cierre"
])

if "ventas_df" not in st.session_state:
    st.session_state.ventas_df = pd.DataFrame()
if "compras_df" not in st.session_state:
    st.session_state.compras_df = pd.DataFrame()

def procesar_csv_afip(archivo):
    try:
        df = pd.read_csv(archivo, encoding="latin1", sep=None, engine="python")
        df.columns = [c.strip() for c in df.columns]
        cols_num = ["Imp. Neto Gravado", "Imp. Total", "IVA", "Imp. Op. Exentas", "Otros Tributos"]
        for col in cols_num:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Error al procesar archivo: {e}")
        return pd.DataFrame()

with tab_carga:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Ventas / Débito Fiscal")
        archivo_ventas = st.file_uploader("Subir 'Mis Comprobantes Emitidos' (CSV)", type=["csv"], key="ventas_file")
        if archivo_ventas:
            df_v = procesar_csv_afip(archivo_ventas)
            if not df_v.empty:
                st.session_state.ventas_df = df_v
                st.success(f"{len(df_v)} comprobantes de venta cargados.")
                columnas_ver = [c for c in ["Fecha", "Tipo", "Denominación Receptor", "Imp. Neto Gravado", "IVA", "Imp. Total"] if c in df_v.columns]
                st.dataframe(df_v[columnas_ver].head())

    with col2:
        st.subheader("2. Compras / Crédito Fiscal")
        archivo_compras = st.file_uploader("Subir 'Mis Comprobantes Recibidos' (CSV)", type=["csv"], key="compras_file")
        if archivo_compras:
            df_c = procesar_csv_afip(archivo_compras)
            if not df_c.empty:
                st.session_state.compras_df = df_c
                st.success(f"{len(df_c)} comprobantes de compra cargados.")
                columnas_ver = [c for c in ["Fecha", "Tipo", "Denominación Emisor", "Imp. Neto Gravado", "IVA", "Imp. Total"] if c in df_c.columns]
                st.dataframe(df_c[columnas_ver].head())

total_debito = st.session_state.ventas_df["IVA"].sum() if not st.session_state.ventas_df.empty and "IVA" in st.session_state.ventas_df else 0.0
total_credito = st.session_state.compras_df["IVA"].sum() if not st.session_state.compras_df.empty and "IVA" in st.session_state.compras_df else 0.0

dif_tecnica = total_debito - total_credito
saldo_tecnico_final = dif_tecnica - saldo_tecnico_anterior

with tab_posicion:
    st.subheader("Liquidación Estimada de IVA del Mes")
    m1, m2, m3 = st.columns(3)
    m1.metric("Débito Fiscal Total", f"${total_debito:,.2f}")
    m2.metric("Crédito Fiscal Total", f"${total_credito:,.2f}")
    if saldo_tecnico_final > 0:
        m3.metric("Saldo Técnico A PAGAR", f"${saldo_tecnico_final:,.2f}")
    else:
        m3.metric("Saldo Técnico A FAVOR", f"${abs(saldo_tecnico_final):,.2f}")
        
    st.divider()
    st.write("#### Determinación del Pago Final")
    if saldo_tecnico_final > 0:
        a_pagar_final = max(0.0, saldo_tecnico_final - retenciones_usina)
        remanente_libre = max(0.0, retenciones_usina - saldo_tecnico_final)
        c1, c2 = st.columns(2)
        c1.info(f"**Impuesto Determinado a Pagar en VEP:** ${a_pagar_final:,.2f}")
        c2.write(f"Remanente Libre Disponibilidad: ${remanente_libre:,.2f}")
    else:
        st.success(f"No hay impuesto a ingresar. Queda un saldo técnico a favor acumulable para el mes siguiente de **${abs(saldo_tecnico_final):,.2f}**.")
        st.write(f"Saldo de libre disponibilidad a favor: **${retenciones_usina:,.2f}**.")

with tab_simulador:
    st.subheader("Simulador de Compras Pre-Cierre Mensual")
    st.markdown("Calculá compras antes de fin de mes para equilibrar el saldo técnico:")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        compra_105 = st.number_input("Compra neta al 10,5% (Balanceado / Granos / Rollos) ($)", min_value=0.0, value=0.0, step=10000.0)
    with col_s2:
        compra_21 = st.number_input("Compra neta al 21% (Repuestos / Fletes / Sanidad) ($)", min_value=0.0, value=0.0, step=10000.0)
    with col_s3:
        compra_27 = st.number_input("Gasto neto al 27% (Energía Eléctrica comercial) ($)", min_value=0.0, value=0.0, step=5000.0)
        
    credito_proyectado = (compra_105 * 0.105) + (compra_21 * 0.21) + (compra_27 * 0.27)
    nuevo_credito_total = total_credito + credito_proyectado
    nuevo_saldo_tecnico = (total_debito - nuevo_credito_total) - saldo_tecnico_anterior
    
    st.write(f"**Crédito fiscal adicional proyectado:** ${credito_proyectado:,.2f}")
    if nuevo_saldo_tecnico > 0:
        st.warning(f"Con estas compras, el saldo técnico a pagar se reduciría a **${nuevo_saldo_tecnico:,.2f}**.")
    else:
        st.success(f"Con estas compras, no pagarías IVA y tendrías un saldo a favor de **${abs(nuevo_saldo_tecnico):,.2f}**.")