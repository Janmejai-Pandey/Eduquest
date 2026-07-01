"""
ai_data.py
Artificial Intelligence specialist job role profiles.
"""

job_skill_profiles = {
    "AI Engineer": {
        "skills": [
            "python", "tensorflow", "pytorch", "keras", "scikit-learn",
            "pandas", "numpy", "matplotlib", "deep learning", "neural networks",
            "cnn", "rnn", "lstm", "transformers", "bert", "gpt",
            "nlp", "computer vision", "opencv", "huggingface",
            "reinforcement learning", "model deployment", "flask",
            "fastapi", "docker", "kubernetes", "aws sagemaker",
            "gcp vertex ai", "mlflow", "git", "linux", "statistics",
            "probability", "linear algebra", "calculus", "agile"
        ],
        "weights": {
            "python": 5, "tensorflow": 5, "pytorch": 5, "deep learning": 5,
            "neural networks": 5, "transformers": 4, "nlp": 4,
            "computer vision": 4, "model deployment": 4, "docker": 3,
            "statistics": 4
        }
    },
    "NLP Engineer": {
        "skills": [
            "python", "nltk", "spacy", "huggingface", "transformers",
            "bert", "gpt", "t5", "llama", "tokenization", "word embeddings",
            "word2vec", "glove", "fasttext", "named entity recognition",
            "sentiment analysis", "text classification", "machine translation",
            "question answering", "summarization", "tensorflow", "pytorch",
            "deep learning", "rnn", "lstm", "attention", "fine-tuning",
            "prompt engineering", "vector databases", "faiss", "pinecone",
            "langchain", "llamaindex", "git", "docker", "aws"
        ],
        "weights": {
            "python": 5, "nlp": 5, "transformers": 5, "bert": 4,
            "huggingface": 4, "tensorflow": 4, "pytorch": 4,
            "named entity recognition": 4, "fine-tuning": 4,
            "prompt engineering": 4, "langchain": 3
        }
    },
    "Computer Vision Engineer": {
        "skills": [
            "python", "opencv", "tensorflow", "pytorch", "keras",
            "cnn", "yolo", "rcnn", "faster rcnn", "mask rcnn", "unet",
            "image classification", "object detection", "image segmentation",
            "pose estimation", "ocr", "face recognition", "image generation",
            "gans", "stable diffusion", "transfer learning",
            "data augmentation", "model optimization", "tensorrt", "onnx",
            "deep learning", "numpy", "pillow", "scikit-image", "matplotlib",
            "docker", "git", "linux", "aws", "edge computing"
        ],
        "weights": {
            "python": 5, "opencv": 5, "tensorflow": 5, "pytorch": 5,
            "cnn": 5, "object detection": 4, "image segmentation": 4,
            "yolo": 4, "deep learning": 5, "git": 3
        }
    },
    "Generative AI Engineer": {
        "skills": [
            "python", "pytorch", "tensorflow", "huggingface", "transformers",
            "gpt", "llama", "claude", "gemini", "stable diffusion",
            "diffusion models", "gans", "vae", "prompt engineering",
            "rag", "retrieval augmented generation", "langchain",
            "llamaindex", "vector databases", "faiss", "pinecone",
            "chromadb", "weaviate", "fine-tuning", "lora", "peft",
            "rlhf", "openai api", "anthropic api", "groq", "fastapi",
            "docker", "kubernetes", "aws", "gcp", "git", "deep learning"
        ],
        "weights": {
            "python": 5, "transformers": 5, "huggingface": 4,
            "prompt engineering": 5, "rag": 5, "langchain": 4,
            "vector databases": 4, "fine-tuning": 4, "openai api": 4,
            "deep learning": 4
        }
    },
    "AI Research Scientist": {
        "skills": [
            "python", "pytorch", "tensorflow", "jax", "deep learning",
            "machine learning", "reinforcement learning", "nlp",
            "computer vision", "transformers", "graph neural networks",
            "generative models", "diffusion models", "research papers",
            "publication", "experimentation", "statistics", "probability",
            "linear algebra", "calculus", "optimization", "latex",
            "git", "linux", "high performance computing", "gpu",
            "cuda", "distributed training", "phd", "academic writing"
        ],
        "weights": {
            "python": 5, "pytorch": 5, "deep learning": 5,
            "machine learning": 5, "research papers": 5, "publication": 5,
            "statistics": 5, "linear algebra": 5, "optimization": 4
        }
    },
    "AI Product Manager": {
        "skills": [
            "product management", "ai/ml fundamentals", "machine learning",
            "deep learning", "nlp", "computer vision", "model deployment",
            "mlops", "data strategy", "roadmap planning", "agile",
            "scrum", "jira", "stakeholder management", "communication",
            "leadership", "kpis", "metrics", "a/b testing", "analytics",
            "python", "sql", "tableau", "user research", "ethics in ai"
        ],
        "weights": {
            "product management": 5, "ai/ml fundamentals": 5,
            "machine learning": 4, "model deployment": 4,
            "roadmap planning": 4, "stakeholder management": 5,
            "communication": 4
        }
    }
}