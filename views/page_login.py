import streamlit as st
import streamlit.components.v1 as components

from core.auth import check_credentials, do_login

# Button colour injected via JS so it wins over Streamlit's emotion CSS
_BTN_JS = """
<script>
(function() {
    var BG   = '#1a2535';
    var HBG  = '#2c3e57';
    var sel  = 'button[kind="primary"], [data-testid="stBaseButton-primary"] button';

    function applyStyles() {
        var doc = window.parent ? window.parent.document : document;
        doc.querySelectorAll(sel).forEach(function(btn) {
            btn.style.setProperty('background-color', BG,     'important');
            btn.style.setProperty('color',            '#fff', 'important');
            btn.style.setProperty('border',           'none', 'important');
            btn.style.setProperty('border-radius',    '10px', 'important');
            btn.style.setProperty('height',           '48px', 'important');
            btn.style.setProperty('font-weight',      '600',  'important');
            btn.style.setProperty('font-size',        '15px', 'important');
            btn.style.setProperty('letter-spacing',   '.3px', 'important');
            btn.style.setProperty('box-shadow', '0 2px 8px rgba(26,37,53,.30)', 'important');
            btn.onmouseenter = function() {
                this.style.setProperty('background-color', HBG, 'important');
            };
            btn.onmouseleave = function() {
                this.style.setProperty('background-color', BG, 'important');
            };
        });
    }

    applyStyles();
    [100, 300, 600, 1200].forEach(function(t){ setTimeout(applyStyles, t); });

    var doc = window.parent ? window.parent.document : document;
    new MutationObserver(applyStyles).observe(doc.body, {childList:true, subtree:true});
})();
</script>
"""


def render() -> None:
    st.markdown(
        """
        <style>
        /* ── Lock scroll ────────────────────────────────────────────────────── */
        html, body { overflow: hidden !important; height: 100vh !important; }

        /* ── Hide Streamlit chrome ─────────────────────────────────────────── */
        [data-testid="stHeader"],
        section[data-testid="stSidebar"] { display: none !important; }

        /* ── Grey page background ──────────────────────────────────────────── */
        [data-testid="stAppViewContainer"] { background: #f0f0f2 !important; }
        [data-testid="stAppViewBlockContainer"] {
            padding: 0 !important;
            max-width: 100% !important;
        }
        [data-testid="stMain"] { padding: 0 !important; }

        /* ── Centre card vertically ────────────────────────────────────────── */
        [data-testid="stHorizontalBlock"] {
            position: fixed !important;
            top: 50% !important;
            left: 0 !important;
            right: 0 !important;
            transform: translateY(-50%) !important;
            margin: 0 !important;
            padding: 0 16px !important;
            box-sizing: border-box !important;
        }

        /* ── White card ─────────────────────────────────────────────────────── */
        [data-testid="stHorizontalBlock"]
            > div:nth-child(2)
            > [data-testid="stVerticalBlock"] {
            background: #ffffff;
            border-radius: 14px;
            box-shadow: 0 4px 28px rgba(0,0,0,.09), 0 1px 5px rgba(0,0,0,.04);
            padding: 44px 40px 38px !important;
        }

        /* ── Typography ─────────────────────────────────────────────────────── */
        .si-title {
            font-size: 26px;
            font-weight: 800;
            color: #1a2535;
            letter-spacing: -.5px;
            margin-bottom: 4px;
        }
        .si-sub {
            font-size: 13.5px;
            color: #93979e;
            line-height: 1.55;
            margin-bottom: 20px;
        }

        /* ── Inputs ─────────────────────────────────────────────────────────── */
        [data-testid="stTextInput"] > div > div {
            border-radius: 8px !important;
            border: 1.5px solid #e4e6eb !important;
            background: #ffffff !important;
            box-shadow: none !important;
            transition: border-color .18s, box-shadow .18s !important;
        }
        [data-testid="stTextInput"] > div > div:focus-within {
            border-color: #7c83e5 !important;
            box-shadow: 0 0 0 3px rgba(124,131,229,.15) !important;
        }
        [data-testid="stTextInput"] input {
            font-size: 14px !important;
            color: #1a2535 !important;
        }
        [data-testid="stTextInput"] input::placeholder { color: #b8bcc4 !important; }
        [data-testid="stTextInput"] label {
            font-size: 13px !important;
            font-weight: 600 !important;
            color: #3d4554 !important;
        }

        /* ── Alert ──────────────────────────────────────────────────────────── */
        [data-testid="stAlert"] {
            border-radius: 8px !important;
            font-size: 13px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _, col, _ = st.columns([1, 1.2, 1])

    with col:
        st.markdown(
            '<div class="si-title">Sign In</div>'
            '<div class="si-sub">Enter your credentials to access your account</div>',
            unsafe_allow_html=True,
        )

        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", placeholder="Enter your password", type="password")

        st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

        if st.button("Sign In", icon=":material/login:", type="primary", use_container_width=True):
            ok, role = check_credentials(username, password)
            if ok:
                do_login(username, role)
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.", icon=":material/lock:")

    # Inject JS after the button is in the DOM
    components.html(_BTN_JS, height=0)
