import streamlit as st
import time
from job_winning_interviewer import JobWinningInterviewAgent, api_key

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Excel Interviewer",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="auto"
)

# --- App Title and Description ---
st.title("🤖 AI-Powered Excel Mock Interviewer")
st.markdown("""
Welcome! This is an AI-powered mock interviewer designed to help you practice for your next technical screening. 
It uses a case-study approach to assess your practical Excel skills. Good luck!
""")

# --- State Management ---
if 'stage' not in st.session_state:
    st.session_state.stage = 'start'
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'agent' not in st.session_state:
    st.session_state.agent = None
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
if 'current_skill' not in st.session_state:
    st.session_state.current_skill = None
# NEW: State for handling the exit confirmation
if 'confirm_exit' not in st.session_state:
    st.session_state.confirm_exit = False

# --- Helper Functions ---
def reset_interview():
    """NEW: Resets the entire session state to start over."""
    st.session_state.stage = 'start'
    st.session_state.messages = []
    st.session_state.agent = None
    st.session_state.current_question = None
    st.session_state.current_skill = None
    st.session_state.confirm_exit = False
    st.success("Interview has been reset.")
    time.sleep(2) # Give user time to see the message

def start_interview(name, role):
    """Initializes the interview agent and moves to the case study stage."""
    st.session_state.agent = JobWinningInterviewAgent(candidate_name=name)
    st.session_state.agent.interview_role = role
    st.session_state.messages = [{"role": "assistant", "content": f"Hello {name}! Welcome to the interview. The role is set to {role}."}]
    
    with st.spinner("AI is generating a custom case study for you..."):
        case_study_intro = st.session_state.agent._introduce_case_study()
    
    st.session_state.messages.append({"role": "assistant", "content": case_study_intro})
    st.session_state.stage = 'technical_interview'
    ask_next_technical_question()

def ask_next_technical_question():
    """Asks the next technical question based on the skill profile."""
    technical_skills = ["Data Cleaning", "Data Analysis", "Data Summarization"]
    next_skill_to_test = next((skill for skill in technical_skills if st.session_state.agent.skill_profile[skill]["status"] == "Untested"), None)
    
    if next_skill_to_test:
        st.session_state.current_skill = next_skill_to_test
        with st.spinner("AI is thinking of the next question..."):
            question = st.session_state.agent._ask_next_question(next_skill_to_test)
        st.session_state.current_question = question
        st.session_state.messages.append({"role": "assistant", "content": question})
    else:
        st.session_state.stage = 'behavioral_interview'
        ask_behavioral_question()

def ask_behavioral_question():
    """Asks the behavioral question."""
    st.session_state.messages.append({"role": "assistant", "content": "Great, that concludes the technical case study. Let's move on to one final behavioral question."})
    with st.spinner("..."):
        question = st.session_state.agent._ask_and_evaluate_behavioral()
    st.session_state.current_question = question
    st.session_state.messages.append({"role": "assistant", "content": question})
    
def handle_user_response(prompt):
    """Handles all user responses based on the current interview stage."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    agent = st.session_state.agent
    
    if st.session_state.stage == 'technical_interview':
        with st.spinner("AI is analyzing your answer..."):
            intent = agent._check_user_intent(prompt)
            if intent == "ANSWERING":
                bot_response = agent._evaluate_technical_answer(st.session_state.current_question, prompt, st.session_state.current_skill)
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                ask_next_technical_question()
            elif intent == "HINT_REQUEST":
                hint = agent._generate_hint(st.session_state.current_question)
                st.session_state.messages.append({"role": "assistant", "content": f"Of course. Here's a hint: {hint}"})
            else: # UNCERTAIN
                agent.skill_profile[st.session_state.current_skill]["status"] = "Skipped"
                st.session_state.messages.append({"role": "assistant", "content": "No problem, let's move on."})
                ask_next_technical_question()

    elif st.session_state.stage == 'behavioral_interview':
        with st.spinner("AI is analyzing your answer..."):
            bot_response = agent.evaluate_behavioral_answer(st.session_state.current_question, prompt)
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
        st.session_state.stage = 'report'

# --- UI Rendering ---

# Check for API Key first
if not api_key:
    st.error("Your Gemini API key is not configured!")
    st.info("Please add your GEMINI_API_KEY to your Streamlit secrets to run this app.")
else:
    if st.session_state.stage == 'start':
        st.header("🏁 Get Started")
        with st.form("start_form"):
            name = st.text_input("Enter your name", "Candidate")
            role = st.selectbox("Select the role you're applying for", ["Data Analytics", "Finance", "Operations"])
            submitted = st.form_submit_button("Start Interview")
            if submitted:
                start_interview(name, role)
                st.rerun()

    elif st.session_state.stage in ['technical_interview', 'behavioral_interview']:
        st.header("💬 Interview in Progress...")
        
        # NEW: Add the exit button and confirmation logic to the sidebar
        with st.sidebar:
            st.warning("Need to end the session?")
            if st.button("Exit Interview", use_container_width=True):
                st.session_state.confirm_exit = True
        
        if st.session_state.confirm_exit:
            st.error("Are you sure you want to exit? All progress will be lost.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, Exit Now", use_container_width=True, type="primary"):
                    reset_interview()
                    st.rerun()
            with col2:
                if st.button("No, Continue Interview", use_container_width=True):
                    st.session_state.confirm_exit = False
                    st.rerun()
        
        # The main chat interface
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        if prompt := st.chat_input("Your answer..."):
            handle_user_response(prompt)
            st.rerun()

    elif st.session_state.stage == 'report':
        st.header("📊 Your Performance Report")
        st.balloons()
        st.success("Congratulations on completing the interview!")
        with st.spinner("Generating your detailed feedback report..."):
            report = st.session_state.agent.generate_final_report()
            st.markdown(report)
            st.info("A detailed log of this interview has been saved for review.")
        
        if st.button("Start New Interview"):
            reset_interview()
            st.rerun()

