import json
import sqlite3
from datetime import datetime
from transformers import pipeline


class FeedbackHandler:
    def __init__(self):
        self.emotion_model = pipeline(
            "text-classification", model="nateraw/bert-base-uncased-emotion")
        self.feedback_db = "riya_feedback.db"
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.feedback_db)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS feedback
                    (timestamp TEXT, user_input TEXT, response TEXT, 
                     feedback_score INTEGER, emotion TEXT, context TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS learning_stats
                    (category TEXT, success_count INTEGER, total_count INTEGER)''')
        conn.commit()
        conn.close()

    def save_feedback(self, user_input, response, feedback_score, emotion, context=None):
        conn = sqlite3.connect(self.feedback_db)
        c = conn.cursor()
        c.execute("INSERT INTO feedback VALUES (?, ?, ?, ?, ?, ?)",
                  (datetime.now().isoformat(), user_input, response,
                   feedback_score, emotion, json.dumps(context)))
        conn.commit()
        conn.close()

    def analyze_performance(self):
        conn = sqlite3.connect(self.feedback_db)
        c = conn.cursor()
        c.execute(
            "SELECT AVG(feedback_score), emotion FROM feedback GROUP BY emotion")
        emotion_stats = c.fetchall()
        conn.close()
        return emotion_stats

    def get_successful_patterns(self, min_score=4):
        conn = sqlite3.connect(self.feedback_db)
        c = conn.cursor()
        c.execute(
            "SELECT response, emotion FROM feedback WHERE feedback_score >= ?", (min_score,))
        patterns = c.fetchall()
        conn.close()
        return patterns
