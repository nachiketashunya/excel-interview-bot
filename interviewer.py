import os
import json
import time
import google.generativeai as genai

# --- Configuration and Setup ---

# This script assumes the API key is set as an environment variable
# or Streamlit secret. No changes are needed here.

try:
    # Attempt to get API key from Streamlit secrets first
    import streamlit as st
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        # Fallback to environment variable if not in secrets
        api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        genai.configure(api_key=api_key)
    else:
        # This will be handled in the Streamlit app's UI
        pass
except (ImportError, ValueError):
    # Fallback for non-Streamlit environments
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)


class JobWinningInterviewAgent:
    """
    An enhanced, industry-grade agent with behavioral questions, advanced
    evaluation, a hint system, and a built-in feedback loop for continuous improvement.
    (This is the same class as the previous version, optimized for Streamlit integration)
    """
    def __init__(self, candidate_name, model_name="gemini-1.5-flash"):
        if not api_key:
            raise ValueError("Gemini API key is not configured.")
        self.candidate_name = candidate_name
        self.model = genai.GenerativeModel(model_name)
        self.interview_role = None
        self.skill_profile = {
            "Data Cleaning": {"status": "Untested", "score": 0, "efficiency": 0, "evidence": ""},
            "Data Analysis": {"status": "Untested", "score": 0, "efficiency": 0, "evidence": ""},
            "Data Summarization": {"status": "Untested", "score": 0, "efficiency": 0, "evidence": ""},
            "Behavioral": {"status": "Untested", "score": 0, "evidence": ""}
        }
        self.case_study_data = None
        self.conversation_history = []

    def _call_gemini(self, prompt, is_json=False):
        """Helper to call the Gemini API and handle responses."""
        try:
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            response = self.model.generate_content(prompt, safety_settings=safety_settings)
            if is_json:
                text = response.text.strip().replace("```json", "").replace("```", "")
                return json.loads(text)
            return response.text
        except (json.JSONDecodeError, Exception) as e:
            print(f"--- Model or JSON Error: {e} ---")
            if is_json:
                return {"error": "Failed to get a valid response from the model."}
            return "My apologies, there was a system error. Let's move on."

    def _introduce_case_study(self):
        prompt = f"""
        You are an AI Interviewer. Your task is to create a realistic business case study to assess a candidate's Excel skills for a '{self.interview_role}' role.
        The case study needs a simple, text-based dataset with 3-4 columns and a few rows. The data should have some intentional messiness (e.g., extra spaces, inconsistent casing).
        Return ONLY a JSON object with the scenario and the data description.
        """
        self.case_study_data = self._call_gemini(prompt, is_json=True)
        return f"Okay, let's dive into a practical case study.\n\n**Scenario:** {self.case_study_data.get('scenario')}\n\n**Dataset:** {self.case_study_data.get('dataset_description')}\n\nLet's tackle this in a few steps. First, let's talk about cleaning this data."

    def _ask_next_question(self, skill_to_test):
        prompt = f"""
        You are an AI Interviewer guiding a candidate through a case study for a '{self.interview_role}' role.
        The overall scenario is: "{self.case_study_data.get('scenario')}"
        The dataset is: "{self.case_study_data.get('dataset_description')}"
        Your current goal is to assess their skill in: **{skill_to_test}**.
        Formulate a single, clear question to test this skill using the case study context.
        Return ONLY the question as a string.
        """
        return self._call_gemini(prompt)

    def _check_user_intent(self, answer):
        prompt = f"""
        Analyze the user's response: "{answer}".
        Determine the user's intent. Choose ONLY ONE from the following options:
        - 'ANSWERING': The user is directly trying to answer the question.
        - 'HINT_REQUEST': The user is asking for a hint, help, or clarification.
        - 'UNCERTAIN': The user states they don't know the answer or are unsure.
        Return ONLY the single-word intent.
        """
        return self._call_gemini(prompt).strip()

    def _generate_hint(self, question):
        prompt = f"The user is stuck on this question: '{question}'. Provide a brief, encouraging hint to guide them in the right direction without giving away the answer."
        return self._call_gemini(prompt)
        
    def _evaluate_technical_answer(self, question, answer, skill_being_tested):
        prompt = f"""
        You are an expert Senior Analyst evaluating a candidate's response.
        The skill being tested is: **{skill_being_tested}**.
        The question was: "{question}"
        The candidate's answer was: "{answer}"
        Return ONLY a JSON object:
        {{
          "score": <1-5>,
          "justification": "<Reasoning for correctness score>",
          "efficiency_score": <1-5>,
          "efficiency_justification": "<Reasoning for efficiency score>",
          "bot_response": "<A short, conversational reply to the candidate>"
        }}
        """
        evaluation = self._call_gemini(prompt, is_json=True)
        self.skill_profile[skill_being_tested].update({
            "status": "Assessed",
            "score": evaluation.get("score", 0),
            "efficiency": evaluation.get("efficiency_score", 0),
            "evidence": f"Q: {question}\nA: {answer}\nEval: {evaluation.get('justification')}\nEfficency: {evaluation.get('efficiency_justification')}"
        })
        return evaluation.get("bot_response", "Okay, thank you for that.")

    def _ask_and_evaluate_behavioral(self):
        prompt = "Ask one standard behavioral interview question, like 'Tell me about a challenging project' or 'Describe a time you made a mistake'."
        question = self._call_gemini(prompt)
        
        # This will be handled by the Streamlit app, which will get an answer and then call the evaluation part.
        return question

    def evaluate_behavioral_answer(self, question, answer):
        eval_prompt = f"""
        You are a hiring manager evaluating a candidate's response to a behavioral question.
        The question was: "{question}"
        The answer was: "{answer}"
        Evaluate the answer's structure and clarity (e.g., STAR method).
        Assign a score from 1 (unstructured) to 5 (clear and well-structured).
        Provide a brief justification.
        Return ONLY a JSON object: {{"score": <1-5>, "justification": "<Your reasoning>"}}
        """
        evaluation = self._call_gemini(eval_prompt, is_json=True)
        self.skill_profile["Behavioral"].update({
            "status": "Assessed",
            "score": evaluation.get("score", 0),
            "evidence": f"Q: {question}\nA: {answer}\nEval: {evaluation.get('justification')}"
        })
        return "Thank you for sharing that."
    
    def generate_final_report(self):
        """Generates the final, structured performance report."""
        summary_prompt = f"""
        You are a Senior Hiring Manager creating a final candidate report.
        **Candidate Name:** {self.candidate_name}, **Role:** {self.interview_role}
        **Final Skill Profile:** {json.dumps(self.skill_profile, indent=2)}
        **Your Task:**
        Write a formal, structured performance report in Markdown. The report must include:
        1. **Overall Summary:** A brief overview.
        2. **Technical Strengths:** List skills where the score was 4 or 5. Mention efficiency if it was a highlight.
        3. **Areas for Development:** List skills where the score was 3 or less. Be constructive.
        4. **Behavioral Competency:** Comment on the structure and clarity of their behavioral answer.
        5. **Final Recommendation:** (Strongly Recommend, Recommend, Recommend with Reservations, Do Not Recommend) with a one-sentence justification.
        """
        final_report = self._call_gemini(summary_prompt)

        # Create feedback log as well
        feedback_data = {
            "candidate_name": self.candidate_name,
            "interview_role": self.interview_role,
            "final_skill_profile": self.skill_profile,
            "ai_generated_report": final_report,
            "full_transcript": self.conversation_history,
            "timestamp": time.time()
        }
        filename = f"interview_log_{self.candidate_name.replace(' ','_')}_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(feedback_data, f, indent=4)
        print(f"--- [Admin] Interview data saved to '{filename}' for quality review. ---")
        
        return final_report

