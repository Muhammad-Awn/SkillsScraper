import re
from bs4 import BeautifulSoup


SKILLS_VOCAB = [
    # Programming Languages
    "swift", "python", "java", "kotlin", "objective-c",
    "c", "c++", "javascript", "typescript", "go", "rust",
    "ruby", "php", "sql", "bash", "rails", "dart", "tailwind css", "css",

    # Mobile Platforms
    "ios", "android", "ipados", "macos", "watchos", "tvos",

    # Apple Frameworks
    "swiftui", "uikit", "combine",
    "core data", "core animation", "core graphics",
    "avfoundation", "mapkit", "storekit", "healthkit",
    "icloud", "push notifications",

    # Android Frameworks
    "jetpack compose", "android studio", "gradle",
    "hilt", "dagger", "retrofit", "coroutines", "flutter"

    # Web & Backend Frameworks
    "react", "react native", "vue", "angular",
    "node.js", "express", "next.js",
    "django", "flask", "fastapi", "spring boot",

    # APIs & Protocols
    "rest api", "graphql", "websockets",
    "oauth", "openid connect", "jwt", "restful",

    # Data Engineering
    "apache airflow", "airflow",
    "dbt",
    "apache spark", "spark",
    "apache kafka", "kafka",
    "apache flink",
    "apache beam",
    "hadoop",
    "snowflake", "bigquery", "redshift",
    "databricks",
    "delta lake",
    "parquet", "avro",
    "data warehouse",
    "data lake",

    # Databases & Storage
    "sqlite", "postgresql", "mysql",
    "mongodb", "redis", "firebase",

    # DevOps & Cloud Platforms
    "aws", "gcp", "azure",
    "docker", "kubernetes",
    "terraform", "serverless",

    # CI/CD & Version Control
    "git", "github", "gitlab",
    "ci/cd", "fastlane", "jenkins", "selenium"

    # Development Tools
    "xcode", "visual studio code",
    "intellij idea", "postman",

    # Software Engineering Practices (mainstream)
    "unit testing", "integration testing",
    "dependency injection",
    "multithreading", "concurrency",
    "solid principles",

    # Architecture (mainstream)
    "mvc", "mvvm", "viper",
    "microservices", "monolith",
    "distributed systems",

    # Security
    "https", "tls", "ssl",
    "authentication", "authorization",
    "encryption", "keychain",

    # Monitoring & Analytics Tools
    "sentry", "datadog",
    "firebase analytics",

    # AI / Machine Learning
    "machine learning", "deep learning",
    "computer vision", "natural language processing",
    "nlp", "reinforcement learning", "cv", 

    # GenAI & Agentic AI
    "large language models", "llm", "llms",
    "prompt engineering",
    "retrieval augmented generation",
    "rag", "langchain",
    "agentic ai",
    "autonomous agents",
    "tool calling",

    # ML Frameworks & Platforms
    "tensorflow", "pytorch", "keras",
    "scikit-learn",
    "hugging face",
    "onnx", "elasticsearch",

    # AI Infrastructure
    "model serving",
    "vector databases",
    "embedding models",

    # Data Science & Analysis
    "data analysis", "data visualization",
    "pandas", "numpy", "matplotlib", "seaborn",
    "Looker", "tableau", "power bi"
]


def extract_technical_section(text: str) -> str:
    sections = [
        "technical requirements",
        "technical skills",
        "requirements",
        "ideal candidate"
        "nice to have",
        "qualifications",
    ]
    
    lower = text.lower()
    for section in sections:
        if section in lower:
            start = lower.index(section)
            return text[start:start + 2000]  # grab next chunk
    
    return text


def extract_skills(text: str, skills_vocab: list[str]) -> list[str]:
    text = text.lower()
    found_skills = set()

    for skill in skills_vocab:
        # escape special characters like "+"
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text):
            found_skills.add(skill)

    return sorted(found_skills)


def skills_finder(text: str):
    soup = BeautifulSoup(text, "html.parser")

    # Remove script/style/img tags if present
    for tag in soup(["script", "style", "img"]):
        tag.decompose()

    # Extract readable text
    job_description = soup.get_text(separator="\n", strip=True)
    tech_section = extract_technical_section(job_description)

    description = tech_section if tech_section else job_description
    skills = extract_skills(description, SKILLS_VOCAB)

    return skills # if skills else None