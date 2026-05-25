import io
import re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CV Passenger Market Share",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── css ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stAppViewContainer"] { background:#f4f6f9; }
[data-testid="stSidebar"] { background:#1a2b4a; }
[data-testid="stSidebar"] * { color:#e8edf5 !important; }
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] { background:#2a4a7f !important; }
[data-testid="stSidebar"] hr { border-color:#2a4a7f; }
.block-container { padding-top:1.5rem; }
.kpi-card { background:white; border-radius:12px; padding:1rem 1.25rem;
    border:1px solid #e2e8f0; text-align:center; }
.kpi-num  { font-size:2rem; font-weight:700; color:#1a2b4a; line-height:1.1; }
.kpi-lbl  { font-size:0.78rem; color:#64748b; margin-top:2px; text-transform:uppercase; letter-spacing:.05em; }
.kpi-sub  { font-size:0.82rem; color:#1a6eb5; font-weight:600; margin-top:4px; }
.sec-hdr  { font-size:1rem; font-weight:700; color:#1a2b4a;
    border-left:4px solid #1a6eb5; padding-left:10px; margin:1.2rem 0 .5rem; }
.step-box { background:white; border-radius:14px; padding:1.5rem 1.8rem;
    border:1px solid #e2e8f0; margin-bottom:1rem; }
.step-num { display:inline-block; background:#1a6eb5; color:white;
    border-radius:50%; width:28px; height:28px; text-align:center; line-height:28px;
    font-weight:700; font-size:14px; margin-right:10px; }
.pill { display:inline-block; padding:2px 10px; border-radius:20px; font-size:11px;
    font-weight:600; margin:2px; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── pincode → taluka (Nashik district) ─────────────────────────────────────────
PINCODE_TALUKA = {
    # Nashik city + Nashik taluka + Nashik Road / Deolali
    **{p: "Nashik" for p in [
        "422001","422002","422003","422004","422005","422006","422007","422008",
        "422009","422010","422011","422012","422013","422014","422015","422016",
        "422101","422102","422105","422222","422401","422402",
    ]},
    # Sinnar
    **{p: "Sinnar"         for p in ["422103","422104","422112","422502"]},
    # Dindori
    **{p: "Dindori"        for p in ["422202","422209","422215","421302"]},
    # Trimbakeshwar
    **{p: "Trimbakeshwar"  for p in ["422212","422203"]},
    # Niphad
    **{p: "Niphad"         for p in ["422206","422207","422210","422221",
                                      "422301","422303","422305","422306","422308"]},
    # Igatpuri
    **{p: "Igatpuri"       for p in ["422403","422402"]},
    # Chandwad
    **{p: "Chandwad"       for p in ["423101","423111"]},
    # Yeola
    **{p: "Yeola"          for p in ["423401","423403"]},
    # Baglan / Satana
    **{p: "Baglan/Satana"  for p in ["423301","423302","423303"]},
    # Malegaon
    **{p: "Malegaon"       for p in ["423203","423204","423205"]},
    # Deola
    **{p: "Deola"          for p in ["423102"]},
    # Kalwan
    **{p: "Kalwan"         for p in ["423501","423502"]},
    # Surgana
    **{p: "Surgana"        for p in ["422211","422214"]},
    # Peint
    **{p: "Peint"          for p in ["422208"]},
}

OEM_COLORS = {
    "TATA MOTORS LTD":             "#1a6eb5",
    "FORCE MOTORS LIMITED":        "#27ae60",
    "VE COMMERCIAL VEHICLES LTD":  "#e67e22",
    "MAHINDRA & MAHINDRA LIMITED": "#8e44ad",
    "MARUTI SUZUKI INDIA LTD":     "#c0392b",
    "SML ISUZU LTD":               "#16a085",
    "ASHOK LEYLAND LTD":           "#d35400",
    "SML MAHINDRA LTD":            "#7f8c8d",
}
OEM_SHORT = {
    "TATA MOTORS LTD":             "Tata",
    "FORCE MOTORS LIMITED":        "Force",
    "VE COMMERCIAL VEHICLES LTD":  "Eicher/VE",
    "MAHINDRA & MAHINDRA LIMITED": "Mahindra",
    "MARUTI SUZUKI INDIA LTD":     "Maruti",
    "SML ISUZU LTD":               "SML Isuzu",
    "ASHOK LEYLAND LTD":           "Ashok Leyland",
    "SML MAHINDRA LTD":            "SML Mahindra",
}

# ── helpers ────────────────────────────────────────────────────────────────────
def extract_pincode(addr):
    if pd.isna(addr):
        return None
    m = re.findall(r"\b4\d{5}\b", str(addr))
    return m[-1] if m else None

def color_for(maker):
    return OEM_COLORS.get(maker.upper(), "#95a5a6")

def short(maker):
    return OEM_SHORT.get(maker.upper(), maker)

def bar_layout(height=380):
    return dict(
        height=height, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0, r=10, t=40, b=80),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.55, xanchor="center", x=0.5),
    )

# ── SESSION STATE ──────────────────────────────────────────────────────────────
if "classified" not in st.session_state:
    st.session_state.classified = False
if "df_passenger" not in st.session_state:
    st.session_state.df_passenger = None

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<h1 style='margin:0 0 2px; font-size:1.65rem; color:#1a2b4a;'>
  🚌 CV Passenger Market Share Dashboard
</h1>
<p style='color:#64748b; margin:0; font-size:.9rem;'>
  Upload → Classify → Analyse &nbsp;|&nbsp; 3-wheelers always excluded
</p>
""", unsafe_allow_html=True)
st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — UPLOAD
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='sec-hdr'><span class='step-num'>1</span>Upload RTO Excel File</div>",
            unsafe_allow_html=True)

uploaded = st.file_uploader("Choose the RTO .xlsx export", type=["xlsx"],
                             label_visibility="collapsed")

if uploaded is None:
    st.info("Upload your RTO Excel file above to begin. The file should contain columns like **Vehicle Class**, **Body Type**, **Vehicle Category**, **Maker Name**, etc.")
    st.stop()

@st.cache_data(show_spinner="Reading file…")
def read_raw(b):
    df = pd.read_excel(io.BytesIO(b))
    df.columns = [c.strip() for c in df.columns]
    return df

raw = read_raw(uploaded.read())
total_raw = len(raw)

st.success(f"✅ Loaded **{total_raw:,} rows** · {raw.shape[1]} columns detected")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — CLASSIFY
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("<div class='sec-hdr'><span class='step-num'>2</span>Classify Passenger CVs</div>",
            unsafe_allow_html=True)
st.caption("Pick which values in each column identify a **passenger CV**. 3-wheelers are excluded automatically regardless of selection.")

with st.form("classify_form"):
    col_a, col_b, col_c = st.columns(3)

    # --- Vehicle Class ---
    with col_a:
        vc_opts = sorted(raw["Vehicle Class"].dropna().unique().tolist())
        sel_vc = st.multiselect(
            "Vehicle Class  (include these)",
            options=vc_opts,
            default=[],
            placeholder="Select values…",
            help="Select all Vehicle Class values that represent passenger CVs"
        )

    # --- Vehicle Category ---
    with col_b:
        cat_opts = sorted(raw["Vehicle Category"].dropna().unique().tolist())
        sel_cat = st.multiselect(
            "Vehicle Category  (include these)",
            options=cat_opts,
            default=[],
            placeholder="Select values…",
            help="Select Vehicle Category values that are passenger-type"
        )

    # --- Body Type ---
    with col_c:
        bt_opts = sorted(raw["Body Type"].dropna().unique().tolist())
        sel_bt = st.multiselect(
            "Body Type  (include these)",
            options=bt_opts,
            default=[],
            placeholder="Select values…",
            help="Select Body Type values that are passenger-type bodies"
        )

    st.caption("⚠️  Rows matching **SCVPASS**, **SCV CARGO**, **SCV PICK UP**, **Goods Carrier**, **Dumper** and any 3-wheeler body types are always excluded even if selected above.")

    submitted = st.form_submit_button("🔍 Apply Classification & Load Dashboard", use_container_width=True,
                                       type="primary")

if submitted:
    # rows that match ANY of the three selector groups
    mask = (
        raw["Vehicle Class"].isin(sel_vc) |
        raw["Vehicle Category"].isin(sel_cat) |
        raw["Body Type"].isin(sel_bt)
    )
    dfp = raw[mask].copy()

    # ── always-exclude: 3-wheelers & pure goods
    EXCLUDE_CATEGORY = {"SCVPASS","SCV CARGO","SCV PICK UP","LCV"}
    EXCLUDE_CLASS    = {"Goods Carrier","Dumper"}
    EXCLUDE_BODY_KW  = ["AUTO","RICKSHAW","TOTO","E-RICK","TEMPO","LOADER","TIPPER",
                        "TANKER","BULKER","CONTAINER","OPEN BODY","HSD","FSD",
                        "LOADBODY","LOAD BODY","PLATFORM","DUMPER","ROCK","RMC",
                        "MIXER","GARBAGE","SCAVENGING","VACUUM","PETROLEUM","FUEL",
                        "BULKER","TRAILER","ARTICULATED"]
    body_excl_mask = dfp["Body Type"].str.upper().str.contains(
        "|".join(EXCLUDE_BODY_KW), na=False)
    dfp = dfp[
        ~dfp["Vehicle Category"].isin(EXCLUDE_CATEGORY) &
        ~dfp["Vehicle Class"].isin(EXCLUDE_CLASS) &
        ~body_excl_mask
    ].copy()

    # ── enrich
    dfp["Maker"]    = dfp["Maker Name"].str.strip().str.upper()
    dfp["Model"]    = dfp["Model Name"].str.strip()
    dfp["BodyType"] = dfp["Body Type"].str.strip().str.upper()
    dfp["RegDate"]  = pd.to_datetime(dfp["Registration Date"], errors="coerce")
    dfp["Month"]    = dfp["RegDate"].dt.to_period("M").astype(str)
    dfp["Pincode"]  = dfp["Current Address"].apply(extract_pincode)
    dfp["Taluka"]   = dfp["Pincode"].map(PINCODE_TALUKA).fillna("Other / Unknown")

    def app_type(bt):
        bt = str(bt).upper()
        if "SCHOOL" in bt:                          return "School Bus"
        if "AMBULANCE" in bt or "TYPE B" in bt:     return "Ambulance"
        if "STAFF" in bt:                           return "Staff Bus"
        if "SLEEPER" in bt:                         return "Sleeper Bus"
        if "MONOCOQUE" in bt or "FULLY BUILT" in bt:return "Passenger Bus"
        if "BUS" in bt:                             return "Passenger Bus"
        if "HARD TOP" in bt or "DOOR" in bt or "HIGH ROOF" in bt: return "Passenger Van"
        if "TOURS" in bt or "TRAVEL" in bt:         return "Tourist / Travel"
        if "VAN" in bt:                             return "Passenger Van"
        return "Other"

    dfp["AppType"] = dfp["BodyType"].apply(app_type)

    st.session_state.df_passenger = dfp
    st.session_state.classified   = True

# ── preview of classification result ──────────────────────────────────────────
if st.session_state.classified and st.session_state.df_passenger is not None:
    dfp = st.session_state.df_passenger
    n   = len(dfp)
    st.success(
        f"✅ Classification complete — **{n:,} passenger CV records** selected "
        f"({n/total_raw*100:.1f}% of total {total_raw:,} rows)"
    )
    with st.expander("Preview classified records (first 20 rows)", expanded=False):
        st.dataframe(dfp[["Registration Number","Maker","Model","BodyType",
                           "Vehicle Category","AppType","Seat Capacity",
                           "Pincode","Taluka","Month"]].head(20),
                     use_container_width=True, hide_index=True)
else:
    st.info("Configure the classification above and click **Apply** to load the dashboard.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
df = st.session_state.df_passenger.copy()

st.markdown("<div class='sec-hdr'><span class='step-num'>3</span>Dashboard</div>",
            unsafe_allow_html=True)

# ── sidebar filters ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎛️ Filters")
    st.divider()

    all_oems    = sorted(df["Maker"].unique())

    all_app     = sorted(df["AppType"].unique())
    sel_app_raw = st.selectbox("Application Type", ["All"] + all_app, index=0)
    sel_app     = all_app if sel_app_raw == "All" else [sel_app_raw]

    all_months  = sorted(df["Month"].dropna().unique())
    sel_mon_raw = st.selectbox("Month", ["All"] + all_months, index=0)
    sel_months  = all_months if sel_mon_raw == "All" else [sel_mon_raw]

    all_talukas = sorted(df["Taluka"].unique())
    sel_tal_raw = st.selectbox("Taluka", ["All"] + all_talukas, index=0)
    sel_talukas = all_talukas if sel_tal_raw == "All" else [sel_tal_raw]

    st.divider()
    st.caption(f"📊 Classified records: **{len(df):,}**")
    st.caption(f"🏭 OEMs: **{df['Maker'].nunique()}**")
    st.caption(f"📍 Pincodes: **{df['Pincode'].nunique()}**")
    st.caption(f"🗺️ Talukas: **{df['Taluka'].nunique()}**")

dff = df[
    df["AppType"].isin(sel_app) &
    df["Month"].isin(sel_months) &
    df["Taluka"].isin(sel_talukas)
].copy()

if dff.empty:
    st.warning("No records match the current sidebar filters.")
    st.stop()

total = len(dff)

# ── KPI cards ──────────────────────────────────────────────────────────────────
oem_vc   = dff["Maker"].value_counts()
pin_vc   = dff["Pincode"].value_counts()
tal_vc   = dff["Taluka"].value_counts()
top_oem  = oem_vc.idxmax()
top_pin  = pin_vc.idxmax() if not pin_vc.empty else "N/A"
top_tal  = tal_vc.idxmax()

k1,k2,k3,k4,k5 = st.columns(5)
def kpi(col, num, label, sub=""):
    col.markdown(f"""
    <div class='kpi-card'>
      <div class='kpi-num'>{num}</div>
      <div class='kpi-lbl'>{label}</div>
      <div class='kpi-sub'>{sub}</div>
    </div>""", unsafe_allow_html=True)

kpi(k1, f"{total:,}",                        "Total Registrations",    "filtered")
kpi(k2, short(top_oem),                       "Market Leader",          f"{oem_vc[top_oem]/total*100:.1f}% share")
kpi(k3, top_pin,                              "Top Pincode",            f"{pin_vc[top_pin]} units" if top_pin!="N/A" else "")
kpi(k4, top_tal,                              "Top Taluka",             f"{tal_vc[top_tal]} units")
kpi(k5, f"{dff['Seat Capacity'].median():.0f}","Median Seat Capacity",  "seats per vehicle")

st.markdown("<br>", unsafe_allow_html=True)

# ── tabs ───────────────────────────────────────────────────────────────────────
t1,t2,t3,t4,t5,t6 = st.tabs([
    "📊 Market Share",
    "🗺️ Region",
    "📍 Pincode",
    "🏘️ Taluka",
    "🏭 OEM Vehicles",
    "📋 Data",
])

# ════════════════════════════════════════
# T1 — MARKET SHARE
# ════════════════════════════════════════
with t1:
    oem_df = oem_vc.reset_index()
    oem_df.columns = ["Maker","Units"]
    oem_df["Share"]   = (oem_df["Units"]/total*100).round(1)
    oem_df["Label"]   = oem_df["Maker"].apply(short)
    oem_df["Color"]   = oem_df["Maker"].apply(color_for)

    c1,c2 = st.columns([1.15, 0.85])

    with c1:
        st.markdown("<div class='sec-hdr'>OEM Market Share</div>", unsafe_allow_html=True)
        fig = go.Figure(go.Bar(
            x=oem_df["Share"], y=oem_df["Label"], orientation="h",
            marker_color=oem_df["Color"],
            text=[f"{u} units  ·  {s:.1f}%" for u,s in zip(oem_df["Units"],oem_df["Share"])],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Units: %{customdata[0]}<br>Share: %{x:.1f}%<extra></extra>",
            customdata=oem_df[["Units"]].values,
        ))
        fig.update_layout(
            height=320, plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(l=0,r=120,t=10,b=20),
            xaxis=dict(range=[0, oem_df["Share"].max()*1.35], showgrid=True, gridcolor="#f0f0f0",
                       title="Market Share (%)"),
            yaxis=dict(categoryorder="total ascending"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("<div class='sec-hdr'>Donut</div>", unsafe_allow_html=True)
        fig2 = go.Figure(go.Pie(
            labels=oem_df["Label"], values=oem_df["Units"],
            hole=0.58, marker_colors=oem_df["Color"],
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>Units: %{value}<br>%{percent}<extra></extra>",
        ))
        fig2.update_layout(
            height=320, paper_bgcolor="white", margin=dict(l=0,r=0,t=10,b=10),
            showlegend=False,
            annotations=[dict(text=f"<b>{total}</b><br>total", x=.5, y=.5,
                              font_size=15, showarrow=False)],
        )
        st.plotly_chart(fig2, use_container_width=True)

    # podium
    st.markdown("<div class='sec-hdr'>Leaderboard</div>", unsafe_allow_html=True)
    cols = st.columns(min(len(oem_df),5))
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣"]
    for i, row in oem_df.head(5).iterrows():
        with cols[i]:
            st.markdown(f"""
            <div class='kpi-card'>
              <div style='font-size:1.4rem'>{medals[i]}</div>
              <div style='font-size:.9rem;font-weight:700;color:#1a2b4a;margin-top:4px'>{short(row['Maker'])}</div>
              <div class='kpi-num' style='font-size:1.5rem'>{row['Units']}</div>
              <div class='kpi-sub'>{row['Share']:.1f}%</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # app-type + trend side by side
    ca,cb = st.columns(2)
    with ca:
        st.markdown("<div class='sec-hdr'>Application Mix by OEM</div>", unsafe_allow_html=True)
        app_oem = dff.groupby(["AppType","Maker"]).size().reset_index(name="Units")
        app_oem["Label"] = app_oem["Maker"].apply(short)
        fig3 = px.bar(app_oem, x="AppType", y="Units", color="Label",
                      color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                      barmode="stack",
                      labels={"AppType":"Application","Units":"Registrations","Label":"OEM"})
        fig3.update_layout(**bar_layout(320))
        fig3.update_layout(xaxis=dict(tickangle=-25))
        st.plotly_chart(fig3, use_container_width=True)

    with cb:
        st.markdown("<div class='sec-hdr'>Monthly Trend by OEM</div>", unsafe_allow_html=True)
        mon_oem = dff.groupby(["Month","Maker"]).size().reset_index(name="Units")
        mon_oem["Label"] = mon_oem["Maker"].apply(short)
        fig4 = px.line(mon_oem, x="Month", y="Units", color="Label", markers=True,
                       color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                       labels={"Month":"Month","Units":"Registrations","Label":"OEM"})
        fig4.update_layout(**bar_layout(320))
        fig4.update_layout(xaxis=dict(tickangle=-25))
        st.plotly_chart(fig4, use_container_width=True)

# ════════════════════════════════════════
# T2 — REGION
# ════════════════════════════════════════
with t2:
    st.markdown("<div class='sec-hdr'>Market Share by Region / RTO Office</div>", unsafe_allow_html=True)

    reg_total = dff.groupby("Office Name").size().reset_index(name="Total")
    reg_oem   = dff.groupby(["Office Name","Maker"]).size().reset_index(name="Units")
    reg_oem   = reg_oem.merge(reg_total, on="Office Name")
    reg_oem["Share%"] = (reg_oem["Units"]/reg_oem["Total"]*100).round(1)
    reg_oem["Label"]  = reg_oem["Maker"].apply(short)

    r1,r2 = st.columns([1.4, 0.6])
    with r1:
        fig5 = px.bar(reg_oem, x="Office Name", y="Units", color="Label",
                      color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                      barmode="stack", text="Units",
                      hover_data={"Share%":True},
                      labels={"Office Name":"Region","Units":"Registrations","Label":"OEM"},
                      title="Volume by Region")
        fig5.update_traces(textposition="inside", textfont_size=10)
        fig5.update_layout(**bar_layout(380))
        st.plotly_chart(fig5, use_container_width=True)

    with r2:
        # summary table
        top_per_reg = reg_oem.loc[reg_oem.groupby("Office Name")["Units"].idxmax()][
            ["Office Name","Total","Label","Share%"]].rename(
            columns={"Office Name":"Region","Total":"Units","Label":"Leader","Share%":"Leader %"})
        st.markdown("**Region Summary**")
        st.dataframe(top_per_reg.sort_values("Units",ascending=False),
                     hide_index=True, use_container_width=True, height=320)

    # 100% stacked
    st.markdown("<div class='sec-hdr'>Share % by Region (100% stacked)</div>", unsafe_allow_html=True)
    fig6 = px.bar(reg_oem, x="Office Name", y="Share%", color="Label",
                  color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                  barmode="stack", text="Units",
                  labels={"Office Name":"Region","Share%":"Market Share (%)","Label":"OEM"})
    fig6.update_traces(textposition="inside", textfont_size=10)
    fig6.update_layout(**bar_layout(340))
    fig6.update_layout(yaxis=dict(range=[0,105]))
    st.plotly_chart(fig6, use_container_width=True)

    # heatmap OEM × AppType
    st.markdown("<div class='sec-hdr'>OEM × Application Type Heatmap</div>", unsafe_allow_html=True)
    pivot = dff.pivot_table(index="Maker", columns="AppType", aggfunc="size", fill_value=0)
    pivot.index = [short(i) for i in pivot.index]
    fig7 = px.imshow(pivot, text_auto=True, color_continuous_scale="Blues", aspect="auto",
                     labels={"color":"Units"})
    fig7.update_layout(height=260, paper_bgcolor="white", margin=dict(l=80,r=10,t=20,b=60),
                       coloraxis_showscale=False)
    st.plotly_chart(fig7, use_container_width=True)

# ════════════════════════════════════════
# T3 — PINCODE
# ════════════════════════════════════════
with t3:
    pin_total = dff.groupby("Pincode").size().reset_index(name="Total")
    pin_oem   = dff.groupby(["Pincode","Maker"]).size().reset_index(name="Units")
    pin_oem   = pin_oem.merge(pin_total, on="Pincode")
    pin_oem["Share%"] = (pin_oem["Units"]/pin_oem["Total"]*100).round(1)
    pin_oem["Label"]  = pin_oem["Maker"].apply(short)
    pin_oem["Taluka"] = pin_oem["Pincode"].map(PINCODE_TALUKA).fillna("Other")

    top_n = st.slider("Show top N pincodes by volume", 5, min(40, pin_total.shape[0]), 20, key="top_n_pin")
    top_pins = pin_total.nlargest(top_n,"Total")["Pincode"].tolist()
    plot_data = pin_oem[pin_oem["Pincode"].isin(top_pins)]

    st.markdown("<div class='sec-hdr'>Volume by Pincode (stacked OEM)</div>", unsafe_allow_html=True)
    fig8 = px.bar(plot_data.sort_values("Total", ascending=False),
                  x="Pincode", y="Units", color="Label",
                  color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                  barmode="stack",
                  hover_data={"Taluka":True,"Share%":True},
                  labels={"Units":"Registrations","Label":"OEM"},
                  title=f"Top {top_n} Pincodes by Volume")
    fig8.update_layout(**bar_layout(400))
    fig8.update_layout(xaxis=dict(type="category",tickangle=-45))
    st.plotly_chart(fig8, use_container_width=True)

    st.markdown("<div class='sec-hdr'>Market Share % by Pincode (100% stacked)</div>",
                unsafe_allow_html=True)
    fig9 = px.bar(plot_data.sort_values("Total",ascending=False),
                  x="Pincode", y="Share%", color="Label",
                  color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                  barmode="stack", hover_data={"Units":True,"Taluka":True},
                  labels={"Share%":"Market Share (%)","Label":"OEM"},
                  title=f"Top {top_n} Pincodes — Share %")
    fig9.update_layout(**bar_layout(380))
    fig9.update_layout(xaxis=dict(type="category",tickangle=-45),yaxis=dict(range=[0,105]))
    st.plotly_chart(fig9, use_container_width=True)

    st.markdown("<div class='sec-hdr'>Pincode Market Leader Table</div>", unsafe_allow_html=True)
    leader_pin = pin_oem.loc[pin_oem.groupby("Pincode")["Units"].idxmax()].copy()
    leader_pin = leader_pin.merge(pin_total, on="Pincode", suffixes=("","_t"))
    tbl = leader_pin.sort_values("Total_t",ascending=False)[
        ["Pincode","Taluka","Total_t","Label","Share%"]
    ].rename(columns={"Total_t":"Total Units","Label":"Market Leader","Share%":"Leader Share %"})
    tbl.insert(0,"Rank", range(1, len(tbl)+1))

    def hl(val):
        cmap = {"Tata":"#dbeafe","Force":"#dcfce7","Eicher/VE":"#ffedd5",
                "Mahindra":"#f3e8ff","Maruti":"#fee2e2","SML Isuzu":"#ccfbf1",
                "Ashok Leyland":"#fef3c7","SML Mahindra":"#f1f5f9"}
        return f"background-color:{cmap.get(val,'#f9fafb')}"

    st.dataframe(
        tbl.style.applymap(hl, subset=["Market Leader"])
               .format({"Leader Share %":"{:.1f}%"}),
        use_container_width=True, hide_index=True, height=420
    )

# ════════════════════════════════════════
# T4 — TALUKA
# ════════════════════════════════════════
with t4:
    tal_total = dff.groupby("Taluka").size().reset_index(name="Total")
    tal_oem   = dff.groupby(["Taluka","Maker"]).size().reset_index(name="Units")
    tal_oem   = tal_oem.merge(tal_total, on="Taluka")
    tal_oem["Share%"] = (tal_oem["Units"]/tal_oem["Total"]*100).round(1)
    tal_oem["Label"]  = tal_oem["Maker"].apply(short)

    ta1, ta2 = st.columns([1.35, 0.65])

    with ta1:
        st.markdown("<div class='sec-hdr'>Volume by Taluka (stacked OEM)</div>", unsafe_allow_html=True)
        fig10 = px.bar(tal_oem.sort_values("Total",ascending=False),
                       x="Taluka", y="Units", color="Label",
                       color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                       barmode="stack", hover_data={"Share%":True}, text="Units",
                       labels={"Units":"Registrations","Label":"OEM"})
        fig10.update_traces(textposition="inside", textfont_size=11)
        fig10.update_layout(**bar_layout(420))
        fig10.update_layout(xaxis=dict(tickangle=-25))
        st.plotly_chart(fig10, use_container_width=True)

    with ta2:
        st.markdown("**Taluka Leaders**")
        leader_tal = tal_oem.loc[tal_oem.groupby("Taluka")["Units"].idxmax()].copy()
        leader_tal = leader_tal.merge(tal_total, on="Taluka", suffixes=("","_t"))
        tbl2 = leader_tal.sort_values("Total_t",ascending=False)[
            ["Taluka","Total_t","Label","Share%"]
        ].rename(columns={"Total_t":"Units","Label":"Leader","Share%":"Leader %"})
        st.dataframe(tbl2, hide_index=True, use_container_width=True, height=380)

    # 100% stacked
    st.markdown("<div class='sec-hdr'>Market Share % by Taluka (100% stacked)</div>",
                unsafe_allow_html=True)
    fig11 = px.bar(tal_oem.sort_values("Total",ascending=False),
                   x="Taluka", y="Share%", color="Label",
                   color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                   barmode="stack", text="Units",
                   labels={"Share%":"Market Share (%)","Label":"OEM"})
    fig11.update_traces(textposition="inside", textfont_size=11)
    fig11.update_layout(**bar_layout(380))
    fig11.update_layout(xaxis=dict(tickangle=-25),yaxis=dict(range=[0,105]))
    st.plotly_chart(fig11, use_container_width=True)

    # application mix
    st.markdown("<div class='sec-hdr'>Application Mix % by Taluka</div>", unsafe_allow_html=True)
    tal_app = dff.groupby(["Taluka","AppType"]).size().reset_index(name="Units")
    tal_app = tal_app.merge(tal_total, on="Taluka")
    tal_app["Share%"] = (tal_app["Units"]/tal_app["Total"]*100).round(1)
    fig12 = px.bar(tal_app.sort_values("Total",ascending=False),
                   x="Taluka", y="Share%", color="AppType",
                   barmode="stack", text="Units",
                   labels={"Share%":"Share (%)","AppType":"Application"})
    fig12.update_traces(textposition="inside", textfont_size=10)
    fig12.update_layout(**bar_layout(360))
    fig12.update_layout(xaxis=dict(tickangle=-25),yaxis=dict(range=[0,105]))
    st.plotly_chart(fig12, use_container_width=True)

    # pincode drill-down within taluka
    st.markdown("<div class='sec-hdr'>Drill-down: Pincodes within a Taluka</div>",
                unsafe_allow_html=True)
    chosen = st.selectbox("Select Taluka", sorted(dff["Taluka"].unique()), key="taluka_dd")
    sub = dff[dff["Taluka"]==chosen]
    sub_oem = sub.groupby(["Pincode","Maker"]).size().reset_index(name="Units")
    sub_oem["Label"] = sub_oem["Maker"].apply(short)

    if not sub_oem.empty:
        fig13 = px.bar(sub_oem, x="Pincode", y="Units", color="Label",
                       color_discrete_map={short(k):v for k,v in OEM_COLORS.items()},
                       barmode="stack", text_auto=True,
                       title=f"{chosen} — Pincode-wise OEM breakdown",
                       labels={"Units":"Registrations","Label":"OEM"})
        fig13.update_layout(**bar_layout(340))
        fig13.update_layout(xaxis=dict(type="category",tickangle=-30))
        st.plotly_chart(fig13, use_container_width=True)

        # summary table
        sub_pin_total = sub.groupby("Pincode").size().reset_index(name="Total")
        sub_leader    = sub_oem.loc[sub_oem.groupby("Pincode")["Units"].idxmax()]
        sub_tbl = sub_pin_total.merge(sub_leader[["Pincode","Label","Units"]],
                                       on="Pincode").rename(
            columns={"Total":"Total Units","Label":"Leader","Units":"Leader Units"})
        sub_tbl["Leader Share %"] = (sub_tbl["Leader Units"]/sub_tbl["Total Units"]*100).round(1)
        st.dataframe(sub_tbl.sort_values("Total Units",ascending=False),
                     hide_index=True, use_container_width=True)

# ════════════════════════════════════════
# T5 — OEM VEHICLES
# ════════════════════════════════════════
with t5:
    st.markdown("<div class='sec-hdr'>Vehicles included in this dataset — by OEM</div>",
                unsafe_allow_html=True)
    st.caption("Every OEM and model present after your classification. Shows unit count and application type breakdown per model.")

    # build model summary
    mdl_summary = (
        dff.groupby(["Maker","Model","AppType"])
           .size()
           .reset_index(name="Units")
    )
    mdl_summary["OEM"] = mdl_summary["Maker"].apply(short)
    mdl_summary["Color"] = mdl_summary["Maker"].apply(color_for)

    oem_order = (
        dff.groupby("Maker").size()
           .sort_values(ascending=False)
           .index.tolist()
    )

    for maker in oem_order:
        sub = mdl_summary[mdl_summary["Maker"] == maker].copy()
        if sub.empty:
            continue
        oem_label  = short(maker)
        oem_color  = color_for(maker)
        oem_total  = sub["Units"].sum()
        oem_models = sub["Model"].nunique()

        st.markdown(
            f"""<div style='background:white; border-radius:12px; border:1px solid #e2e8f0;
                padding:1rem 1.25rem; margin-bottom:1rem;'>
              <div style='display:flex; align-items:center; gap:12px; margin-bottom:.6rem;'>
                <div style='width:14px; height:14px; border-radius:50%;
                     background:{oem_color}; flex-shrink:0;'></div>
                <span style='font-weight:700; font-size:1.05rem; color:#1a2b4a;'>{oem_label}</span>
                <span style='margin-left:auto; background:#f1f5f9; border-radius:20px;
                     padding:2px 12px; font-size:.8rem; color:#475569;'>
                  {oem_total} units &nbsp;·&nbsp; {oem_models} model(s)
                </span>
              </div>""",
            unsafe_allow_html=True,
        )

        # one row per model — pivot app types as pill badges
        mdl_pivot = (
            sub.groupby("Model")["Units"].sum()
               .sort_values(ascending=False)
               .reset_index()
        )
        mdl_app = sub.groupby("Model")["AppType"].apply(lambda x: list(x.unique())).reset_index()
        mdl_pivot = mdl_pivot.merge(mdl_app, on="Model")

        APP_COLORS = {
            "School Bus":      ("#dcfce7","#166534"),
            "Passenger Bus":   ("#dbeafe","#1e40af"),
            "Staff Bus":       ("#fef3c7","#92400e"),
            "Ambulance":       ("#fee2e2","#991b1b"),
            "Passenger Van":   ("#f3e8ff","#6b21a8"),
            "Sleeper Bus":     ("#e0e7ff","#3730a3"),
            "Tourist / Travel":("#ffedd5","#9a3412"),
            "Other":           ("#f1f5f9","#475569"),
        }

        rows_html = ""
        for _, row in mdl_pivot.iterrows():
            pills = ""
            for a in row["AppType"]:
                bg, fg = APP_COLORS.get(a, APP_COLORS["Other"])
                pills += (
                    f"<span style='background:{bg}; color:{fg}; "
                    f"padding:1px 8px; border-radius:12px; font-size:.75rem; font-weight:600; margin:1px 2px;'>"
                    f"{a}</span>"
                )
            rows_html += (
                f"<tr>"
                f"<td style='padding:5px 10px; font-size:.88rem; color:#1a2b4a;'>{row['Model']}</td>"
                f"<td style='padding:5px 10px; font-size:.88rem; text-align:center; font-weight:600; color:{oem_color};'>{row['Units']}</td>"
                f"<td style='padding:5px 10px;'>{pills}</td>"
                f"</tr>"
            )

        st.markdown(
            f"""<table style='width:100%; border-collapse:collapse;'>
              <thead>
                <tr style='border-bottom:1.5px solid #e2e8f0;'>
                  <th style='padding:4px 10px; text-align:left; font-size:.8rem; color:#64748b; font-weight:600;'>Model</th>
                  <th style='padding:4px 10px; text-align:center; font-size:.8rem; color:#64748b; font-weight:600;'>Units</th>
                  <th style='padding:4px 10px; text-align:left; font-size:.8rem; color:#64748b; font-weight:600;'>Application Types</th>
                </tr>
              </thead>
              <tbody>{rows_html}</tbody>
            </table></div>""",
            unsafe_allow_html=True,
        )

    # summary bar — models per OEM
    st.markdown("<div class='sec-hdr'>Models per OEM</div>", unsafe_allow_html=True)
    models_per_oem = (
        dff.groupby("Maker")["Model"].nunique()
           .reset_index(name="Models")
           .sort_values("Models", ascending=False)
    )
    models_per_oem["OEM"]   = models_per_oem["Maker"].apply(short)
    models_per_oem["Color"] = models_per_oem["Maker"].apply(color_for)
    fig_mpo = go.Figure(go.Bar(
        x=models_per_oem["OEM"], y=models_per_oem["Models"],
        marker_color=models_per_oem["Color"],
        text=models_per_oem["Models"], textposition="outside",
        hovertemplate="<b>%{x}</b><br>%{y} distinct model(s)<extra></extra>",
    ))
    fig_mpo.update_layout(
        height=300, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(l=0,r=10,t=20,b=40),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0", title="Distinct Models"),
        xaxis=dict(title=""),
    )
    st.plotly_chart(fig_mpo, use_container_width=True)


# ════════════════════════════════════════
# T6 — DATA
# ════════════════════════════════════════
with t6:
    st.markdown("<div class='sec-hdr'>Filtered Records</div>", unsafe_allow_html=True)
    st.caption(f"{len(dff):,} records match current filters")

    col_map = {
        "Registration Number":"Reg No.", "Maker":"OEM", "Model":"Model",
        "BodyType":"Body", "Vehicle Category":"Category", "AppType":"Application",
        "Seat Capacity":"Seats", "Fuel":"Fuel", "Dealer Name":"Dealer",
        "Registration Date":"Reg Date", "Pincode":"Pincode", "Taluka":"Taluka",
    }
    disp = dff[[c for c in col_map if c in dff.columns]].rename(columns=col_map)

    srch = st.text_input("🔍 Search across all columns", "")
    if srch:
        mask = disp.apply(lambda r: r.astype(str).str.contains(srch,case=False).any(), axis=1)
        disp = disp[mask]

    st.dataframe(disp.reset_index(drop=True), use_container_width=True, height=480)
    csv = disp.to_csv(index=False).encode()
    st.download_button("⬇️ Download CSV", csv, "cv_passenger_filtered.csv", "text/csv")

# ── footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption("🚌 CV Passenger Market Share Dashboard · 3-wheelers excluded · Pincode → Taluka: Nashik district mapping")
