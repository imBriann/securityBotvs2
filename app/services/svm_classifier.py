"""
Módulo para clasificación de mensajes usando SVM (Support Vector Machine).
Este módulo puede ser usado como alternativa o complemento al análisis con DeepSeek.
"""
from typing import Optional, Tuple
import pickle
import os


class SVMClassifier:
    """
    Clasificador SVM para detectar mensajes de phishing/spam.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Inicializa el clasificador SVM.
        
        Args:
            model_path: Ruta al archivo del modelo entrenado (.pkl)
        """
        self.model = None
        self.vectorizer = None
        self.model_path = model_path or "models/svm_phishing_model.pkl"
        
    def load_model(self) -> bool:
        """
        Carga el modelo SVM pre-entrenado.
        
        Returns:
            True si el modelo se cargó exitosamente, False en caso contrario
        """
        if not os.path.exists(self.model_path):
            print(f"Advertencia: No se encontró el modelo SVM en {self.model_path}")
            return False
            
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.vectorizer = model_data['vectorizer']
            print(f"Modelo SVM cargado exitosamente desde {self.model_path}")
            return True
        except Exception as e:
            print(f"Error al cargar el modelo SVM: {e}")
            return False
    
    def predict(self, text: str) -> Optional[Tuple[str, float]]:
        """
        Predice si un mensaje es phishing/spam.
        
        Args:
            text: Texto del mensaje a clasificar
            
        Returns:
            Tupla (predicción, confianza) donde predicción es "phishing" o "legítimo"
            y confianza es un valor entre 0 y 1. Retorna None si hay error.
        """
        if not self.model or not self.vectorizer:
            print("Error: Modelo SVM no cargado. Llama a load_model() primero.")
            return None
            
        try:
            # Vectorizar el texto
            text_vectorized = self.vectorizer.transform([text])
            
            # Hacer predicción
            prediction = self.model.predict(text_vectorized)[0]
            
            # Obtener probabilidad/confianza
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba(text_vectorized)[0]
                confidence = max(probabilities)
            elif hasattr(self.model, 'decision_function'):
                decision = self.model.decision_function(text_vectorized)[0]
                # Convertir a probabilidad usando función sigmoide
                confidence = 1 / (1 + abs(decision))
            else:
                confidence = 0.5  # Confianza neutral si no hay método disponible
            
            label = "phishing" if prediction == 1 else "legítimo"
            
            return (label, confidence)
            
        except Exception as e:
            print(f"Error en predicción SVM: {e}")
            return None
    
    def analyze_message(self, text: str) -> dict:
        """
        Analiza un mensaje y retorna un diccionario con los resultados.
        
        Args:
            text: Texto del mensaje a analizar
            
        Returns:
            Diccionario con 'is_phishing', 'confidence', 'label' y 'message'
        """
        result = self.predict(text)
        
        if result is None:
            return {
                'is_phishing': None,
                'confidence': 0.0,
                'label': 'error',
                'message': 'Error al analizar el mensaje con SVM'
            }
        
        label, confidence = result
        is_phishing = (label == "phishing")
        
        # Generar mensaje interpretativo
        if confidence > 0.8:
            certainty = "muy seguro"
        elif confidence > 0.6:
            certainty = "bastante seguro"
        elif confidence > 0.4:
            certainty = "moderadamente seguro"
        else:
            certainty = "poco seguro"
        
        message = f"Estoy {certainty} ({confidence:.0%}) de que este mensaje es {label}."
        
        return {
            'is_phishing': is_phishing,
            'confidence': confidence,
            'label': label,
            'message': message
        }


# Instancia global del clasificador
svm_classifier = SVMClassifier()


def initialize_svm(model_path: Optional[str] = None) -> bool:
    """
    Inicializa el clasificador SVM global.
    
    Args:
        model_path: Ruta opcional al modelo
        
    Returns:
        True si se inicializó correctamente
    """
    global svm_classifier
    if model_path:
        svm_classifier = SVMClassifier(model_path)
    return svm_classifier.load_model()


def get_svm_classifier() -> SVMClassifier:
    """
    Obtiene la instancia global del clasificador SVM.
    
    Returns:
        Instancia del clasificador
    """
    return svm_classifier