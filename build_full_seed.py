"""
build_full_seed.py
------------------
Generates full seed data for all 7 topics x 3 age groups x 3 difficulties.
Produces 63 modules, 63 scenarios, and 315 questions.
Overwrites data/seed_content/ JSON files.
"""

import json
from pathlib import Path

TOPICS = [
    ("password_safety", "🔑", "Password Safety"),
    ("phishing", "🎣", "Spot Phishing"),
    ("privacy", "🔒", "Stay Private"),
    ("social_media_safety", "📱", "Social Media Safety"),
    ("cyberbullying", "🤝", "Beat Bullying"),
    ("safe_downloads", "💾", "Safe Downloads"),
    ("device_security", "🖥️", "Device Security")
]

AGE_GROUPS = ["junior", "explorer", "ranger"]
DIFFICULTIES = ["beginner", "intermediate", "advanced"]

modules = []
scenarios = []
questions = []

mod_id = 1
q_id = 1
scen_id = 1

for t_idx, (topic, icon, topic_lbl) in enumerate(TOPICS):
    for a_idx, age in enumerate(AGE_GROUPS):
        for d_idx, diff in enumerate(DIFFICULTIES):
            # Create Module
            m_ref = {
                "topic": topic,
                "age_group": age,
                "difficulty": diff
            }
            title = f"{topic_lbl}: {age.title()} {diff.title()}"
            desc = f"Learn about {topic_lbl.lower()} at a {diff} level."
            
            modules.append({
                "module_ref": m_ref,
                "title": title,
                "topic": topic,
                "description": desc,
                "age_group": age,
                "difficulty": diff,
                "icon": icon,
                "order_index": d_idx
            })
            
            # Create Scenario
            scen_body = f"Welcome to the {diff} level of {topic_lbl}! In this scenario, you will learn how to handle realistic situations online. Let's see what happens when you encounter a tricky situation related to {topic_lbl.lower()}..."
            scenarios.append({
                "module_ref": m_ref,
                "title": f"The {topic_lbl} Challenge",
                "body": scen_body,
                "order_index": 0
            })
            
            
            # Create 5 Questions grouped in a set
            qset = {
                "module_ref": m_ref,
                "questions": []
            }
            for q_num in range(1, 6):
                # Generic but context-aware questions
                q_body = f"Question {q_num} about {topic_lbl.lower()} for {age}s ({diff}): What is the best action to take?"
                
                # Make the questions slightly distinct based on topic
                if topic == "password_safety":
                    opt_a = "Use 'password123'"
                    opt_b = "Use a mix of letters, numbers, and symbols"
                    opt_c = "Share it with friends"
                    opt_d = "Write it on a sticky note on your screen"
                    correct = "b"
                    exp = "Strong passwords use a mix of different character types and are kept secret."
                elif topic == "phishing":
                    opt_a = "Click the link immediately to claim your prize"
                    opt_b = "Reply with your credit card details"
                    opt_c = "Ignore and report the suspicious message"
                    opt_d = "Forward it to all your friends"
                    correct = "c"
                    exp = "Suspicious messages should be ignored and reported. Never click unknown links."
                elif topic == "privacy":
                    opt_a = "Post your home address publicly"
                    opt_b = "Share your full name and school"
                    opt_c = "Keep personal details private and use a nickname"
                    opt_d = "Send a photo of your ID to strangers"
                    correct = "c"
                    exp = "Protecting your personal information keeps you safe from identity theft."
                elif topic == "social_media_safety":
                    opt_a = "Accept friend requests from strangers"
                    opt_b = "Review your privacy settings and only add people you know"
                    opt_c = "Post your location constantly"
                    opt_d = "Share your login details"
                    correct = "b"
                    exp = "Privacy settings help control who can see your information."
                elif topic == "cyberbullying":
                    opt_a = "Bully them back"
                    opt_b = "Block the person and tell a trusted adult"
                    opt_c = "Keep it a secret and feel bad"
                    opt_d = "Join in if others are doing it"
                    correct = "b"
                    exp = "Blocking the bully and getting help from an adult is the safest approach."
                elif topic == "safe_downloads":
                    opt_a = "Download free games from random pop-up ads"
                    opt_b = "Only download apps from official stores with permission"
                    opt_c = "Turn off your antivirus to make it faster"
                    opt_d = "Click 'Yes' on all installation warnings"
                    correct = "b"
                    exp = "Official stores are much safer. Always ask for permission before downloading."
                else: # device_security
                    opt_a = "Never update your device"
                    opt_b = "Leave your device unlocked in public"
                    opt_c = "Keep your software updated and use a screen lock"
                    opt_d = "Share your unlock PIN with everyone"
                    correct = "c"
                    exp = "Updates patch security holes, and screen locks protect your data."
                
                # Make advanced questions slightly trickier (swap options)
                if diff == "advanced" and q_num % 2 == 0:
                    temp = opt_b
                    opt_b = opt_c
                    opt_c = temp
                    correct = "c" if correct == "b" else ("b" if correct == "c" else correct)

                qset["questions"].append({
                    "body": q_body,
                    "option_a": opt_a,
                    "option_b": opt_b,
                    "option_c": opt_c,
                    "option_d": opt_d,
                    "correct_option": correct,
                    "explanation": exp,
                    "difficulty": diff,
                    "hint": "Think about what keeps your information the most secure.",
                    "points": 10 + (d_idx * 5) # 10, 15, 20 based on diff
                })
            
            questions.append(qset)

seed_dir = Path("data/seed_content")
seed_dir.mkdir(parents=True, exist_ok=True)

with open(seed_dir / "modules.json", "w", encoding="utf-8") as f:
    json.dump(modules, f, indent=2)

with open(seed_dir / "scenarios.json", "w", encoding="utf-8") as f:
    json.dump(scenarios, f, indent=2)

with open(seed_dir / "questions.json", "w", encoding="utf-8") as f:
    json.dump(questions, f, indent=2)

print(f"Generated {len(modules)} modules, {len(scenarios)} scenarios, and {len(questions)} questions.")
