"""
Caption name checker, web version.
Paste or upload a start list -> clean names and on-screen captions, with every change explained
and anything uncertain held back from the graphics export.
"""
import html
import os

import pandas as pd
import streamlit as st

import checker
import kit

kit.page("Caption Check", "Fixes misspelled player names before they go on screen", mark="captions", icon="🔤", theme="booth",
         meta="For broadcast graphics teams · names are invented examples")
st.markdown("""<style>
.strap{display:inline-block;font-family:Arial,Helvetica,sans-serif;box-shadow:0 6px 18px rgba(0,0,0,.35)}
.strap .n{background:#0b1f3a;color:#fff;font-weight:700;font-size:20px;padding:7px 14px;letter-spacing:.3px;border-left:4px solid #e8b100}
.strap .c{background:#e8b100;color:#0b1f3a;font-weight:800;font-size:20px;padding:7px 10px}
.strap .r{display:block;background:#fff;color:#0b1f3a;font-size:13px;padding:4px 14px}
</style>""", unsafe_allow_html=True)

START_COLS = ["Name (as received)", "Country", "Role"]


PORTFOLIO = "https://janis-saulitis-portfolio.netlify.app"
DEMO_VIDEO = os.environ.get("DEMO_VIDEO", PORTFOLIO + "/media/captions.mp4")
answer_box = st.container()
kit.demo(DEMO_VIDEO, "Caption Check in 1 minute",
         '1. The sample list below is already checked: `BERZINS Karlis` became `Kārlis Bērziņš`, the duplicate is held back.\n'
         '2. Add a row: `ozolins janis`, country `lat`. It is **held back**: a person must confirm the spelling.\n'
         '3. Add `Jānis Ozoliņš` under **Reference names** and the row becomes **Fixed**.\n'
         '4. Download the clean list at the bottom. Held-back rows are left out.')

# ------------------------------------------------------------------ input
def sample_frames():
    return (pd.DataFrame(checker.SAMPLE_START, columns=START_COLS),
            pd.DataFrame({"Correct spelling": checker.SAMPLE_REFERENCE}))


def read_table(upload):
    return checker.read_table(upload.name, upload.getvalue())


if "start" not in st.session_state:
    st.session_state.start, st.session_state.ref = sample_frames()
    st.session_state.ver = 0

st.markdown("#### Start list")
b = st.container(horizontal=True)
if b.button("↺ Reset to the sample"):
    st.session_state.start, st.session_state.ref = sample_frames()
    st.session_state.ver += 1
if b.button("Clear the list"):
    st.session_state.start = pd.DataFrame(columns=START_COLS)
    st.session_state.ver += 1
with b.popover("Upload my own list (CSV or Excel)"):
    up = st.file_uploader("First three columns: name, country, role", type=["csv", "xlsx"], key=f"up{st.session_state.ver}")
    if up is not None:
        try:
            t = read_table(up).iloc[:, :3]
            while t.shape[1] < 3:
                t[f"extra{t.shape[1]}"] = ""
            t.columns = START_COLS
            st.session_state.start = t.fillna("")
            st.session_state.ver += 1
            st.rerun()
        except Exception as e:
            st.error(f"Couldn't read that file ({e}). Save it as CSV or Excel with name, country, role columns.")

st.caption("Edit cells directly, paste rows from a spreadsheet, or add rows at the bottom.")
start = st.data_editor(st.session_state.start, num_rows="dynamic", width="stretch", hide_index=True,
                       height=36 * (len(st.session_state.start) + 3) + 4,
                       key=f"start{st.session_state.ver}",
                       column_config={START_COLS[0]: st.column_config.TextColumn(width="large")})

with st.expander(f"Reference names: the correct spellings ({len(st.session_state.ref)} names)"):
    st.caption("The broadcaster's master list. A name that matches one of these, ignoring capitals, "
               "missing diacritics and name order, is replaced by the exact spelling here.")
    ref = st.data_editor(st.session_state.ref, num_rows="dynamic", width="stretch", hide_index=True,
                         height=36 * (len(st.session_state.ref) + 3) + 4, key=f"ref{st.session_state.ver}")
    max_len = st.number_input("Longest caption that fits the name strap (characters)", 10, 40, checker.MAX_CAPTION)

# ------------------------------------------------------------------ check
rows = [tuple("" if pd.isna(v) else str(v) for v in r) for r in start[START_COLS].itertuples(index=False)]
results = checker.process_rows(rows, [str(v) for v in ref.iloc[:, 0].dropna()], int(max_len))
done = [(i + 1, r) for i, r in enumerate(results) if r]

if not done:
    answer_box.info("The start list is empty. Add names above or reset to the sample.")
    st.stop()

held = [r for _, r in done if r["held_back"]]
fixed = sum("FIXED" in r["status"] for _, r in done)
with answer_box:
    st.markdown(f'<div class="k-bug"><div class="tag">Captions</div><div class="t"><b>Fix player names before they go on screen</b>'
                f'<small>Names are invented examples · checked just now</small></div>'
                f'<div class="n">{len(done) - len(held)} ready</div></div>', unsafe_allow_html=True)
    kit.answer("", "", (f"<b>{len(held)}</b> held back until a person confirms: "
                        + ", ".join(html.escape(f"{r['clean']} ({r['status'].lower()})") for r in held) + "."
                        if held else "Nothing needs a person. Every name is checked and ready."),
               [("Checked", str(len(done))), ("Fixed", str(fixed)), ("Held for a human", str(len(held))),
                ("Ready for graphics", str(len(done) - len(held)))])

def state(s):
    if any(h in s for h in checker.HELD_BACK):
        return "Held back"
    return "Fixed" if "FIXED" in s else "New name" if "NEW" in s else "OK"


table = pd.DataFrame([{"Row": n, "As received": r["original"], "Clean name": r["clean"], "Caption": r["caption"],
                       "Country": r["country"], "Role": r["role"], "Status": r["status"], "Why": r["note"]}
                      for n, r in done])
st.markdown("#### Result")
TONE = {"Held back": "bad", "Fixed": "warn", "New name": "info", "OK": "good"}
kit.table([{"n": n, "a": r["original"], "c": r["clean"], "cap": r["caption"], "co": r["country"], "ro": r["role"],
            "s": r["status"].upper(), "w": r["note"]} for n, r in done],
          [kit.col("#", "n", "muted"), kit.col("As received", "a", "muted"), kit.col("Clean name", "c", "strong"),
           kit.col("Caption", "cap"), kit.col("Country", "co", "lang"), kit.col("Role", "ro", "muted"),
           kit.col("Status", "s", "chip", {r["status"].upper(): TONE[state(r["status"])] for _, r in done}),
           kit.col("Why", "w", "wrap")])
st.caption("Fixed: spelling, letters or order restored from the reference list · New name: not in the reference list, "
           "confirm and add it · Held back: needs a person (check, duplicate or too long) and is left out of the export.")

# ------------------------------------------------------------------ preview + export
ready = checker.export_rows(results)
st.markdown("#### How it looks on screen")
st.markdown('<div class="k-stage">' + ("".join(
    f'<span class="lt"><span class="edge"></span><span class="nm"><b>{html.escape(e["caption"])}</b>'
    f'<small>{html.escape(e["role"])}</small></span><span class="co">{html.escape(e["country"])}</span></span>'
    for e in ready[:4]) or '<span style="color:#cfd8e3">Nothing ready yet.</span>') + "</div>", unsafe_allow_html=True)
st.caption("A mock lower third with the first four names that are ready.")

st.markdown("#### Download")
d = st.columns(2)
export = pd.DataFrame(ready, columns=["full_name", "caption", "country", "role"]).rename(
    columns={"full_name": "Full name", "caption": "Caption", "country": "Country", "role": "Role"})
d[0].download_button(f"⬇ Clean list for graphics ({len(ready)} names, CSV)", export.to_csv(index=False).encode("utf-8-sig"),
                     file_name="captions_for_graphics.csv", mime="text/csv", type="primary")
d[1].download_button("⬇ Full check with reasons (CSV)", table.to_csv(index=False).encode("utf-8-sig"),
                     file_name="caption_check.csv", mime="text/csv")

kit.footer("checker.py · first built in Google Sheets, ported to Python and tested on 30 tricky names")
