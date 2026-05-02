"""Domain pack for the education / learning-analytics review.

Defines canonical task ids, human-facing names, aliases, template mapping,
and the list of domain-specific Notion properties to extract beyond the
bibliographic canonical set.

Compliance: no imports from notion_zotero.core — this module is intentionally
kept free of core-model dependencies so it can be loaded before core models
are fully initialised.
"""
from __future__ import annotations

from typing import Dict, Any, Optional

# Module-level constants for external reference without loading the full dict.
DOMAIN_PACK_ID: str = "education_learning_analytics"
DOMAIN_PACK_VERSION: str = "1.0"

# Short label map used by task_label_fn — exported for notebook / analysis use.
_TASK_LABEL_MAP: dict[str, str] = {
    "performance_prediction": "PRED",
    "descriptive_modelling": "DESC",
    "recommender_systems": "REC",
    "knowledge_tracing": "KT",
}

# Notion property names to extract beyond the canonical bibliographic fields.
# Stored in sync_metadata["domain_properties"] in each canonical bundle.
# Groups:
#   reading_workflow  — checkbox fields tracking which sections have been read
#   domain_classification — domain-specific analytic tags for each paper
#   screening — review decision fields beyond Status / Status_1
DOMAIN_NOTION_PROPERTIES: list[str] = [
    # reading workflow (checkbox)
    "Introduction",
    "Related Work",
    "Methods",
    "Results",
    "Discussion",
    "Conclusion",
    "Limitations",
    "Completed",
    # domain classification (select / multi_select)
    "Keywords/Type",
    "Learner Population",
    "Learner Representation",
    "Course-Agnostic Approach",
    "Deployed/ Deployable",
    "Work Nature",
    # screening (select / rich_text)
    "Motive For Exclusion",
]

#------------------------------/------------------------------/------------------------------/
# Data Source Mappings
#------------------------------/------------------------------/------------------------------/
# Column candidates used in task extraction tables.
DATA_SOURCE_COLUMN_CANDIDATES: list[str] = [
    "Data sources",
    "Data source",
    "Dataset",
    "Datasets",
    "Data",
]

# Regexes are matched against a normalized lower-case key:
# e.g. "LMS logs" -> "lms logs"
#
# Keep this map deliberately conservative. Anything not matched will appear
# in the audit table and can be added later.
DATA_SOURCE_ALIAS_PATTERNS: dict[str, list[str]] = {
    "LMS/VLE/MOOC logs": [
        r"\blms\b",
        r"\bvle\b",
        r"learning management system",
        r"virtual learning environment",
        r"moodle",
        r"blackboard",
        r"canvas",
        r"clickstream",
        r"click stream",
        r"event log",
        r"platform log",
        r"activity log",
        r"trace log",
        r'timestamps',
        r'course records',
        r'Learning resource/content interactions',
        r'CourseKata online textbook trace data',
        r'ITS logs',
        r'Mouse and Keyboard clicks',
        r'Learner-Activity Record',
        r"resource view",
        r"page view",
        r"video visit",
        r"video view",
        r"lesson",
        r"learning resource",
        r"content access",
        r"reading activity",
        r'Engagament Status',
        r'Learner-word session traces',
        r'Video Interactions',
        r'Video-Interactions',
        r'Code Traces',
        r'Video',
        r'interaction logs',
        r'interaction records',
        r'learning duration',
        r'platform activity',
        r'participation logs',
        r"\bmooc\b",
        r"massive open online course",
        r"edx",
        r"coursera",
        r"open edx",
        r'MoocRadar',
        r'Tomplay',
        r'Project CodeNet',
        r"assistments",
        r'ASSIST17',
        r'ASSIST09',
        r'ASSIST12', 
        r"ednet",
        r"junyi",
        r"xes",
        r"open university learning analytics dataset",
        r"\boulad\b",
        r"public dataset",
        r"benchmark dataset",
        r'Algebra2005',
        r'ASSIST2009',
        r'Eedi',
    ],

    "Student demographics/characteristics": [
        r"student demographic",
        r"learner demographic",
        r"student characteristic",
        r"learner characteristic",
        r"student profile",
        r"learner profile",
        r"gender",
        r"age",
        r"first generation",
        r"6. Personal/ Family Aspects",
        r'Demographics',
        r'demographic data in enhanced versions',
        r"personal\s*family",
        r'LearnerProfile',
        r'Demographic Information',
        r'3. Financial Aspects',
        r'Demograhic Data',
        r'Vacation Information',
        r'Socio-Economic Data',
        r'Student and Family characteristics',
        r'Socio-Demographic Variables',
        r'Student Demograohics',

    ],

    "Academic background records": [
        r"academic background",
        r"prior academic",
        r"previous academic",
        r"entry qualification",
        r"admission",
        r"major",
        r'Academic Records',
        r'Academic Records in University',
        r'Academic History and Ratings',
        r'Academic Information',
        r'Academic History',
        r'Acdemic Background',
        r'Academic Spreadsheets',
        r'Highschool History and Characteristics',
        r'University student records',
        r'Pre-University Variables',
        r'School Characteristics',
        r'Student learning history data',
        r'Student’s personal course history',

    ],

    "Professional background records": [
        r"Curriculum PDFs",
        r"Professional background",
        r"work experience",
        r"employment history",
        r"job history",
        r'5. Job Alternative/ Career',
        r"job alternative",
    ],

    "Assessment/performance records": [
        r"grade",
        r"grades",
        r"score",
        r"scores",
        r"mark",
        r"marks",
        r"gpa",
        r"assessment",
        r"exam",
        r"quiz",
        r"test result",
        r"performance",
        r"learner grade",
        r"student grade",
        r'Learner Results',
        r'Student Reports',
        r'Number of Credits Completed in First Year',
        r'student outcomes',

    ],

    "Administrative/SIS records": [
        r"student information system",
        r"\bsis\b",
        r"administrative",
        r"enrollment",
        r"enrolment",
        r"registration",
        r"course enrollment",
        r"course enrolment",
        r'Institutuional Data',
        r'Institutional Data',
        r'Enollment Data',
        r'MicroOERProfile',
        r'Student Infornation System',

    ],

    "Forum/discussion data": [
        r"forum",
        r"discussion",
        r"post",
        r"reply",
        r"thread",
        r"message",
    ],

    "Exercise/question interactions": [
        r"student exercise interaction",
        r"exercise interaction",
        r"question interaction",
        r"answer sequence",
        r"answer sequences",
        r"response sequence",
        r"responses",
        r"transactions",
        r"user generated transaction",
        r"problem attempt",
        r"attempt data",
        r"option selected",
        r'In-Question activities',
        r'attempts',
        r'Intermediate learner solutions in the poroblem-solving process',
        r'question/problem logs',
    ],

    "Question/Answer Sequences": [
        r'Sequence of Questions',
        r'Answer of Sequences',
        r'Sequence of Answers',
        r'Sequences of Answers',
        r'ITS answers',
        r'Exercise Sequence',
        r'Question Sequences',
        r'Time between exercises',
    ],

    "Learning Gains": [
        r'Learning Gains',
        r'Learning Gain',
        r'Learning Improvement',
        r'Pre-Test',
        r'Knowledge Topics',
        r'Math',
        r'Transfer Test',
        r'errors',
        r'course progress',
    ],

    "Exercise/question/Assignment metadata": [
        r'Question Text',
        r'Questions',
        r'Problem Difficulty',
        r'623 correct and 104',
        r'869',
        r'711 incorrect answers',
        r'Activity Metadata',
        r'Description of Activities Undertaken.',
        r'Activity Metadata',
        r"exercise metadata",
        r"question metadata",
        r'Answers',
        r'177',
        r'Difficulty',
        r'1',
        r'Exercise Sentences',
        r'Question Sentences',
        r'Question Attributes',
        r'Question Attribtutes',
        r'Question Test',

    ],

    "Course/content metadata": [
        r"course catalog",
        r"course catalogue",
        r"course metadata",
        r"course description",
        r"lesson description",
        r'Course Information',
        r'chapter summaries',
        r'Course Semantic Information',
        r'Course and professor Metadata',
        r'Course Learning Outcomes',
        r'Course Descriptors',
        r'PLO Description',
        r'Learning Objects',
        r'e-Textbook',
        r'Module presentation',
        r'course2vec embeddings',
        r'curriculum and course-outcome structure',
        r'item–outcome alignment mappings',
        r'categories)',
        r'– Lecture slides (concept text',
        r'learning items',
    ],

    "In-Class Behavior": [
        r"classroom",
        r"attendance",
        r"Attendance Records",
        r'Conversational transcripts',

    ],

    "Knowledge Components/Concepts": [
        r"knowledge component",
        r"\bkc\b",
        r"knowledge concept",
        r"knowledge component tagging",
        r'Knowledge Concepts',
        r'topic taxonom',
        r'Course Pre-Requisites embeddings',
        r'Association',
        r'Pre-requisite Concept Mapping',
        r'concept/outcome mappings',
        r'SQL course data',
        r'knowledge-point graph',
        r'skill labels',
        r'outcome tree',
        
    ],

    "Project/Code Assignments": [
        r'Code Submissions',
        r'Assignments',
        r'Programming submissions',
        r'Assignment submissions',
        r'Submission Records',
        r'Submissions',
        r'Term Paper Proposal',
    ],

    "Survey data": [
        r"survey",
        r'– Student DNU feedback logs',

    ],

    "Questionnaire/ Interview data": [
        r"questionnaire",
        r"self report",
        r"self reported",
        r"motivation",
        r"engagement scale",
        r'MSLQ',
        r'Interviews',
        r'Preferences',
        r'Perfect Solution for each task',
        r'4. Study Conditions',
        r'Contextual Information',
        r'– Student reflection texts (2 prompts per week)',
        r'mental effort',
        r'psychological stress ratings on 5-point Likert scales)',
        r'Student Reflection',
    ],

    "Wearable Devices/ Sensors": [
        r"eye tracking",
        r"wearable",
        r"sensor",
        r"physiological",
        r"biometric",
        r'Eye-Tracking Data',
        r'Eye-Tracking',
        r'Eye-Tracker and Facial Expression',
        r'NIPS34',
        r'Observational Instrutments',
        r'Peripheral Data',
        r'Headset',
        r'Think-Aloud records',
    ],
    
    "In-Campus Behavioral Data": [
        r'In-Campus Behavioral Data',
        r'Library Visits',
        r'Campus Facility Usage',
        r'On-Campus Event Attendance',
        r'Library',
        r'Library Access Control',
        r'Consumption Data',
        r'Digital Card interactions with Campus Infrastructure',
        r'Once-Card Consumption',
        r'Transaction Data',
        r"social network",
        r"social data",
        r"peer interaction",
        r"collaboration",
        r"social relationship",
        r'Peer Interactions',
        r'Social Networks',
        r'Collaborative Learning Data',
        r'Social tags',
        r'Social Networks',
    ],

    "External Websites/Apps usage": [
        r'Websites/App usage data',
        r'Web Browsing',
        r'GitLab commits',
        r'GitLab issues',
        r'Application data',
        r'Gateway Logins',
        r'Learning Tools',
        r'- Wikipedia Articles',
        r'Cellphone Use Time',
        r'– External APIs (Wikipedia + YouTube)',
        r'Publications on Social Media',
    ],

    "Instructor Behavior/Interventions": [
        r'Instructor Behavior/Interventions',
        r'Instructor Interventions',
        r'Feedback from Instructors',
        r'Course Instructor Behavior',
        r'instructor-defined attainment rules',
        r'Professor',
    ],

    "Others": [
        r"other",
        r"miscellaneous",
        r"various",
        r"multiple",
        r"mixed",
        r'There is no representation of the users. Instead it is solely based on the content provided.',
        r'Available Time',
        r'expert suggestions for LO initialization',
        r'– Historical dataset of prior students’ “challenges” and “solutions”',
        r'Multi-Source Writiing Session',
        r'chatbot queries',
        r'extracted keyphrases)',
    ],
}

DATA_SOURCE_MISSING_VALUES: set[str] = {
    "",
    "None",
    "N/A",
    "NA",
    "Not Applicable",
    "None Specified",
    "Not Specified",
    "-",
}

TASK_DISPLAY_LABELS: dict[str, str] = {
    "PRED": "PRED",
    "DESC": "DESC",
    "KT": "KT",
    "REC": "ERS",
    "ERS": "ERS",
}

#------------------------------/------------------------------/------------------------------/
# Paper Summary Table Mappings
#------------------------------/------------------------------/------------------------------/
# These vocabularies support paper-facing task summary tables. They deliberately
# stay conservative: raw extraction values are preserved by the analysis layer
# and unmatched values are surfaced in audit output.

PAPER_TASK_TABLES: dict[str, str] = {
    "PRED": "PRED",
    "DESC": "DESC",
    "KT": "KT",
    "REC": "ERS",
}

PAPER_TASK_ORDER: list[str] = ["PRED", "DESC", "KT", "ERS"]

PAPER_SUMMARY_MISSING_VALUES: set[str] = {
    "",
    "None",
    "N/A",
    "NA",
    "N\\A",
    "Not Applicable",
    "None Specified",
    "Not Specified",
    "-",
}

CONTEXT_COLUMN_CANDIDATES: list[str] = ["Context"]
CONTEXT_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Higher Education": [
        r"higher education",
        r"higher edfucation",
        r"higherr education",
        r"higher education students",
        r"undergraduate course",
        r"social networks in higher education",
        r"srl in undergraduate students",
    ],
    "MOOC": [
        r"\bmooc\b",
        r"massive open online course",
    ],
    "Intelligent Tutoring System": [
        r"intelligent tutoring system",
        r"intelligent tutoring systems",
        r"intellingent tutoring system",
        r"inteligent tutoring system",
        r"\bits\b",
    ],
    "K-12": [
        r"\bk 12\b",
        r"\bk-12\b",
    ],
    "Interactive Learning Platform": [
        r"interactive content platform",
        r"subscription based platform",
        r"e learning",
    ],
    "Educational Recommender Systems Guidelines": [
        r"guidelines for educational recommender systems",
    ],
}

TEACHING_METHOD_COLUMN_CANDIDATES: list[str] = ["Teaching Method"]
TEACHING_METHOD_ALIAS_PATTERNS: dict[str, list[str]] = {
    "E-Learning": [
        r"e learning",
        r"elearning",
        r"online learning",
        r"mobile e learning",
        r"\bmoocs?\b",
    ],
    "Blended Learning": [
        r"blended learning",
        r"blended learning and mooc",
        r"\bb learning\b",
        r"face to face learning with online forum",
    ],
    "Face-to-Face Learning": [
        r"face to face learning",
        r"face to face education",
    ],
    "Problem-Based Learning": [
        r"problem based learning",
        r"project based learning",
    ],
    "Collaborative Learning": [
        r"collaborative learning",
        r"peer learning",
    ],
    "Flipped Classroom": [
        r"flipped classroom",
    ],
    "Active Learning": [
        r"active learning",
    ],
    "E-Book Supported Learning": [
        r"e book supported learning",
    ],
    "Graduate Programs": [
        r"graduate programs",
    ],
}

ANALYTIC_TASK_COLUMN_CANDIDATES: list[str] = ["Task"]
ANALYTIC_TASK_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Classification": [r"classification"],
    "Regression": [r"regression"],
    "Clustering": [r"clustering"],
    "Process Mining": [r"process mining"],
    "Sequential Pattern Mining": [
        r"sequential pattern mining",
        r"sequence mining",
        r"temporal pattern mining",
        r"lag sequential analysis",
    ],
    "Association Rule Mining": [r"association rule mining"],
    "Topic Modelling": [r"topic modelling", r"topic modeling"],
    "Factor Analysis": [r"factor analysis"],
}

ASSESSMENT_STRATEGY_COLUMN_CANDIDATES: list[str] = ["Assessment Strategy"]
ASSESSMENT_STRATEGY_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Holdout": [
        r"holdout",
        r"train test split",
        r"80 20",
        r"70 30",
        r"75 25",
    ],
    "Repeated Holdout": [
        r"repeated holdout",
        r"10 repeated holdout",
        r"100 repeated holdout",
        r"5 repeated holdout",
        r"3 repeated holdout",
    ],
    "K-Fold Cross-Validation": [
        r"k fold cross validation",
        r"fold cross validation",
        r"fold cross validation",
        r"cross validation",
        r"10 fold",
        r"5 fold",
    ],
    "Repeated K-Fold Cross-Validation": [
        r"repeated 3 fold",
        r"repeated k fold",
        r"10 repeated 3 fold",
    ],
    "Stratified Cross-Validation": [
        r"stratified cross validation",
    ],
    "Temporal Validation": [
        r"temporal validation",
        r"time split",
        r"prefix split",
        r"chronological",
    ],
    "Leave-One-Out Cross-Validation": [
        r"leave one out",
        r"loocv",
    ],
}

RECOMMENDER_TYPE_COLUMN_CANDIDATES: list[str] = ["Recommender System Type"]
RECOMMENDER_TYPE_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Hybrid": [r"hybrid"],
    "Content-Based Filtering": [
        r"content based filtering",
        r"content based",
    ],
    "Collaborative Filtering": [
        r"collaborative filtering",
        r"collaborative",
        r"userknn",
        r"itemknn",
        r"matrix factorization",
    ],
    "Knowledge-Based": [
        r"knowledge based",
        r"\bkb\b",
    ],
    "Goal-Based": [
        r"goal based",
        r"outcome based",
    ],
    "Sequential Recommendation": [
        r"sequential recommendation",
        r"trajectory",
    ],
}

THEORETICAL_GROUNDING_COLUMN_CANDIDATES: list[str] = [
    "Theoretical Grounding",
    "Thereotical Model",
]
THEORETICAL_GROUNDING_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Self-Regulated Learning": [
        r"pintrich",
        r"winne",
        r"hadwin",
        r"trace srl",
        r"self regulated learning",
        r"\bsrl\b",
    ],
    "Biggs' 3P Model": [
        r"bigg",
        r"3p model",
    ],
    "Big Five Personality Traits": [
        r"big 5",
        r"big five",
    ],
    "Complex Dynamic Systems Theory": [
        r"complex dynamic systems",
    ],
}

ALGORITHM_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Random Forest": [r"random forest", r"\brf\b"],
    "Support Vector Machine": [r"\bsvm\b", r"support vector", r"linear svm"],
    "Logistic Regression": [r"logistic regression", r"\blr\b"],
    "Linear Regression": [r"linear regression"],
    "Decision Tree": [r"decision tree", r"\bcart\b"],
    "Naive Bayes": [r"naive bayes", r"\bnb\b"],
    "k-Nearest Neighbors": [r"\bknn\b", r"k nearest", r"k-nearest"],
    "Multi-Layer Perceptron": [r"\bmlp\b", r"multi layer perceptron"],
    "Neural Network": [r"neural network"],
    "XGBoost": [r"xgboost", r"xg boost"],
    "Gradient Boosting": [r"gradient boosting", r"\bgbm\b"],
    "LSTM": [r"\blstm\b", r"long short term memory"],
    "RNN": [r"\brnn\b", r"recurrent neural network"],
    "BKT": [r"\bbkt\b", r"bayesian knowledge tracing"],
    "DKT": [r"\bdkt\b", r"deep knowledge tracing"],
    "DKVMN": [r"\bdkvmn\b"],
    "SAKT": [r"\bsakt\b"],
    "AKT": [r"\bakt\b"],
    "SAINT": [r"\bsaint\b"],
    "IRT": [r"\birt\b", r"item response theory"],
    "Matrix Factorization": [r"matrix factorization", r"\bgmf\b", r"\bneumf\b"],
    "Collaborative Filtering": [r"collaborative filtering", r"userknn", r"itemknn"],
    "Content-Based Filtering": [r"content based filtering", r"content based"],
    "Knowledge-Based Recommendation": [r"knowledge based", r"\bkb\b"],
    "k-Means": [r"k means", r"k-means"],
    "Hierarchical Clustering": [r"hierarchical clustering"],
    "Expectation-Maximization": [r"expectation maximization", r"\bem\b"],
    "Structural Equation Modeling": [r"\bsem\b", r"structural equation"],
    "Markov Model": [r"markov"],
}

RECOMMENDER_ALGORITHM_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Hybrid Recommendation": [r"hybrid"],
    "Collaborative Filtering": [r"collaborative filtering", r"collaborative"],
    "Content-Based Filtering": [r"content based filtering", r"content based"],
    "Knowledge-Based Recommendation": [r"knowledge based", r"\bkb\b"],
    "Sequential Recommendation": [r"sequential recommendation", r"sequential recommender"],
    "Matrix Factorization": [r"matrix factorization", r"\bgmf\b", r"\bneumf\b"],
    "User-kNN": [r"userknn", r"user knn", r"user k nearest"],
    "Item-kNN": [r"itemknn", r"item knn", r"item k nearest"],
    "Neural Collaborative Filtering": [r"neural collaborative filtering", r"\bncf\b"],
    "Deep Knowledge Tracing": [r"\bdkt\b", r"deep knowledge tracing"],
    "Reinforcement Learning": [r"reinforcement learning", r"\brl\b", r"rl head"],
    "Contrastive Learning": [r"contrastive learning", r"\bcl\b", r"contrastive head"],
    "Transformer / BERT Embeddings": [r"\bbert\b", r"roberta", r"transformer", r"sentence embeddings"],
    "Learning Embeddings": [r"embedding", r"embeddings"],
    "Ontology-Based Recommendation": [r"ontology", r"qualifier tags"],
    "Analytic Hierarchy Process": [r"\bahp\b", r"analytic hierarchy"],
    "Graph Search": [r"depth first search", r"\bdfs\b", r"course graph", r"learning path"],
    "Self-Organizing Map": [r"self organizing map", r"self organising map", r"\bsom\b"],
    "Item Response Theory": [r"\birt\b", r"item response theory"],
    "Algorithmic Recourse": [r"algorithmic recourse", r"\brecourse\b", r"\brecrec\b"],
    "Rule-Based Recommendation": [r"rule based", r"set of rules"],
}

FEATURE_CATEGORY_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Demographics": [
        r"gender",
        r"age",
        r"demographic",
        r"socio",
        r"income",
        r"first generation",
    ],
    "Prior academic performance": [
        r"gpa",
        r"grade",
        r"score",
        r"mark",
        r"exam",
        r"quiz",
        r"sat",
        r"assessment",
        r"prior performance",
        r"previous performance",
    ],
    "Academic background": [
        r"degree",
        r"major",
        r"entry qualification",
        r"academic history",
        r"highschool",
        r"high school",
    ],
    "LMS activity": [
        r"click",
        r"view",
        r"visit",
        r"login",
        r"access",
        r"resource",
        r"page",
        r"video",
        r"activity",
        r"session",
        r"time spent",
        r"duration",
    ],
    "Assessment interactions": [
        r"attempt",
        r"answer",
        r"question",
        r"problem",
        r"exercise",
        r"response",
        r"hint",
        r"correct",
        r"incorrect",
    ],
    "Temporal / sequential behavior": [
        r"sequence",
        r"sequential",
        r"lag",
        r"week",
        r"daily",
        r"timestamp",
        r"temporal",
        r"early",
    ],
    "Forum / social interaction": [
        r"forum",
        r"discussion",
        r"post",
        r"reply",
        r"peer",
        r"social",
        r"network",
        r"collaboration",
    ],
    "Course / content metadata": [
        r"course",
        r"content",
        r"lesson",
        r"module",
        r"chapter",
        r"concept",
        r"knowledge component",
        r"skill",
        r"topic",
    ],
    "Survey / self-report": [
        r"survey",
        r"questionnaire",
        r"self report",
        r"motivation",
        r"engagement",
        r"preference",
        r"reflection",
    ],
}

PREDICTION_TARGET_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Predict student dropout risk": [
        r"dropout",
        r"drop out",
        r"drop-out",
    ],
    "Predict the student's final grade": [
        r"final grade",
        r"final mark",
        r"final score",
        r"course grade",
    ],
    "Predict whether the student will pass or fail": [
        r"pass or fail",
        r"pass/fail",
        r"pass fail",
    ],
    "Identify students at risk of poor academic performance": [
        r"at-risk",
        r"at risk",
        r"poor academic performance",
    ],
    "Predict student academic success": [
        r"student success",
        r"academic success",
    ],
    "Predict student academic performance": [
        r"academic performance",
        r"student performance",
        r"performance in.*course",
    ],
}

KT_TARGET_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Predict the probability that the student will answer the next question correctly": [
        r"probability.*next.*(question|item|problem).*(correct|success)",
    ],
    "Predict whether the student will answer the next question correctly": [
        r"next.*(question|item|problem).*(correct|answer)",
        r"correctness of the next question",
        r"correct answer in next question",
    ],
    "Predict whether the student will answer correctly on the first attempt": [
        r"first attempt.*(correct|success)",
    ],
    "Predict whether the student will solve the next exercise correctly": [
        r"next exercise.*(correct|success)",
    ],
    "Predict whether the student will solve the exercise correctly": [
        r"exercise.*(correct|success)",
    ],
    "Estimate the student's knowledge state or skill mastery": [
        r"knowledge state",
        r"knowledge level",
        r"skill mastery",
        r"\bmastery\b",
    ],
    "Predict the student's performance on the next learning activity": [
        r"performance.*next",
    ],
    "Predict the student's need for hints or assistance": [
        r"\bhint\b",
        r"\bhelp\b",
        r"assistance",
    ],
}

RECOMMENDATION_TARGET_ALIAS_PATTERNS: dict[str, list[str]] = {
    "Recommend learning resources to students": [
        r"recommend.*resource",
        r"learning resource",
        r"learning object",
    ],
    "Recommend courses or learning paths to students": [
        r"recommend.*course",
        r"recommend.*path",
        r"learning path",
        r"courses? to take",
        r"course.*enrol",
        r"course.*enroll",
    ],
    "Recommend learning activities to students": [
        r"recommend.*activity",
        r"exercise",
        r"problem",
    ],
    "Recommend peers or collaborators to students": [
        r"recommend.*peer",
        r"collaborator",
    ],
    "Recommend personalized learning support to students": [
        r"recommend",
        r"personalized learning support",
    ],
}

RESULT_METRIC_LABELS: dict[str, str] = {
    "accuracy": "Accuracy",
    "auc": "AUC",
    "f1": "F1",
    "f1 score": "F1",
    "f1-score": "F1",
    "precision": "Precision",
    "recall": "Recall",
    "rmse": "RMSE",
    "mae": "MAE",
    "mse": "MSE",
    "r2": "R2",
    "ndcg": "NDCG",
    "hit rate": "Hit rate",
    "hit-rate": "Hit rate",
    "hr": "Hit rate",
    "mcc": "MCC",
}

#------------------------------/------------------------------/------------------------------/
# Domain Pack Definition
#------------------------------/------------------------------/------------------------------/

domain_pack = {
    "id": "education_learning_analytics",
    "version": "1.1",
    "name": "Education / Learning Analytics",
    "tasks": {
        "descriptive_modelling": {
            "name": "Descriptive Modelling",
            "aliases": ["descriptive", "descriptive modelling", "descriptive analysis", "desc"],
            "template_id": "descriptive_analysis",
        },
        "performance_prediction": {
            "name": "Performance Prediction",
            "aliases": ["prediction", "performance prediction", "predictive", "pred"],
            "template_id": "prediction_modeling",
        },
        "recommender_systems": {
            "name": "Recommender Systems",
            "aliases": ["recommender", "recommendation", "recommender systems", "rec"],
            "template_id": "recommendation_system",
        },
        "knowledge_tracing": {
            "name": "Knowledge Tracing",
            "aliases": ["knowledge tracing", "kt", "tracing"],
            "template_id": "sequence_tracing",
        },
    },
    # Domain-specific Notion properties to extract (beyond canonical bibliographic set).
    # Importer reads this list and stores values in sync_metadata["domain_properties"].
    "notion_properties": DOMAIN_NOTION_PROPERTIES,
    # Short-label mapping for task names → analysis abbreviations.
    "task_labels": _TASK_LABEL_MAP,
}


def task_label_fn(task_name: str | None) -> str:
    """Map a full task name to its short analysis label (PRED / DESC / REC / KT).

    Falls back to the task name itself when no mapping is found.
    """
    key = (task_name or "").lower().replace(" ", "_").replace("-", "_")
    # exact match first
    if key in _TASK_LABEL_MAP:
        return _TASK_LABEL_MAP[key]
    # substring match for partial names
    for tid, label in _TASK_LABEL_MAP.items():
        if tid in key or key in tid:
            return label
    return task_name or ""


def list_tasks() -> Dict[str, Dict[str, Any]]:
    return domain_pack["tasks"]


def match_heading_to_task(heading: str | None) -> Optional[str]:
    if not heading:
        return None
    h = heading.lower()
    for tid, meta in domain_pack["tasks"].items():
        for a in meta.get("aliases", []):
            if a.lower() in h:
                return tid
    return None


__all__ = [
    "DOMAIN_PACK_ID",
    "DOMAIN_PACK_VERSION",
    "DOMAIN_NOTION_PROPERTIES",
    "domain_pack",
    "task_label_fn",
    "list_tasks",
    "match_heading_to_task",
    "DATA_SOURCE_COLUMN_CANDIDATES",
    "DATA_SOURCE_ALIAS_PATTERNS",
    "DATA_SOURCE_MISSING_VALUES",
    "TASK_DISPLAY_LABELS",
    "PAPER_TASK_TABLES",
    "PAPER_TASK_ORDER",
    "PAPER_SUMMARY_MISSING_VALUES",
    "CONTEXT_COLUMN_CANDIDATES",
    "CONTEXT_ALIAS_PATTERNS",
    "TEACHING_METHOD_COLUMN_CANDIDATES",
    "TEACHING_METHOD_ALIAS_PATTERNS",
    "ANALYTIC_TASK_COLUMN_CANDIDATES",
    "ANALYTIC_TASK_ALIAS_PATTERNS",
    "ASSESSMENT_STRATEGY_COLUMN_CANDIDATES",
    "ASSESSMENT_STRATEGY_ALIAS_PATTERNS",
    "RECOMMENDER_TYPE_COLUMN_CANDIDATES",
    "RECOMMENDER_TYPE_ALIAS_PATTERNS",
    "THEORETICAL_GROUNDING_COLUMN_CANDIDATES",
    "THEORETICAL_GROUNDING_ALIAS_PATTERNS",
    "ALGORITHM_ALIAS_PATTERNS",
    "RECOMMENDER_ALGORITHM_ALIAS_PATTERNS",
    "FEATURE_CATEGORY_ALIAS_PATTERNS",
    "PREDICTION_TARGET_ALIAS_PATTERNS",
    "KT_TARGET_ALIAS_PATTERNS",
    "RECOMMENDATION_TARGET_ALIAS_PATTERNS",
    "RESULT_METRIC_LABELS",
]
