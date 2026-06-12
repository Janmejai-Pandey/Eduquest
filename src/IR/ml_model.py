import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import joblib  # For saving/loading models
import os

# Download NLTK resources (run once)
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('punkt')

class ResumeClassifier:
    def __init__(self, model_path='resume_classifier_model.pkl', vectorizer_path='tfidf_vectorizer.pkl'):
        self.model_path = model_path
        self.vectorizer_path = vectorizer_path
        self.model = None
        self.vectorizer = None
        self.label_encoder = LabelEncoder()
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))

    def clean_resume(self, text):
        """Clean and preprocess resume text."""
        # Remove URLs
        text = re.sub(r'http\S+|www\S+', '', text)
        # Remove emails
        text = re.sub(r'\S+@\S+', '', text)
        # Remove special chars and numbers
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        # Lowercase
        text = text.lower()
        # Tokenize, remove stopwords, and lemmatize
        tokens = text.split()
        tokens = [self.lemmatizer.lemmatize(word) for word in tokens if word not in self.stop_words]
        return ' '.join(tokens)

    def train(self, df, text_col='cleaned_resume', category_col='Category'):
        """
        Train the classifier on a DataFrame of resumes.

        Args:
            df (pd.DataFrame): DataFrame containing resumes and categories.
            text_col (str): Column name with resume text.
            category_col (str): Column name with job categories.
        """
        print("🔧 Training ML model...")

        # Clean resumes if not already cleaned
        if text_col != 'cleaned_resume':
            df['cleaned_resume'] = df[text_col].apply(self.clean_resume)

        # TF-IDF Vectorization
        self.vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        X = self.vectorizer.fit_transform(df['cleaned_resume'])

        # Encode categories
        y = self.label_encoder.fit_transform(df[category_col])

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Train model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)
        print(f"✅ Model trained! Accuracy: {accuracy_score(y_test, y_pred):.4f}")
        print("\n📊 Classification Report:")
        print(classification_report(y_test, y_pred, target_names=self.label_encoder.classes_))

        # Save model and vectorizer
        self.save_model()

    def save_model(self):
        """Save the trained model and vectorizer to disk."""
        if self.model and self.vectorizer:
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
            print(f"💾 Model saved to {self.model_path}")
            print(f"💾 Vectorizer saved to {self.vectorizer_path}")

    def load_model(self):
        """Load a pre-trained model and vectorizer from disk."""
        if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
            self.model = joblib.load(self.model_path)
            self.vectorizer = joblib.load(self.vectorizer_path)
            print(f"🔄 Model loaded from {self.model_path}")
            return True
        else:
            print("⚠️ No saved model found. Train a model first.")
            return False

    def predict_category(self, resume_text):
        """Predict the most likely job category for a resume."""
        if not self.model or not self.vectorizer:
            if not self.load_model():
                raise ValueError("Model not trained or loaded.")

        cleaned = self.clean_resume(resume_text)
        vectorized = self.vectorizer.transform([cleaned])
        prediction = self.model.predict(vectorized)[0]
        return self.label_encoder.inverse_transform([prediction])[0]

    def predict_category_probabilities(self, resume_text):
        """Get probability scores for all job categories."""
        if not self.model or not self.vectorizer:
            if not self.load_model():
                raise ValueError("Model not trained or loaded.")

        cleaned = self.clean_resume(resume_text)
        vectorized = self.vectorizer.transform([cleaned])
        probabilities = self.model.predict_proba(vectorized)[0]

        # Create a sorted list of (category, probability) tuples
        category_scores = {
            self.label_encoder.classes_[idx]: round(prob * 100, 2)
            for idx, prob in enumerate(probabilities)
        }
        return sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
    
#code for main 

#     from ml_model import ResumeClassifier
# import pandas as pd

# # Load your dataset
# df = pd.read_csv('resumes.csv')  # Adjust filename

# # Initialize and train the classifier
# classifier = ResumeClassifier()
# classifier.train(df, text_col='Resume_str', category_col='Category')  # Adjust column names