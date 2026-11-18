import streamlit as st
from datetime import date, timedelta
import logic

st.title("Welcome to Beyond28!")
st.write("Cycle tracking for women who may experience cycle irregularities.")

if "starts" not in st.session_state:
    st.session_state.starts = []    # createes a list to store the start dates of cycles

st.header("Log your cycle")
new_start = st.date_input("Enter the start date of your cycle:", value=date.today())
max_value = date.today()
if st.button("Save cycle start date"):
    if new_start in st.session_state.starts:
        st.warning("This start date has already been logged.")
    else:
        st.session_state.starts.append(new_start)
        st.success(f"Cycle start date {new_start} saved!")

if st.button("Load demo data:"):
    gaps = [28, 30, 32, 29, 31, 27, 33, 28, 30, 29] # cycle length in days example
    starts = [date.today() - timedelta(days=20)]  # starting point for demo data
    for gap in reversed(gaps):
        starts.insert(0, starts[0] - timedelta(days=gap))
        st.session_state.starts = starts

st.write(f"Cycles logged: {len(st.session_state.starts)}")