import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Control IVA - Tambo", layout="wide")

st.title("🚜 Control de IVA y Saldo Técnico — Tambo")

# --- BARRA LATERAL: Arrastre de saldos ---
st.sidebar.header("Parámetros del Mes")
saldo_tecnico_anterior = st.sidebar.number_input(
    "Saldo Técnico a favor mes anterior ($)", 
    min_value=0.0, 
    value=0.0, 
    step=10000.0
)
retenciones_usina = st.sidebar.number_input(
    "Retenciones/Percepciones sufridas (Libre Disp.) ($)", 
    min_value=0.0, 
    value=0.0, 
    step=10000.0
)

# Inicializar listas en memoria
if "comprobantes_manuales" not in st.session_state:
    st.session_state.comprobantes_manuales = []
if "ventas_afip" not in st.session_state:
    st.session_state.ventas_afip = pd.DataFrame()
if "compras_afip" not in st.session_state:
    st.session_state.compras_afip = pd.DataFrame()

# --- PESTAÑAS PRINCIPALES ---
tab_movil, tab_afip, tab_posicion, tab_simulador = st.tabs([
    "📸 Carga Rápida (Celu / Foto)", 
    "📁 Importar AFIP (CSV)", 
    "📊 Posición Mensual", 
    "🎯 Simulador Pre-Cierre"
])

# ==========================================
# 1. PESTAÑA: CARGA RÁPIDA CON CÁMARA / MANUAL
# ==========================================
with tab_movil:
    st.subheader("Anotar Comprobante en el Momento")
    
    # Cámara del teléfono
    foto = st.camera_input("Sacar foto de la factura o ticket (opcional)")
    if foto:
        st.success("Foto capturada. Anotá los importes acá abajo para sumarlo:")

    with st.form("form_carga_rapida", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            tipo_mov = st.selectbox("Tipo de operación", ["Compra (Crédito Fiscal)", "Venta (Débito Fiscal)"])
            detalle = st.text_input("Detalle / Proveedor", placeholder="Ej: Balanceado Coop, Repuestos, Factura Usina")
            fecha_cbte = st.date_input("Fecha", value=date.today())
        
        with col_f2:
            monto_neto = st.number_input("Monto Neto Gravado ($)", min_value=0.0, step=1000.0)
            alicuota = st.selectbox(
                "Alícuota IVA", 
                [10.5, 21.0, 27.0], 
                format_func=lambda x: f"{x}% (10,5% Balanceado/Hacienda | 21% Gral | 27% Luz EPE/Coop)" if x==10.5 else f"{x}%"
            )
        
        btn_guardar = st.form_submit_button("➕ Guardar Comprobante")
        
        if btn_guardar and monto_neto > 0:
            iva_calculado = monto_neto * (alicuota / 100.0)
            total_calculado = monto_neto + iva_calculado
            st.session_state.comprobantes_manuales.append({
                "Fecha": fecha_cbte.strftime("%d/%m/%Y"),
                "Tipo": tipo_mov,
                "Detalle": detalle,
                "Neto Gravado": monto_neto,
                "Alícuota": f"{alicuota}%",
                "IVA": iva_calculado,
                "Total": total_calculado
            })
            st.success(f"Guardado: IVA computable de ${iva_calculado:,.2f}")

    # Mostrar tabla de comprobantes cargados
    if st.session_state.comprobantes_manuales:
        st.write("#### Comprobantes cargados este mes:")
        df_manual = pd.DataFrame(st.session_state.comprobantes_manuales)
        st.dataframe(df_manual, use_container_width=True)
        if st.button("🗑️ Borrar lista manual"):
            st.session_state.comprobantes_manuales = []
            st.rerun()

# ==========================================
# 2. PESTAÑA: IMPORTAR CSV DE AFIP
# ==========================================
def procesar_csv_afip(archivo):
    try:
        df = pd.read_csv(archivo, encoding="latin1", sep=None, engine="python")
        df.columns = [c.strip() for c in df.columns]
        for col in ["Imp. Neto Gravado", "Imp. Total", "IVA"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

with tab_afip:
    st.subheader("Subir archivos de Mis Comprobantes (AFIP)")
    c_afip1, c_afip2 = st.columns(2)
    with c_afip1:
        arch_v = st.file_uploader("Ventas (Emitidos CSV)", type=["csv"], key="v_csv")
        if arch_v:
            st.session_state.ventas_afip = procesar_csv_afip(arch_v)
            st.success(f"{len(st.session_state.ventas_afip)} ventas cargadas.")
    with c_afip2:
        arch_c = st.file_uploader("Compras (Recibidos CSV)", type=["csv"], key="c_csv")
        if arch_c:
            st.session_state.compras_afip = procesar_csv_afip(arch_c)
            st.success(f"{len(st.session_state.compras_afip)} compras cargadas.")

# ==========================================
# 3. CONSOLIDACIÓN Y POSICIÓN FISCAL
# ==========================================
# IVA de manuales
df_man = pd.DataFrame(st.session_state.comprobantes_manuales)
debito_man = df_man[df_man["Tipo"] == "Venta (Débito Fiscal)"]["IVA"].sum() if not df_man.empty else 0.0
credito_man = df_man[df_man["Tipo"] == "Compra (Crédito Fiscal)"]["IVA"].sum() if not df_man.empty else 0.0

# IVA de AFIP
debito_afip = st.session_state.ventas_afip["IVA"].sum() if not st.session_state.ventas_afip.empty and "IVA" in st.session_state.ventas_afip else 0.0
credito_afip = st.session_state.compras_afip["IVA"].sum() if not st.session_state.compras_afip.empty and "IVA" in st.session_state.compras_afip else 0.0

total_debito = debito_man + debito_afip
total_credito = credito_man + credito_afip

# Saldo Técnico (Art. 24, primer párrafo)
dif_tecnica = total_debito - total_credito
saldo_tecnico_final = dif_tecnica - saldo_tecnico_anterior

with tab_posicion:
    st.subheader("Liquidación Estimada del Mes")
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Débito Fiscal Total (Ventas)", f"${total_debito:,.2f}")
    col_m2.metric("Crédito Fiscal Total (Compras)", f"${total_credito:,.2f}")
    
    if saldo_tecnico_final > 0:
        col_m3.metric("Saldo Técnico A PAGAR", f"${saldo_tecnico_final:,.2f}")
    else:
        col_m3.metric("Saldo Técnico A FAVOR", f"${abs(saldo_tecnico_final):,.2f}")
        
    st.divider()
    st.write("#### Determinación del Pago Final con Retenciones")
    if saldo_tecnico_final > 0:
        a_pagar_final = max(0.0, saldo_tecnico_final - retenciones_usina)
        libre_remanente = max(0.0, retenciones_usina - saldo_tecnico_final)
        r1, r2 = st.columns(2)
        r1.info(f"**Impuesto a Pagar en VEP:** ${a_pagar_final:,.2f}")
        r2.write(f"Remanente Libre Disponibilidad: ${libre_remanente:,.2f}")
    else:
        st.success(f"No tenés impuesto a ingresar. Saldo técnico a favor acumulable para el mes que viene: **${abs(saldo_tecnico_final):,.2f}**.")
        st.write(f"Saldo de libre disponibilidad a favor: **${retenciones_usina:,.2f}**.")

# ==========================================
# 4. SIMULADOR PRE-CIERRE
# ==========================================
with tab_simulador:
    st.subheader("Simulador de Compras antes de Fin de Mes")
    st.markdown("Proyectá compras para no dejar tanto saldo a pagar:")
    
    s1, s2, s3 = st.columns(3)
    with s1:
        c_105 = st.number_input("Compra neta al 10,5% (Balanceado / Granos / Rollos) ($)", min_value=0.0, step=10000.0)
    with s2:
        c_21 = st.number_input("Compra neta al 21% (Repuestos / Sanidad / Fletes) ($)", min_value=0.0, step=10000.0)
    with s3:
        c_27 = st.number_input("Gasto neto al 27% (Luz / Energía sala ordeñe) ($)", min_value=0.0, step=5000.0)
        
    adicional = (c_105 * 0.105) + (c_21 * 0.21) + (c_27 * 0.27)
    nuevo_saldo = (total_debito - (total_credito + adicional)) - saldo_tecnico_anterior
    
    st.write(f"**Crédito fiscal extra:** ${adicional:,.2f}")
    if nuevo_saldo > 0:
        st.warning(f"El saldo técnico a pagar se reduciría a **${nuevo_saldo:,.2f}**.")
    else:
        st.success(f"No pagarías IVA y tendrías saldo técnico a favor de **${abs(nuevo_saldo):,.2f}**.")
