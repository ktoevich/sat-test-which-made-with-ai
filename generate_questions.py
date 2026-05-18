import json
import random

def generate_math_questions(count):
    questions = []
    for i in range(1, count + 1):
        q_type = random.choice(['linear_eq', 'quadratic', 'system', 'percentage', 'geometry_rect', 'geometry_circle'])
        
        passage = ""
        question = ""
        options = []
        correct_idx = 0
        
        if q_type == 'linear_eq':
            a = random.randint(2, 9)
            b = random.randint(1, 20)
            c = random.randint(10, 50)
            # ax + b = c  => x = (c-b)/a
            # to ensure integer:
            ans = random.randint(1, 10)
            c = a * ans + b
            question = f"If {a}x + {b} = {c}, what is the value of x?"
            correct_ans = ans
            wrong_answers = [ans + random.randint(1,3), ans - random.randint(1,3), ans * 2]
            
        elif q_type == 'quadratic':
            # (x - r1)(x - r2) = x^2 - (r1+r2)x + r1*r2
            r1 = random.randint(1, 5)
            r2 = random.randint(2, 6)
            b = -(r1 + r2)
            c = r1 * r2
            question = f"The function f is defined by f(x) = x^2 {b}x + {c}. What is one possible value of x for which f(x) = 0?"
            question = question.replace("+ -", "- ")
            correct_ans = r1
            wrong_answers = [-r1, r2 + 2, -r2]
            
        elif q_type == 'system':
            x = random.randint(1, 5)
            y = random.randint(1, 5)
            c1 = 2*x + y
            c2 = x - y
            question = f"If 2x + y = {c1} and x - y = {c2}, what is the value of x?"
            correct_ans = x
            wrong_answers = [y, x+y, x-y]
            
        elif q_type == 'percentage':
            base = random.choice([50, 100, 150, 200, 250, 500])
            perc = random.choice([10, 15, 20, 25, 30, 40, 50])
            ans = int(base * (perc / 100))
            question = f"What is {perc}% of {base}?"
            correct_ans = ans
            wrong_answers = [ans + 10, int(base * (perc+10)/100), ans - 5]
            
        elif q_type == 'geometry_rect':
            w = random.randint(3, 10)
            l = w + random.randint(1, 5)
            area = w * l
            question = f"A rectangle has an area of {area} square units. If the length is {l} units, what is the width?"
            correct_ans = w
            wrong_answers = [l, area - l, w + 2]
            
        elif q_type == 'geometry_circle':
            r = random.randint(2, 10)
            area = r * r
            question = f"The area of a circle is {area}π. What is the radius of the circle?"
            correct_ans = r
            wrong_answers = [r * 2, r * r, int(r / 2)]

        wrong_answers = list(set(wrong_answers))
        while len(wrong_answers) < 3:
            wrong_answers.append(wrong_answers[-1] + 1)
            wrong_answers = list(set(wrong_answers))
            
        all_options = [str(correct_ans)] + [str(wa) for wa in wrong_answers[:3]]
        random.shuffle(all_options)
        correct_idx = all_options.index(str(correct_ans))
        
        labeled_options = [f"{chr(65+idx)}) {opt}" for idx, opt in enumerate(all_options)]
        
        questions.append({
            "id": i + 1000,
            "passage": passage,
            "question": question,
            "options": labeled_options,
            "correctAnswer": correct_idx
        })
        
    return questions

def generate_rw_questions(count):
    base_templates = [
        {
            "passage": "While researching the effects of urban noise on bird communication, biologist Sarah Thompson and her team noticed a distinct shift in the vocalizations of city-dwelling robins. Compared to their rural counterparts, the urban robins sang at a noticeably higher pitch. Thompson hypothesizes that this upward shift in frequency allows the birds' songs to penetrate the low-frequency rumble of city traffic, thereby ensuring their mating calls and territorial warnings are heard.",
            "question": "Which finding, if true, would most directly support Thompson’s hypothesis?",
            "correct": "The primary frequencies of city traffic noise are significantly lower than the altered pitch of the urban robins' songs.",
            "wrongs": [
                "Urban robins are found to sing louder than rural robins in addition to singing at a higher pitch.",
                "Rural robins relocated to urban environments do not immediately adjust the pitch of their songs.",
                "Other species of birds in the same urban environments have not demonstrated a similar shift in vocal pitch."
            ]
        },
        {
            "passage": "The phenomenon of \"quantum entanglement\" occurs when two or more particles become linked such that the state of one particle instantly influences the state of the other, regardless of the distance separating them. This seemingly impossible instant connection, which Albert Einstein famously referred to as \"spooky action at a distance,\" challenges classical intuitions about the limits of communication speed, specifically the universal speed limit set by the speed of light.",
            "question": "As used in the text, what does the word \"challenges\" most nearly mean?",
            "correct": "Defies",
            "wrongs": ["Questions", "Competes with", "Threatens"]
        },
        {
            "passage": "To conserve water, many homeowners in arid regions are turning to xeriscaping—a landscaping method that uses drought-resistant plants. While the initial cost of removing a traditional lawn and installing a xeriscape can be high, proponents argue that the long-term savings on water bills make it a financially sound decision.",
            "question": "Which statement best describes the function of the second sentence in the overall structure of the text?",
            "correct": "It presents a potential drawback to xeriscaping and then immediately refutes it with a long-term benefit.",
            "wrongs": [
                "It explains the step-by-step process of converting a traditional lawn into a xeriscape.",
                "It provides a historical context for the recent popularity of xeriscaping in arid regions.",
                "It compares the aesthetic appeal of xeriscaping with that of traditional grass lawns."
            ]
        },
        {
            "passage": "In 1934, archaeologist Gertrude Caton-Thompson led an expedition to the Hadhramaut region of Yemen. Her meticulous excavations at the site of Hureidha revealed a complex irrigation system dating back to the 5th century BCE. This discovery fundamentally altered the understanding of ancient Arabian agriculture, demonstrating that sophisticated water management techniques were employed much earlier than previously believed.",
            "question": "According to the text, what was the main significance of Caton-Thompson's discovery at Hureidha?",
            "correct": "It showed that advanced irrigation methods were used in ancient Arabia earlier than scholars had thought.",
            "wrongs": [
                "It proved that the Hadhramaut region was the sole origin point for all Middle Eastern agriculture.",
                "It revealed that ancient Arabian irrigation systems were designed primarily for aesthetic purposes.",
                "It indicated that the 5th century BCE was a period of unprecedented drought in the region."
            ]
        },
        {
            "passage": "The Venus flytrap (Dionaea muscipula) is a carnivorous plant native to subtropical wetlands on the East Coast of the United States. When an insect crawls along the plant's leaves and contacts its sensitive hairs, the leaf snaps shut. However, the plant relies on a sophisticated mechanism: the trap only closes if two different hairs are touched within 20 seconds of each other. This dual-trigger system prevents the plant from wasting energy on false alarms like raindrops or falling debris.",
            "question": "What is the primary purpose of the dual-trigger mechanism in the Venus flytrap?",
            "correct": "To ensure that the plant only expends energy when a living prey item is likely present.",
            "wrongs": [
                "To allow the plant to capture larger insects that require more force to contain.",
                "To give the insect enough time to escape before the trap fully closes.",
                "To measure the exact size and weight of the potential prey."
            ]
        }
    ]

    grammar_templates = [
        {
            "passage": "The committee's recent report on urban planning ______ several key recommendations for improving public transportation infrastructure over the next decade.",
            "question": "Which choice completes the text so that it conforms to the conventions of Standard English?",
            "correct": "outlines",
            "wrongs": ["outline", "outlining", "are outlining"]
        },
        {
            "passage": "Despite the harsh conditions of the Mojave Desert, the Joshua tree thrives. Its root system extends deep into the soil to access hidden water ______ its spiky leaves are adapted to minimize moisture loss.",
            "question": "Which choice completes the text so that it conforms to the conventions of Standard English?",
            "correct": "sources, and",
            "wrongs": ["sources; and", "sources and", "sources,"]
        },
        {
            "passage": "Many critics argue that the director's latest film is a masterpiece; ______, audiences have responded with mixed reviews, leading to disappointing box office returns.",
            "question": "Which choice completes the text with the most logical transition?",
            "correct": "however",
            "wrongs": ["therefore", "in addition", "similarly"]
        }
    ]

    all_templates = base_templates + grammar_templates
    
    questions = []
    for i in range(1, count + 1):
        template = random.choice(all_templates)
        
        all_options = [template["correct"]] + template["wrongs"][:3]
        random.shuffle(all_options)
        correct_idx = all_options.index(template["correct"])
        
        labeled_options = [f"{chr(65+idx)}) {opt}" for idx, opt in enumerate(all_options)]
        
        questions.append({
            "id": i + 2000,
            "passage": template["passage"],
            "question": template["question"],
            "options": labeled_options,
            "correctAnswer": correct_idx
        })
        
    return questions

def main():
    math_count = 50
    rw_count = 54
    
    data = {
        "Reading & Writing": generate_rw_questions(rw_count),
        "Math": generate_math_questions(math_count)
    }
    
    js_content = "const questionsData = " + json.dumps(data, indent=4) + ";"
    
    with open("questions.js", "w", encoding="utf-8") as f:
        f.write(js_content)
        
    print(f"Generated {math_count} Math and {rw_count} Reading & Writing questions in questions.js")

if __name__ == "__main__":
    main()
