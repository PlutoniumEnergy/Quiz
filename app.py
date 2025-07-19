import streamlit as st
import openai
import PyPDF2
import docx
import json
import os
import time

# Set your OpenAI API key here or via environment variable or Streamlit secrets
openai.api_key = (
    st.secrets.get("OPENAI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or "YOUR_OPENAI_API_KEY"
)

def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"
    return text.strip()

def extract_text_from_docx(file):
    doc = docx.Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return "\n".join(full_text)

def generate_questions(text, num_questions=5):
    prompt = f"""
You are a medical exam question writer. Create {num_questions} challenging, case-based, USMLE-style questions based on the following content.
Each question should have:
- A clinical case scenario as 'question'
- 4 answer choices labeled A, B, C, D
- The letter of the correct answer as 'correct'
- A brief explanation of the answer as 'explanation'

Format the output as a JSON array with this structure:

[
  {{
    "question": "Case scenario text here...",
    "choices": {{
      "A": "Answer choice A",
      "B": "Answer choice B",
      "C": "Answer choice C",
      "D": "Answer choice D"
    }},
    "correct": "A",
    "explanation": "Explanation text here..."
  }},
  ...
]

Content:
{text}
"""
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a board exam question generator."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1500
    )
    return response['choices'][0]['message']['content']

def countdown_timer(seconds):
    placeholder = st.empty()
    for i in range(seconds, 0, -1):
        placeholder.markdown(f"⏳ Time left: {i} seconds")
        time.sleep(1)
    placeholder.markdown("⌛ Time's up! Moving to next question.")

def main():
    st.set_page_config(page_title="🧠 Gamified Case Quiz", layout="wide")
    st.title("🧠 Gamified Case-Based Quiz Generator")

    # Initialize session state variables
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'score' not in st.session_state:
        st.session_state.score = 0
    if 'streak' not in st.session_state:
        st.session_state.streak = 0
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'answered' not in st.session_state:
        st.session_state.answered = False

    uploaded_file = st.file_uploader(
        "Upload your study material (PDF, TXT, DOCX, MD)", type=['pdf', 'txt', 'docx', 'md']
    )

    num_questions = st.slider(
        "Number of questions to generate", min_value=1, max_value=10, value=5
    )

    if uploaded_file and not st.session_state.quiz_started:
        # Extract text based on file type
        try:
            if uploaded_file.name.endswith('.pdf'):
                text = extract_text_from_pdf(uploaded_file)
            elif uploaded_file.name.endswith('.docx'):
                text = extract_text_from_docx(uploaded_file)
            elif uploaded_file.name.endswith('.txt') or uploaded_file.name.endswith('.md'):
                text = uploaded_file.read().decode('utf-8')
            else:
                st.error("Unsupported file format")
                return
        except Exception as e:
            st.error(f"Failed to extract text: {e}")
            return

        with st.expander("Preview Extracted Text (first 1000 chars)"):
            st.write(text[:1000] + ("..." if len(text) > 1000 else ""))

        if st.button("Generate Questions"):
            with st.spinner("Generating questions..."):
                try:
                    questions_json = generate_questions(text, num_questions)
                    questions = json.loads(questions_json)
                    st.session_state.questions = questions
                    st.session_state.quiz_started = True
                    st.session_state.current_question = 0
                    st.session_state.score = 0
                    st.session_state.streak = 0
                    st.session_state.answered = False
                    st.experimental_rerun()
                except json.JSONDecodeError:
                    st.error("Failed to parse generated questions. Showing raw output:")
                    st.code(questions_json)
                except Exception as e:
                    st.error(f"Error generating questions: {e}")

    # Quiz Interface
    if st.session_state.quiz_started:
        q_idx = st.session_state.current_question
        questions = st.session_state.questions
        if q_idx >= len(questions):
            st.success("🎉 Quiz complete!")
            st.markdown(f"**Final Score:** {st.session_state.score} / {len(questions)}")
            st.markdown(f"**Best Streak:** {st.session_state.streak}")
            if st.button("Restart Quiz"):
                st.session_state.quiz_started = False
                st.experimental_rerun()
            return

        question = questions[q_idx]
        st.markdown(f"### Question {q_idx + 1} of {len(questions)}")
        st.markdown(f"**{question['question']}**")

        # Show progress bar
        progress = (q_idx) / len(questions)
        st.progress(progress)

        choice_labels = ["A", "B", "C", "D"]
        options = [f"{label}. {question['choices'][label]}" for label in choice_labels]

        # Disable radio if answered already
        disabled = st.session_state.answered

        user_choice = st.radio(
            "Select your answer:",
            options=options,
            key="answer",
            disabled=disabled
        )

        if not st.session_state.answered and st.button("Submit Answer"):
            selected_label = user_choice[0]  # first char is letter e.g. 'A'
            correct_label = question['correct']

            if selected_label == correct_label:
                st.success("✅ Correct!")
                st.session_state.score += 1
                st.session_state.streak += 1
                st.balloons()
            else:
                st.error(f"❌ Incorrect. Correct answer: {correct_label}.")
                st.session_state.streak = 0

            st.info(f"Explanation: {question['explanation']}")

            st.session_state.answered = True

        if st.session_state.answered:
            if st.button("Next Question"):
                st.session_state.current_question += 1
                st.session_state.answered = False
                st.experimental_rerun()

        # Show score and streak
        st.markdown(f"**Score:** {st.session_state.score} / {len(questions)}")
        st.markdown(f"**Current Streak:** {st.session_state.streak}")

if __name__ == "__main__":
    main()
