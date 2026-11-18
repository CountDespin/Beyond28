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