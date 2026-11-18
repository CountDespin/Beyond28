import streamlit as st
from datetime import date, timedelta
import logic

st.title("Welcome to Beyond28!")
st.write("Cycle tracking for women who may experience cycle irregularities.")

if "starts" not in st.session_state:
    st.session_state.starts = []    # createes a list to store the start dates of cycles

st.header("Log your cycle")
new_start = st.date_input("Enter the start date of your cycle:", value=date.today(), max_value=date.today())
if st.button("Save cycle start date"):
    if new_start in st.session_state.starts:
        st.warning("This start date has already been logged.")
    else:
        st.session_state.starts.append(new_start)
        st.success(f"Cycle start date {new_start} saved!")

if st.button("Load demo data:"):
    gaps = [38, 52, 31, 64, 41, 29, 47, 58] # cycle length in days example
    starts = [date.today() - timedelta(days=20)]  # starting point for demo data
    for gap in reversed(gaps):
        starts.insert(0, starts[0] - timedelta(days=gap))
        st.session_state.starts = starts

st.write(f"Cycles logged: {len(st.session_state.starts)}")

st.header("My pattern")
starts = st.session_state.starts
lengths = logic.cycle_lengths(starts)

if len(lengths) == 0:
    st.write("Please log at least two cycle start dates to see your pattern.")
else:
    s = logic.summary(lengths)
    col1, col2, col3 = st.columns(3)
    col1.metric("Cycles", s["count"])
    col2.metric("Average length", f"{s['average']} days")
    col3.metric("Range", f"{s['shortest']} - {s['longest']} days")
    earliest, latest = logic.next_window(starts, lengths)
    st.info(f"Your next cycle is likely between {earliest} and {latest} based on your logged cycles.")

    near_28 = len([n for n in lengths if abs(n - 28) <= 3])
    st.write(f"Only {near_28} of your {len(lengths)} cycles were within 2 days of the typical 28-day cycle.")
    st.bar_chart({"Cycle length (days)":lengths})
    for note in logic.flags(lengths):
        st.warning(note + "Please discuss with your GP if you have any concerns.")

# tips based on mood, all advice is from NHS ()
TIPS = {
    "Cramps": ["Try a warm compress or heating pad on your lower abdomen. Light exercise, like yoga, can also help relieve cramps."],
    "Tiredness": ["Try to maintain regular sleep and wake times. Light exercise can boost your energy levels. Consider a balanced diet rich in iron and vitamins."],
    "Low mood": ["Talk to someone you trust about how you're feeling. Engage in activities that you enjoy and that make you feel good. If low mood persists, consider seeking professional help."],
    "Good mood": ["Keep up the good work! Continue engaging in activities and habits that make you feel happy and fulfilled."],
}
st.header("How are you feeling today?")
feeling = st.selectbox("Pick one", list(TIPS))
for tip in TIPS[feeling]:
    st.write("- " + tip)

# summary for the GP
st.header("Summary for your GP")
if len(lengths) > 0:
    text = "Cycle summary\n\n"
    text += f"Cycles logged: {s['count']}\n"
    text += f"Average {s['average']} days, shortest {s['shortest']}, longest {s['longest']}\n"
    text += "Cycle lengths: " + ", ".join(str(n) for n in lengths) + "\n\n"
    for note in logic.flags(lengths):
        text += "- " + note + "\n"
    st.download_button("Download summary (.txt)", text, file_name="gp-summary.txt")
else:
    st.write("Please log two periods to make a summary.")

# chatbot
st.header("Ask Beyond28")
question = st.text_input("Ask a question about your cycle.")
if st.button("Ask") and question:
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
        reply = client.chat.completions.create(
            model="deepseek-flash",
            messages=[
                {"role": "system", "content": "You only give general health information about periods, irregular cycles, and PMOS (formerly PCOS). YOu never diagnose or provide diagnosis. Suggest a GP when relevant. ALways under 120 or less."},
                {"role": "user", "content": question}
            ],
        )
        st.write(reply.choices[0].message.content)
    except Exception as error:
        st.error(f"Error: ({type(error).__name__}). Please API key and try again.")
